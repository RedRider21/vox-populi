# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Daniele Deplano (RedRider21)
"""Vox Populi - sottotitoli e voce tradotti in tempo reale per Google Meet.

Il sistema e' composto da due parti indipendenti:

* il **motore** (`audio`, `vad`, `stt`, `mt`, `pipeline`) cattura l'audio di
  sistema e il microfono, segmenta le frasi, le trascrive e le traduce;
* l'**interfaccia** (`ui`) mostra il risultato in due finestre: un pannello
  sopra Meet per l'utente e una finestra da condividere con l'interlocutore.

Tutto gira in locale: nessun dato lascia il computer.
"""

__version__ = "0.1.0"
__all__ = ["config", "audio", "vad", "stt", "mt", "pipeline"]
