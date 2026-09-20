# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Daniele Deplano (RedRider21)
"""Configurazione di Vox Populi.

Costanti tecniche in testa al file e preferenze utente persistite in
~/.config/vox-populi/config.json. Le preferenze salvate vincono sui default,
ma ogni valore mancante ricade sul default: un file di config vecchio o
parziale non deve mai impedire l'avvio.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

APP_NAME = "vox-populi"

# Tutto in una cartella sola, facile da trovare, copiare, spostare o
# cancellare: modelli di traduzione, modello di trascrizione, elenco delle
# voci e preferenze. Chi vuole portarsi via il programma con i suoi modelli
# copia questa e nient'altro.
#
#   ~/.local/share/vox-populi/
#   ├── config.json     preferenze
#   ├── voci.json       elenco delle voci sintetiche
#   ├── modelli/        pacchetti di traduzione (argostranslate)
#   └── whisper/        modello di trascrizione (faster-whisper)
DATA_DIR = Path(
    os.environ.get("VOXPOPULI_DATA_DIR")
    or (Path.home() / ".local" / "share" / APP_NAME)
)
MODELLI_DIR = DATA_DIR / "modelli"
WHISPER_DIR = DATA_DIR / "whisper"
VOCI_CACHE = DATA_DIR / "voci.json"
CONFIG_PATH = DATA_DIR / "config.json"

# Percorsi usati dalle versioni precedenti, tenuti solo per migrarli.
VECCHIA_CONFIG = (
    Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")) / APP_NAME
) / "config.json"
VECCHI_MODELLI = Path.home() / ".local" / "share" / "argos-translate" / "packages"
VECCHIA_CACHE_VOCI = Path.home() / ".cache" / APP_NAME / "voci.json"
VECCHIA_CACHE_WHISPER = Path.home() / ".cache" / "huggingface" / "hub"

# argostranslate sceglie la cartella dei pacchetti da una variabile d'ambiente,
# che deve essere impostata PRIMA che la libreria venga importata. Questo
# modulo e' il primo che tutti gli altri importano, quindi il posto giusto e'
# qui. Con setdefault si rispetta una scelta gia' fatta dall'utente.
os.environ.setdefault("ARGOS_PACKAGES_DIR", str(MODELLI_DIR))

# ---------------------------------------------------------------- audio ----
# 16 kHz mono int16 e' il formato nativo di Whisper: nessuna conversione.
SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2                      # int16
FRAME_MS = 20
FRAME_SAMPLES = SAMPLE_RATE * FRAME_MS // 1000        # 320 campioni
BYTES_PER_FRAME = FRAME_SAMPLES * SAMPLE_WIDTH        # 640 byte

# ------------------------------------------------------------------ VAD ----
VAD_SILENCE_MS = 600          # silenzio che chiude una frase
VAD_MIN_SPEECH_MS = 300       # sotto questa soglia il segmento si scarta
VAD_MAX_SEGMENT_MS = 12000    # taglio duro, poi riparte subito
VAD_PREROLL_MS = 300          # coda audio tenuta prima dell'attacco
VAD_ON_THRESHOLD = 0.008      # soglia RMS minima assoluta
VAD_NOISE_MULT = 3.0          # la soglia sale a N volte il rumore di fondo
VAD_OFF_RATIO = 0.6           # isteresi: si chiude a ON * questo fattore
VAD_NOISE_ALPHA = 0.02        # EMA della stima del rumore di fondo

# ------------------------------------------------------------------ STT ----
WHISPER_MODEL = "small"       # gia' in cache su questa macchina
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"
WHISPER_CPU_THREADS = 8

# Termini attesi, passati come initial_prompt. Misurato: NON risolve gli
# anglicismi italianizzati ("call" resta ambiguo), quindi disattivato di
# default. Resta configurabile perche' aiuta sui nomi propri e sul gergo.
STT_INITIAL_PROMPT = ""
STT_INITIAL_PROMPT_IT = (
    "Riunione di lavoro fra Italia e India. Termini frequenti: call, meeting, "
    "link, preventivo, spedizione, tracking, report, deadline, follow-up."
)
STT_INITIAL_PROMPT_EN = (
    "Business call between India and Italy. Frequent terms: quote, shipment, "
    "tracking, invoice, deadline, follow-up, batch, consignment."
)

# ------------------------------------------------------------------- MT ----
LANG_IT = "it"                          # lingue usate dai collaudi e dalla CLI
LANG_EN = "en"

# Lingue effettivamente traducibili con argostranslate. Il nome e' quello
# italiano, perche' compare nei menu dell'interfaccia. Le coppie dirette
# dall'italiano esistono solo verso l'inglese: per tutte le altre si passa
# per l'inglese (vedi mt.percorso()). Aggiungere lingue qui non basta: i
# modelli vanno anche scaricati (voce "Installa modelli" nel pannello).
LINGUE: dict[str, str] = {
    "it": "italiano",        "en": "inglese",       "fr": "francese",
    "es": "spagnolo",        "de": "tedesco",       "pt": "portoghese",
    "pb": "portoghese (Brasile)",                    "nl": "olandese",
    "sv": "svedese",         "da": "danese",        "nb": "norvegese",
    "fi": "finlandese",      "pl": "polacco",       "cs": "ceco",
    "sk": "slovacco",        "sl": "sloveno",       "hu": "ungherese",
    "ro": "rumeno",          "bg": "bulgaro",       "el": "greco",
    "ru": "russo",           "uk": "ucraino",       "lt": "lituano",
    "lv": "lettone",         "et": "estone",        "sq": "albanese",
    "tr": "turco",           "ar": "arabo",         "he": "ebraico",
    "fa": "persiano",        "hi": "hindi",         "bn": "bengalese",
    "ur": "urdu",            "th": "thai",
    "vi": "vietnamita",      "id": "indonesiano",   "ms": "malese",
    "tl": "tagalog",         "sw": "swahili",       "zh": "cinese (semplificato)",
    "zt": "cinese (tradizionale)",                   "ja": "giapponese",
    "ko": "coreano",         "ca": "catalano",      "gl": "galiziano",
    "eu": "basco",           "eo": "esperanto",     "az": "azero",
    "ky": "chirghiso",       "ga": "irlandese",
}

# Lingua con cui si fa da ponte quando manca la coppia diretta fra due
# lingue: e' la piu' coperta da argostranslate (quasi tutte le 50 lingue
# hanno un pacchetto da o verso l'inglese).
LINGUA_PONTE = "en"


def nome_lingua(codice: str) -> str:
    """Nome leggibile di una lingua, o il codice stesso se sconosciuta."""
    return LINGUE.get(codice, codice)

# ---------------------------------------------------------------- testo ----
# Quante frasi restano visibili nella finestra condivisa con l'interlocutore.
SPEAKER_HISTORY = 4

# ------------------------------------------------------------ preferenze ----
DEFAULTS: dict = {
    # Dispositivi scelti dall'utente (nomi PulseAudio completi).
    "remote_source": "",          # sorgente della voce dell'interlocutore
    "mic_source": "",             # microfono locale
    "whisper_model": WHISPER_MODEL,
    # Le due lingue della conversazione: la mia e quella dell'interlocutore.
    "my_lang": LANG_IT,           # lingua che parlo io
    "their_lang": LANG_EN,        # lingua che parla lui
    "theme": "scuro",             # schema cromatico (vedi ui/stile.py)
    "font_size": 20,              # carattere del pannello
    "speaker_font_size": 44,      # carattere della finestra per l'interlocutore
    "speaker_history": SPEAKER_HISTORY,
    "half_duplex": True,          # sospende il mic mentre l'altro parla
    "use_initial_prompt": False,
    "voice_enabled": False,       # interruttore voce sintetica (fase 4)
    "tts_voice": "en-IN-PrabhatNeural",
    # L'altezza tiene dentro tutte le righe di controllo (lingue, dispositivi,
    # voce, colori): sotto i 700 qualcuna finisce tagliata dal bordo inferiore.
    "window": {"x": 40, "y": 40, "w": 660, "h": 700},
    "speaker_window": {"x": 700, "y": 40, "w": 760, "h": 520},
}


def load() -> dict:
    """Legge la config salvata, completando i valori mancanti coi default."""
    cfg = json.loads(json.dumps(DEFAULTS))       # copia profonda
    sorgente = CONFIG_PATH
    if not sorgente.exists() and VECCHIA_CONFIG.exists():
        # Prima esecuzione dopo il passaggio alla cartella unica: le
        # preferenze possono essere ancora nel vecchio posto.
        sorgente = VECCHIA_CONFIG
    try:
        with open(sorgente, encoding="utf-8") as fh:
            saved = json.load(fh)
    except FileNotFoundError:
        return cfg
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[config] file illeggibile ({exc}), uso i valori predefiniti")
        return cfg
    for key, value in saved.items():
        # I sotto-dizionari si fondono chiave per chiave, cosi' una config
        # scritta da una versione precedente non perde i campi nuovi.
        if isinstance(value, dict) and isinstance(cfg.get(key), dict):
            cfg[key].update(value)
        else:
            cfg[key] = value
    return cfg


def save(cfg: dict) -> None:
    """Salva le preferenze, ignorando silenziosamente i fallimenti di scrittura."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = CONFIG_PATH.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=2, ensure_ascii=False)
        tmp.replace(CONFIG_PATH)          # scrittura atomica
    except OSError as exc:
        print(f"[config] salvataggio non riuscito: {exc}")


def _sposta(origine: Path, destinazione: Path) -> bool:
    """Sposta una cartella o un file, senza mai sovrascrivere niente."""
    if not origine.exists() or destinazione.exists():
        return False
    try:
        import shutil
        destinazione.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(origine), str(destinazione))
    except OSError as exc:
        print(f"[config] spostamento non riuscito ({origine}): {exc}")
        return False
    return True


def migra_dati() -> list[str]:
    """Porta nella cartella unica i dati delle versioni precedenti.

    Serve a chi aveva gia' usato il programma prima che tutto fosse
    raccolto in un posto solo: senza questa funzione i modelli resterebbero
    dove sono e verrebbero scaricati di nuovo, per centinaia di MB. Non
    sovrascrive mai nulla e non solleva eccezioni: se qualcosa va storto si
    limita a non spostare, e il programma riscarichera' quel pezzo.
    """
    spostati: list[str] = []
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        return spostati

    # Preferenze.
    if _sposta(VECCHIA_CONFIG, CONFIG_PATH):
        spostati.append("preferenze")

    # Pacchetti di traduzione: si sposta il contenuto, non la cartella, perche'
    # quella vecchia puo' contenere anche altro.
    if VECCHI_MODELLI.is_dir() and VECCHI_MODELLI != MODELLI_DIR:
        for pacchetto in sorted(VECCHI_MODELLI.iterdir()):
            if _sposta(pacchetto, MODELLI_DIR / pacchetto.name):
                spostati.append(f"modello {pacchetto.name}")

    # Elenco delle voci.
    if _sposta(VECCHIA_CACHE_VOCI, VOCI_CACHE):
        spostati.append("elenco voci")

    # Modello di trascrizione: si sposta solo quello di faster-whisper, perche'
    # la cache di Hugging Face puo' contenere i modelli di altri programmi.
    if VECCHIA_CACHE_WHISPER.is_dir():
        for voce in sorted(VECCHIA_CACHE_WHISPER.glob("models--Systran--faster-whisper-*")):
            if _sposta(voce, WHISPER_DIR / voce.name):
                spostati.append(f"trascrizione {voce.name.split('--')[-1]}")

    return spostati
