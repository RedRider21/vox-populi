# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Daniele Deplano (RedRider21)
"""Avvio dell'applicazione.

    python3 -m voxpopuli.main

Mette insieme le due finestre e la pipeline. Il punto delicato e' il confine
fra i thread: la pipeline produce risultati su thread propri, mentre GTK
accetta modifiche ai widget solo dal thread principale. Ogni callback che
tocca l'interfaccia passa quindi da `GLib.idle_add`, che accoda la chiamata
sul thread giusto.
"""

from __future__ import annotations

import argparse
import signal
import sys
import threading

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import GLib, Gtk  # noqa: E402

from . import audio as A
from . import config as C
from . import stt
from . import ui
from .ui import stile
from .pipeline import Motore


class Applicazione:
    """Coordina finestre e pipeline."""

    def __init__(self, apri_speaker: bool = False) -> None:
        self.cfg = C.load()
        stile.applica(
            int(self.cfg.get("font_size", 20)),
            int(self.cfg.get("speaker_font_size", 44)),
        )

        self.pannello = ui.FinestraPannello(
            cfg=self.cfg,
            on_avvia=self.avvia,
            on_ferma=self.ferma,
            on_mostra_speaker=self.mostra_speaker,
            on_dispositivi=self._su_dispositivi,
            on_half_duplex=self._su_half_duplex,
        )
        self.speaker = ui.FinestraSpeaker(self.cfg)
        self.speaker.hide()

        self.motore: Motore | None = None
        self._thread_avvio: threading.Thread | None = None

        self.pannello.connect("destroy", self._su_chiusura)
        if apri_speaker:
            self.mostra_speaker()

    # ------------------------------------------------------------- comandi ----
    def avvia(self) -> None:
        """Avvia la pipeline in un thread, per non congelare l'interfaccia."""
        if self.motore is not None:
            return
        sorgente_remota = self.cfg.get("remote_source", "")
        sorgente_mic = self.cfg.get("mic_source", "")
        if not sorgente_remota or not sorgente_mic:
            self.pannello.mostra_stato(
                _StatoFinto("Configura i dispositivi audio prima di avviare.")
            )
            return

        self.pannello.mostra_stato(_StatoFinto("Caricamento dei modelli..."))
        self.pannello.imposta_in_esecuzione(True)

        def procedura() -> None:
            motore = Motore(
                sorgente_remota=sorgente_remota,
                sorgente_mic=sorgente_mic,
                on_risultato=self._su_risultato,
                on_stato=self._su_stato,
                half_duplex=bool(self.cfg.get("half_duplex", True)),
                modello=self.cfg.get("whisper_model", C.WHISPER_MODEL),
            )
            try:
                motore.avvia()
            except (stt.SttError, A.AudioError) as exc:
                GLib.idle_add(self._mostra_errore, str(exc))
                GLib.idle_add(self.pannello.imposta_in_esecuzione, False)
                return
            except Exception as exc:              # noqa: BLE001 - messaggio all'utente
                GLib.idle_add(self._mostra_errore, f"Avvio non riuscito: {exc}")
                GLib.idle_add(self.pannello.imposta_in_esecuzione, False)
                return
            self.motore = motore

        self._thread_avvio = threading.Thread(target=procedura, daemon=True)
        self._thread_avvio.start()

    def ferma(self) -> None:
        """Arresta la pipeline e riabilita i controlli."""
        motore, self.motore = self.motore, None
        if motore is not None:
            threading.Thread(target=motore.ferma, daemon=True).start()
        self.pannello.imposta_in_esecuzione(False)
        self.pannello.mostra_stato(_StatoFinto())

    def mostra_speaker(self) -> None:
        """Mostra la finestra da condividere in Meet."""
        self.speaker.show_all()
        self.speaker.present()

    # -------------------------------------------------------- callback dati ----
    def _su_risultato(self, risultato) -> None:
        """Arriva da un thread della pipeline: rimbalza su GTK."""
        GLib.idle_add(self.pannello.mostra_risultato, risultato)
        if risultato.flusso == "locale":
            # Nella finestra condivisa va solo cio' che dice l'utente,
            # tradotto: e' quello che l'interlocutore deve capire.
            GLib.idle_add(self.speaker.aggiungi, risultato.traduzione)

    def _su_stato(self, stato) -> None:
        GLib.idle_add(self.pannello.mostra_stato, stato)

    def _mostra_errore(self, messaggio: str) -> None:
        self.pannello.mostra_stato(_StatoFinto(messaggio))

    # ------------------------------------------------------------ interfaccia ----
    def _su_dispositivi(self, remoto: str, mic: str) -> None:
        self.cfg["remote_source"] = remoto
        self.cfg["mic_source"] = mic
        C.save(self.cfg)

    def _su_half_duplex(self, attivo: bool) -> None:
        self.cfg["half_duplex"] = attivo
        C.save(self.cfg)
        if self.motore is not None:
            self.motore.half_duplex = attivo

    def _su_chiusura(self, *_args) -> None:
        self.ferma()
        C.save(self.cfg)
        Gtk.main_quit()


class _StatoFinto:
    """Stato minimo per riusare `mostra_stato` nei messaggi non della pipeline."""

    def __init__(self, errore: str = "", attivo: bool = False) -> None:
        self.errore = errore
        self.attivo = attivo
        self.frasi = 0
        self.ultima_latenza = 0.0
        self.media_latenza = 0.0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vox-populi",
        description="Sottotitoli e voce tradotti in tempo reale per Google Meet.",
    )
    parser.add_argument(
        "--apri-speaker", action="store_true",
        help="apre subito la finestra da condividere con l'interlocutore",
    )
    parser.add_argument(
        "--avvia", action="store_true",
        help="avvia la cattura senza dover premere il pulsante",
    )
    args = parser.parse_args(argv)

    signal.signal(signal.SIGINT, signal.SIG_DFL)   # Ctrl+C chiude
    applicazione = Applicazione(apri_speaker=args.apri_speaker)
    if args.avvia:
        applicazione.avvia()
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
