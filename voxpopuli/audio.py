# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Daniele Deplano (RedRider21)
"""Dispositivi audio di sistema: elenco e cattura.

Si appoggia agli strumenti PulseAudio/PipeWire (`pactl`, `parec`) invece che a
una libreria di binding: sono sempre presenti sulle distribuzioni desktop,
evitano una dipendenza compilata e, soprattutto, `parec` consegna gia' PCM a
16 kHz mono, che e' il formato nativo di Whisper.

Il parsing e' testuale perche' `pactl -f json` produce JSON non valido quando
le descrizioni contengono caratteri accentati (verificato su PulseAudio 15.99).
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass

from . import config as C

# Le etichette di `pactl list` sono localizzate: su questo sistema e' in
# italiano, ma il codice deve funzionare anche con locale inglese.
_CAMPI_NOME = ("Nome:", "Name:")
_CAMPI_DESCRIZIONE = ("Descrizione:", "Description:")
_CAMPI_STATO = ("Stato:", "State:")
_CAMPI_MONITOR = ("Monitor della sorgente:", "Monitor Source:")
_CAMPI_PORTA = ("Porta attiva:", "Active Port:")


class AudioError(RuntimeError):
    """Errore nell'interazione con il server audio."""


@dataclass(frozen=True)
class Sorgente:
    """Una sorgente audio: microfono oppure monitor di un'uscita."""

    nome: str
    descrizione: str
    monitor: bool
    stato: str = ""

    @property
    def etichetta(self) -> str:
        """Testo da mostrare nei menu a tendina."""
        if self.monitor:
            # Il nome del monitor e' "<sink>.monitor": ricavo l'uscita a cui
            # corrisponde per rendere comprensibile la voce di menu.
            uscita = self.nome[: -len(".monitor")]
            uscita = uscita.rsplit(".", 1)[-1]
            return f"Audio di sistema ({uscita}) - sente l'interlocutore"
        return f"{self.descrizione} - microfono"

    @property
    def etichetta_breve(self) -> str:
        return self.descrizione or self.nome


def strumenti_disponibili() -> list[str]:
    """Restituisce l'elenco degli strumenti mancanti (vuoto se tutto ok)."""
    return [nome for nome in ("pactl", "parec") if shutil.which(nome) is None]


def _campo(righe: list[str], etichette: tuple[str, ...]) -> str:
    for riga in righe:
        for etichetta in etichette:
            if riga.startswith(etichetta):
                return riga[len(etichetta) :].strip()
    return ""


def elenca_sorgenti() -> list[Sorgente]:
    """Elenca microfoni e monitor disponibili, nell'ordine riportato dal sistema."""
    mancanti = strumenti_disponibili()
    if mancanti:
        raise AudioError(
            "Strumenti audio mancanti: " + ", ".join(mancanti)
            + ". Installa con: sudo apt install pulseaudio-utils"
        )

    try:
        esito = subprocess.run(
            ["pactl", "list", "sources"],
            capture_output=True, text=True, timeout=10, check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise AudioError(f"pactl ha fallito: {exc.stderr.strip()}") from exc
    except subprocess.TimeoutExpired as exc:
        raise AudioError("pactl non ha risposto entro 10 secondi") from exc

    sorgenti: list[Sorgente] = []
    blocco: list[str] = []

    def chiudi() -> None:
        if not blocco:
            return
        nome = _campo(blocco, _CAMPI_NOME)
        if not nome:
            return
        # Un monitor e' riconoscibile dal suffisso del nome; il campo
        # "Monitor della sorgente" e' popolato solo sulle sorgenti normali.
        monitor = nome.endswith(".monitor")
        sorgenti.append(
            Sorgente(
                nome=nome,
                descrizione=_campo(blocco, _CAMPI_DESCRIZIONE) or nome,
                monitor=monitor,
                stato=_campo(blocco, _CAMPI_STATO),
            )
        )

    for riga in esito.stdout.splitlines():
        if riga.startswith("Sorgente #") or riga.startswith("Source #"):
            chiudi()
            blocco = []
            continue
        blocco.append(riga.strip())
    chiudi()

    return sorgenti


def sorgenti_monitor(sorgenti: list[Sorgente] | None = None) -> list[Sorgente]:
    """Solo i monitor: da qui arriva la voce dell'interlocutore."""
    return [s for s in (sorgenti or elenca_sorgenti()) if s.monitor]


def sorgenti_microfono(sorgenti: list[Sorgente] | None = None) -> list[Sorgente]:
    """Solo i microfoni veri e propri."""
    return [s for s in (sorgenti or elenca_sorgenti()) if not s.monitor]


def monitor_predefinito() -> Sorgente | None:
    """Monitor dell'uscita predefinita: il caso d'uso normale."""
    try:
        esito = subprocess.run(
            ["pactl", "get-default-sink"],
            capture_output=True, text=True, timeout=5, check=True,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return None
    sink = esito.stdout.strip()
    if not sink:
        return None
    atteso = f"{sink}.monitor"
    for sorgente in elenca_sorgenti():
        if sorgente.nome == atteso:
            return sorgente
    return None


def microfono_predefinito() -> Sorgente | None:
    """Sorgente di ingresso contrassegnata come predefinita dal sistema."""
    try:
        esito = subprocess.run(
            ["pactl", "get-default-source"],
            capture_output=True, text=True, timeout=5, check=True,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return None
    nome = esito.stdout.strip()
    for sorgente in elenca_sorgenti():
        if sorgente.nome == nome:
            return sorgente
    return None


def nome_dispositivo_parec(nome_sorgente: str) -> str:
    """`parec` accetta il nome PulseAudio direttamente."""
    return nome_sorgente


class CatturaAudio:
    """Legge PCM da una sorgente tramite `parec`, in modo bloccante.

    Va usata da un thread dedicato: `leggi` resta in attesa finche' non arriva
    audio o finche' il processo non viene chiuso. E' un contesto manager.
    """

    def __init__(
        self,
        nome_sorgente: str,
        sample_rate: int = C.SAMPLE_RATE,
        frame_ms: int = C.FRAME_MS,
    ) -> None:
        self.nome_sorgente = nome_sorgente
        self.sample_rate = sample_rate
        self.frame_bytes = sample_rate * frame_ms // 1000 * C.SAMPLE_WIDTH
        self._proc: subprocess.Popen | None = None

    def avvia(self) -> None:
        if self._proc is not None:
            return
        comando = [
            "parec",
            f"--device={self.nome_sorgente}",
            f"--rate={self.sample_rate}",
            "--channels=1",
            "--format=s16le",
            "--raw",
        ]
        try:
            self._proc = subprocess.Popen(
                comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
        except OSError as exc:
            raise AudioError(f"Impossibile avviare parec: {exc}") from exc

        # `parec` puo' partire e morire subito (dispositivo inesistente,
        # server audio assente): senza questo controllo il guasto si
        # manifesterebbe solo come silenzio, molto piu' difficile da capire.
        if self._proc.poll() is not None:
            errore = self._proc.stderr.read().decode(errors="replace").strip()
            self._proc = None
            raise AudioError(
                f"parec non ha potuto aprire '{self.nome_sorgente}': "
                f"{errore or 'errore sconosciuto'}"
            )

    def leggi(self) -> bytes:
        """Legge un frame di PCM. Restituisce b'' a flusso terminato."""
        if self._proc is None or self._proc.stdout is None:
            return b""
        try:
            return self._proc.stdout.read(self.frame_bytes)
        except (OSError, ValueError):
            return b""

    def chiudi(self) -> None:
        if self._proc is None:
            return
        proc, self._proc = self._proc, None
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        except OSError:
            pass
        for flusso in (proc.stdout, proc.stderr):
            try:
                if flusso is not None:
                    flusso.close()
            except OSError:
                pass

    def __enter__(self) -> "CatturaAudio":
        self.avvia()
        return self

    def __exit__(self, *_exc) -> None:
        self.chiudi()


def pulisci_nome(nome: str) -> str:
    """Riduce un nome di sorgente a qualcosa di leggibile nei log."""
    return re.sub(r"^alsa_(output|input)\.", "", nome)[:60]
