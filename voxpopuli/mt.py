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
    return _archi_installati()


def lingue_installate() -> set[str]:
    """Codici delle lingue coperte almeno da un pacchetto installato."""
    return {codice for coppia in _archi_installati() for codice in coppia}


def _archi_installati() -> set[tuple[str, str]]:
    try:
        from argostranslate import package
        return {(p.from_code, p.to_code) for p in package.get_installed_packages()}
    except Exception:                             # noqa: BLE001 - diagnosi best effort
        return set()


def periodo(da: str, a: str, archi: set[tuple[str, str]] | None = None) -> list[str] | None:
    """Tappe per andare da una lingua all'altra, o None se non e' possibile.

    Serve perche' argostranslate non ha la coppia diretta fra tutte le lingue:
    dall'italiano, per esempio, esistono solo i pacchetti verso l'inglese. Per
    arrivare in tedesco si passa allora per l'inglese (it -> en -> de), che e'
    esattamente il "pivot" usato dagli strumenti di traduzione offline.

    Il percorso piu' corto si cerca con una visita in ampiezza: con poche
    decine di lingue e' istantaneo e trova sempre la catena con meno passaggi,
    che e' anche quella che perde meno qualita'.
    """
    if da == a:
        return [da]
    archi = _archi_installati() if archi is None else archi
    if (da, a) in archi:                          # scorciatoia per il caso comune
        return [da, a]

    # Il ponte preferito (l'inglese) viene esplorato per primo: a parita' di
    # lunghezza il percorso che ci passa e' quello con i modelli migliori.
    def vicini(codice: str) -> list[str]:
        uscite = sorted({b for x, b in archi if x == codice})
        return sorted(uscite, key=lambda c: c != C.LINGUA_PONTE)

    coda: list[list[str]] = [[da]]
    visti = {da}
    while coda:
        cammino = coda.pop(0)
        for prossimo in vicini(cammino[-1]):
            if prossimo in visti:
                continue
            nuovo = cammino + [prossimo]
            if prossimo == a:
                return nuovo
            visti.add(prossimo)
            coda.append(nuovo)
    return None


def percorso(da: str, a: str) -> list[str] | None:
    """Tappe percorribili con i modelli gia' installati."""
    return periodo(da, a, _archi_installati())


def pacchetti_disponibili() -> set[tuple[str, str]]:
    """Coppie scaricabili dall'indice di argostranslate (richiede rete)."""
    try:
        from argostranslate import package
        return {(p.from_code, p.to_code) for p in package.get_available_packages()}
    except Exception:                             # noqa: BLE001 - diagnosi best effort
        return set()


def pacchetti_mancanti(da: str, a: str) -> list[tuple[str, str]] | None:
    """Coppie da scaricare per poter tradurre fra le due lingue.

    Restituisce la catena di pacchetti mancanti, lista vuota se basta quanto
    gia' installato, None se nemmeno scaricando tutto la coppia e' possibile.
    """
    if percorso(da, a) is not None:
        return []
    disponibili = pacchetti_disponibili()
    if not disponibili:
        return None
    tappe = periodo(da, a, disponibili)
    if tappe is None:
        return None
    # Il percorso va calcolato sui disponibili (potrebbe passare per lingue
    # che non sono ancora installate), ma si scarica solo cio' che manca:
    # senza questo filtro verrebbe reinstallato anche il ponte gia' presente.
    installati = _archi_installati()
    return [coppia for coppia in zip(tappe, tappe[1:]) if coppia not in installati]


def prepara(da: str | None = None, a: str | None = None) -> float:
    """Scalda i modelli sulle due direzioni della conversazione.

    Nota: non prende il lock, perche' `traduci()` lo prende gia' e il lock non
    e' rientrante. Le due direzioni sono indipendenti: se una non e' pronta,
    l'altra si scalda lo stesso.
    """
    global _PRONTO
    da = da or C.LANG_IT
    a = a or C.LANG_EN
    inizio = time.perf_counter()
    for testo, x, y in (("ciao", da, a), ("hello", a, da)):
        try:
            traduci(testo, x, y)
        except MtError:
            pass
    _PRONTO = True
    return time.perf_counter() - inizio


def traduci(testo: str, da: str, a: str) -> tuple[str, float]:
    """Traduce `testo` fra due lingue. Restituisce (traduzione, secondi).

    Se fra le due lingue non esiste un pacchetto diretto, la frase viene
    portata attraverso la lingua ponte (di norma l'inglese): it -> en -> de.
    Il tempo riportato comprende tutti i passaggi.
    """
    testo = (testo or "").strip()
    if not testo:
        return "", 0.0
    if da == a:
        return testo, 0.0

    tappe = percorso(da, a)
    if tappe is None:
        raise MtError(
            f"Nessun modello per tradurre da {C.nome_lingua(da)} a "
            f"{C.nome_lingua(a)}. Usa 'Installa modelli' nel pannello."
        )

    traduzione = _argos()
    inizio = time.perf_counter()
    with _LOCK:
        try:
            corrente = testo
            for x, y in zip(tappe, tappe[1:]):
                corrente = traduzione.translate(corrente, x, y)
        except Exception as exc:                  # noqa: BLE001 - messaggio all'utente
            raise MtError(
                f"Traduzione {da}->{a} non riuscita: {exc}. "
                "Verifica che i modelli siano installati (voce 'Installa modelli')."
            ) from exc
    return corrente.strip(), time.perf_counter() - inizio


def direzione_remota(cfg: dict) -> tuple[str, str]:
    """Lingue dell'interlocutore: la sua in ingresso, la mia in uscita."""
    return str(cfg.get("their_lang", C.LANG_EN)), str(cfg.get("my_lang", C.LANG_IT))


def direzione_locale(cfg: dict) -> tuple[str, str]:
    """Lingue dell'utente: la mia in ingresso, la sua in uscita."""
    return str(cfg.get("my_lang", C.LANG_IT)), str(cfg.get("their_lang", C.LANG_EN))


def installa(catena: list[tuple[str, str]], on_stato=None) -> list[tuple[str, str]]:
    """Scarica e installa i pacchetti mancanti. Restituisce quelli riusciti.

    Il download puo' durare minuti: `on_stato` viene chiamato con un messaggio
    leggibile prima di ogni pacchetto, perche' l'interfaccia possa mostrare a
    che punto e'. Non solleva eccezioni: un pacchetto che fallisce non deve
    impedire gli altri, che restano validi.
    """
    try:
        from argostranslate import package as pacchetti
    except ImportError as exc:
        raise MtError("argostranslate non installato.") from exc

    def annuncia(messaggio: str) -> None:
        if on_stato is not None:
            try:
                on_stato(messaggio)
            except Exception:                     # noqa: BLE001 - la UI non blocca
                pass

    annuncia("Aggiorno l'indice dei modelli...")
    try:
        pacchetti.update_package_index()
        disponibili = pacchetti.get_available_packages()
    except Exception as exc:                      # noqa: BLE001 - messaggio all'utente
        raise MtError(f"Indice dei modelli non raggiungibile: {exc}") from exc

    riusciti: list[tuple[str, str]] = []
    for indice, (da, a) in enumerate(catena, start=1):
        pacchetto = next(
            (p for p in disponibili if p.from_code == da and p.to_code == a), None,
        )
        if pacchetto is None:
            annuncia(f"Pacchetto {da}->{a} non disponibile.")
            continue
        annuncia(
            f"[{indice}/{len(catena)}] scarico {C.nome_lingua(da)} -> "
            f"{C.nome_lingua(a)} (~94 MB)..."
        )
        try:
            percorso_file = pacchetto.download()
            pacchetto.install(percorso_file)
        except Exception as exc:                  # noqa: BLE001 - messaggio all'utente
            annuncia(f"Installazione {da}->{a} non riuscita: {exc}")
            continue
        riusciti.append((da, a))
    return riusciti
