#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Daniele Deplano (RedRider21)
#
# Installa Vox Populi su Debian/Ubuntu e affini.
#
# Uso:
#     ./install.sh          chiede conferma prima di scaricare i modelli
#     ./install.sh --si     procede senza chiedere (per script automatici)
#
# Lo script e' idempotente: rilanciarlo non fa danni, salta cio' che c'e' gia'.
# Prima di scaricare qualsiasi cosa dice quanto occupa e dove finisce.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

OK="\033[32m"; KO="\033[31m"; AVV="\033[33m"; FINE="\033[0m"
ok()   { printf "${OK}  ok${FINE}  %s\n" "$1"; }
ko()   { printf "${KO}  !!${FINE}  %s\n" "$1"; }
avv()  { printf "${AVV}  ..${FINE}  %s\n" "$1"; }

echo "=== Vox Populi: installazione ==="
echo
echo "Cosa scarica questo programma, e dove:"
echo "  trascrizione (Whisper small)       ~465 MB"
echo "  traduzione italiano <-> inglese    ~190 MB"
echo "  ------------------------------------------"
echo "  totale al primo avvio              ~655 MB"
echo
echo "Tutto finisce in un'unica cartella, ~/.local/share/vox-populi/,"
echo "che puoi copiare o cancellare quando vuoi. Le lingue aggiuntive"
echo "costano ~190 MB ciascuna e si scaricano dall'app, non da qui."
echo

if [[ "${1:-}" != "--si" && "${1:-}" != "-y" ]]; then
    read -r -p "Procedo? [S/n] " risposta
    case "${risposta:-s}" in
        [nN]*) echo "Annullato: non e' stato scaricato niente."; exit 0 ;;
    esac
    echo
fi

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

# ---------------------------------------------------- cartella unica -----
# Chi aveva una versione precedente ha i dati sparsi fra ~/.config, ~/.cache
# e ~/.local/share/argos-translate: si portano tutti nella cartella unica,
# altrimenti verrebbero scaricati di nuovo da capo.
avv "raccolgo i dati in un'unica cartella"
python3 - <<'PY'
from voxpopuli import config as C
for voce in C.migra_dati():
    print(f"  spostato: {voce}  ->  {C.DATA_DIR}")
print(f"  cartella dati: {C.DATA_DIR}")
PY
ok "dati raccolti in ~/.local/share/vox-populi"

# -------------------------------------------------------- traduzione -----
avv "verifico i modelli di traduzione"
python3 - <<'PY' || MODELLI_MANCANTI=1
from voxpopuli import mt
cammino = mt.percorso("it", "en")
if cammino is None:
    raise SystemExit(1)
print(f"  presenti: {' -> '.join(cammino)} e ritorno")
PY
if [[ -n "${MODELLI_MANCANTI:-}" ]]; then
    avv "scarico i modelli di traduzione (~190 MB)"
    python3 - <<'PY'
from voxpopuli import mt
riusciti = mt.installa([("it", "en"), ("en", "it")],
                       on_stato=lambda m: print(f"  {m}"))
print(f"  installati: {len(riusciti)} su 2")
PY
    ok "modelli di traduzione pronti"
else
    ok "modelli di traduzione gia' presenti"
fi

# ------------------------------------------------------- trascrizione ----
avv "verifico il modello di trascrizione"
if python3 - <<'PY'
from faster_whisper.utils import download_model
from voxpopuli import config as C
download_model("small", local_files_only=True, cache_dir=str(C.WHISPER_DIR))
raise SystemExit(0)
PY
then
    ok "modello 'small' gia' presente"
else
    avv "scarico il modello di trascrizione (~465 MB), puo' richiedere qualche minuto"
    if python3 - <<'PY'
from faster_whisper.utils import download_model
from voxpopuli import config as C
download_model("small", cache_dir=str(C.WHISPER_DIR))
raise SystemExit(0)
PY
    then
        ok "modello di trascrizione pronto"
    else
        ko "download non riuscito: verra' ritentato al primo avvio"
    fi
fi

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
