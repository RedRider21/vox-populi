# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Daniele Deplano (RedRider21)
"""La finestra che l'interlocutore vede.

Viene condivisa in Meet con "Condividi una finestra" e mostra l'ultima frase
dell'utente tradotta in inglese, a caratteri molto grandi, con le precedenti
attenuate sopra. Serve a due cose:

* la frase appena detta e' sempre nella stessa posizione, in fondo, cosi' si
  sa dove guardare senza cercarla;
* le frasi precedenti restano leggibili per qualche secondo, perche' chi legge
  una lingua straniera ha bisogno di rileggere se perde il filo.

Non contiene pulsanti ne' altri elementi di interfaccia: tutto cio' che appare
qui lo vede anche l'interlocutore.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk  # noqa: E402

from .. import config as C


class FinestraSpeaker(Gtk.Window):
    """Finestra da condividere, con lo storico recente in inglese."""

    def __init__(self, cfg: dict | None = None) -> None:
        super().__init__(title="Vox Populi - leggere qui")
        self.cfg = cfg or C.load()
        self._frasi: list[str] = []
        self._etichette: list[Gtk.Label] = []
        self._massimo = int(self.cfg.get("speaker_history", C.SPEAKER_HISTORY))

        self.set_default_size(760, 520)
        self.set_keep_above(False)      # condividendo la finestra non serve

        radice = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        radice.get_style_context().add_class("speaker-radice")
        self.add(radice)

        # Il contenuto e' ancorato in basso: la frase nuova compare sempre
        # nello stesso punto invece di far saltare il testo a ogni riga.
        self._contenuto = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._contenuto.set_valign(Gtk.Align.END)
        self._contenuto.set_margin_bottom(24)

        self._attesa = Gtk.Label(label="In attesa della conversazione...")
        self._attesa.get_style_context().add_class("speaker-istruzione")
        self._attesa.set_xalign(0)

        radice.pack_start(Gtk.Box(), True, True, 0)      # spaziatore elastico
        radice.pack_start(self._contenuto, False, False, 0)
        radice.pack_start(self._attesa, False, False, 0)

        self.connect("delete-event", self._su_chiusura)
        self.show_all()

    # ---------------------------------------------------------------- API ----
    def aggiungi(self, testo: str) -> None:
        """Aggiunge una frase tradotta.

        Va chiamata dal thread principale di GTK: la pipeline usa
        `GLib.idle_add` per arrivare qui.
        """
        testo = (testo or "").strip()
        if not testo:
            return
        self._attesa.set_visible(False)

        self._frasi.append(testo)
        etichetta = Gtk.Label(label=testo)
        etichetta.set_xalign(0)
        etichetta.set_line_wrap(True)
        etichetta.set_line_wrap_mode(2)      # PANGO_WRAP_WORD_CHAR
        etichetta.set_selectable(False)
        self._etichette.append(etichetta)
        self._contenuto.pack_start(etichetta, False, False, 0)

        # Oltre il massimo si scarta la piu' vecchia: lo storico serve a
        # rileggere, non a ricostruire l'intera conversazione.
        while len(self._frasi) > self._massimo:
            self._frasi.pop(0)
            vecchia = self._etichette.pop(0)
            self._contenuto.remove(vecchia)

        self._ridisegna()
        self.show_all()

    def sostituisci_ultima(self, testo: str) -> None:
        """Riscrive l'ultima frase (usato quando una traduzione viene rifinita)."""
        testo = (testo or "").strip()
        if not testo or not self._frasi:
            return
        self._frasi[-1] = testo
        self._etichette[-1].set_text(testo)
        self._ridisegna()

    def pulisci(self) -> None:
        """Svuota lo storico, a fine sessione."""
        for etichetta in self._etichette:
            self._contenuto.remove(etichetta)
        self._etichette.clear()
        self._frasi.clear()
        self._attesa.set_visible(True)
        self.show_all()

    def imposta_carattere(self, dimensione: int) -> None:
        """Aggiorna la dimensione del testo (richiede di rigenerare il CSS)."""
        self.cfg["speaker_font_size"] = dimensione

    # ------------------------------------------------------------- interno ----
    def _ridisegna(self) -> None:
        """Riapplica gli stili: solo l'ultima frase resta in evidenza."""
        for indice, etichetta in enumerate(self._etichette):
            contesto = etichetta.get_style_context()
            recente = indice == len(self._etichette) - 1
            contesto.remove_class("speaker-frase")
            contesto.remove_class("speaker-frase-recente")
            contesto.add_class(
                "speaker-frase-recente" if recente else "speaker-frase"
            )

    def _su_chiusura(self, _widget, _evento) -> bool:
        """La finestra si nasconde invece di distruggersi.

        Chiuderla davvero durante una call obbligherebbe a ricrearla e a
        rifare la condivisione in Meet: nasconderla e' reversibile.
        """
        self.hide()
        return True
