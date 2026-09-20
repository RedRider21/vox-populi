# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Daniele Deplano (RedRider21)
"""Segmentazione del parlato: dal flusso audio continuo alle singole frasi.

Il VAD lavora su frame da 20 ms e usa l'energia RMS con soglia adattiva:

* una stima EMA del rumore di fondo fa salire la soglia quando l'ambiente e'
  rumoroso, cosi' non serve ritoccare le costanti a mano;
* l'isteresi (si chiude a una soglia piu' bassa di quella di attacco) evita di
  spezzare una frase durante le pause brevi;
* il pre-roll di 300 ms conserva l'attacco, che altrimenti verrebbe tagliato
  perche' la soglia viene superata solo dopo la prima sillaba.

La classe e' volutamente senza stato condiviso e senza I/O: riceve campioni,
restituisce segmenti. Tutto il resto (thread, code, modelli) sta altrove.
"""

from __future__ import annotations

import numpy as np

from . import config as C


class VadSegmenter:
    """Accumula campioni e restituisce i segmenti di parlato completati."""

    def __init__(
        self,
        sample_rate: int = C.SAMPLE_RATE,
        silence_ms: int = C.VAD_SILENCE_MS,
        min_speech_ms: int = C.VAD_MIN_SPEECH_MS,
        max_segment_ms: int = C.VAD_MAX_SEGMENT_MS,
        preroll_ms: int = C.VAD_PREROLL_MS,
        on_threshold: float = C.VAD_ON_THRESHOLD,
        noise_mult: float = C.VAD_NOISE_MULT,
        off_ratio: float = C.VAD_OFF_RATIO,
        noise_alpha: float = C.VAD_NOISE_ALPHA,
    ) -> None:
        self.sample_rate = sample_rate
        self.frame_samples = sample_rate * C.FRAME_MS // 1000
        self.preroll_frames = max(1, preroll_ms // C.FRAME_MS)
        self.silence_samples = sample_rate * silence_ms // 1000
        self.min_speech_samples = sample_rate * min_speech_ms // 1000
        self.max_segment_samples = sample_rate * max_segment_ms // 1000
        self.on_threshold = on_threshold
        self.noise_mult = noise_mult
        self.off_ratio = off_ratio
        self.noise_alpha = noise_alpha

        self._residuo = np.empty(0, dtype=np.float32)   # campioni non ancora a frame
        self._preroll: list[np.ndarray] = []            # coda pre-attacco
        self._segmento: list[np.ndarray] = []
        self._lunghezza = 0                             # campioni nel segmento
        self._silenzio = 0                              # campioni di silenzio in coda
        self._attivo = False
        self._rumore = 0.003                            # stima iniziale del fondo
        self._parlato_da = 0.0                          # istante d'inizio (per la UI)

    # ------------------------------------------------------------ proprieta' ----
    @property
    def attivo(self) -> bool:
        """True mentre e' in corso un segmento di parlato."""
        return self._attivo

    @property
    def soglia(self) -> float:
        """Soglia di attacco corrente, utile per la taratura dal vivo."""
        return max(self.on_threshold, self._rumore * self.noise_mult)

    @property
    def rumore(self) -> float:
        return self._rumore

    # ---------------------------------------------------------------- flusso ----
    def feed(self, campioni: np.ndarray) -> list[np.ndarray]:
        """Consuma campioni float32 mono in [-1, 1] e restituisce i segmenti chiusi."""
        if campioni.size == 0:
            return []

        if self._residuo.size:
            campioni = np.concatenate((self._residuo, campioni))
        n_frame = campioni.size // self.frame_samples
        if n_frame == 0:
            self._residuo = campioni
            return []

        completi = campioni[: n_frame * self.frame_samples]
        self._residuo = campioni[n_frame * self.frame_samples :].copy()

        segmenti: list[np.ndarray] = []
        for i in range(n_frame):
            frame = completi[i * self.frame_samples : (i + 1) * self.frame_samples]
            rms = float(np.sqrt(np.mean(np.square(frame))))
            segmento = self._elabora_frame(frame, rms)
            if segmento is not None:
                segmenti.append(segmento)
        return segmenti

    def flush(self) -> np.ndarray | None:
        """Chiude il segmento in corso, se abbastanza lungo. Da chiamare allo stop."""
        return self._chiudi()

    # ---------------------------------------------------------------- interno ----
    def _elabora_frame(self, frame: np.ndarray, rms: float) -> np.ndarray | None:
        soglia_on = self.soglia
        soglia_off = soglia_on * self.off_ratio

        if not self._attivo:
            if rms < soglia_on:
                # Silenzio: affina la stima del fondo e alimenta il pre-roll.
                self._rumore = (
                    (1 - self.noise_alpha) * self._rumore + self.noise_alpha * rms
                )
                self._preroll.append(frame.copy())
                if len(self._preroll) > self.preroll_frames:
                    self._preroll.pop(0)
                return None
            # Attacco: il segmento inizia dal pre-roll, non dal frame corrente.
            self._attivo = True
            self._segmento = list(self._preroll)
            self._lunghezza = sum(f.size for f in self._segmento)
            self._preroll = []
            self._silenzio = 0

        self._segmento.append(frame.copy())
        self._lunghezza += frame.size

        if rms < soglia_off:
            self._silenzio += frame.size
            if self._silenzio >= self.silence_samples:
                return self._chiudi()
        else:
            self._silenzio = 0

        if self._lunghezza >= self.max_segment_samples:
            # Taglio duro: chiude il segmento e riparte subito dal frame
            # corrente, altrimenti si perderebbe il parlato che segue.
            chiuso = self._chiudi()
            self._attivo = True
            self._segmento = [frame.copy()]
            self._lunghezza = frame.size
            self._silenzio = 0
            return chiuso

        return None

    def _chiudi(self) -> np.ndarray | None:
        segmento = self._segmento
        lunghezza = self._lunghezza
        self._segmento = []
        self._lunghezza = 0
        self._silenzio = 0
        self._attivo = False

        if lunghezza < self.min_speech_samples:
            return None
        if not segmento:
            return None
        return np.concatenate(segmento).astype(np.float32, copy=False)


def pcm16_a_float(dati: bytes) -> np.ndarray:
    """Converte PCM int16 little-endian in float32 mono in [-1, 1]."""
    if not dati:
        return np.empty(0, dtype=np.float32)
    interi = np.frombuffer(dati, dtype="<i2")
    return (interi.astype(np.float32) / 32768.0).copy()
