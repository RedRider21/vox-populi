#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Daniele Deplano (RedRider21)
"""Collaudo della cattura dal vivo, senza microfono e senza interlocutore.

Riproduce dei file audio sull'uscita di sistema e verifica che il motore li
catturi dal monitor, li trascriva e li traduca. E' il test che valida l'intera
catena (parec -> VAD -> Whisper -> argos) senza dipendere dalla voce di
nessuno, quindi e' ripetibile e usabile come regressione.

    python3 tools/prova_cattura.py                 # usa i campioni in /tmp/vp_test
    python3 tools/prova_cattura.py file1.mp3 ...   # oppure file a scelta
"""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from voxpopuli import audio as A                    # noqa: E402
from voxpopuli.pipeline import Motore, descrivi      # noqa: E402

CAMPIONI_PREDEFINITI = [
    "/tmp/vp_test/en_0.wav",
    "/tmp/vp_test/en_2.wav",
    "/tmp/vp_test/en_4.wav",
]


def main(percorsi: list[str]) -> int:
    mancanti = A.strumenti_disponibili()
    if mancanti:
        print(f"Strumenti mancanti: {', '.join(mancanti)}")
        return 1

    monitor = A.monitor_predefinito()
    microfono = A.microfono_predefinito()
    if monitor is None or microfono is None:
        print("Monitor o microfono non trovati.")
        return 1

    print(f"Uscita di sistema : {monitor.descrizione}")
    print(f"Microfono         : {microfono.descrizione}")
    print("\nRiproduco i campioni sull'uscita e ascolto dal monitor.\n")

    risultati: list = []
    errori: list[str] = []

    def on_risultato(risultato) -> None:
        risultati.append(risultato)
        print(descrivi(risultato), flush=True)

    def on_stato(stato) -> None:
        if stato.errore and stato.errore not in errori:
            errori.append(stato.errore)
            print(f"[stato] {stato.errore}", flush=True)

    motore = Motore(
        sorgente_remota=monitor.nome,
        sorgente_mic=microfono.nome,
        on_risultato=on_risultato,
        on_stato=on_stato,
        half_duplex=True,
    )
    motore.avvia()

    def riproduci() -> None:
        time.sleep(1.0)
        for percorso in percorsi:
            if not Path(percorso).exists():
                print(f"[prova] file assente, salto: {percorso}")
                continue
            print(f"[prova] riproduco {Path(percorso).name}")
            try:
                subprocess.run(["paplay", percorso], check=False)
            except OSError as exc:
                print(f"[prova] riproduzione non riuscita: {exc}")
            # Pausa fra un campione e l'altro: serve al VAD per chiudere la
            # frase, altrimenti l'audio verrebbe fuso in un unico segmento.
            time.sleep(1.2)

    riproduttore = threading.Thread(target=riproduci, daemon=True)
    riproduttore.start()
    riproduttore.join(timeout=120)

    # Margine per l'ultima inferenza in corso.
    time.sleep(4.0)
    motore.ferma()

    print("\n" + "=" * 60)
    print(f"Frasi catturate e tradotte: {len(risultati)} su {len(percorsi)} riprodotte")
    if risultati:
        media = sum(r.latenza for r in risultati) / len(risultati)
        print(f"Latenza media di inferenza: {media:.2f}s")
    if errori:
        print("Errori segnalati:")
        for errore in errori:
            print(f"  - {errore}")
    if not risultati:
        print("\nNessuna frase catturata: verifica che l'uscita audio sia quella")
        print("predefinita e che il volume non sia a zero.")

    return 0 if risultati else 1


if __name__ == "__main__":
    argomenti = sys.argv[1:] or CAMPIONI_PREDEFINITI
    sys.exit(main(argomenti))
