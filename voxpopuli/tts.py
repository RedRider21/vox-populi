# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Daniele Deplano (RedRider21)
"""Voce sintetica inglese, riprodotta nel microfono virtuale.

Due passaggi separati: `edge_tts` produce un mp3 con la voce neurale scelta,
poi `ffmpeg` lo decodifica in audio grezzo che `paplay` riversa nel sink
virtuale, quello che Meet vede come microfono.

Il thread della voce e' distinto da quello dell'inferenza di proposito: la
sintesi richiede qualche decimo di secondo e la riproduzione qualche secondo,
e farla aspettare al worker della trascrizione significherebbe accumulare
ritardo su tutte le frasi successive.

La riproduzione e' anche il momento in cui il passaggio della voce reale viene
chiuso: si apre il ducking all'inizio della frase e lo si chiude quando l'audio
e' finito. Se qualcosa va storto, il `finally` lo riapre comunque.
"""

from __future__ import annotations

import asyncio
import queue
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

# Voci neurali indiane: la prima maschile, la seconda femminile. Entrambe
# rendono l'inglese con l'accento di Mumbai, che e' quello che l'interlocutore
# si aspetta di sentire.
VOCI = {
    "en-IN-PrabhatNeural": "maschile, accento indiano",
    "en-IN-NeerjaNeural": "femminile, accento indiano",
    "en-IN-NeerjaExpressiveNeural": "femminile, piu' espressiva",
    "en-GB-RyanNeural": "maschile britannico",
    "en-US-GuyNeural": "maschile americano",
}
VOCE_PREDEFINITA = "en-IN-PrabhatNeural"

# La coda e' corta: se la voce non tiene il passo si scarta, perche' sentire la
# traduzione di tre frasi fa mentre l'altro ha gia' cambiato discorso e' peggio
# che non sentirne nessuna.
MAX_IN_CODA = 2

FREQUENZA_HZ = 24000


class TtsError(RuntimeError):
    """Errore nella sintesi o nella riproduzione della voce."""


def _sintetizza(testo: str, voce: str) -> bytes:
    """Genera l'mp3 della frase con edge-tts. Bloccante."""
    try:
        import edge_tts
    except ImportError as exc:
        raise TtsError("edge-tts non installato: esegui ./install.sh") from exc

    if shutil.which("ffmpeg") is None:
        raise TtsError("ffmpeg non trovato: serve per riprodurre la voce")

    async def genera() -> bytes:
        comunica = edge_tts.Communicate(testo, voce)
        pezzi: list[bytes] = []
        async for evento in comunica.stream():
            if evento["type"] == "audio":
                pezzi.append(evento["data"])
        return b"".join(pezzi)

    try:
        dati = asyncio.run(genera())
    except Exception as exc:                  # noqa: BLE001 - rete o voce inesistente
        raise TtsError(f"sintesi non riuscita: {exc}") from exc
    if not dati:
        raise TtsError("la sintesi non ha prodotto audio")
    return dati


def _riproduci(dati_mp3: bytes, sink: str, processo: list[subprocess.Popen]) -> None:
    """Decodifica e riversa l'audio nel sink virtuale. Bloccante.

    Il processo `paplay` viene registrato nella lista passata dal chiamante,
    cosi' un arresto improvviso puo' terminarlo invece di lasciarlo suonare.
    """
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp.write(dati_mp3)
        percorso = Path(tmp.name)
    try:
        decodifica = subprocess.Popen(
            [
                "ffmpeg", "-loglevel", "error", "-i", str(percorso),
                "-f", "s16le", "-ar", str(FREQUENZA_HZ), "-ac", "1", "-",
            ],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        riproduzione = subprocess.Popen(
            [
                "paplay", f"--device={sink}", "--raw",
                "--format=s16le", f"--rate={FREQUENZA_HZ}", "--channels=1",
            ],
            stdin=decodifica.stdout, stderr=subprocess.DEVNULL,
        )
        processo.append(riproduzione)
        if decodifica.stdout is not None:
            decodifica.stdout.close()          # il figlio ha la sua copia
        try:
            riproduzione.wait(timeout=30)
        except subprocess.TimeoutExpired:
            riproduzione.kill()
        finally:
            if riproduzione in processo:
                processo.remove(riproduzione)
        decodifica.wait(timeout=5)
    finally:
        percorso.unlink(missing_ok=True)


class Voce:
    """Coda della voce sintetica, con un thread che la consuma.

    `ducka` e' una funzione chiamata con True all'inizio di ogni frase e con
    False alla fine: serve a chiudere il passaggio del microfono reale mentre
    parla la voce inglese. `ducka_a_tempo` e' invece la rete di sicurezza che
    riapre il passaggio se una frase non arriva mai. Se non vengono fornite, la
    voce si limita a suonare.
    """

    def __init__(
        self,
        sink: str,
        voce: str = VOCE_PREDEFINITA,
        ducka=None,
        ducka_a_tempo=None,
    ) -> None:
        self.sink = sink
        self.voce = voce
        self.ducka = ducka
        self.ducka_a_tempo = ducka_a_tempo
        self._coda: queue.Queue[str] = queue.Queue(maxsize=MAX_IN_CODA)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._processi: list[subprocess.Popen] = []
        self._lock = threading.Lock()
        self.ultimo_errore = ""
        self.attiva = False

    # ------------------------------------------------------- ciclo di vita ----
    def avvia(self) -> None:
        if self._thread is not None:
            return
        self._stop.clear()
        self.attiva = True
        self._thread = threading.Thread(target=self._ciclo, name="voce", daemon=True)
        self._thread.start()

    def ferma(self) -> None:
        self._stop.set()
        if self.ducka is not None:
            self.ducka(False)                   # mai lasciare il mic chiuso
        with self._lock:
            for processo in list(self._processi):
                try:
                    processo.terminate()
                except Exception:               # noqa: BLE001 - solo pulizia
                    pass
        if self._thread is not None:
            self._thread.join(timeout=3)
            self._thread = None
        self.attiva = False

    def __enter__(self) -> "Voce":
        self.avvia()
        return self

    def __exit__(self, *_exc) -> None:
        self.ferma()

    # ------------------------------------------------------------------ uso ----
    def di(self, testo: str) -> None:
        """Mette in coda una frase da pronunciare, scartando la piu' vecchia."""
        if not testo.strip() or self._thread is None:
            return
        try:
            self._coda.put_nowait(testo)
        except queue.Full:
            try:
                self._coda.get_nowait()
            except queue.Empty:
                pass
            try:
                self._coda.put_nowait(testo)
            except queue.Full:
                pass

    def prova(self, testo: str = "Hello, this is a test of the synthetic voice.") -> None:
        """Pronuncia una frase subito, senza passare dalla coda. Per il collaudo."""
        self._pronuncia(testo)

    # -------------------------------------------------------------- interno ----
    def _ciclo(self) -> None:
        while not self._stop.is_set():
            try:
                testo = self._coda.get(timeout=0.3)
            except queue.Empty:
                # Nessuna frase in attesa: e' il momento buono per accorgersi
                # che il microfono e' rimasto chiuso troppo a lungo.
                if self.ducka_a_tempo is not None:
                    self.ducka_a_tempo()
                continue
            self._pronuncia(testo)

    def _pronuncia(self, testo: str) -> None:
        try:
            audio = _sintetizza(testo, self.voce)
        except TtsError as exc:
            self.ultimo_errore = str(exc)
            print(f"[voce] {exc}")
            return
        if self.ducka is not None:
            self.ducka(True)
        try:
            _riproduci(audio, self.sink, self._processi)
        except Exception as exc:                # noqa: BLE001 - la voce non deve fermare nulla
            self.ultimo_errore = f"riproduzione non riuscita: {exc}"
            print(f"[voce] {self.ultimo_errore}")
        finally:
            # Sempre, anche se paplay e' morto a meta': un microfono che resta
            # chiuso e' molto peggio di una voce mancata.
            if self.ducka is not None:
                self.ducka(False)


def voci_disponibili() -> dict[str, str]:
    """Elenco delle voci selezionabili, per l'interfaccia."""
    return dict(VOCI)
