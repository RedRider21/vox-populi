# SPDX-License-Identifier: AGPL-3.0-or-later
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
from . import tts
from . import ui
from .ui import stile
from .pipeline import Motore
from .virtualmic import ETICHETTA_SINK, MicrofonoVirtuale, VirtualMicError


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
            on_voce=self._su_voce,
            on_prova_voce=self.prova_voce,
        )
        self.speaker = ui.FinestraSpeaker(self.cfg)
        self.speaker.hide()

        self.motore: Motore | None = None
        self._thread_avvio: threading.Thread | None = None
        # Microfono virtuale e voce sintetica esistono solo a interruttore
        # acceso: a interruttore spento l'app non tocca l'audio di sistema.
        self.microfono_virtuale: MicrofonoVirtuale | None = None
        self.voce: tts.Voce | None = None

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
            # La voce sintetica si prepara per prima: se fallisce, la
            # conversazione deve comunque partire coi soli sottotitoli.
            if bool(self.cfg.get("voice_enabled", False)):
                self._prepara_voce(sorgente_mic)

            motore = Motore(
                sorgente_remota=sorgente_remota,
                sorgente_mic=sorgente_mic,
                on_risultato=self._su_risultato,
                on_stato=self._su_stato,
                half_duplex=bool(self.cfg.get("half_duplex", True)),
                modello=self.cfg.get("whisper_model", C.WHISPER_MODEL),
                on_parlato_locale=self._su_parlato_locale,
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
        """Arresta la pipeline, smonta la voce e riabilita i controlli."""
        motore, self.motore = self.motore, None
        if motore is not None:
            threading.Thread(target=motore.ferma, daemon=True).start()
        self._smonta_voce()
        self.pannello.imposta_in_esecuzione(False)
        self.pannello.mostra_stato(_StatoFinto())

    # ------------------------------------------------------- voce sintetica ----
    def _prepara_voce(self, microfono: str) -> None:
        """Carica il microfono virtuale e apre la coda della voce. Bloccante."""
        try:
            virtuale = MicrofonoVirtuale(microfono)
            sink = virtuale.attiva()
        except VirtualMicError as exc:
            GLib.idle_add(
                self._mostra_errore,
                f"Voce non attivata: {exc}. I sottotitoli funzionano lo stesso.",
            )
            return

        voce = tts.Voce(
            sink="vox_populi_mic",
            voce=str(self.cfg.get("tts_voice", tts.VOCE_PREDEFINITA)),
            ducka=virtuale.ducka,
            ducka_a_tempo=virtuale.ducka_a_tempo,
        )
        voce.avvia()
        self.microfono_virtuale = virtuale
        self.voce = voce
        # All'utente serve il nome che legge nel menu di Meet, non quello che
        # usa pactl: sono diversi, e confonderli il giorno della call costa.
        GLib.idle_add(
            self.pannello.mostra_sorgente_virtuale, f"Monitor of {ETICHETTA_SINK}",
        )
        print(f"[voce] microfono virtuale pronto ({sink}): "
              f"in Meet scegli 'Monitor of {ETICHETTA_SINK}'")

    def _smonta_voce(self) -> None:
        """Chiude voce e microfono virtuale, ripristinando l'audio di sistema."""
        voce, self.voce = self.voce, None
        virtuale, self.microfono_virtuale = self.microfono_virtuale, None
        if voce is not None:
            voce.ferma()
        if virtuale is not None:
            virtuale.chiudi()

    def prova_voce(self) -> None:
        """Fa dire una frase alla voce, per sentire come suona. Non blocca."""
        voce = self.voce
        if voce is None:
            self.pannello.mostra_stato(_StatoFinto(
                "La voce e' attiva solo durante la conversazione: avvia prima."
            ))
            return
        threading.Thread(target=voce.prova, daemon=True).start()

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
            # La voce segue lo stesso percorso del testo: se compare nella
            # finestra, va anche pronunciata.
            if self.voce is not None:
                self.voce.di(risultato.traduzione)

    def _su_stato(self, stato) -> None:
        GLib.idle_add(self.pannello.mostra_stato, stato)

    def _su_parlato_locale(self) -> None:
        """L'utente ha iniziato a parlare: chiude il passaggio della voce reale.

        Arriva dal thread di cattura, che non deve mai aspettare: la chiamata a
        pactl e' breve ma e' pur sempre un processo, quindi va su un thread suo.
        Chiudere adesso, e non quando la traduzione e' pronta, e' cio' che
        impedisce all'interlocutore di sentire l'italiano prima dell'inglese.
        """
        virtuale = self.microfono_virtuale
        if virtuale is None:
            return
        threading.Thread(target=virtuale.ducka, args=(True,), daemon=True).start()

    def _su_voce(self, attivo: bool) -> None:
        """Interruttore della voce dal pannello."""
        self.cfg["voice_enabled"] = attivo
        C.save(self.cfg)
        if not attivo and self.motore is not None:
            # Spegnere la voce a conversazione avviata deve riaprire subito il
            # microfono, altrimenti l'interlocutore non sente piu' nulla.
            threading.Thread(target=self._smonta_voce, daemon=True).start()
            self.pannello.mostra_sorgente_virtuale(None)

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

    applicazione = Applicazione(apri_speaker=args.apri_speaker)

    def _chiudi_per_segnale(_numero, _frame) -> None:
        """Chiude come se l'utente avesse chiuso la finestra.

        Non basta uscire: la voce sintetica ha caricato moduli di PulseAudio che
        resterebbero nel sistema, lasciando il microfono del computer in uno
        stato strano. Distruggere il pannello passa dalla stessa pulizia della
        chiusura normale.
        """
        applicazione.pannello.destroy()

    for segnale in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        try:
            signal.signal(segnale, _chiudi_per_segnale)
        except (ValueError, OSError):
            pass                      # segnale non disponibile su questa piattaforma

    if args.avvia:
        applicazione.avvia()
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
