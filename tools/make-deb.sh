#!/bin/sh
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Daniele Deplano (RedRider21). Parte di Vox Populi.
#
# Costruisce il pacchetto .deb di Vox Populi (Debian, Ubuntu, Linux Mint).
# Usa lo STESSO install.sh dell'installazione manuale, montato su una radice
# finta con DESTDIR: quello che finisce nel pacchetto e' esattamente cio' che
# installerebbe lo script, senza duplicare la lista dei file.
#
#   ./tools/make-deb.sh                 -> packaging/vox-populi_<ver>_all.deb
#   ./tools/make-deb.sh --out /tmp      cambia la cartella di destinazione
#
# Il pacchetto e' "all" (indipendente dall'architettura): dentro c'e' solo
# Python, dati e uno script di shell.
#
# NOTA sulle dipendenze Python. faster-whisper, argostranslate ed edge-tts non
# sono pacchetti Debian, e non lo saranno: si installano in un ambiente
# dedicato la PRIMA VOLTA CHE SI AVVIA il programma, non qui. Il pacchetto
# resta percio' leggero (poche centinaia di KB) e dpkg non passa mezz'ora a
# scaricare roba: la preparazione la fa /usr/bin/vox-populi, dicendo prima
# quanto pesa. Le dipendenze dichiarate qui sotto sono solo quelle di sistema.
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT="$ROOT/packaging"
for a in "$@"; do
  case "$a" in
    --out) shift; OUT="${1:-$OUT}" ;;
    --out=*) OUT="${a#--out=}" ;;
  esac
done

command -v dpkg-deb >/dev/null 2>&1 || {
  echo "serve dpkg-deb (pacchetto dpkg)" >&2; exit 1; }

VER=$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$ROOT/voxpopuli/__init__.py")
[ -n "$VER" ] || VER=0.1.0
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT

echo "Vox Populi $VER: preparo l'albero del pacchetto..."
# install.sh e' bash (usa `set -o pipefail`), quindi va chiamato con bash.
DESTDIR="$STAGE" bash "$ROOT/install.sh" --prefix=/usr >/dev/null

# Il bytecode lo genera il postinst sulla macchina di destinazione: nel
# pacchetto NON deve finirci (sarebbe legato alla versione di Python di chi
# costruisce, e i .pyc stantii fanno eseguire codice vecchio).
find "$STAGE" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
find "$STAGE" -name '*.pyc' -delete 2>/dev/null || true
# Cache generate: le rifa' il postinst sulla macchina dell'utente, nel
# pacchetto non ci vanno (Debian le considera un errore).
rm -f "$STAGE/usr/share/applications/mimeinfo.cache" \
      "$STAGE/usr/share/icons/hicolor/icon-theme.cache" 2>/dev/null || true
# Le pagine di manuale nel pacchetto vanno compresse: dpkg non lo fa da solo
# e senza questo passaggio man non le trova, oltre al rilievo di lintian.
find "$STAGE/usr/share/man" -type f ! -name '*.gz' -exec gzip -9n {} + 2>/dev/null || true
# La radice dello staging nasce 0700 da mktemp: nel pacchetto non si nota
# (dpkg non tocca i permessi di /), ma chi lo estrae con dpkg-deb -x si
# ritroverebbe una cartella inaccessibile.
chmod 755 "$STAGE"

INSTALLED=$(du -sk "$STAGE/usr" | cut -f1)

mkdir -p "$STAGE/DEBIAN"
cat > "$STAGE/DEBIAN/control" <<EOF
Package: vox-populi
Version: $VER
Section: sound
Priority: optional
Architecture: all
Maintainer: Daniele Deplano <deplano.d@gmail.com>
Installed-Size: $INSTALLED
Depends: python3 (>= 3.10), python3-gi, python3-gi-cairo, gir1.2-gtk-3.0, python3-numpy, python3-venv, python3-pip, pulseaudio-utils, ffmpeg, libportaudio2
Recommends: zenity, fonts-dejavu-core
Homepage: https://github.com/RedRider21/vox-populi
Description: traduzione simultanea per le videochiamate, tutta in locale
 Vox Populi ascolta la voce dell'interlocutore e la propria, le trascrive,
 le traduce e le mostra in due finestre: un pannello che resta sopra la
 videochiamata, che vede solo l'utente, e una finestra da condividere con
 l'interlocutore, con il testo grande.
 .
 Funziona con 50 lingue e 322 voci sintetiche, interamente sul computer di
 chi lo usa: nessun servizio esterno, nessuna chiave API. L'interlocutore
 non deve installare ne' un programma ne' un'estensione.
 .
 La voce sintetica e l'elenco aggiornato delle voci richiedono Internet; i
 sottotitoli funzionano anche senza. I modelli di trascrizione e traduzione
 (~655 MB) si scaricano al primo avvio, sempre chiedendo conferma.
EOF

cat > "$STAGE/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
# Bytecode compilato QUI, sulla macchina di destinazione.
if command -v py3compile >/dev/null 2>&1; then
    py3compile -q /usr/lib/vox-populi 2>/dev/null || true
elif command -v python3 >/dev/null 2>&1; then
    python3 -m compileall -q /usr/lib/vox-populi >/dev/null 2>&1 || true
fi
command -v gtk-update-icon-cache >/dev/null 2>&1 && \
    gtk-update-icon-cache -q -f -t /usr/share/icons/hicolor 2>/dev/null || true
command -v update-desktop-database >/dev/null 2>&1 && \
    update-desktop-database -q /usr/share/applications 2>/dev/null || true

# Alla disinstallazione l'ambiente Python resta nella cartella dell'utente:
# e' roba sua, e puo' valere ~500 MB di download. Meglio dirglielo che
# cancellargliela di nascosto.
if [ "$1" = "configure" ]; then
    echo "Vox Populi installato. Al primo avvio preparera' le sue librerie Python"
    echo "in ~/.local/share/vox-populi/venv, dicendo prima quanto pesa."
fi
exit 0
EOF

cat > "$STAGE/DEBIAN/prerm" <<'EOF'
#!/bin/sh
set -e
# Via il bytecode generato dal postinst (non e' nel pacchetto, quindi dpkg non
# lo rimuoverebbe da solo e lascerebbe cartelle orfane).
if command -v py3clean >/dev/null 2>&1; then
    py3clean /usr/lib/vox-populi 2>/dev/null || true
else
    find /usr/lib/vox-populi -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
fi
exit 0
EOF

cat > "$STAGE/DEBIAN/postrm" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = "remove" ] || [ "$1" = "purge" ]; then
    rm -rf /usr/lib/vox-populi 2>/dev/null || true
    command -v gtk-update-icon-cache >/dev/null 2>&1 && \
        gtk-update-icon-cache -q -f -t /usr/share/icons/hicolor 2>/dev/null || true
fi
if [ "$1" = "purge" ]; then
    echo "I modelli e le librerie di Vox Populi restano in ~/.local/share/vox-populi/"
    echo "Se non servono piu', si cancella quella cartella: e' tutto li' dentro."
fi
exit 0
EOF
chmod 755 "$STAGE/DEBIAN/postinst" "$STAGE/DEBIAN/prerm" "$STAGE/DEBIAN/postrm"

# Licenza e changelog dove se li aspetta Debian
mkdir -p "$STAGE/usr/share/doc/vox-populi"
cp "$ROOT/README.md" "$STAGE/usr/share/doc/vox-populi/README.md" 2>/dev/null || true
printf 'vox-populi (%s) unstable; urgency=low\n\n  * Versione %s.\n\n -- %s  %s\n' \
  "$VER" "$VER" "Daniele Deplano <deplano.d@gmail.com>" "$(date -R)" \
  | gzip -9n > "$STAGE/usr/share/doc/vox-populi/changelog.gz"
gzip -9n < "$ROOT/COPYRIGHT" > "$STAGE/usr/share/doc/vox-populi/COPYRIGHT.gz" 2>/dev/null || true

cat > "$STAGE/usr/share/doc/vox-populi/copyright" <<'EOF'
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: vox-populi
Source: https://github.com/RedRider21/vox-populi

Files: *
Copyright: 2026 Daniele Deplano (RedRider21)
License: AGPL-3.0-or-later
 Questo programma e' software libero: lo si puo' ridistribuire e modificare
 secondo i termini della GNU Affero General Public License, versione 3 o
 successiva. Il testo completo e' in /usr/share/common-licenses/AGPL-3.
 .
 E' disponibile anche una licenza commerciale alternativa, per chi vuole
 integrarlo in prodotti proprietari senza gli obblighi dell'AGPL: vedi
 COMMERCIAL.md nel repository.

Files: debian/*
Copyright: 2026 Daniele Deplano (RedRider21)
License: AGPL-3.0-or-later

# Le librerie Python dell'applicazione (faster-whisper, argostranslate,
# ctranslate2, edge-tts, PyAV, onnxruntime) NON sono ridistribuite in questo
# pacchetto: si scaricano al primo avvio, con i loro termini (MIT, BSD,
# LGPL). L'elenco completo e' in COPYRIGHT nel repository.
EOF
find "$STAGE/usr/share/doc" -type d -exec chmod 755 {} +
find "$STAGE/usr/share/doc" -type f -exec chmod 644 {} +

mkdir -p "$OUT"
DEB="$OUT/vox-populi_${VER}_all.deb"
# --root-owner-group: dentro il pacchetto tutto risulta di root:root anche
# costruendo da utente normale.
dpkg-deb --root-owner-group --build "$STAGE" "$DEB" >/dev/null
# impronta accanto al pacchetto: va allegata alla release
( cd "$OUT" && sha256sum "vox-populi_${VER}_all.deb" > "vox-populi_${VER}_all.deb.sha256" )
echo "pacchetto: $DEB"
cat "$OUT/vox-populi_${VER}_all.deb.sha256"
command -v lintian >/dev/null 2>&1 && lintian "$DEB" 2>&1 | head -20 || true
