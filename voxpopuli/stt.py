# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Daniele Deplano (RedRider21)
"""Trascrizione: da campioni audio a testo, con faster-whisper.

Un solo modello multilingue serve entrambe le direzioni: la lingua viene
indicata a ogni chiamata, cosi' si evita di tenere due modelli in memoria
(il `small` multilingue occupa gia' ~500 MB) e si salta il rilevamento
automatico della lingua, che costerebbe tempo a ogni frase.

I parametri sono scelti per la latenza, non per la qualita' massima: le frasi
sono brevi e il contesto e' una conversazione, quindi `beam_size=1` e
`condition_on_previous_text=False` non degradano in modo percepibile e
tagliano parecchio il tempo di inferenza.

Misurato su questa macchina (i5-1235U, int8, 8 thread): 1,7-1,9 s per frase.
"""

from __future__ import annotations

import threading
import time

import numpy as np

from . import config as C

_MODEL_CACHE: dict[tuple[str, str, str], object] = {}
# faster-whisper non e' thread-safe sullo stesso modello: due flussi che
# trascrivono insieme corromperebbero lo stato interno. Le due direzioni si
# serializzano qui, ed e' accettabile perche' raramente si parla in due.
_LOCK = threading.Lock()


class SttError(RuntimeError):
    """Errore nel caricamento del modello o nella trascrizione."""


def _modello_presente(size: str) -> bool:
    """Vero se il modello e' gia' nella cartella del programma.

    Serve solo a sapere se stiamo per scaricare: il modello arriva da Internet
    e pesa centinaia di MB, quindi chi avvia il programma deve essere avvisato
    invece di vedere la macchina ferma per qualche minuto senza spiegazione.
    """
    return any(C.WHISPER_DIR.glob(f"models--*--faster-whisper-{size}"))


def _get_model(size: str):
    """Carica il modello una volta sola e lo riusa."""
    chiave = (size, C.WHISPER_DEVICE, C.WHISPER_COMPUTE_TYPE)
    if chiave in _MODEL_CACHE:
        return _MODEL_CACHE[chiave]
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise SttError(
            "faster-whisper non installato. Installa con: pip install faster-whisper"
        ) from exc
    if not _modello_presente(size):
        # Una riga sola, ma senza di essa sembra che il programma si sia
        # piantato: e' il primo avvio e il download puo' durare minuti.
        print(
            f"[stt] modello '{size}' assente: lo scarico ora (~465 MB). "
            f"Succede una volta sola, resta in {C.WHISPER_DIR}.",
            flush=True,
        )
    try:
        modello = WhisperModel(
            size,
            device=C.WHISPER_DEVICE,
            compute_type=C.WHISPER_COMPUTE_TYPE,
            cpu_threads=C.WHISPER_CPU_THREADS,
            # Il modello va nella cartella del programma, non nella cache
            # condivisa di Hugging Face: cosi' tutti i dati di Vox Populi
            # stanno insieme e si trovano in un posto solo.
            download_root=str(C.WHISPER_DIR),
        )
    except Exception as exc:                      # noqa: BLE001 - messaggio all'utente
        raise SttError(
            f"Caricamento del modello Whisper '{size}' non riuscito: {exc}"
        ) from exc
    _MODEL_CACHE[chiave] = modello
    return modello


def prepara(size: str | None = None) -> float:
    """Carica il modello e lo scalda con un secondo di silenzio.

    Senza warm-up la prima frase reale paga l'inizializzazione dei kernel e
    sembra che il sistema si sia bloccato. Restituisce i secondi impiegati.
    """
    inizio = time.perf_counter()
    modello = _get_model(size or C.WHISPER_MODEL)
    silenzio = np.zeros(C.SAMPLE_RATE, dtype=np.float32)
    with _LOCK:
        try:
            segmenti, _ = modello.transcribe(
                silenzio, language=C.LANG_IT, beam_size=1,
                condition_on_previous_text=False, vad_filter=False,
                without_timestamps=True,
            )
            list(segmenti)                        # generatore: va consumato
        except Exception:                          # noqa: BLE001 - warm-up best effort
            pass
    return time.perf_counter() - inizio


def trascrivi(
    audio: np.ndarray,
    lingua: str,
    size: str | None = None,
    prompt: str | None = None,
) -> tuple[str, float]:
    """Trascrive campioni float32 mono. Restituisce (testo, secondi).

    Il testo puo' essere vuoto: succede con segmenti che sono solo rumore, ed
    e' un esito normale, non un errore.
    """
    if audio.size == 0:
        return "", 0.0

    modello = _get_model(size or C.WHISPER_MODEL)
    prompt = prompt if prompt is not None else C.STT_INITIAL_PROMPT
    inizio = time.perf_counter()
    with _LOCK:
        try:
            segmenti, _info = modello.transcribe(
                audio,
                language=lingua,
                beam_size=1,
                condition_on_previous_text=False,
                vad_filter=False,
                without_timestamps=True,
                initial_prompt=prompt or None,
            )
            testo = " ".join(s.text.strip() for s in segmenti).strip()
        except Exception as exc:                  # noqa: BLE001 - messaggio all'utente
            raise SttError(f"Trascrizione non riuscita: {exc}") from exc
    return testo, time.perf_counter() - inizio
