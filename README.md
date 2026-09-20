# Vox Populi

Traduzione simultanea italiano ⇄ inglese per le videochiamate, tutta in locale.

Nasce da un'esigenza concreta: sostenere una call Google Meet con un
interlocutore di Mumbai che parla inglese, senza padroneggiare l'inglese. Il
programma ascolta entrambe le voci, le trascrive, le traduce e le mostra a
schermo — in due finestre diverse, una per te e una da condividere.

**L'interlocutore non deve installare niente.** Nessuna estensione, nessun
account, nessun programma. Usa Meet come ha sempre fatto e vede solo una
finestra condivisa, come se fosse una presentazione. Tutto il lavoro avviene
sul tuo PC.

## Come funziona

```
   la voce di Mumbai  ──►  monitor delle casse/cuffie  ──┐
                                                         ├──►  VAD  ──►  Whisper  ──►  argos  ──┐
   la tua voce        ──►  microfono                    ──┘         (trascrive)   (traduce)  │
                                                                                             │
                          ┌──────────────────────────────────────────────────────────────────┘
                          ▼
   ┌─ Pannello (solo per te, resta sopra Meet) ─┐   ┌─ Finestra per lui (la condividi) ─┐
   │  LORO · inglese → italiano                 │   │                                   │
   │  TU   · italiano → inglese                 │   │   testo grande, ultime frasi      │
   └────────────────────────────────────────────┘   └───────────────────────────────────┘
```

Tutto gira sul tuo computer: nessun dato viene inviato a servizi esterni,
nessuna chiave API, nessun abbonamento. Dopo il primo avvio funziona anche
senza connessione.

## Cosa sente e cosa vede l'interlocutore

Questo punto va capito bene prima della call, perché cambia il modo di parlare.

| | Tu senti | Mumbai sente | Mumbai vede |
|---|---|---|---|
| Tu parli italiano | la sua voce tradotta in italiano nel pannello | **la tua voce italiana reale** | la traduzione inglese nella finestra condivisa |
| Lui parla inglese | la sua voce tradotta in italiano nel pannello | la propria voce, normalmente | — |

In altre parole: **la voce non viene sostituita**, viene affiancata dal testo.
Mumbai ti sente parlare in italiano e legge l'inglese nella finestra. Non è
doppiaggio: è supporto alla lettura, ed è il motivo per cui vale la pena
parlare scandendo bene e un po' più lentamente del solito.

> La voce sintetica inglese (che sostituirebbe la tua) è prevista come
> miglioramento successivo e non è ancora attiva in questa versione.

## Installazione

Su Debian/Ubuntu e affini:

```bash
./install.sh
```

Lo script installa i pacchetti di sistema mancanti (`python3-gi`,
`pulseaudio-utils`, `ffmpeg`), le dipendenze Python e i modelli di traduzione,
poi esegue una diagnosi. È idempotente: rilanciarlo non fa danni.

La trascrizione usa il modello `small` di Whisper, circa 500 MB: se non è già
nella cache viene scaricato al primo avvio.

## Uso

### Il giorno della call

```bash
./vox-populi
```

Si aprono due finestre. Poi, in ordine:

1. **Nel pannello**, controlla i due menu in basso:
   - **Ascolta** — la sorgente della voce dell'interlocutore. Scegli il
     *monitor* dell'uscita audio che stai usando: se hai le cuffie, il monitor
     delle cuffie; se usi le casse, il monitor delle casse.
   - **Microfono** — il tuo microfono.
   La scelta viene ricordata per la volta successiva.

2. **Premi Avvia.** La prima volta carica i modelli: qualche secondo, poi
   compare `● in ascolto`.

3. **In Meet, condividi la finestra "Vox Populi - leggere qui"** con
   *Condividi una finestra* (non tutto lo schermo). È la finestra con il testo
   grande: è quella che l'interlocutore deve vedere.

4. **Parla normalmente.** Le frasi tradotte appaiono nel pannello e, per le
   tue, anche nella finestra condivisa.

### Le cuffie sono meglio delle casse

Con le casse, la voce di Mumbai esce dagli altoparlanti, rientra dal microfono
e verrebbe trascritta come se fossi tu. Il programma se ne accorge e sospende
il microfono mentre l'altro parla (la casella *Non trascrivere il microfono
mentre l'altro parla*), ma con le cuffie il problema non esiste proprio.

### Comandi da terminale

Servono per le prove, senza aprire l'interfaccia:

```bash
python3 -m voxpopuli.cli diagnosi                  # dipendenze, modelli, sorgenti audio
python3 -m voxpopuli.cli dispositivi               # elenca monitor e microfoni
python3 -m voxpopuli.cli file audio.mp3 en         # trascrive e traduce un file
python3 -m voxpopuli.cli live                      # cattura dal vivo, stampa a terminale
```

`live` accetta `--remoto NOME`, `--mic NOME` e `--no-half-duplex`.

## Requisiti

- Linux con PulseAudio o PipeWire (per `parec` e `pactl`)
- Sessione X11 — su Wayland la finestra sempre-in-alto può non funzionare
- Python 3.10 o superiore, PyGObject e GTK 3
- CPU decente: la trascrizione gira su CPU, senza GPU

## Latenza

Misurata su questa macchina, a modelli già caricati:

| Stadio | Tempo |
|---|---|
| Attesa di fine frase (VAD) | ~0,6 s |
| Trascrizione (faster-whisper `small` int8) | ~1,75 s |
| Traduzione (argostranslate) | ~0,06 s |
| **Totale percepito** | **~2,4 s** |

Il ritardo fra la fine di una frase e la sua traduzione a schermo è quindi di
circa due secondi e mezzo. Nella pratica si legge la traduzione della frase
precedente mentre l'altro sta già dicendo la successiva: conviene rassegnarsi a
questo ritmo invece di aspettare il testo prima di rispondere.

## Struttura

```
vox-populi
├── voxpopuli/
│   ├── main.py          avvio dell'applicazione e orchestrazione
│   ├── config.py        costanti tecniche e preferenze salvate
│   ├── audio.py         elenco dispositivi (pactl) e cattura (parec)
│   ├── vad.py           segmentazione in frasi
│   ├── stt.py           trascrizione (faster-whisper)
│   ├── mt.py            traduzione (argostranslate)
│   ├── pipeline.py      code, thread, half-duplex, latenze
│   ├── cli.py           prove da terminale
│   └── ui/              pannello, finestra condivisa, foglio di stile
├── docs/guida-call.md   promemoria passo-passo per il giorno della call
├── tools/               script di collaudo della cattura audio
├── install.sh
└── requirements.txt
```

Le preferenze (dispositivi scelti, dimensione del carattere, posizione delle
finestre) stanno in `~/.config/vox-populi/config.json`.

## Se qualcosa non va

**Il pannello non mostra niente mentre l'altro parla.**
Nel menu *Ascolta* hai scelto il monitor sbagliato. Prova a riprodurre un video
inglese e cambia voce nel menu finché il testo non compare. `python3 -m
voxpopuli.cli dispositivi` mostra i nomi disponibili.

**La tua voce viene trascritta mentre l'altro parla.**
È l'eco delle casse. Usa le cuffie, oppure lascia attiva la casella
*Non trascrivere il microfono mentre l'altro parla*.

**Le traduzioni sono storte.**
Succede con le frasi molto lunghe o con gli idiomismi. Parlare in frasi brevi
e complete migliora molto il risultato: il traduttore lavora bene su periodi
con senso compiuto.

**La finestra non resta sopra Meet.**
Serve una sessione X11, non Wayland. E Meet va usato in finestra, non a schermo
intero, altrimenti copre tutto.

**L'avvio è lento.**
La prima volta carica i modelli (Whisper e argostranslate): qualche secondo in
più è normale. Dalla seconda è immediato.

## Licenza

MIT — vedi il file `LICENSE`.
