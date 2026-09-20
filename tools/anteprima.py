#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Daniele Deplano (RedRider21)
"""Genera le schermate del README con le finestre vere.

Non simula niente: prende i campioni audio di prova, li fa passare davvero per
faster-whisper e argostranslate, e mette i risultati nelle stesse finestre che
si vedono durante la call. Poi le fotografa. Le immagini che ne escono
mostrano l'interfaccia reale con testi reali prodotti dai modelli.

Uso:
    python3 tools/anteprima.py [cartella_campioni] [cartella_uscita]

Predefiniti: /tmp/vp_test e /tmp/vp_shot (mai sulla Scrivania).
I campioni si generano con /tmp/vp_test/gen.py, oppure registrando due voci.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

import numpy as np  # noqa: E402

from voxpopuli import config as C  # noqa: E402
from voxpopuli import mt, stt  # noqa: E402
from voxpopuli.pipeline import Risultato, Stato  # noqa: E402
from voxpopuli.ui import stile  # noqa: E402
from voxpopuli.ui.panel import FinestraPannello  # noqa: E402
from voxpopuli.ui.speaker import FinestraSpeaker  # noqa: E402

CAMPIONI = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/vp_test")
USCITA = Path(sys.argv[2] if len(sys.argv) > 2 else "/tmp/vp_shot")
QUANTE = 4          # frasi per lato: quante ne mostra la finestra condivisa


def decodifica(percorso: Path) -> np.ndarray:
    """Legge un file audio come float32 mono a 16 kHz, il formato di Whisper."""
    grezzo = subprocess.run(
        ["ffmpeg", "-v", "quiet", "-i", str(percorso),
         "-f", "f32le", "-ac", "1", "-ar", str(C.SAMPLE_RATE), "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(grezzo, dtype=np.float32)


def fotografa(finestra: Gtk.Window, nome: str) -> None:
    """Salva l'immagine di una sola finestra, senza il resto dello schermo."""
    subprocess.run(
        ["import", "-window", str(finestra.get_window().get_xid()), str(USCITA / nome)],
        check=True,
    )


def prepara_frasi() -> tuple[list[Risultato], list[Risultato]]:
    """Trascrive e traduce i campioni. Restituisce (frasi di lui, frasi tue)."""
    print("Carico i modelli...", flush=True)
    stt.prepara()
    mt.prepara(C.LANG_IT, C.LANG_EN)

    remoti: list[Risultato] = []
    locali: list[Risultato] = []

    for indice in range(QUANTE):
        # L'interlocutore: inglese in ingresso, italiano a schermo.
        file_en = CAMPIONI / f"en_{indice}.wav"
        testo_en, t_stt = stt.trascrivi(decodifica(file_en), C.LANG_EN)
        tradotto_it, t_mt = mt.traduci(testo_en, C.LANG_EN, C.LANG_IT)
        remoti.append(Risultato(
            flusso="remoto", originale=testo_en, traduzione=tradotto_it,
            lingua_orig=C.LANG_EN, lingua_trad=C.LANG_IT, t_stt=t_stt, t_mt=t_mt,
        ))
        print(f"  LORO {indice + 1}: {tradotto_it[:70]}", flush=True)

        # L'utente: italiano in ingresso, inglese a schermo e da condividere.
        file_it = CAMPIONI / f"it_{indice}.wav"
        testo_it, t_stt = stt.trascrivi(decodifica(file_it), C.LANG_IT)
        tradotto_en, t_mt = mt.traduci(testo_it, C.LANG_IT, C.LANG_EN)
        locali.append(Risultato(
            flusso="locale", originale=testo_it, traduzione=tradotto_en,
            lingua_orig=C.LANG_IT, lingua_trad=C.LANG_EN, t_stt=t_stt, t_mt=t_mt,
        ))
        print(f"  TU   {indice + 1}: {tradotto_en[:70]}", flush=True)

    return remoti, locali


def main() -> int:
    for file_necessario in (CAMPIONI / "en_0.wav", CAMPIONI / "it_0.wav"):
        if not file_necessario.exists():
            print(f"Manca {file_necessario}. Genera prima i campioni di prova.",
                  file=sys.stderr)
            return 1
    USCITA.mkdir(parents=True, exist_ok=True)

    remoti, locali = prepara_frasi()

    cfg = C.load()
    stile.applica(
        int(cfg.get("font_size", 20)),
        int(cfg.get("speaker_font_size", 44)),
        str(cfg.get("theme", stile.TEMA_PREDEFINITO)),
    )

    pannello = FinestraPannello(
        cfg, on_avvia=lambda: None, on_ferma=lambda: None,
        on_mostra_speaker=lambda: None, on_dispositivi=lambda _a, _b: None,
        on_half_duplex=lambda _a: None,
    )
    speaker = FinestraSpeaker(cfg)

    def popola() -> bool:
        """Riempie le finestre come farebbe la pipeline durante la call."""
        for risultato in remoti:
            pannello.mostra_risultato(risultato)
        for risultato in locali:
            pannello.mostra_risultato(risultato)
            speaker.aggiungi(risultato.traduzione)

        ultima = locali[-1]
        pannello.mostra_stato(Stato(
            attivo=True,
            sorgente_remota=str(cfg.get("remote_source", "")),
            sorgente_mic=str(cfg.get("mic_source", "")),
            ultima_latenza=ultima.latenza,
            media_latenza=sum(r.latenza for r in locali + remoti) / (2 * QUANTE),
            frasi=2 * QUANTE,
        ))
        pannello.imposta_in_esecuzione(True)
        return False

    def scatta() -> bool:
        fotografa(pannello, "pannello.png")
        fotografa(speaker, "speaker.png")
        print(f"Salvate in {USCITA}", flush=True)
        return False

    def scatta_con_voce() -> bool:
        """Seconda immagine del pannello, con la voce sintetica accesa."""
        pannello._check_voce.set_active(True)
        pannello.mostra_sorgente_virtuale("Monitor of VoxPopuli_Mic")
        return False

    def scatta_voce() -> bool:
        fotografa(pannello, "pannello-voce.png")
        return False

    GLib.timeout_add(900, popola)
    GLib.timeout_add(2000, scatta)
    GLib.timeout_add(2500, scatta_con_voce)
    GLib.timeout_add(3200, scatta_voce)

    # Un'immagine per ogni schema cromatico, cosi' si vedono tutti insieme
    # senza doverli provare a uno a uno.
    istante = 3600

    def applica_tema(chiave: str):
        def passo() -> bool:
            stile.applica(
                int(cfg.get("font_size", 20)),
                int(cfg.get("speaker_font_size", 44)),
                chiave,
            )
            return False
        return passo

    def scatta_tema(chiave: str):
        def passo() -> bool:
            fotografa(pannello, f"tema-{chiave}.png")
            return False
        return passo

    for chiave in stile.temi_disponibili():
        GLib.timeout_add(istante, applica_tema(chiave))
        GLib.timeout_add(istante + 350, scatta_tema(chiave))
        istante += 700

    GLib.timeout_add(istante + 200, Gtk.main_quit)
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
