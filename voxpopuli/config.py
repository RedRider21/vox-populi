# SPDX-License-Identifier: MIT
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
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")) / APP_NAME
CONFIG_PATH = CONFIG_DIR / "config.json"

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
LANG_IT = "it"
LANG_EN = "en"

# ---------------------------------------------------------------- testo ----
# Quante frasi restano visibili nella finestra condivisa con l'interlocutore.
SPEAKER_HISTORY = 4

# ------------------------------------------------------------ preferenze ----
DEFAULTS: dict = {
    # Dispositivi scelti dall'utente (nomi PulseAudio completi).
    "remote_source": "",          # sorgente della voce dell'interlocutore
    "mic_source": "",             # microfono locale
    "whisper_model": WHISPER_MODEL,
    "font_size": 20,              # carattere del pannello
    "speaker_font_size": 44,      # carattere della finestra per l'interlocutore
    "half_duplex": True,          # sospende il mic mentre l'altro parla
    "use_initial_prompt": False,
    "voice_enabled": False,       # interruttore voce sintetica (fase 4)
    "tts_voice": "en-IN-PrabhatNeural",
    "window": {"x": 40, "y": 40, "w": 620, "h": 460},
    "speaker_window": {"x": 700, "y": 40, "w": 760, "h": 520},
}


def load() -> dict:
    """Legge la config salvata, completando i valori mancanti coi default."""
    cfg = json.loads(json.dumps(DEFAULTS))       # copia profonda
    try:
        with open(CONFIG_PATH, encoding="utf-8") as fh:
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
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        tmp = CONFIG_PATH.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=2, ensure_ascii=False)
        tmp.replace(CONFIG_PATH)          # scrittura atomica
    except OSError as exc:
        print(f"[config] salvataggio non riuscito: {exc}")
