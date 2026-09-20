# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Daniele Deplano (RedRider21)
"""Traduzione: da testo a testo, con argostranslate (NMT locale).

Scelto dopo aver misurato le alternative: un modello linguistico da 7B via
Ollama impiega 2,1 s a frase, argostranslate 0,06 s. Su una conversazione dal
vivo la differenza e' decisiva, e la qualita' e' piu' che sufficiente su frasi
di lavoro. Il primo scambio paga ~3 s di caricamento dei modelli, da qui il
`prepara()` all'avvio.

Il limite noto sono gli idiomi ("not up to the mark" diventa "non era fino al
segno"): se in futuro servisse, un rifinitore a valle via LLM puo' correggere
la frase senza bloccare la lettura immediata.
"""

from __future__ import annotations

import logging
import threading
import time

from . import config as C

# argostranslate emette un warning su ogni chiamata ("package default expects
# mwt"), che e' rumore: il tokenizzatore viene aggiunto automaticamente e la
# traduzione e' corretta. Senza questo finirebbe in mezzo ai sottotitoli.
logging.getLogger("argostranslate").setLevel(logging.ERROR)
logging.getLogger("stanza").setLevel(logging.ERROR)

_LOCK = threading.Lock()
_PRONTO = False


class MtError(RuntimeError):
    """Errore nel caricamento dei modelli o nella traduzione."""


def _argos():
    try:
        import argostranslate.translate as traduzione
    except ImportError as exc:
        raise MtError(
            "argostranslate non installato. Installa con: pip install argostranslate"
        ) from exc
    return traduzione


def lingue_disponibili() -> set[tuple[str, str]]:
    """ Coppie (da, a) effettivamente installate. """
    try:
        from argostranslate import package
        return {(p.from_code, p.to_code) for p in package.get_installed_packages()}
    except Exception:                             # noqa: BLE001 - diagnosi best effort
        return set()


def prepara() -> float:
    """Scalda i modelli con una traduzione minima in entrambe le direzioni."""
    global _PRONTO
    inizio = time.perf_counter()
    traduzione = _argos()
    with _LOCK:
        for da, a, campione in (
            (C.LANG_IT, C.LANG_EN, "ciao"),
            (C.LANG_EN, C.LANG_IT, "hello"),
        ):
            try:
                traduzione.translate(campione, da, a)
            except Exception:                     # noqa: BLE001 - warm-up best effort
                pass
    _PRONTO = True
    return time.perf_counter() - inizio


def traduci(testo: str, da: str, a: str) -> tuple[str, float]:
    """Traduce `testo` fra due lingue. Restituisce (traduzione, secondi)."""
    testo = (testo or "").strip()
    if not testo:
        return "", 0.0
    if da == a:
        return testo, 0.0

    traduzione = _argos()
    inizio = time.perf_counter()
    with _LOCK:
        try:
            risultato = traduzione.translate(testo, da, a)
        except Exception as exc:                  # noqa: BLE001 - messaggio all'utente
            raise MtError(
                f"Traduzione {da}->{a} non riuscita: {exc}. "
                "Verifica che i modelli siano installati (voce 'Installa modelli')."
            ) from exc
    return risultato.strip(), time.perf_counter() - inizio


def direzione_remota() -> tuple[str, str]:
    """Lingue dell'interlocutore: inglese in ingresso, italiano in uscita."""
    return C.LANG_EN, C.LANG_IT


def direzione_locale() -> tuple[str, str]:
    """Lingue dell'utente: italiano in ingresso, inglese in uscita."""
    return C.LANG_IT, C.LANG_EN
