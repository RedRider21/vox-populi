# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Daniele Deplano (RedRider21)
"""Foglio di stile delle due finestre.

Il CSS viene generato a runtime invece di stare in un file, cosi' le
dimensioni del carattere scelte dall'utente sono interpolate direttamente e
non serve ricaricare un provider a ogni modifica.

La palette segue quella degli altri progetti dell'autore: fondo molto scuro,
accento ciano, allarme rosa. Serve leggibilita' a colpo d'occhio durante una
conversazione, quando non c'e' tempo di cercare le parole sullo schermo.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gdk, Gtk  # noqa: E402

# Palette
FONDO = "#050a14"
FONDO_RIQUADRO = "#0b1420"
FONDO_SPEAKER = "#000000"
TESTO = "#ffffff"
TESTO_TENUE = "#8b98a5"
ACCENTO = "#00e5ff"
ALLARME = "#ff5a8a"
OK_VERDE = "#3ddc84"


def css(font_size: int = 20, speaker_font_size: int = 44) -> str:
    """Genera il foglio di stile per le dimensioni richieste."""
    # Nota: GTK CSS non accetta selettori multipli separati da virgola
    # ("window, .radice {...}") - la regola viene scartata in silenzio e il
    # tema torna a imporre i suoi colori. Ogni selettore va scritto da solo.
    return f"""
    window {{
        background-color: {FONDO};
    }}
    .radice {{
        background-color: {FONDO};
    }}

    /* ------------------------------------------------ pannello utente ---- */
    .intestazione {{
        background-color: {FONDO_RIQUADRO};
        padding: 8px 12px;
    }}
    .titolo {{
        color: {ACCENTO};
        font-size: 14px;
        font-weight: bold;
    }}
    .stato-attivo   {{ color: {OK_VERDE}; font-size: 12px; }}
    .stato-fermo    {{ color: {TESTO_TENUE}; font-size: 12px; }}
    .stato-errore   {{ color: {ALLARME}; font-size: 12px; }}

    .riquadro {{
        background-color: {FONDO_RIQUADRO};
        border-radius: 6px;
        margin: 6px;
        padding: 10px 12px;
    }}
    .intestazione-riquadro {{
        color: {TESTO_TENUE};
        font-size: 11px;
        font-weight: bold;
    }}
    .originale {{
        color: {TESTO_TENUE};
        font-size: {max(11, font_size - 7)}px;
    }}
    .tradotto {{
        color: {TESTO};
        font-size: {font_size}px;
        font-weight: bold;
    }}
    .tradotto-remoto {{ color: {ACCENTO}; }}
    .tradotto-locale {{ color: {TESTO}; }}

    .barra {{
        background-color: {FONDO_RIQUADRO};
        padding: 6px 10px;
    }}
    .dettaglio {{ color: {TESTO_TENUE}; font-size: 11px; }}
    .errore    {{ color: {ALLARME}; font-size: 11px; }}

    button {{
        background-image: none;
        background-color: #16263a;
        color: {TESTO};
        border: 1px solid #24405c;
        border-radius: 5px;
        padding: 6px 14px;
        font-size: 12px;
    }}
    button:hover   {{ background-color: #1e3550; }}
    button:disabled {{ color: {TESTO_TENUE}; background-color: #0d1622; }}
    button.primario {{ background-color: #0d3b4a; border-color: {ACCENTO}; }}

    combobox button {{ padding: 4px 8px; font-size: 11px; }}
    combobox window {{ background-color: {FONDO_RIQUADRO}; }}
    menu     {{ background-color: {FONDO_RIQUADRO}; }}
    menuitem {{ background-color: {FONDO_RIQUADRO}; color: {TESTO}; }}
    menuitem:hover {{ background-color: #1e3550; }}

    /* ------------------------------------- finestra per l'interlocutore ---- */
    .speaker-radice {{
        background-color: {FONDO_SPEAKER};
    }}
    .speaker-frase {{
        color: {TESTO_TENUE};
        font-size: {max(16, int(speaker_font_size * 0.55))}px;
        padding: 6px 18px;
    }}
    .speaker-frase-recente {{
        color: {TESTO};
        font-size: {speaker_font_size}px;
        font-weight: bold;
        padding: 10px 18px;
    }}
    .speaker-istruzione {{
        color: #3a4756;
        font-size: 13px;
        padding: 8px 18px;
    }}
    """


def applica(font_size: int = 20, speaker_font_size: int = 44) -> Gtk.CssProvider:
    """Installa il foglio di stile sulla schermata corrente."""
    provider = Gtk.CssProvider()
    provider.load_from_data(css(font_size, speaker_font_size).encode("utf-8"))
    schermo = Gdk.Screen.get_default()
    if schermo is not None:
        Gtk.StyleContext.add_provider_for_screen(
            schermo, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )
    return provider
