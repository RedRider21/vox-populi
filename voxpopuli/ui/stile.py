# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Daniele Deplano (RedRider21)
"""Foglio di stile delle due finestre, con piu' schemi cromatici.

Il CSS viene generato a runtime invece di stare in un file: cosi' le
dimensioni del carattere e i colori del tema scelto sono interpolati
direttamente, e cambiare tema e' immediato (basta ricaricare lo stesso
provider, senza rimettere insieme le finestre).

Tutte le palette sono scure o comunque ad alto contrasto nello spirito del
progetto: durante una conversazione non c'e' tempo di cercare le parole sullo
schermo, e un testo che si legge a colpo d'occhio vale piu' di un tema
graziato. Il tema "contrasto" esiste per chi lavora in condizioni di luce
difficile o ha problemi di vista.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gdk, Gtk  # noqa: E402

# Ogni tema e' un insieme completo di colori: nessun valore e' derivato da un
# altro, cosi' una palette puo' essere ritoccata senza effetti collaterali.
TEMI: dict[str, dict[str, str]] = {
    "scuro": {
        "nome": "Scuro (ciano)",
        "fondo": "#050a14",
        "riquadro": "#0b1420",
        "speaker": "#000000",
        "testo": "#ffffff",
        "tenue": "#8b98a5",
        "accento": "#00e5ff",
        "allarme": "#ff5a8a",
        "ok": "#3ddc84",
        "bottone": "#16263a",
        "bordo": "#24405c",
        "hover": "#1e3550",
        "spento": "#0d1622",
        "primario": "#0d3b4a",
        "speaker_tenue": "#3a4756",
    },
    "chiaro": {
        "nome": "Chiaro",
        "fondo": "#eef1f5",
        "riquadro": "#ffffff",
        "speaker": "#ffffff",
        "testo": "#10151c",
        "tenue": "#5b6773",
        "accento": "#0055b8",
        "allarme": "#b3253f",
        "ok": "#146c3a",
        "bottone": "#ffffff",
        "bordo": "#b9c4d0",
        "hover": "#dfe6ee",
        "spento": "#e4e8ed",
        "primario": "#cfe4fb",
        "speaker_tenue": "#98a3b0",
    },
    "ambra": {
        "nome": "Ambra (terminale)",
        "fondo": "#120c00",
        "riquadro": "#1c1300",
        "speaker": "#000000",
        "testo": "#ffb340",
        "tenue": "#9a7433",
        "accento": "#ffcc66",
        "allarme": "#ff6b6b",
        "ok": "#8fdc5a",
        "bottone": "#2a1d00",
        "bordo": "#4a3400",
        "hover": "#3d2a00",
        "spento": "#1a1200",
        "primario": "#4a3400",
        "speaker_tenue": "#5c4416",
    },
    "verde": {
        "nome": "Verde fosforo",
        "fondo": "#000a04",
        "riquadro": "#04160c",
        "speaker": "#000000",
        "testo": "#5cff9d",
        "tenue": "#3d9963",
        "accento": "#00ff88",
        "allarme": "#ff5a5a",
        "ok": "#3ddc84",
        "bottone": "#062012",
        "bordo": "#0f4a28",
        "hover": "#0a3320",
        "spento": "#03140a",
        "primario": "#0f4a28",
        "speaker_tenue": "#1e4a30",
    },
    "notte": {
        "nome": "Notte (viola)",
        "fondo": "#0d0a1a",
        "riquadro": "#161029",
        "speaker": "#05030d",
        "testo": "#f0ecff",
        "tenue": "#9a90c0",
        "accento": "#b48cff",
        "allarme": "#ff7ab8",
        "ok": "#5ce6a0",
        "bottone": "#221a3d",
        "bordo": "#3d2f6b",
        "hover": "#2e2450",
        "spento": "#150f26",
        "primario": "#3d2f6b",
        "speaker_tenue": "#3a3057",
    },
    "contrasto": {
        "nome": "Alto contrasto",
        "fondo": "#000000",
        "riquadro": "#000000",
        "speaker": "#000000",
        "testo": "#ffffff",
        "tenue": "#c8c8c8",
        "accento": "#ffff00",
        "allarme": "#ff8080",
        "ok": "#00ff00",
        "bottone": "#1a1a1a",
        "bordo": "#ffffff",
        "hover": "#333333",
        "spento": "#0d0d0d",
        "primario": "#333300",
        "speaker_tenue": "#808080",
    },
}

TEMA_PREDEFINITO = "scuro"
_PROVIDER: Gtk.CssProvider | None = None


def nome_tema(chiave: str) -> str:
    """Nome leggibile di un tema, o la chiave stessa se sconosciuto."""
    return TEMI.get(chiave, {}).get("nome", chiave)


def temi_disponibili() -> dict[str, str]:
    """Elenco {chiave: nome} per i menu dell'interfaccia."""
    return {chiave: valori["nome"] for chiave, valori in TEMI.items()}


def css(font_size: int = 20, speaker_font_size: int = 44,
        tema: str = TEMA_PREDEFINITO) -> str:
    """Genera il foglio di stile per il tema e le dimensioni richieste."""
    c = TEMI.get(tema) or TEMI[TEMA_PREDEFINITO]
    fondo = c["fondo"]
    riquadro = c["riquadro"]
    testo = c["testo"]
    tenue = c["tenue"]
    accento = c["accento"]
    allarme = c["allarme"]
    # Nota: GTK CSS non accetta selettori multipli separati da virgola
    # ("window, .radice {...}") - la regola viene scartata in silenzio e il
    # tema torna a imporre i suoi colori. Ogni selettore va scritto da solo.
    return f"""
    window {{
        background-color: {fondo};
    }}
    .radice {{
        background-color: {fondo};
    }}

    /* ------------------------------------------------ pannello utente ---- */
    .intestazione {{
        background-color: {riquadro};
        padding: 8px 12px;
    }}
    .titolo {{
        color: {accento};
        font-size: 14px;
        font-weight: bold;
    }}
    .stato-attivo   {{ color: {c["ok"]}; font-size: 12px; }}
    .stato-fermo    {{ color: {tenue}; font-size: 12px; }}
    .stato-errore   {{ color: {allarme}; font-size: 12px; }}

    .riquadro {{
        background-color: {riquadro};
        border-radius: 6px;
        margin: 6px;
        padding: 10px 12px;
    }}
    .intestazione-riquadro {{
        color: {tenue};
        font-size: 11px;
        font-weight: bold;
    }}
    .originale {{
        color: {tenue};
        font-size: {max(11, font_size - 7)}px;
    }}
    .tradotto {{
        color: {testo};
        font-size: {font_size}px;
        font-weight: bold;
    }}
    .tradotto-remoto {{ color: {accento}; }}
    .tradotto-locale {{ color: {testo}; }}

    .barra {{
        background-color: {riquadro};
        padding: 6px 10px;
    }}
    .dettaglio {{ color: {tenue}; font-size: 11px; }}
    .errore    {{ color: {allarme}; font-size: 11px; }}

    button {{
        background-image: none;
        background-color: {c["bottone"]};
        color: {testo};
        border: 1px solid {c["bordo"]};
        border-radius: 5px;
        padding: 6px 14px;
        font-size: 12px;
    }}
    button:hover   {{ background-color: {c["hover"]}; }}
    button:disabled {{ color: {tenue}; background-color: {c["spento"]}; }}
    button.primario {{ background-color: {c["primario"]}; border-color: {accento}; }}

    combobox button {{ padding: 4px 8px; font-size: 11px; }}
    combobox window {{ background-color: {riquadro}; }}
    menu     {{ background-color: {riquadro}; }}
    menuitem {{ background-color: {riquadro}; color: {testo}; }}
    menuitem:hover {{ background-color: {c["hover"]}; }}

    /* ------------------------------------- finestra per l'interlocutore ---- */
    .speaker-radice {{
        background-color: {c["speaker"]};
    }}
    .speaker-frase {{
        color: {tenue};
        font-size: {max(16, int(speaker_font_size * 0.55))}px;
        padding: 6px 18px;
    }}
    .speaker-frase-recente {{
        color: {testo};
        font-size: {speaker_font_size}px;
        font-weight: bold;
        padding: 10px 18px;
    }}
    .speaker-istruzione {{
        color: {c["speaker_tenue"]};
        font-size: 13px;
        padding: 8px 18px;
    }}
    """


def applica(font_size: int = 20, speaker_font_size: int = 44,
            tema: str = TEMA_PREDEFINITO) -> Gtk.CssProvider:
    """Installa o aggiorna il foglio di stile sulla schermata corrente.

    Il provider viene creato una volta sola e poi ricaricato: e' cosi' che il
    cambio di tema ha effetto immediato sulle finestre gia' aperte, senza
    chiuderle e riaprirle.
    """
    global _PROVIDER
    if _PROVIDER is None:
        _PROVIDER = Gtk.CssProvider()
        schermo = Gdk.Screen.get_default()
        if schermo is not None:
            Gtk.StyleContext.add_provider_for_screen(
                schermo, _PROVIDER, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
    _PROVIDER.load_from_data(
        css(font_size, speaker_font_size, tema).encode("utf-8")
    )
    return _PROVIDER
