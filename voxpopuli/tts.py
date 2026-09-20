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
import json
import queue
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from . import config as C

# Le voci disponibili sono oltre trecento, in 75 lingue, e le elenca edge-tts
# interrogando il servizio: non sono elencate a mano perche' cambiano nel
# tempo. La lista viene messa in cache su disco, cosi' l'interfaccia si apre
# subito e continua a funzionare anche senza rete.
VOCI_CACHE = C.VOCI_CACHE
VOCI_CACHE_GIORNI = 30

# Riserva usata al primo avvio senza rete, o se la cache e' illeggibile:
# poche voci per le due lingue di partenza. Senza queste, l'interfaccia
# mostrerebbe un menu vuoto prima ancora di aver mai parlato col servizio.
VOCI_FALLBACK: dict[str, dict[str, str]] = {
    "en": {
        "en-IN-PrabhatNeural": "Prabhat · maschile · India",
        "en-IN-NeerjaNeural": "Neerja · femminile · India",
        "en-IN-NeerjaExpressiveNeural": "Neerja espressiva · femminile · India",
        "en-GB-RyanNeural": "Ryan · maschile · Regno Unito",
        "en-US-GuyNeural": "Guy · maschile · Stati Uniti",
        "en-US-AriaNeural": "Aria · femminile · Stati Uniti",
    },
    "it": {
        "it-IT-DiegoNeural": "Diego · maschile · Italia",
        "it-IT-ElsaNeural": "Elsa · femminile · Italia",
        "it-IT-IsabellaNeural": "Isabella · femminile · Italia",
        "it-IT-GiuseppeMultilingualNeural": "Giuseppe · maschile · Italia",
    },
}

# La voce indiana maschile resta la scelta di partenza per l'inglese: e'
# l'accento che l'interlocutore di Mumbai si aspetta di sentire.
VOCE_PREDEFINITA = "en-IN-PrabhatNeural"

# Paese dedotto dal codice regione del locale (en-IN -> India), per rendere
# leggibile il nome della voce. Non serve coprire il mondo: per i codici non
# presenti si mostra il codice stesso, che resta comprensibile.
PAESI = {
    "AU": "Australia", "BR": "Brasile", "CA": "Canada", "CH": "Svizzera",
    "CN": "Cina", "CZ": "Cechia", "DE": "Germania", "DK": "Danimarca",
    "ES": "Spagna", "FI": "Finlandia", "FR": "Francia", "GB": "Regno Unito",
    "GR": "Grecia", "HK": "Hong Kong", "IE": "Irlanda", "IL": "Israele",
    "IN": "India", "IT": "Italia", "JP": "Giappone", "KE": "Kenya",
    "KR": "Corea", "MX": "Messico", "NG": "Nigeria", "NL": "Paesi Bassi",
    "NO": "Norvegia", "NZ": "Nuova Zelanda", "PH": "Filippine",
    "PL": "Polonia", "PT": "Portogallo", "RO": "Romania", "RU": "Russia",
    "SA": "Arabia Saudita", "SE": "Svezia", "SG": "Singapore",
    "TR": "Turchia", "TW": "Taiwan", "TZ": "Tanzania", "UA": "Ucraina",
    "US": "Stati Uniti", "ZA": "Sudafrica",
}

_GENERI = {"Male": "maschile", "Female": "femminile"}

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


def _descrizione(voce: dict) -> str:
    """Rende leggibile una voce: 'en-IN-PrabhatNeural' -> 'Prabhat · maschile · India'."""
    nome = str(voce.get("ShortName", ""))
    parti = nome.split("-")
    breve = parti[2] if len(parti) > 2 else nome
    for suffisso in ("MultilingualNeural", "ExpressiveNeural", "Neural"):
        if breve.endswith(suffisso):
            breve = breve[: -len(suffisso)]
            break
    genere = _GENERI.get(str(voce.get("Gender", "")), "")
    regione = parti[1] if len(parti) > 1 else ""
    pezzi = [breve] + [p for p in (genere, PAESI.get(regione, regione)) if p]
    return " · ".join(pezzi)


def _elenco_online() -> list[dict]:
    """Interroga edge-tts per l'elenco completo delle voci. Richiede rete."""
    import edge_tts
    return list(asyncio.run(edge_tts.list_voices()))


def _leggi_cache() -> list[dict] | None:
    """Legge l'elenco salvato, se non e' troppo vecchio."""
    try:
        with open(VOCI_CACHE, encoding="utf-8") as fh:
            salvato = json.load(fh)
        quando = float(salvato.get("quando", 0))
        if time.time() - quando > VOCI_CACHE_GIORNI * 86400:
            return None
        return list(salvato.get("voci", []))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def _scrivi_cache(elenco: list[dict]) -> None:
    """Salva l'elenco per gli avvii successivi. Un fallimento non e' un problema."""
    try:
        VOCI_CACHE.parent.mkdir(parents=True, exist_ok=True)
        tmp = VOCI_CACHE.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"quando": time.time(), "voci": elenco}, fh, ensure_ascii=False)
        tmp.replace(VOCI_CACHE)
    except OSError as exc:
        print(f"[voce] elenco voci non salvato: {exc}")


def elenco_voci(forza: bool = False) -> list[dict]:
    """Elenco grezzo delle voci: cache su disco, altrimenti rete."""
    if not forza:
        salvato = _leggi_cache()
        if salvato:
            return salvato
    try:
        elenco = _elenco_online()
    except Exception as exc:                      # noqa: BLE001 - rete assente
        print(f"[voce] elenco voci non disponibile ({exc}); uso la riserva")
        return []
    if elenco:
        _scrivi_cache(elenco)
    return elenco


def voci_per_lingua(codice: str, forza: bool = False) -> dict[str, str]:
    """Voci pronunciabili in una lingua: {nome_tecnico: descrizione leggibile}."""
    elenco = elenco_voci(forza)
    trovate = {
        str(v.get("ShortName")): _descrizione(v)
        for v in elenco
        if str(v.get("Locale", "")).startswith(f"{codice}-")
    }
    if trovate:
        return dict(sorted(trovate.items(), key=lambda coppia: coppia[1]))
    return dict(VOCI_FALLBACK.get(codice, {}))


def voce_predefinita(codice: str) -> str:
    """Voce da preselezionare per una lingua, stringa vuota se non ce ne sono."""
    disponibili = voci_per_lingua(codice)
    if codice == "en" and VOCE_PREDEFINITA in disponibili:
        return VOCE_PREDEFINITA
    return next(iter(disponibili), "")


def voci_disponibili() -> dict[str, str]:
    """Elenco delle voci selezionabili per l'inglese (compatibilita')."""
    return voci_per_lingua("en")
