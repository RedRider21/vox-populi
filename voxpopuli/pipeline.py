# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Daniele Deplano (RedRider21)
"""Orchestrazione: due flussi audio, una sola catena di inferenza.

Due thread leggono l'audio (voce dell'interlocutore e voce dell'utente) e
segmentano le frasi con il VAD; un terzo thread le trascrive e le traduce,
consegnando i risultati a una callback.

La coda e' unica e corta di proposito: l'inferenza e' gia' serializzata dai
lock di `stt` e `mt`, e una coda lunga trasformerebbe un ritardo momentaneo in
un ritardo permanente, mostrando sottotitoli sempre piu' vecchi. Quando e'
piena si scarta il segmento piu' vecchio, cosi' il testo a schermo resta
aderente a cio' che si sta dicendo adesso.

L'eco con gli altoparlanti si contrasta con l'half-duplex: finche' parla
l'interlocutore, i segmenti del microfono vengono scartati. Funziona perche'
la voce dell'utente non viene mai riprodotta dalle casse.
"""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

from . import audio as A
from . import config as C
from . import mt, stt
from .vad import VadSegmenter, pcm16_a_float

# Oltre questa distanza dal parlato remoto il mic torna ad essere trascritto.
FINESTRA_HALF_DUPLEX = 0.8


@dataclass
class Risultato:
    """Una frase tradotta, pronta per essere mostrata."""

    flusso: str                 # "remoto" (lui) oppure "locale" (tu)
    originale: str
    traduzione: str
    lingua_orig: str
    lingua_trad: str
    t_stt: float = 0.0
    t_mt: float = 0.0
    durata_audio: float = 0.0
    istante: float = field(default_factory=time.time)

    @property
    def latenza(self) -> float:
        """Secondi spesi dopo la fine della frase (solo inferenza)."""
        return self.t_stt + self.t_mt


@dataclass
class Stato:
    """Fotografia del sistema, per la barra di stato della UI."""

    attivo: bool = False
    sorgente_remota: str = ""
    sorgente_mic: str = ""
    ultima_latenza: float = 0.0
    media_latenza: float = 0.0
    frasi: int = 0
    errore: str = ""


class Motore:
    """Coordina cattura, trascrizione e traduzione."""

    def __init__(
        self,
        sorgente_remota: str,
        sorgente_mic: str,
        on_risultato: Callable[[Risultato], None],
        on_stato: Callable[[Stato], None] | None = None,
        half_duplex: bool = True,
        modello: str | None = None,
        prompt: str | None = None,
        on_parlato_locale: Callable[[], None] | None = None,
        lingua_mia: str = C.LANG_IT,
        lingua_sua: str = C.LANG_EN,
    ) -> None:
        # Le due lingue della conversazione. Da queste dipendono tutte e
        # quattro le direzioni: trascrivo nella lingua di chi parla, traduco
        # verso quella di chi ascolta.
        self.lingua_mia = lingua_mia
        self.lingua_sua = lingua_sua
        self.sorgente_remota = sorgente_remota
        self.sorgente_mic = sorgente_mic
        self.on_risultato = on_risultato
        self.on_stato = on_stato
        self.half_duplex = half_duplex
        self.modello = modello or C.WHISPER_MODEL
        self.prompt = prompt
        # Chiamata quando l'utente comincia a parlare: serve alla voce sintetica
        # per chiudere subito il passaggio del microfono, invece di aspettare
        # che la traduzione sia pronta e lasciar passare nel frattempo l'italiano.
        self.on_parlato_locale = on_parlato_locale

        self.stato = Stato(
            sorgente_remota=sorgente_remota, sorgente_mic=sorgente_mic,
        )
        self._coda: queue.Queue[tuple[str, object, float]] = queue.Queue(maxsize=4)
        self._stop = threading.Event()
        self._thread: list[threading.Thread] = []
        self._vad_remoto = VadSegmenter()
        self._ultimo_parlato_remoto = 0.0
        self._lock_stato = threading.Lock()

    # ------------------------------------------------------------- ciclo di vita ----
    def avvia(self) -> None:
        """Carica i modelli (bloccante) e fa partire i thread."""
        if self.stato.attivo:
            return
        t_stt = stt.prepara(self.modello)
        t_mt = mt.prepara(self.lingua_mia, self.lingua_sua)
        print(f"[motore] modelli pronti (whisper {t_stt:.1f}s, traduzione {t_mt:.1f}s)")

        self._stop.clear()
        self._thread = [
            threading.Thread(
                target=self._cattura, name="cattura-remoto",
                args=("remoto", self.sorgente_remota), daemon=True,
            ),
            threading.Thread(
                target=self._cattura, name="cattura-locale",
                args=("locale", self.sorgente_mic), daemon=True,
            ),
            threading.Thread(target=self._lavora, name="inferenza", daemon=True),
        ]
        for t in self._thread:
            t.start()
        self._aggiorna(attivo=True, errore="")
        print(f"[motore] in ascolto\n  interlocutore <- {A.pulisci_nome(self.sorgente_remota)}\n  microfono     <- {A.pulisci_nome(self.sorgente_mic)}")

    def ferma(self) -> None:
        """Ferma i thread e chiude le catture."""
        if not self.stato.attivo:
            return
        self._stop.set()
        for t in self._thread:
            t.join(timeout=3)
        self._thread = []
        self._aggiorna(attivo=False)

    def __enter__(self) -> "Motore":
        self.avvia()
        return self

    def __exit__(self, *_exc) -> None:
        self.ferma()

    # ---------------------------------------------------------------- interno ----
    def _aggiorna(self, **campi) -> None:
        with self._lock_stato:
            for chiave, valore in campi.items():
                setattr(self.stato, chiave, valore)
        if self.on_stato is not None:
            try:
                self.on_stato(self.stato)
            except Exception as exc:              # noqa: BLE001 - la UI non deve fermare il motore
                print(f"[motore] callback di stato fallita: {exc}")

    def _cattura(self, flusso: str, sorgente: str) -> None:
        """Legge una sorgente e mette in coda i segmenti di parlato."""
        vad = VadSegmenter() if flusso == "locale" else self._vad_remoto
        # Il VAD resta "attivo" per tutta la durata della frase: la callback va
        # invocata solo sul fronte di salita, non a ogni frame.
        era_attivo = False
        try:
            with A.CatturaAudio(sorgente) as cattura:
                while not self._stop.is_set():
                    dati = cattura.leggi()
                    if not dati:
                        if self._stop.is_set():
                            break
                        # Flusso interrotto (dispositivo scollegato): non e' un
                        # errore fatale, ma va segnalato perche' l'utente lo veda.
                        self._aggiorna(errore=f"Cattura interrotta su '{A.pulisci_nome(sorgente)}'")
                        time.sleep(0.5)
                        break
                    for segmento in vad.feed(pcm16_a_float(dati)):
                        self._accoda(flusso, segmento)
                    if vad.attivo and not era_attivo:
                        if flusso == "remoto":
                            self._ultimo_parlato_remoto = time.monotonic()
                        elif self.on_parlato_locale is not None:
                            try:
                                self.on_parlato_locale()
                            except Exception as exc:      # noqa: BLE001 - la cattura non si ferma
                                print(f"[motore] callback di parlato fallita: {exc}")
                    elif vad.attivo and flusso == "remoto":
                        self._ultimo_parlato_remoto = time.monotonic()
                    era_attivo = vad.attivo
        except A.AudioError as exc:
            self._aggiorna(errore=str(exc))
            print(f"[motore] {exc}")

    def _accoda(self, flusso: str, segmento) -> None:
        if self._stop.is_set():
            return
        if flusso == "locale" and self.half_duplex:
            # Mentre l'interlocutore parla, il microfono sente le casse:
            # trascriverlo produrrebbe frasi fantasma.
            if time.monotonic() - self._ultimo_parlato_remoto < FINESTRA_HALF_DUPLEX:
                return
        elemento = (flusso, segmento, time.monotonic())
        try:
            self._coda.put_nowait(elemento)
        except queue.Full:
            # Scarta il piu' vecchio: meglio perdere una frase che accumulare
            # ritardo e mostrare sottotitoli sempre piu' indietro.
            try:
                scartato = self._coda.get_nowait()
                print(f"[motore] coda piena, scartato un segmento ({scartato[0]})")
            except queue.Empty:
                pass
            try:
                self._coda.put_nowait(elemento)
            except queue.Full:
                pass

    def _lavora(self) -> None:
        """Trascrive e traduce i segmenti, uno alla volta."""
        while not self._stop.is_set():
            try:
                flusso, segmento, istante = self._coda.get(timeout=0.3)
            except queue.Empty:
                continue

            # Lui parla la sua lingua e va reso nella mia; io il contrario.
            da, a = (
                (self.lingua_sua, self.lingua_mia) if flusso == "remoto"
                else (self.lingua_mia, self.lingua_sua)
            )
            durata = segmento.size / C.SAMPLE_RATE
            try:
                originale, t_stt = stt.trascrivi(
                    segmento, da, size=self.modello, prompt=self.prompt,
                )
                if not originale:
                    continue
                traduzione, t_mt = mt.traduci(originale, da, a)
            except (stt.SttError, mt.MtError) as exc:
                self._aggiorna(errore=str(exc))
                print(f"[motore] {exc}")
                continue
            except Exception as exc:              # noqa: BLE001 - il worker non deve morire
                self._aggiorna(errore=f"Errore imprevisto: {exc}")
                print(f"[motore] errore imprevisto: {exc}")
                continue

            risultato = Risultato(
                flusso=flusso, originale=originale, traduzione=traduzione,
                lingua_orig=da, lingua_trad=a, t_stt=t_stt, t_mt=t_mt,
                durata_audio=durata,
            )
            self._registra_latenza(risultato, istante)
            try:
                self.on_risultato(risultato)
            except Exception as exc:              # noqa: BLE001 - idem
                print(f"[motore] callback di risultato fallita: {exc}")

    def _registra_latenza(self, risultato: Risultato, istante_coda: float) -> None:
        """Aggiorna le statistiche mostrate nella barra di stato."""
        with self._lock_stato:
            frasi = self.stato.frasi + 1
            latenza = risultato.latenza
            # Media incrementale: evita di tenere la storia completa.
            media = (
                self.stato.media_latenza + (latenza - self.stato.media_latenza) / frasi
                if frasi > 1 else latenza
            )
            self.stato.frasi = frasi
            self.stato.ultima_latenza = latenza
            self.stato.media_latenza = media
        if self.on_stato is not None:
            try:
                self.on_stato(self.stato)
            except Exception:                     # noqa: BLE001 - idem
                pass


def descrivi(risultato: Risultato) -> str:
    """Riga di log leggibile, usata dal CLI e dai test."""
    chi = "LUI " if risultato.flusso == "remoto" else "TU  "
    return (
        f"{chi} | {risultato.originale}\n"
        f"     -> {risultato.traduzione}\n"
        f"     [{risultato.t_stt:.2f}s stt + {risultato.t_mt:.2f}s mt"
        f" = {risultato.latenza:.2f}s, audio {risultato.durata_audio:.1f}s]"
    )
