#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Daniele Deplano (RedRider21)
#
# Installa Vox Populi su Debian/Ubuntu e affini.
#
# Lo script e' idempotente: rilanciarlo non fa danni, salta cio' che c'e' gia'.
# Non scarica nulla di pesante a sorpresa: il modello di trascrizione viene
# chiesto solo se manca, perche' pesa circa 500 MB.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

OK="\033[32m"; KO="\033[31m"; AVV="\033[33m"; FINE="\033[0m"
ok()   { printf "${OK}  ok${FINE}  %s\n" "$1"; }
ko()   { printf "${KO}  !!${FINE}  %s\n" "$1"; }
avv()  { printf "${AVV}  ..${FINE}  %s\n" "$1"; }

echo "=== Vox Populi: installazione ==="

# --------------------------------------------------------- sistema -------
# I pacchetti di sistema si installano con apt solo se mancano davvero.
PACCHETTI=()
command -v pactl       >/dev/null || PACCHETTI+=(pulseaudio-utils)
command -v parec       >/dev/null || PACCHETTI+=(pulseaudio-utils)
python3 -c "import gi" 2>/dev/null || PACCHETTI+=(python3-gi gir1.2-gtk-3.0)
command -v ffmpeg      >/dev/null || PACCHETTI+=(ffmpeg)

if (( ${#PACCHETTI[@]} )); then
    avv "mancano pacchetti di sistema: ${PACCHETTI[*]}"
    if command -v apt-get >/dev/null; then
        sudo apt-get update -qq
        sudo apt-get install -y "${PACCHETTI[@]}"
        ok "pacchetti di sistema installati"
    else
        ko "apt non disponibile: installa a mano ${PACCHETTI[*]} e rilancia"
        exit 1
    fi
else
    ok "pacchetti di sistema gia' presenti (pactl, GTK3, ffmpeg)"
fi

# ---------------------------------------------------------- python -------
avv "installo le dipendenze Python"
# --user evita di toccare il Python di sistema; se l'utente usa un virtualenv
# attivo, pip installa li' dentro senza accorgersene.
if python3 -m pip install --user -r requirements.txt; then
    ok "dipendenze Python installate"
else
    ko "installazione pip non riuscita"
    exit 1
fi

# -------------------------------------------------------- traduzione -----
# argostranslate ha bisogno dei due modelli di lingua per funzionare offline.
avv "verifico i modelli di traduzione it<->en"
MODELLI_MANCANTI=()
python3 - <<'PY' || MODELLI_MANCANTI=(it_en en_it)
import argostranslate.package as p
installate = {(x.from_code, x.to_code) for x in p.get_installed_packages()}
raise SystemExit(0 if {("it", "en"), ("en", "it")} <= installate else 1)
PY
if (( ${#MODELLI_MANCANTI[@]} )); then
    avv "scarico i modelli di traduzione (pochi MB)"
    python3 - <<'PY'
import argostranslate.package as p
p.update_package_index()
disponibili = p.get_available_packages()
for da, a in (("it", "en"), ("en", "it")):
    for pacchetto in disponibili:
        if pacchetto.from_code == da and pacchetto.to_code == a:
            print(f"  scarico {da}->{a} ...")
            p.install_from_path(pacchetto.download())
            break
PY
    ok "modelli di traduzione pronti"
else
    ok "modelli di traduzione gia' installati"
fi

# ------------------------------------------------------- trascrizione ----
avv "verifico il modello di trascrizione"
python3 - <<'PY' || true
from faster_whisper.utils import download_model
try:
    download_model("small", local_files_only=True)
    print("  ok  modello 'small' gia' in cache")
except Exception:
    print("  ..  il modello 'small' (~500 MB) non e' in cache.")
    print("      Al primo avvio verra' scaricato automaticamente.")
PY

# ------------------------------------------------------------- prova -----
echo
avv "prova di funzionamento"
if python3 -m voxpopuli.cli diagnosi; then
    echo
    ok "tutto pronto. Avvia con:  ./vox-populi"
else
    ko "la diagnosi ha segnalato problemi, vedi sopra"
    exit 1
fi
