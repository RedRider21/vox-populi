# Vox Populi

Traduzione simultanea per le videochiamate, in **50 lingue** e tutta in locale.

Nasce da un'esigenza concreta: sostenere una call Google Meet con un
interlocutore di Mumbai che parla inglese, senza padroneggiare l'inglese. Il
programma ascolta entrambe le voci, le trascrive, le traduce e le mostra a
schermo — in due finestre diverse, una per te e una da condividere.

**L'interlocutore non deve installare niente.** Nessuna estensione, nessun
account, nessun programma. Usa Meet come ha sempre fatto e vede solo una
finestra condivisa, come se fosse una presentazione. Tutto il lavoro avviene
sul tuo PC.

> ### Da leggere prima di scaricare
>
> Il programma funziona con modelli che **non stanno in questo repository**:
> al primo avvio ne scarica **circa 655 MB**, e ogni lingua in più rispetto
> alla coppia italiano/inglese ne costa altri 190 circa. Non parte nessun
> download da solo — `install.sh` chiede conferma, e dall'app i modelli si
> scaricano solo premendo **Installa modelli**. Tutto finisce in
> `~/.local/share/vox-populi/`, una cartella sola che puoi cancellare quando
> vuoi. L'installazione non tocca nient'altro sul tuo sistema.

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

## Come si presenta

Il **pannello**, che resta sopra Meet e vedi solo tu. In alto la traduzione di
quello che dice l'interlocutore, in basso la tua — con l'originale in piccolo
sopra, la traduzione in grande sotto:

![Pannello con la conversazione in corso](docs/img/pannello.png)

La **finestra per lui**, quella che condividi in Meet con *Condividi una
finestra*. Testo molto grande, alto contrasto, le ultime frasi che scorrono:

![Finestra condivisa con le frasi tradotte](docs/img/speaker.png)

Con la voce sintetica accesa il pannello mostra anche quale voce è in uso e
quale microfono scegliere in Meet:

![Pannello con la voce sintetica attiva](docs/img/pannello-voce.png)

### Sei schemi di colore

Si scelgono da **Colori** e si applicano subito, anche a finestre già aperte e
a quella che stai condividendo. Servono a leggere meglio: c'è chi lavora al
buio, chi in pieno sole, e chi ha bisogno del massimo contrasto.

| | | |
|---|---|---|
| ![Chiaro](docs/img/tema-chiaro.png) | ![Ambra](docs/img/tema-ambra.png) | ![Verde](docs/img/tema-verde.png) |
| Chiaro | Ambra (terminale) | Verde fosforo |
| ![Notte](docs/img/tema-notte.png) | ![Alto contrasto](docs/img/tema-contrasto.png) | |
| Notte (viola) | Alto contrasto | |

## Cosa sente e cosa vede l'interlocutore

Questo punto va capito bene prima della call, perché cambia il modo di parlare.

Ci sono due modi di usare il programma, e si scelgono dall'interruttore
**Voce inglese** nel pannello.

**A voce spenta** (predefinito) — Mumbai ti sente parlare in italiano e legge
l'inglese:

| | Tu senti | Mumbai sente | Mumbai vede |
|---|---|---|---|
| Tu parli italiano | la traduzione nel pannello | **la tua voce italiana reale** | la traduzione inglese |
| Lui parla inglese | la traduzione nel pannello | la propria voce, normalmente | — |

**A voce accesa** — Mumbai sente l'inglese, pronunciato da una voce sintetica
con accento indiano. È doppiaggio vero, ma con un ritardo:

| | Tu senti | Mumbai sente | Mumbai vede |
|---|---|---|---|
| Tu parli italiano | la traduzione nel pannello | **un breve silenzio, poi la frase in inglese** | la traduzione inglese |
| Lui parla inglese | la traduzione nel pannello | la propria voce, normalmente | — |

Il silenzio dura quanto la traduzione, cioè circa due secondi: mentre parli,
il tuo microfono viene chiuso, e si riapre quando la voce inglese ha finito.
Senza questa chiusura l'interlocutore sentirebbe l'italiano *e poi* l'inglese,
che è peggio di entrambi. Per questo a voce accesa la conversazione diventa
inevitabilmente più lenta e a turni.

**Consiglio pratico**: la voce serve se l'interlocutore fatica a leggere mentre
ascolta, o se la call è affollata e i sottotitoli passano in secondo piano.
Per una conversazione normale, i sottotitoli da soli sono più reattivi.

## Installazione

> **Prima di iniziare: il programma scarica circa 655 MB di modelli.**
> Non sono nel repository e non sono opzionali — senza, non trascrive e non
> traduce. Lo script lo dice e chiede conferma prima di scaricare qualcosa.
> Per procedere senza domande (script automatici): `./install.sh --si`.

Su Debian/Ubuntu e affini:

```bash
./install.sh
```

Lo script installa i pacchetti di sistema mancanti (`python3-gi`,
`pulseaudio-utils`, `ffmpeg`), le dipendenze Python e i modelli, poi esegue una
diagnosi. È idempotente: rilanciarlo non fa danni e non riscarica nulla.

### Cosa viene scaricato

| Cosa | Dove | Spazio |
|---|---|---|
| Trascrizione — Whisper `small` | `~/.local/share/vox-populi/whisper/` | ~465 MB |
| Traduzione italiano ↔ inglese | `~/.local/share/vox-populi/modelli/` | ~190 MB |
| **Totale al primo avvio** | | **~655 MB** |

Ogni lingua in più rispetto alla coppia italiano/inglese costa circa 190 MB per
direzione, e si scarica dall'app con **Installa modelli**, non da `install.sh`.
Non c'è nessun download che parta da solo: o lo chiede `install.sh`, o lo
chiedi tu dal pannello.

Tutto sta in **una cartella sola**, `~/.local/share/vox-populi/`: preferenze,
elenco delle voci, modelli di traduzione e modello di trascrizione. Per
liberare lo spazio basta cancellarla; per portarti il programma su un'altra
macchina basta copiarla. Il percorso si può cambiare con la variabile
d'ambiente `VOXPOPULI_DATA_DIR`.

Chi aveva già usato una versione precedente ha i dati sparsi fra `~/.config`,
`~/.cache` e `~/.local/share/argos-translate`: lo script li porta nella
cartella unica senza riscaricarli.

## Uso

Per la spiegazione completa c'è il **[manuale](docs/manuale.md)** (o la sua
versione web, se il progetto ha il sito attivo). Qui la versione breve.

### Il giorno della call

```bash
./vox-populi
```

Si aprono due finestre. Poi, in ordine:

1. **Nel pannello**, controlla i menu:
   - **Ascolta** — la sorgente della voce dell'interlocutore. Scegli il
     *monitor* dell'uscita audio che stai usando: se hai le cuffie, il monitor
     delle cuffie; se usi le casse, il monitor delle casse.
   - **Microfono** — il tuo microfono.
   - **Parlo / Lui parla** — le due lingue della conversazione. Se la coppia
     scelta non è ancora installata compare **Installa modelli**: dimmi quanto
     scaricherà prima di farlo. Vale la pena farlo *prima* della call, non
     durante.
   - **Colori** — sei schemi già pronti, che si applicano subito anche a
     finestre aperte, compresa quella che stai condividendo.
   La scelta viene ricordata per la volta successiva.

2. **Se vuoi la voce sintetica**, spunta **Voce inglese** e scegli quale voce
   fra quelle della lingua dell'interlocutore: sono le voci neurali di
   Microsoft, più di 300 in 75 lingue, ognuna con la sua nazionalità. Il
   pulsante **Prova** fa pronunciare una frase di esempio, ma funziona solo a
   conversazione avviata.

3. **Premi Avvia.** La prima volta carica i modelli: qualche secondo, poi
   compare `● in ascolto`. A voce accesa compare anche la scritta con il
   microfono da scegliere in Meet.

4. **In Meet, condividi la finestra "Vox Populi - leggere qui"** con
   *Condividi una finestra* (non tutto lo schermo). È la finestra con il testo
   grande: è quella che l'interlocutore deve vedere.

5. **Solo se hai acceso la voce, cambia il microfono in Meet**: scegli
   `Monitor of VoxPopuli_Mic`. Va fatto una volta per call: è così che la voce
   inglese arriva all'interlocutore. Se ti dimentichi questo passaggio, lui
   continuerà a sentirti in italiano e la voce sintetica resterà muta.

6. **Parla normalmente.** Le frasi tradotte appaiono nel pannello e, per le
   tue, anche nella finestra condivisa.

### Lingue e voci

**50 lingue** per la traduzione, **75** per la voce sintetica, **322 voci**
diverse. Non sono le stesse liste: servono entrambe, e la lingua dell'app è
quella che compare in tutti e due i menu.

Su 50 lingue traducibili, **46 hanno anche una voce sintetica** con cui
l'interlocutore può sentirle. Le altre 4 (esperanto, basco, chirghiso,
tagalog) si traducono e basta: si leggono, non si pronunciano.

Le lingue si scelgono dal pannello, e si possono cambiare anche a metà
conversazione. I modelli di traduzione fra italiano e inglese ci sono sempre;
per tutte le altre coppie il programma passa dall'inglese come lingua ponte
(`italiano → inglese → tedesco`), perché è l'unica che argostranslate collega
un po' con tutte. Funziona, ma allunga leggermente la traduzione: la diagnosi
lo dice quando accade.

Le voci non sono un elenco fisso scritto nel programma: vengono chieste al
servizio di Microsoft e messe in cache per 30 giorni, così restano aggiornate
da sole. Ognuna porta con sé genere e nazionalità (`Prabhat · maschile ·
India`), utile per far parlare l'interlocutore con la voce di casa sua invece
che con un accento a caso.

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
│   ├── tts.py           voce sintetica (edge-tts)
│   ├── virtualmic.py    microfono virtuale e ducking (pactl)
│   ├── pipeline.py      code, thread, half-duplex, latenze
│   ├── cli.py           prove da terminale
│   └── ui/              pannello, finestra condivisa, foglio di stile
├── docs/guida-call.md   promemoria passo-passo per il giorno della call
├── tools/               script di collaudo della cattura audio
├── install.sh
├── requirements.txt
├── LICENSE              GNU AGPL v3.0
├── COPYRIGHT            attribuzione e licenze delle dipendenze
└── COMMERCIAL.md        licenza commerciale alternativa
```

Le preferenze (dispositivi scelti, lingue, tema, dimensione del carattere,
posizione delle finestre) stanno in `~/.local/share/vox-populi/config.json`,
insieme a tutto il resto: l'intera cartella si copia, si sposta o si cancella
in un colpo solo.

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

**Ho acceso la voce ma l'interlocutore non sente niente.**
Quasi sempre è il microfono di Meet rimasto su quello vero: va scelto
`Monitor of VoxPopuli_Mic`. Il nome esatto compare nel pannello quando la voce
è attiva.

**La voce sintetica non si sente, o arriva a scatti.**
Serve la connessione a Internet: edge-tts genera la voce online al momento.
I sottotitoli invece funzionano anche offline.

**Dopo la chiusura il microfono del computer si comporta in modo strano.**
Non dovrebbe: il microfono virtuale viene smontato all'uscita. Se l'app viene
uccisa di forza, i moduli possono restare. Si tolgono con
`pactl list modules short | grep -E 'null-sink|loopback'` per trovare gli
indici, poi `pactl unload-module <indice>`.

## Licenza e autore

Copyright (C) 2026 **Daniele Deplano (RedRider21)**.

Vox Populi è software libero distribuito sotto **GNU Affero General Public
License v3.0 o successiva** (`AGPL-3.0-or-later`): puoi usarlo, studiarlo,
modificarlo e ridistribuirlo, a condizione di rispettare gli obblighi di
copyleft — ogni opera derivata resta sotto la stessa licenza, e chi offre il
programma come servizio in rete deve rendere disponibile il sorgente ai propri
utenti. Il testo completo è in [`LICENSE`](LICENSE); l'enunciazione d'autore e
l'elenco delle licenze delle dipendenze sono in [`COPYRIGHT`](COPYRIGHT).

In alternativa è disponibile una **licenza commerciale** (doppia licenza) per
chi vuole integrare o distribuire Vox Populi in prodotti o servizi
proprietari, senza gli obblighi dell'AGPLv3: vedi
[`COMMERCIAL.md`](COMMERCIAL.md).

Il nome «Vox Populi» e l'identità visiva del progetto sono di Daniele Deplano
(RedRider21) e non sono concessi dalla licenza del software.

Progetto e sviluppo: **Daniele Deplano (RedRider21)** —
[github.com/RedRider21](https://github.com/RedRider21) — deplano.d@gmail.com

Segnalazioni, proposte e correzioni sono benvenute: apri una
[issue](https://github.com/RedRider21/vox-populi/issues) sul repository.

Copyright (C) 2026 Daniele Deplano (RedRider21).
