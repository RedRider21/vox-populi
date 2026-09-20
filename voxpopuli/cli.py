# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Daniele Deplano (RedRider21)
"""Collaudo da terminale, senza interfaccia grafica.

Serve a verificare ogni pezzo prima di aggiungere la UI: se una frase non
viene tradotta, il problema e' nel motore e non nel disegno delle finestre.

    python3 -m voxpopuli.cli diagnosi            # dipendenze e modelli
    python3 -m voxpopuli.cli dispositivi         # sorgenti audio disponibili
    python3 -m voxpopuli.cli file audio.mp3 it   # trascrive e traduce un file
    python3 -m voxpopuli.cli live                # cattura dal vivo a terminale
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time

from . import audio as A
from . import config as C
from . import mt, stt
from .vad import pcm16_a_float

VERDE = "\033[32m"
ROSSO = "\033[31m"
GIALLO = "\033[33m"
GRIGIO = "\033[90m"
RESET = "\033[0m"


def _ok(testo: str) -> None:
    print(f"  {VERDE}OK{RESET}   {testo}")


def _ko(testo: str) -> None:
    print(f"  {ROSSO}NO{RESET}   {testo}")


def _attenzione(testo: str) -> None:
    print(f"  {GIALLO}!!{RESET}   {testo}")


# ------------------------------------------------------------------ comandi ----
def cmd_diagnosi(_args: argparse.Namespace) -> int:
    """Verifica che tutto il necessario sia presente."""
    print("\n=== Dipendenze Python ===")
    esito = 0
    for modulo, nome, installa in (
        ("numpy", "numpy", "pip install numpy"),
        ("faster_whisper", "faster-whisper", "pip install faster-whisper"),
        ("argostranslate", "argostranslate", "pip install argostranslate"),
    ):
        try:
            __import__(modulo)
            _ok(nome)
        except ImportError:
            _ko(f"{nome} mancante -> {installa}")
            esito = 1

    print("\n=== Strumenti di sistema ===")
    mancanti = A.strumenti_disponibili()
    if mancanti:
        _ko("mancano: " + ", ".join(mancanti) + " -> sudo apt install pulseaudio-utils")
        esito = 1
    else:
        _ok("pactl e parec")

    print("\n=== Modelli di traduzione ===")
    coppie = mt.lingue_disponibili()
    for coppia in ((C.LANG_IT, C.LANG_EN), (C.LANG_EN, C.LANG_IT)):
        if coppia in coppie:
            _ok(f"{coppia[0]} -> {coppia[1]}")
        else:
            _ko(f"{coppia[0]} -> {coppia[1]} mancante")
            esito = 1

    print("\n=== Modello di trascrizione ===")
    try:
        secondi = stt.prepara()
        _ok(f"Whisper '{C.WHISPER_MODEL}' caricato e scaldato in {secondi:.1f}s")
    except stt.SttError as exc:
        _ko(str(exc))
        esito = 1

    print("\n=== Sorgenti audio ===")
    try:
        for sorgente in A.elenca_sorgenti():
            tipo = "monitor" if sorgente.monitor else "microfono"
            print(f"  {GRIGIO}{tipo:9}{RESET} {sorgente.nome}")
    except A.AudioError as exc:
        _ko(str(exc))
        esito = 1

    print()
    if esito == 0:
        print(f"{VERDE}Tutto pronto.{RESET}\n")
    else:
        print(f"{ROSSO}Ci sono problemi da risolvere (vedi sopra).{RESET}\n")
    return esito


def cmd_dispositivi(_args: argparse.Namespace) -> int:
    """Elenca le sorgenti, distinguendo monitor e microfoni."""
    try:
        sorgenti = A.elenca_sorgenti()
    except A.AudioError as exc:
        _ko(str(exc))
        return 1

    predefinito = A.monitor_predefinito()
    print(f"\n{VERDE}Monitor{RESET} (voce dell'interlocutore) - l'uscita predefinita:")
    for s in A.sorgenti_monitor(sorgenti):
        marca = f" {VERDE}<- predefinito{RESET}" if predefinito and s.nome == predefinito.nome else ""
        print(f"  {s.descrizione}{marca}\n    {GRIGIO}{s.nome}{RESET}")

    print(f"\n{VERDE}Microfoni{RESET} (la tua voce):")
    for s in A.sorgenti_microfono(sorgenti):
        print(f"  {s.descrizione}\n    {GRIGIO}{s.nome}{RESET}")
    print()
    return 0


def _leggi_audio(percorso: str, sample_rate: int = C.SAMPLE_RATE):
    """Decodifica un file audio in float32 mono con ffmpeg."""
    import numpy as np

    comando = [
        "ffmpeg", "-v", "error", "-i", percorso,
        "-f", "s16le", "-acodec", "pcm_s16le",
        "-ar", str(sample_rate), "-ac", "1", "-",
    ]
    try:
        esito = subprocess.run(comando, capture_output=True, check=True)
    except FileNotFoundError:
        _ko("ffmpeg non trovato. Installa con: sudo apt install ffmpeg")
        return None
    except subprocess.CalledProcessError as exc:
        _ko(f"ffmpeg non ha potuto leggere '{percorso}': {exc.stderr.decode(errors='replace')}")
        return None
    return pcm16_a_float(esito.stdout)


def cmd_file(args: argparse.Namespace) -> int:
    """Trascrive e traduce un file audio, come prova del solo motore."""
    campioni = _leggi_audio(args.percorso)
    if campioni is None or campioni.size == 0:
        return 1

    da, a = (mt.direzione_locale() if args.lingua == C.LANG_IT
             else mt.direzione_remota())
    durata = campioni.size / C.SAMPLE_RATE
    print(f"\nFile: {args.percorso} ({durata:.1f}s, lingua {da})")

    # I modelli vanno caricati prima di cronometrare: altrimenti la prima
    # chiamata misura il caricamento (~3 s per argos) e non la traduzione.
    # Nell'app reale il processo resta vivo e paga questo costo una volta sola.
    t_prep_stt = stt.prepara()
    t_prep_mt = mt.prepara()

    inizio = time.perf_counter()
    try:
        testo, t_stt = stt.trascrivi(campioni, da)
    except stt.SttError as exc:
        _ko(str(exc))
        return 1
    if not testo:
        _attenzione("nessun parlato riconosciuto")
        return 1
    try:
        traduzione, t_mt = mt.traduci(testo, da, a)
    except mt.MtError as exc:
        _ko(str(exc))
        return 1
    totale = time.perf_counter() - inizio

    print(f"\n  {GRIGIO}{da}>{a}{RESET}  {testo}")
    print(f"  {VERDE}{a}{RESET}  {traduzione}\n")
    print(f"  {GRIGIO}trascrizione {t_stt:.2f}s + traduzione {t_mt:.2f}s"
          f" = {totale:.2f}s{RESET}")
    print(f"  {GRIGIO}(caricamento modelli: {t_prep_stt:.1f}s + {t_prep_mt:.1f}s,"
          f" pagato una volta sola all'avvio){RESET}\n")
    return 0


def cmd_live(args: argparse.Namespace) -> int:
    """Cattura dal vivo e stampa le frasi tradotte a terminale."""
    from .pipeline import Motore, descrivi

    cfg = C.load()
    sorgente_remota = args.remoto or cfg.get("remote_source") or ""
    sorgente_mic = args.mic or cfg.get("mic_source") or ""

    if not sorgente_remota:
        predefinito = A.monitor_predefinito()
        if predefinito is None:
            _ko("Nessun monitor trovato: specifica il dispositivo con --remoto")
            return 1
        sorgente_remota = predefinito.nome
        print(f"{GIALLO}Uso il monitor predefinito: {predefinito.descrizione}{RESET}")

    if not sorgente_mic:
        predefinito = A.microfono_predefinito()
        if predefinito is None:
            _ko("Nessun microfono trovato: specifica il dispositivo con --mic")
            return 1
        sorgente_mic = predefinito.nome
        print(f"{GIALLO}Uso il microfono predefinito: {predefinito.descrizione}{RESET}")

    def stampa(risultato) -> None:
        print("\n" + descrivi(risultato), flush=True)

    def stato(s) -> None:
        if s.errore:
            print(f"{ROSSO}[stato] {s.errore}{RESET}", flush=True)

    motore = Motore(
        sorgente_remota=sorgente_remota,
        sorgente_mic=sorgente_mic,
        on_risultato=stampa,
        on_stato=stato,
        half_duplex=not args.no_half_duplex,
    )
    print(f"\n{VERDE}In ascolto.{RESET} Parla, oppure riproduci un audio in inglese.")
    print(f"{GRIGIO}Premi Ctrl+C per uscire.{RESET}\n")
    try:
        motore.avvia()
        while motore.stato.attivo:
            time.sleep(0.3)
    except KeyboardInterrupt:
        print("\nInterrotto.")
    finally:
        motore.ferma()
    return 0


# ------------------------------------------------------------------- parser ----
def costruisci_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="voxpopuli.cli",
        description="Collaudo di Vox Populi senza interfaccia grafica.",
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    sub.add_parser("diagnosi", help="verifica dipendenze, modelli e sorgenti audio")
    sub.add_parser("dispositivi", help="elenca monitor e microfoni disponibili")

    p_file = sub.add_parser("file", help="trascrive e traduce un file audio")
    p_file.add_argument("percorso")
    p_file.add_argument("lingua", nargs="?", default=C.LANG_EN,
                        choices=[C.LANG_IT, C.LANG_EN])
    p_file.set_defaults(func=cmd_file)

    p_live = sub.add_parser("live", help="cattura dal vivo e stampa a terminale")
    p_live.add_argument("--remoto", help="nome della sorgente dell'interlocutore")
    p_live.add_argument("--mic", help="nome del microfono")
    p_live.add_argument("--no-half-duplex", action="store_true",
                        help="trascrive il microfono anche mentre l'altro parla")

    sub.choices["diagnosi"].set_defaults(func=cmd_diagnosi)
    sub.choices["dispositivi"].set_defaults(func=cmd_dispositivi)
    p_live.set_defaults(func=cmd_live)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = costruisci_parser().parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nInterrotto.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
