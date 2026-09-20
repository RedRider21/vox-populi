# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Daniele Deplano (RedRider21)
"""Il pannello di controllo, quello che l'utente tiene sopra Meet.

Mostra entrambe le direzioni della conversazione - cosa dice l'interlocutore
tradotto in italiano e cosa dice l'utente tradotto in inglese - insieme ai
comandi: avvio e arresto, scelta dei dispositivi, apertura della finestra da
condividere e le statistiche di latenza.

E' pensato per essere letto di sfuggita mentre si parla: le traduzioni sono
grandi e colorate, le trascrizioni originali piccole e in grigio, cosi'
l'occhio trova subito cio' che serve senza leggere tutto.
"""

from __future__ import annotations

from typing import Callable

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import GLib, Gtk  # noqa: E402

from .. import audio as A
from .. import config as C
from ..tts import voce_predefinita, voci_per_lingua
from . import stile


class FinestraPannello(Gtk.Window):
    """Pannello con i sottotitoli delle due direzioni e i comandi."""

    def __init__(
        self,
        cfg: dict,
        on_avvia: Callable[[], None],
        on_ferma: Callable[[], None],
        on_mostra_speaker: Callable[[], None],
        on_dispositivi: Callable[[str, str], None],
        on_half_duplex: Callable[[bool], None],
        on_voce: Callable[[bool], None] | None = None,
        on_prova_voce: Callable[[], None] | None = None,
        on_lingue: Callable[[str, str], None] | None = None,
        on_installa_modelli: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(title="Vox Populi")
        self.cfg = cfg
        self._on_avvia = on_avvia
        self._on_ferma = on_ferma
        self._on_mostra_speaker = on_mostra_speaker
        self._on_dispositivi = on_dispositivi
        self._on_half_duplex = on_half_duplex
        self._on_voce = on_voce
        self._on_prova_voce = on_prova_voce
        self._on_lingue = on_lingue
        self._on_installa_modelli = on_installa_modelli
        self._in_esecuzione = False
        # I menu hanno liste diverse (monitor e microfoni): invece di fidarsi
        # dell'indice globale, tengo per ogni combo la propria lista. PyGObject
        # non espone set_data/get_data di GObject, quindi uso un dizionario.
        self._elenchi_combo: dict[int, list[A.Sorgente]] = {}

        finestra = cfg.get("window", {})
        self.set_default_size(int(finestra.get("w", 620)), int(finestra.get("h", 460)))
        self.move(int(finestra.get("x", 40)), int(finestra.get("y", 40)))
        self.set_keep_above(True)        # deve restare sopra la call
        self.set_border_width(0)

        radice = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        radice.get_style_context().add_class("radice")
        self.add(radice)

        radice.pack_start(self._crea_intestazione(), False, False, 0)

        # Le due direzioni, in riquadri separati. Il testo delle intestazioni
        # dipende dalle lingue scelte, quindi si riempie dopo.
        self._riquadro_remoto = self._crea_riquadro("", "tradotto-remoto")
        self._riquadro_locale = self._crea_riquadro("", "tradotto-locale")
        # I due riquadri si dividono lo spazio disponibile: cosi' il pannello
        # resta leggibile anche quando l'utente lo allarga.
        radice.pack_start(self._riquadro_remoto["contenitore"], True, True, 0)
        radice.pack_start(self._riquadro_locale["contenitore"], True, True, 0)

        radice.pack_start(self._crea_barra(), False, False, 0)
        radice.pack_start(self._crea_dispositivi(), False, False, 0)

        self.connect("delete-event", self._su_chiusura)
        self.connect("configure-event", self._salva_posizione)
        self._aggiorna_sorgenti()
        self._aggiorna_intestazioni()
        self._aggiorna_voci()
        self.show_all()

    # ------------------------------------------------------------ costruzione ----
    def _crea_intestazione(self) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.get_style_context().add_class("intestazione")

        titolo = Gtk.Label(label="Vox Populi")
        titolo.get_style_context().add_class("titolo")
        titolo.set_xalign(0)
        box.pack_start(titolo, False, False, 0)

        self._etichetta_stato = Gtk.Label(label="● fermo")
        self._etichetta_stato.get_style_context().add_class("stato-fermo")
        self._etichetta_stato.set_xalign(0)
        box.pack_start(self._etichetta_stato, False, False, 0)

        self._etichetta_errore = Gtk.Label(label="")
        self._etichetta_errore.get_style_context().add_class("errore")
        self._etichetta_errore.set_ellipsize(3)     # PANGO_ELLIPSIZE_END
        box.pack_start(self._etichetta_errore, True, True, 0)

        return box

    def _crea_riquadro(self, intestazione: str, classe_tradotto: str) -> dict:
        contenitore = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        contenitore.get_style_context().add_class("riquadro")

        etichetta = Gtk.Label(label=intestazione)
        etichetta.get_style_context().add_class("intestazione-riquadro")
        etichetta.set_xalign(0)
        contenitore.pack_start(etichetta, False, False, 0)

        originale = Gtk.Label(label="")
        originale.get_style_context().add_class("originale")
        originale.set_xalign(0)
        originale.set_line_wrap(True)
        originale.set_selectable(True)
        contenitore.pack_start(originale, False, False, 0)

        tradotto = Gtk.Label(label="")
        tradotto.get_style_context().add_class("tradotto")
        tradotto.get_style_context().add_class(classe_tradotto)
        tradotto.set_xalign(0)
        tradotto.set_line_wrap(True)
        tradotto.set_selectable(True)
        contenitore.pack_start(tradotto, False, False, 0)

        return {
            "contenitore": contenitore, "intestazione": etichetta,
            "originale": originale, "tradotto": tradotto,
        }

    def _crea_barra(self) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.get_style_context().add_class("barra")

        self._pulsante_avvia = Gtk.Button(label="Avvia")
        self._pulsante_avvia.get_style_context().add_class("primario")
        self._pulsante_avvia.connect("clicked", self._su_avvia)
        box.pack_start(self._pulsante_avvia, False, False, 0)

        pulsante_speaker = Gtk.Button(label="Finestra per lui")
        pulsante_speaker.set_tooltip_text(
            "Apre la finestra da condividere in Meet con 'Condividi una finestra'"
        )
        pulsante_speaker.connect("clicked", lambda _b: self._on_mostra_speaker())
        box.pack_start(pulsante_speaker, False, False, 0)

        self._etichetta_stat = Gtk.Label(label="pronto")
        self._etichetta_stat.get_style_context().add_class("dettaglio")
        self._etichetta_stat.set_xalign(1)
        box.pack_end(self._etichetta_stat, False, False, 0)

        return box

    def _crea_dispositivi(self) -> Gtk.Box:
        contenitore = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        contenitore.get_style_context().add_class("barra")

        # Le due lingue della conversazione. Da queste dipendono le intestazioni
        # dei riquadri, la voce sintetica e i modelli da scaricare.
        riga_lingue = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        etichetta_mia = Gtk.Label(label="Parlo:")
        etichetta_mia.get_style_context().add_class("dettaglio")
        riga_lingue.pack_start(etichetta_mia, False, False, 0)
        self._combo_mia = Gtk.ComboBoxText()
        self._combo_mia.set_tooltip_text("La lingua in cui parli tu")
        riga_lingue.pack_start(self._combo_mia, True, True, 0)

        etichetta_sua = Gtk.Label(label="Lui parla:")
        etichetta_sua.get_style_context().add_class("dettaglio")
        riga_lingue.pack_start(etichetta_sua, False, False, 0)
        self._combo_sua = Gtk.ComboBoxText()
        self._combo_sua.set_tooltip_text("La lingua del tuo interlocutore")
        riga_lingue.pack_start(self._combo_sua, True, True, 0)

        self._pulsante_modelli = Gtk.Button(label="Installa modelli")
        self._pulsante_modelli.set_tooltip_text(
            "Scarica i modelli di traduzione mancanti per la coppia di lingue "
            "scelta (circa 94 MB per lingua)"
        )
        self._pulsante_modelli.connect(
            "clicked", lambda _b: self._installa_modelli(),
        )
        riga_lingue.pack_start(self._pulsante_modelli, False, False, 0)
        contenitore.pack_start(riga_lingue, False, False, 0)

        # L'elenco e' quello di argostranslate, ordinato per nome italiano.
        for codice, nome in sorted(C.LINGUE.items(), key=lambda coppia: coppia[1]):
            self._combo_mia.append(codice, nome)
            self._combo_sua.append(codice, nome)
        self._combo_mia.set_active_id(str(self.cfg.get("my_lang", C.LANG_IT)))
        self._combo_sua.set_active_id(str(self.cfg.get("their_lang", C.LANG_EN)))
        # Il cambio lingua muove parecchie cose: si collega dopo la
        # preselezione, altrimenti scatterebbe una volta a vuoto all'avvio.
        self._combo_mia.connect("changed", self._su_cambio_lingua)
        self._combo_sua.connect("changed", self._su_cambio_lingua)

        riga1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        etichetta = Gtk.Label(label="Ascolta:")
        etichetta.get_style_context().add_class("dettaglio")
        riga1.pack_start(etichetta, False, False, 0)
        self._combo_remoto = Gtk.ComboBoxText()
        self._combo_remoto.set_tooltip_text(
            "Da dove arriva la voce dell'interlocutore: scegli il monitor "
            "dell'uscita audio in uso (casse o cuffie)"
        )
        self._combo_remoto.connect("changed", self._su_cambio_dispositivo)
        riga1.pack_start(self._combo_remoto, True, True, 0)
        contenitore.pack_start(riga1, False, False, 0)

        riga2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        etichetta2 = Gtk.Label(label="Microfono:")
        etichetta2.get_style_context().add_class("dettaglio")
        riga2.pack_start(etichetta2, False, False, 0)
        self._combo_mic = Gtk.ComboBoxText()
        self._combo_mic.set_tooltip_text("Il tuo microfono")
        self._combo_mic.connect("changed", self._su_cambio_dispositivo)
        riga2.pack_start(self._combo_mic, True, True, 0)
        contenitore.pack_start(riga2, False, False, 0)

        self._check_half = Gtk.CheckButton(
            label="Non trascrivere il microfono mentre l'altro parla (evita l'eco)"
        )
        self._check_half.get_style_context().add_class("dettaglio")
        self._check_half.set_active(bool(self.cfg.get("half_duplex", True)))
        self._check_half.connect("toggled", self._su_half_duplex)
        contenitore.pack_start(self._check_half, False, False, 0)

        riga3 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._check_voce = Gtk.CheckButton(
            label="Voce inglese: l'interlocutore sente la traduzione"
        )
        self._check_voce.get_style_context().add_class("dettaglio")
        self._check_voce.set_active(bool(self.cfg.get("voice_enabled", False)))
        self._check_voce.set_tooltip_text(
            "Sostituisce la tua voce con una sintetica in inglese. Mentre parli "
            "l'interlocutore sente un breve silenzio, poi la frase in inglese."
        )
        self._check_voce.connect("toggled", self._su_voce)
        riga3.pack_start(self._check_voce, False, False, 0)

        self._combo_voce = Gtk.ComboBoxText()
        self._combo_voce.set_tooltip_text(
            "La voce sintetica da usare: quelle elencate pronunciano la lingua "
            "dell'interlocutore"
        )
        # Il contenuto dipende dalla lingua dell'interlocutore e viene messo
        # da _aggiorna_voci(), che tiene conto anche del tema scelto.
        self._combo_voce.connect("changed", self._su_cambio_voce)
        # A voce spenta la scelta non ha senso: la si mostra comunque, perche'
        # l'utente veda che esiste, ma non la si lascia toccare.
        self._combo_voce.set_sensitive(self._check_voce.get_active())
        riga3.pack_start(self._combo_voce, True, True, 0)

        pulsante_prova = Gtk.Button(label="Prova")
        pulsante_prova.set_tooltip_text("Pronuncia una frase di prova")
        pulsante_prova.connect("clicked", lambda _b: self._prova_voce())
        riga3.pack_start(pulsante_prova, False, False, 0)
        contenitore.pack_start(riga3, False, False, 0)

        # Qui compare il nome del microfono da scegliere in Meet quando la voce
        # e' attiva: e' l'informazione che serve il giorno della call.
        self._etichetta_virtuale = Gtk.Label(label="")
        self._etichetta_virtuale.get_style_context().add_class("dettaglio")
        self._etichetta_virtuale.set_xalign(0)
        self._etichetta_virtuale.set_line_wrap(True)
        contenitore.pack_start(self._etichetta_virtuale, False, False, 0)

        riga_tema = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        etichetta_tema = Gtk.Label(label="Colori:")
        etichetta_tema.get_style_context().add_class("dettaglio")
        riga_tema.pack_start(etichetta_tema, False, False, 0)
        self._combo_tema = Gtk.ComboBoxText()
        self._combo_tema.set_tooltip_text(
            "Cambia i colori di entrambe le finestre: ha effetto subito"
        )
        for chiave, nome in stile.temi_disponibili().items():
            self._combo_tema.append(chiave, nome)
        if not self._combo_tema.set_active_id(
            str(self.cfg.get("theme", stile.TEMA_PREDEFINITO))
        ):
            self._combo_tema.set_active_id(stile.TEMA_PREDEFINITO)
        self._combo_tema.connect("changed", self._su_cambio_tema)
        riga_tema.pack_start(self._combo_tema, False, False, 0)
        contenitore.pack_start(riga_tema, False, False, 0)

        return contenitore

    # ---------------------------------------------------------------- API ----
    def mostra_risultato(self, risultato) -> None:
        """Mostra una frase tradotta. Sempre dal thread principale di GTK."""
        riquadro = (
            self._riquadro_remoto if risultato.flusso == "remoto"
            else self._riquadro_locale
        )
        riquadro["originale"].set_text(risultato.originale)
        riquadro["tradotto"].set_text(risultato.traduzione)

    def mostra_stato(self, stato) -> None:
        """Aggiorna stato, statistiche ed eventuale errore."""
        if stato.attivo:
            self._etichetta_stato.set_text("● in ascolto")
            self._imposta_classe_stato("stato-attivo")
        else:
            self._etichetta_stato.set_text("● fermo")
            self._imposta_classe_stato("stato-fermo")

        if stato.frasi:
            self._etichetta_stat.set_text(
                f"{stato.ultima_latenza:.2f}s ultima · "
                f"{stato.media_latenza:.2f}s media · {stato.frasi} frasi"
            )
        self._etichetta_errore.set_text(stato.errore or "")

    def imposta_in_esecuzione(self, attivo: bool) -> None:
        """Blocca i menu dei dispositivi mentre il motore gira."""
        self._in_esecuzione = attivo
        self._combo_remoto.set_sensitive(not attivo)
        self._combo_mic.set_sensitive(not attivo)
        self._pulsante_avvia.set_label("Ferma" if attivo else "Avvia")

    def mostra_se_necessario(self) -> None:
        self.show_all()
        self.present()

    # ------------------------------------------------------------- interno ----
    def _imposta_classe_stato(self, classe: str) -> None:
        contesto = self._etichetta_stato.get_style_context()
        for nome in ("stato-attivo", "stato-fermo", "stato-errore"):
            contesto.remove_class(nome)
        contesto.add_class(classe)

    def _su_avvia(self, _bottone) -> None:
        if self._in_esecuzione:
            self._on_ferma()
        else:
            self._on_avvia()

    def _su_cambio_dispositivo(self, _widget) -> None:
        if self._in_esecuzione:
            return
        remoto = self._sorgente_da_combo(self._combo_remoto)
        mic = self._sorgente_da_combo(self._combo_mic)
        if remoto is not None and mic is not None:
            self._on_dispositivi(remoto.nome, mic.nome)

    def _su_half_duplex(self, check: Gtk.CheckButton) -> None:
        self._on_half_duplex(check.get_active())

    def _su_voce(self, check: Gtk.CheckButton) -> None:
        attivo = check.get_active()
        self._combo_voce.set_sensitive(attivo)
        if not attivo:
            self._etichetta_virtuale.set_text("")
        if self._on_voce is not None:
            self._on_voce(attivo)

    def _su_cambio_voce(self, combo: Gtk.ComboBoxText) -> None:
        scelta = combo.get_active_id()
        if not scelta:
            return
        self.cfg["tts_voice"] = scelta
        C.save(self.cfg)
        # La voce nuova ha effetto dalla frase successiva: il motore la rilegge
        # solo quando riparte, quindi vale la pena dirlo invece di far credere
        # che il cambio sia immediato.
        if self._in_esecuzione:
            self._etichetta_virtuale.set_text(
                "Voce cambiata: avra' effetto al prossimo avvio."
            )

    def _su_cambio_lingua(self, _widget) -> None:
        """Cambio di lingua: aggiorna intestazioni e voci, poi avvisa main."""
        mia = self._combo_mia.get_active_id()
        sua = self._combo_sua.get_active_id()
        if not mia or not sua:
            return
        if mia == sua:
            # Tradurre da una lingua a se stessa non significa niente: si dice
            # e non si applica, invece di lasciare il pannello in uno stato
            # che sembra funzionante ma non traduce.
            self._etichetta_errore.set_text("Le due lingue devono essere diverse.")
            return
        self._etichetta_errore.set_text("")
        self.cfg["my_lang"] = mia
        self.cfg["their_lang"] = sua
        C.save(self.cfg)
        self._aggiorna_intestazioni()
        self._aggiorna_voci()
        if self._on_lingue is not None:
            self._on_lingue(mia, sua)

    def _su_cambio_tema(self, combo: Gtk.ComboBoxText) -> None:
        """Cambio di tema: si applica subito, senza riavviare niente."""
        tema = combo.get_active_id()
        if not tema:
            return
        self.cfg["theme"] = tema
        C.save(self.cfg)
        stile.applica(
            int(self.cfg.get("font_size", 20)),
            int(self.cfg.get("speaker_font_size", 44)),
            tema,
        )

    def _installa_modelli(self) -> None:
        if self._on_installa_modelli is not None:
            self._on_installa_modelli()

    def _aggiorna_intestazioni(self) -> None:
        """Riscrive le intestazioni dei riquadri con le lingue scelte."""
        mia = C.nome_lingua(str(self.cfg.get("my_lang", C.LANG_IT)))
        sua = C.nome_lingua(str(self.cfg.get("their_lang", C.LANG_EN)))
        self._riquadro_remoto["intestazione"].set_text(f"LORO · {sua} → {mia}")
        self._riquadro_locale["intestazione"].set_text(f"TU · {mia} → {sua}")

    def _aggiorna_voci(self) -> None:
        """Ripopola il menu delle voci per la lingua dell'interlocutore.

        La voce sintetica pronuncia cio' che l'interlocutore deve sentire,
        quindi dev'essere della SUA lingua: cambiando quella, le voci di
        prima non servono piu'.
        """
        sua = str(self.cfg.get("their_lang", C.LANG_EN))
        voci = voci_per_lingua(sua)
        self._combo_voce.handler_block_by_func(self._su_cambio_voce)
        self._combo_voce.remove_all()
        for nome, descrizione in voci.items():
            self._combo_voce.append(nome, descrizione)
        if not voci:
            self._combo_voce.append("", f"nessuna voce per {C.nome_lingua(sua)}")
        # La voce salvata puo' appartenere alla lingua precedente: in quel caso
        # si ripiega su quella predefinita della lingua nuova.
        if not self._combo_voce.set_active_id(str(self.cfg.get("tts_voice", ""))):
            predefinita = voce_predefinita(sua)
            if predefinita:
                self._combo_voce.set_active_id(predefinita)
                self.cfg["tts_voice"] = predefinita
        self._combo_voce.handler_unblock_by_func(self._su_cambio_voce)

    def mostra_avanzamento(self, messaggio: str) -> None:
        """Messaggio informativo (download dei modelli, stato della voce)."""
        self._etichetta_errore.set_text(messaggio)

    def _prova_voce(self) -> None:
        if self._on_prova_voce is not None:
            self._on_prova_voce()

    def mostra_sorgente_virtuale(self, nome: str | None) -> None:
        """Indica il microfono da selezionare in Meet, o lo nasconde."""
        if nome:
            self._etichetta_virtuale.set_text(
                f"In Meet scegli come microfono: {nome}"
            )
        else:
            self._etichetta_virtuale.set_text("")

    def _aggiorna_sorgenti(self) -> None:
        """Riempe i menu e preseleziona i dispositivi salvati o predefiniti."""
        try:
            sorgenti = A.elenca_sorgenti()
        except A.AudioError as exc:
            self._etichetta_errore.set_text(str(exc))
            return

        monitor = A.sorgenti_monitor(sorgenti)
        microfoni = A.sorgenti_microfono(sorgenti)

        remoto_salvato = self.cfg.get("remote_source", "")
        if not remoto_salvato:
            predefinito = A.monitor_predefinito()
            remoto_salvato = predefinito.nome if predefinito else ""

        mic_salvato = self.cfg.get("mic_source", "")
        if not mic_salvato:
            predefinito = A.microfono_predefinito()
            mic_salvato = predefinito.nome if predefinito else ""

        # Ogni combo ha la propria lista: gli indici devono corrispondere.
        self._riempi_combo(self._combo_remoto, monitor, remoto_salvato)
        self._riempi_combo(self._combo_mic, microfoni, mic_salvato)

        if remoto_salvato:
            self.cfg["remote_source"] = remoto_salvato
        if mic_salvato:
            self.cfg["mic_source"] = mic_salvato

    def _riempi_combo(
        self, combo: Gtk.ComboBoxText, elenco: list[A.Sorgente], selezionato: str,
    ) -> None:
        combo.handler_block_by_func(self._su_cambio_dispositivo)
        combo.remove_all()
        for sorgente in elenco:
            combo.append_text(sorgente.etichetta)
        # La lista della combo e' l'unica fonte degli indici: la conservo
        # accanto alla combo per non dipendere dall'ordine globale delle sorgenti.
        self._elenchi_combo[id(combo)] = elenco
        indice = next(
            (i for i, s in enumerate(elenco) if s.nome == selezionato), 0,
        )
        if elenco:
            combo.set_active(indice)
        combo.handler_unblock_by_func(self._su_cambio_dispositivo)

    def _sorgente_da_combo(self, combo: Gtk.ComboBoxText) -> A.Sorgente | None:
        elenco = self._elenchi_combo.get(id(combo), [])
        indice = combo.get_active()
        if 0 <= indice < len(elenco):
            return elenco[indice]
        return None

    def _su_chiusura(self, _widget, _evento) -> bool:
        """Chiudere il pannello chiude l'applicazione (gestito da main)."""
        return False

    def _salva_posizione(self, _widget, _evento) -> bool:
        """Ricorda dove l'utente ha messo la finestra."""
        try:
            x, y = self.get_position()
            larghezza, altezza = self.get_size()
            self.cfg["window"] = {"x": x, "y": y, "w": larghezza, "h": altezza}
        except Exception:                          # noqa: BLE001 - solo cosmetica
            pass
        return False


def collega_glib(funzione, *args):
    """Scorciatoia: pianifica una chiamata sul thread principale di GTK.

    La pipeline invoca questa per ogni risultato, perche' i widget GTK non
    sono thread-safe e vanno toccati solo dal thread principale.
    """
    return GLib.idle_add(funzione, *args)
