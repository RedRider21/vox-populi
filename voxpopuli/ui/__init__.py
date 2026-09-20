# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Daniele Deplano (RedRider21)
"""Interfaccia grafica GTK3.

Due finestre con ruoli opposti:

* `panel.FinestraPannello` - per l'utente, sta sopra Meet e mostra entrambe le
  direzioni della conversazione;
* `speaker.FinestraSpeaker` - per l'interlocutore, viene condivisa in Meet e
  mostra solo l'inglese a caratteri molto grandi.

Regola non negoziabile: la pipeline gira su thread propri e **nessun widget
viene toccato da quei thread**. Gli aggiornamenti passano sempre da
`GLib.idle_add`, che li riporta sul thread principale di GTK.
"""

from .panel import FinestraPannello
from .speaker import FinestraSpeaker

__all__ = ["FinestraPannello", "FinestraSpeaker"]
