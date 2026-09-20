#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Daniele Deplano (RedRider21)
#
# Installa Vox Populi su Debian/Ubuntu e affini.
#
# Uso:
#     ./install.sh          chiede conferma prima di scaricare i modelli
#     ./install.sh --si     procede senza chiedere (per script automatici)
#     ./install.sh --prefix=/usr
#                           copia SOLO i file sotto quella radice, senza
#                           toccare apt, pip o i modelli: serve a costruire il
#                           pacchetto .deb. Rispetta DESTDIR.
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

# ------------------------------------------- albero per il pacchetto ------
# Con --prefix non si installa niente nel sistema e non si scarica niente:
# si copiano i file dentro una radice (DESTDIR) e basta. Lo usa
# tools/make-deb.sh, cosi' il contenuto del pacchetto e' esattamente cio' che
# installerebbe questo script, senza tenere due liste di file da allineare.
PREFIX=""
for arg in "$@"; do
    case "$arg" in
        --prefix=*) PREFIX="${arg#--prefix=}" ;;
    esac
done

if [[ -n "$PREFIX" ]]; then
    BASE="${DESTDIR:-}$PREFIX"
    echo "=== Vox Populi: preparo l'albero in $BASE ==="

    # Il codice, senza bytecode: i .pyc li rigenera il postinst sulla macchina
    # di destinazione, e quelli di un'altra versione di Python farebbero
    # eseguire codice vecchio.
    install -d "$BASE/lib/vox-populi"
    cp -r "$ROOT_DIR/voxpopuli" "$BASE/lib/vox-populi/"
    find "$BASE/lib/vox-populi" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
    find "$BASE/lib/vox-populi" -name '*.pyc' -delete 2>/dev/null || true
    # I permessi non devono dipendere dall'umask di chi costruisce: nel
    # pacchetto Debian i file sono 0644 e le cartelle 0755, sempre.
    find "$BASE/lib/vox-populi" -type d -exec chmod 755 {} +
    find "$BASE/lib/vox-populi" -type f -exec chmod 644 {} +
    install -m 644 "$ROOT_DIR/requirements.txt" "$BASE/lib/vox-populi/requirements.txt"

    # Il comando: quello "di sistema", che prepara l'ambiente al primo avvio.
    install -d "$BASE/bin"
    install -m 755 "$ROOT_DIR/data/vox-populi-system" "$BASE/bin/vox-populi"

    # Voce di menu e icone
    install -d "$BASE/share/applications"
    install -m 644 "$ROOT_DIR/data/applications/vox-populi.desktop" \
        "$BASE/share/applications/vox-populi.desktop"
    for lato in 32 48 64 128 256; do
        install -d "$BASE/share/icons/hicolor/${lato}x${lato}/apps"
        install -m 644 "$ROOT_DIR/data/icons/vox-populi-$lato.png" \
            "$BASE/share/icons/hicolor/${lato}x${lato}/apps/vox-populi.png"
    done

    # Documentazione
    install -d "$BASE/share/doc/vox-populi"
    for f in README.md COPYRIGHT COMMERCIAL.md CLA.md \
             docs/manuale.md docs/guida-call.md; do
        if [[ -f "$ROOT_DIR/$f" ]]; then
            install -m 644 "$ROOT_DIR/$f" "$BASE/share/doc/vox-populi/$(basename "$f")"
        fi
    done

    # Pagina di manuale
    install -d "$BASE/share/man/man1"
    install -m 644 "$ROOT_DIR/data/man/vox-populi.1" \
        "$BASE/share/man/man1/vox-populi.1"

    echo "  ok  albero pronto ($(du -sk "$BASE" | cut -f1) KB)"
    exit 0
fi

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
