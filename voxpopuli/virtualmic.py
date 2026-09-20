# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Daniele Deplano (RedRider21)
"""Microfono virtuale: fa credere a Chrome che la voce sintetica sia il microfono.

Il problema: Meet prende l'audio da un solo ingresso. Se l'app riproducesse la
voce sintetica dalle casse, l'interlocutore non la sentirebbe (le casse suonano
verso di noi, non verso Internet). Serve un ingresso finto in cui far confluire
la voce inglese.

La soluzione usa due moduli di PulseAudio:

    microfono reale --(module-loopback)--> [ sink vox_populi_mic ] --> Meet

dove `sink vox_populi_mic` e' un `module-null-sink`, un'uscita audio che non
esiste fisicamente. Chrome la vede come ingresso sotto il nome
"Monitor of VoxPopuli Mic", e va scelta una volta sola nel menu di Meet.

Il canale e' lo stesso per entrambe le voci, quindi non possono coesistere:
quando l'app deve pronunciare la frase inglese, il passaggio della voce reale
viene chiuso (`ducka`) per non far arrivare all'interlocutore l'italiano
seguito dall'inglese. Il silenzio dura dall'inizio del parlato fino alla fine
della voce sintetica, ed e' il prezzo del doppiaggio.

Tutto viene smontato all'uscita: i moduli caricati a mano restano nel sistema
finche' qualcuno non li scarica, e un'applicazione che muore lasciandoli dietro
di se' lascia il microfono del computer in uno stato strano.
"""

from __future__ import annotations

import atexit
import re
import subprocess
import threading
import time

NOME_SINK = "vox_populi_mic"
# La descrizione non puo' contenere spazi: PulseAudio risegmenta gli argomenti
# dei moduli sugli spazi, quindi "VoxPopuli Mic" diventerebbe due parametri e il
# modulo fallirebbe con "Inizializzazione del modulo non riuscita". Verificato.
ETICHETTA_SINK = "VoxPopuli_Mic"
SORGENTE_PER_MEET = f"{NOME_SINK}.monitor"

# Oltre questo tempo senza che arrivi una traduzione, il passaggio della voce
# reale viene riaperto: meglio un doppione che un microfono muto.
TIMEOUT_DUCKING = 12.0


class VirtualMicError(RuntimeError):
    """Errore nel caricamento o nella gestione dei moduli PulseAudio."""


def _pactl(*argomenti: str, timeout: float = 5.0) -> str:
    """Esegue pactl e restituisce stdout, sollevando su errore."""
    try:
        esito = subprocess.run(
            ["pactl", *argomenti],
            capture_output=True, text=True, timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise VirtualMicError(f"pactl non eseguibile: {exc}") from exc
    if esito.returncode != 0:
        raise VirtualMicError(
            esito.stderr.strip() or f"pactl {' '.join(argomenti)} e' fallito"
        )
    return esito.stdout


def _carica_modulo(*argomenti: str) -> int:
    """Carica un modulo e restituisce il suo indice."""
    uscita = _pactl("load-module", *argomenti).strip()
    try:
        return int(uscita)
    except ValueError as exc:
        raise VirtualMicError(f"risposta inattesa da pactl: {uscita!r}") from exc


def _indice_modulo(nome: str) -> int | None:
    """Cerca un modulo gia' caricato per nome, per non duplicarlo."""
    try:
        uscita = _pactl("list", "modules", "short")
    except VirtualMicError:
        return None
    for riga in uscita.splitlines():
        campi = riga.split("\t")
        if len(campi) >= 2 and campi[1] == nome:
            try:
                return int(campi[0])
            except ValueError:
                continue
    return None


def _scarica_modulo(indice: int | None) -> None:
    """Scarica un modulo, ignorando l'errore se non c'e' piu'."""
    if indice is None:
        return
    try:
        _pactl("unload-module", str(indice))
    except VirtualMicError:
        pass


class MicrofonoVirtuale:
    """Crea il sink virtuale e vi dirotta il microfono reale.

    Va usato come contesto manager: all'uscita i moduli vengono scaricati, e
    con loro sparisce il finto microfono dal pannello di Meet (che torna a
    mostrare il microfono vero).
    """

    def __init__(self, microfono_reale: str) -> None:
        self.microfono_reale = microfono_reale
        self._modulo_sink: int | None = None
        self._modulo_loopback: int | None = None
        self._indice_loopback: int | None = None      # sink-input del loopback
        self._muto = False
        self._scadenza_ducking: float = 0.0
        self._lock = threading.Lock()
        self._attivo = False
        atexit.register(self.chiudi)

    # ------------------------------------------------------- ciclo di vita ----
    def attiva(self) -> str:
        """Crea sink e loopback. Restituisce il nome da scegliere in Meet."""
        if self._attivo:
            return SORGENTE_PER_MEET

        # Se un'esecuzione precedente e' morta male, i moduli sono ancora li':
        # li riuso invece di accumularne di nuovi.
        self._modulo_sink = _indice_modulo("module-null-sink")
        if self._modulo_sink is None:
            self._modulo_sink = _carica_modulo(
                "module-null-sink",
                f"sink_name={NOME_SINK}",
                f"sink_properties=device.description={ETICHETTA_SINK}",
            )

        self._modulo_loopback = _indice_modulo("module-loopback")
        if self._modulo_loopback is None:
            self._modulo_loopback = _carica_modulo(
                "module-loopback",
                f"source={self.microfono_reale}",
                f"sink={NOME_SINK}",
                "latency_msec=20",
            )

        self._attivo = True
        # Il sink-input del loopback compare con un attimo di ritardo rispetto
        # al caricamento del modulo: si insiste un momento invece di rassegnarsi
        # a un indice mancante, che al primo ducking costerebbe una frase.
        for _ in range(10):
            self._indice_loopback = self._trova_loopback()
            if self._indice_loopback is not None:
                break
            time.sleep(0.1)
        return SORGENTE_PER_MEET

    def chiudi(self) -> None:
        """Smonta tutto. Sicura da chiamare piu' volte e da atexit."""
        with self._lock:
            if not self._attivo:
                return
            self._attivo = False
            _scarica_modulo(self._modulo_loopback)
            _scarica_modulo(self._modulo_sink)
            self._modulo_loopback = None
            self._modulo_sink = None
            self._indice_loopback = None
            self._muto = False

    def __enter__(self) -> "MicrofonoVirtuale":
        self.attiva()
        return self

    def __exit__(self, *_exc) -> None:
        self.chiudi()

    # -------------------------------------------------------------- ducking ----
    def ducka(self, attivo: bool) -> None:
        """Chiude o riapre il passaggio della voce reale verso l'interlocutore.

        L'indice del sink-input puo' cambiare se qualcosa ricarica il loopback:
        se non lo trovo lo cerco di nuovo, e se ancora non c'e' non sollevo -
        il doppiaggio e' un di piu', non deve far cadere la conversazione.
        """
        with self._lock:
            if not self._attivo or attivo == self._muto:
                return
            if self._indice_loopback is None:
                self._indice_loopback = self._trova_loopback()
            if self._indice_loopback is None:
                return
            try:
                _pactl(
                    "set-sink-input-mute", str(self._indice_loopback),
                    "1" if attivo else "0",
                )
            except VirtualMicError:
                return
            self._muto = attivo
            if attivo:
                self._scadenza_ducking = time.monotonic() + TIMEOUT_DUCKING

    def ducka_a_tempo(self) -> None:
        """Riapre il passaggio se il ducking sta durando troppo.

        Chiamata periodicamente dal thread della voce: protegge dal caso in cui
        una frase venga scartata e nessuno riapra piu' il microfono.
        """
        indice = None
        with self._lock:
            if self._muto and time.monotonic() > self._scadenza_ducking:
                self._muto = False                 # per non rientrare subito
                indice = self._indice_loopback
        if indice is not None:
            try:
                _pactl("set-sink-input-mute", str(indice), "0")
            except VirtualMicError:
                pass

    def _trova_loopback(self) -> int | None:
        """Trova il sink-input creato dal nostro loopback.

        Si cerca per modulo proprietario: e' l'unico campo che lega il
        sink-input al modulo che abbiamo caricato noi, e resta valido anche se
        nel frattempo cambiano gli indici dei sink.

        Le etichette di pactl seguono la lingua del sistema: su questa macchina
        sono italiane ("Sink d'ingresso", "Modulo di appartenenza"), quindi
        vanno riconosciute entrambe le forme. Cercare solo quelle inglesi
        faceva fallire la ricerca in silenzio, e il ducking non funzionava.
        """
        if self._modulo_loopback is None:
            return None
        try:
            uscita = _pactl("list", "sink-inputs")
        except VirtualMicError:
            return None
        indice_corrente: int | None = None
        for riga in uscita.splitlines():
            riga = riga.strip()
            incontro = re.match(r"(?:Sink Input|Sink d'ingresso) #(\d+)", riga)
            if incontro:
                indice_corrente = int(incontro.group(1))
                continue
            if riga.startswith(("Owner Module:", "Modulo di appartenenza:")):
                valore = riga.split(":", 1)[1].strip()
                if valore.isdigit() and int(valore) == self._modulo_loopback:
                    return indice_corrente
        return None


def stato_microfono_virtuale() -> dict:
    """Fotografia dei moduli attivi, per la diagnosi da terminale."""
    return {
        "sink": _indice_modulo("module-null-sink"),
        "loopback": _indice_modulo("module-loopback"),
        "sorgente_per_meet": SORGENTE_PER_MEET,
    }
