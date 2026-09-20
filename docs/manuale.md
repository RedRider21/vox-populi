# Manuale di Vox Populi

Tutto quello che serve per installare, usare e, se qualcosa non va, capire
perché. Per il giorno della call c'è un promemoria a parte, più asciutto:
[`guida-call.md`](guida-call.md).

---

## 1. Che cos'è

Vox Populi traduce una conversazione a due, in tempo reale, restando sul tuo
computer. Ascolta due flussi audio — la voce dell'interlocutore, che arriva
dalle casse o dalle cuffie, e la tua, che arriva dal microfono — li trascrive,
li traduce e li mostra a schermo in due finestre: una per te, una da condividere.

**L'interlocutore non installa niente.** Nessuna estensione, nessun account,
nessun programma da avviare. Lui usa la sua solita applicazione di
videoconferenza e vede una finestra condivisa, come se fosse una presentazione.

Non viene inviato niente a Internet mentre conversi: i modelli girano sul tuo
processore. Dopo il primo avvio funziona anche senza connessione.

### Cosa sente e cosa vede l'altro

Questo è il punto da capire prima di iniziare, perché cambia il modo di parlare.
Le due modalità si scelgono dalla casella **Voce** nel pannello.

**A voce spenta** (consigliato per iniziare) — lui ti sente parlare in italiano
e legge la traduzione:

| | Tu senti | Lui sente | Lui vede |
|---|---|---|---|
| Tu parli la tua lingua | la traduzione nel pannello | **la tua voce vera** | la traduzione, nella finestra condivisa |
| Lui parla la sua | la traduzione nel pannello | la propria voce, normalmente | — |

Si parla a turni: lui aspetta che tu finisca di leggere. È una conversazione
più lenta, ma non serve nessun cambio di configurazione a metà strada.

**A voce accesa** — lui sente la traduzione pronunciata da una voce sintetica,
nella sua lingua. È doppiaggio vero, con un ritardo:

| | Tu senti | Lui sente |
|---|---|---|
| Tu parli la tua lingua | la traduzione nel pannello | un breve silenzio, **poi la frase tradotta** |
| Lui parla la sua | la traduzione nel pannello | la propria voce, normalmente |

Il ritardo è la parte da accettare: mentre parli, lui non sente niente; appena
finisci la frase, sente la traduzione. Non è simultanea, è a turni. Per questo
la voce serve soprattutto a chi fatica a leggere mentre ascolta.

---

## 2. Installazione

### Prima di scaricare: quanto occupa

I modelli non stanno nel repository — sono centinaia di MB. Al primo avvio ne
servono **circa 655 MB**:

| Cosa | Dove | Spazio |
|---|---|---|
| Trascrizione (Whisper `small`) | `~/.local/share/vox-populi/whisper/` | ~465 MB |
| Traduzione italiano ↔ inglese | `~/.local/share/vox-populi/modelli/` | ~190 MB |

Ogni lingua in più costa circa **190 MB per direzione** e si scarica dall'app,
non da qui. La coppia italiano/inglese è inclusa nell'installazione.

Se installi dal **pacchetto .deb** si aggiungono le librerie Python, che non
esistono come pacchetti Debian e finiscono in una cartella dell'utente:

| Cosa | Spazio |
|---|---|
| `torch`, nella variante per CPU (quella per le schede video è il doppio e qui non serve) | ~750 MB |
| `faster-whisper`, `argostranslate`, `edge-tts` e le loro dipendenze | ~750 MB |

**Non parte mai un download da solo**: `install.sh` dichiara quanto scaricherà
e chiede conferma; l'avvio dal pacchetto dice quanto pesano le librerie e
chiede conferma pure lui, con una finestra se non c'è un terminale; dall'app i
modelli si scaricano solo premendo **Installa modelli**.

### Procedura

**Dal pacchetto (consigliato).** Scarica `vox-populi_0.1.0_all.deb` dalla
pagina delle release e aprilo con doppio clic: si installa come qualsiasi altro
programma, senza terminale, e compare nel menu delle applicazioni. Al primo
avvio prepara da sé le librerie Python. Se preferisci prepararle in anticipo:

```bash
vox-populi --prepara
```

**Dal sorgente.** Su Debian, Ubuntu e affini:

```bash
./install.sh
```

Lo script:

1. dice quanto occupa e chiede conferma (per saltare la domanda: `./install.sh --si`);
2. installa i pacchetti di sistema mancanti (`python3-gi`, `pulseaudio-utils`, `ffmpeg`);
3. installa le dipendenze Python;
4. raccoglie in un'unica cartella i dati di eventuali versioni precedenti;
5. scarica i modelli mancanti;
6. esegue una diagnosi e dice se è tutto a posto.

È idempotente: rilanciarlo non fa danni e non riscarica ciò che c'è già.

### Dove finisce tutto

In **una cartella sola**, `~/.local/share/vox-populi/`:

```
~/.local/share/vox-populi/
├── config.json     preferenze (dispositivi, lingue, tema, posizione finestre)
├── voci.json       elenco delle voci sintetiche, aggiornato da solo
├── modelli/        pacchetti di traduzione
├── whisper/        modello di trascrizione
└── venv/           librerie Python (solo se installato dal pacchetto)
```

Si copia su un'altra macchina e il programma è già configurato; si cancella e
non resta niente. Il percorso si può spostare con la variabile d'ambiente
`VOXPOPULI_DATA_DIR`.

### Disinstallare

Dal pacchetto:

```bash
sudo apt remove vox-populi            # il programma
rm -rf ~/.local/share/vox-populi      # modelli, preferenze e librerie
```

`apt remove` toglie solo il programma: modelli, preferenze e le librerie Python
restano dove sono, perché sono nella cartella dell'utente e valgono un paio di
GB di download. Se non servono più, la seconda riga li cancella tutti insieme.

Dal sorgente il programma è la cartella del progetto: cancellala, e poi la
stessa riga per i dati dell'utente.

---

## 3. Avvio e primo uso

Dal pacchetto basta **Vox Populi** nel menu delle applicazioni, oppure:

```bash
vox-populi
```

Dal sorgente:

```bash
./vox-populi
```

Al primo avvio, se installato dal pacchetto, il programma prepara le librerie
Python; lo fa una volta sola e dice quanto pesa prima di cominciare.

Si aprono due finestre:

- **Vox Populi** — il pannello, quello che vedi tu. Resta sopra le altre finestre.
- **Vox Populi - leggere qui** — la finestra grande, quella che condividi.

### I controlli del pannello

| Controllo | A cosa serve |
|---|---|
| **Parlo** | la lingua in cui parli tu |
| **Lui parla** | la lingua del tuo interlocutore |
| **Installa modelli** | scarica la coppia scelta, dicendo prima quanto occupa |
| **Ascolta** | da dove arriva la voce dell'interlocutore (casse o cuffie) |
| **Microfono** | il tuo microfono |
| **Non trascrivere il microfono mentre l'altro parla** | evita l'eco con le casse |
| **Voce** | attiva la voce sintetica e scegli quale |
| **Colori** | lo schema di colore delle due finestre |
| **Avvia** / **Ferma** | avvia e ferma la conversazione |
| **Finestra per lui** | riporta in primo piano la finestra da condividere |

Le scelte vengono ricordate per la volta successiva, compresa la posizione
delle finestre e il tema.

### Ordine di avvio

1. Scegli **Parlo** e **Lui parla**. Se compare **Installa modelli**, premilo e
   aspetta: fallo prima della call, non durante.
2. Scegli **Ascolta**: il *monitor* dell'uscita che stai usando. Con le cuffie,
   il monitor delle cuffie; con le casse, il monitor delle casse.
3. Scegli il **Microfono**.
4. **Premi Avvia.** La prima volta carica i modelli (qualche secondo), poi
   compare `● in ascolto`.
5. In Meet, condividi la finestra **"Vox Populi - leggere qui"** con
   *Condividi una finestra* — non tutto lo schermo.
6. Parla normalmente.

### Il monitor giusto

Il menu **Ascolta** elenca sia microfoni sia monitor. I monitor sono le
sorgenti che catturano *quello che esce* dagli altoparlanti: si riconoscono
perché il nome contiene `.monitor` e la descrizione finisce con *"sente
l'interlocutore"*. È da lì che arriva la voce di chi parla dall'altra parte.

Se scegli un microfono al posto del monitor, non sentirai mai l'altro.

Se nel riquadro **LORO** non compare niente, il menu **Ascolta** è la prima
cosa da controllare: prova le altre voci finché non appare il testo.

---

## 4. Lingue

**50 lingue** per la traduzione. Si scelgono dal pannello e si possono cambiare
anche a conversazione avviata.

La coppia più usata, italiano ↔ inglese, ha modelli diretti. Per tutte le altre
coppie il programma passa dall'inglese come **lingua ponte**:

```
italiano  →  inglese  →  tedesco
```

Funziona, ma allunga leggermente la traduzione e può aggiungere qualche
imprecisione, perché il testo passa per una lingua intermedia. La diagnosi
(`python3 -m voxpopuli.cli diagnosi`) dice quando una coppia passa dal ponte.

Le lingue disponibili sono: albanese, arabo, azero, basco, bengalese, bulgaro,
catalano, ceco, chirghiso, cinese (semplificato), cinese (tradizionale),
coreano, danese, ebraico, esperanto, estone, finlandese, francese,
galiziano, giapponese, greco, hindi, indonesiano, inglese, irlandese,
italiano, lettone, lituano, malese, norvegese, olandese, persiano, polacco,
portoghese, portoghese (Brasile), rumeno, russo, slovacco, sloveno, spagnolo,
svedese, swahili, tagalog, tedesco, thai, turco, ucraino, ungherese, urdu,
vietnamita.

### Scaricare una lingua nuova

Premi **Installa modelli** dopo aver scelto la coppia. Il programma dice quali
pacchetti servono e quanto occupano, poi li scarica mostrando l'avanzamento.

Per l'italiano serve quasi sempre passare dall'inglese, quindi una lingua nuova
possono essere due pacchetti (~190 MB), non uno.

---

## 5. Voci

**322 voci in 75 lingue**. Non sono un elenco scritto nel programma: vengono
chieste al servizio di Microsoft e messe in cache per 30 giorni, così restano
aggiornate. Se la rete non è disponibile, il programma usa sei voci di riserva
e continua a funzionare.

Ogni voce è descritta con genere e nazionalità — `Prabhat · maschile · India` —
utile per far parlare l'interlocutore con la voce del suo paese invece che con
un accento a caso. L'elenco del menu **Voce** cambia in base alla lingua scelta
in **Lui parla**.

Su 50 lingue traducibili, **46 hanno anche una voce**. Le altre quattro —
esperanto, basco, chirghiso, tagalog — si traducono e si leggono, ma non hanno
una voce sintetica: a voce accesa quelle lingue resterebbero mute. Il programma
lo segnala.

Il pulsante **Prova** pronuncia una frase di esempio con la voce scelta.
Funziona solo a conversazione già avviata.

### Far arrivare la voce all'interlocutore

Questa parte si fa **una volta sola per call**. Il programma crea un
**microfono virtuale** nel sistema: un dispositivo che Meet vede come un
microfono normale, dentro cui il programma può mettere la voce sintetica.

1. Spunta **Voce** e scegli la voce, prima di premere Avvia.
2. Premi **Avvia**. Compare la scritta con il nome del microfono da scegliere.
3. In Meet, imposta come microfono **`Monitor of VoxPopuli_Mic`**.
4. Premi **Prova** e verifica che la voce si senta.

Se salti il punto 3, lui continua a sentirti in italiano e la voce sintetica
resta muta: è l'errore più facile da fare.

Alla chiusura del programma il microfono virtuale viene rimosso e il sistema
torna come prima. Se per un blocco il programma non si chiude bene, si tolgono
a mano con:

```bash
pactl unload-module module-null-sink
pactl unload-module module-loopback
```

---

## 6. Aspetto

Sei schemi di colore, da **Colori**: Scuro (ciano), Chiaro, Ambra (terminale),
Verde fosforo, Notte (viola), Alto contrasto. Si applicano subito, anche alle
finestre già aperte e a quella che stai condividendo.

Servono a leggere meglio: c'è chi lavora al buio, chi in pieno sole, e chi ha
bisogno del massimo contrasto. **Alto contrasto** è pensato per chi ha problemi
di vista o lavora in condizioni di luce difficile.

Il carattere delle due finestre si regola dalle preferenze (`font_size` per il
pannello, `speaker_font_size` per la finestra condivisa, in `config.json`).

---

## 7. Cuffie e casse

**Con le cuffie non c'è nessun problema**: la voce dell'altro finisce nelle
tue orecchie e non rientra dal microfono.

**Con le casse** la voce di chi parla esce dagli altoparlanti, rientra dal
microfono e verrebbe trascritta come se fossi tu, generando frasi fantasma.
Il programma se ne accorge e sospende il microfono mentre l'altro parla — è la
casella **Non trascrivere il microfono mentre l'altro parla (evita l'eco)**,
attiva di default. Funziona, ma se parlate insieme una delle due frasi si perde.

Se puoi, usa le cuffie. Se non puoi, lascia la casella attiva e parla a turni.

---

## 8. Latenza

Misurata su una macchina con i5-1235U, a modelli già caricati:

| Stadio | Tempo |
|---|---|
| Attesa di fine frase | ~0,6 s |
| Trascrizione | ~1,75 s |
| Traduzione | ~0,06 s |
| **Totale percepito** | **~2,4 s** |

In pratica: leggi la traduzione della frase precedente mentre l'altro sta già
dicendo la successiva. Conviene rassegnarsi a questo ritmo, invece di aspettare
il testo prima di rispondere — altrimenti la conversazione si impunta.

La prima frase dopo l'avvio è più lenta: i modelli si stanno caricando. Vale la
pena avviare il programma qualche minuto prima della call.

---

## 9. Se qualcosa non va

**Il pannello non mostra niente mentre l'altro parla.**
Il menu **Ascolta** non punta al monitor giusto. Prova le altre voci finché non
appare il testo. Controlla anche che l'audio dell'altro esca davvero dalle
casse o dalle cuffie che stai monitorando.

**Non appare niente nel riquadro TU.**
Il **Microfono** scelto non è quello che stai usando, oppure è muto a livello di
sistema. Prova con `python3 -m voxpopuli.cli live` e parla: se non compare
niente nemmeno lì, il problema è nel dispositivo.

**Le frasi si spezzano a metà.**
Il rumore di fondo o una pausa lunga. Parla con frasi intere e un tono
uniforme; avvicinati al microfono se l'ambiente è rumoroso.

**La traduzione è sbagliata o senza senso.**
Succede con frasi molto brevi o con frasi lasciate a metà. Il motore è locale e
gratuito: sui discorsi completi se la cava bene, sulle interiezioni no. Parla
per frasi compiute.

**Una lingua non c'è nel menu.**
O non è fra le 50 supportate, o mancano i modelli: scegli la coppia e premi
**Installa modelli**. La lingua deve essere disponibile sia per la traduzione
sia, se usi la voce, per la sintesi.

**La voce sintetica non si sente in Meet.**
Il microfono di Meet non è `Monitor of VoxPopuli_Mic`. È il punto 3 della
sezione 5.

**Il programma sembra bloccato al primo avvio.**
Sta scaricando il modello di trascrizione (~465 MB) e non lo dice ancora in
modo visibile. Guarda il terminale da cui l'hai avviato: se c'è scritto
`[stt] modello 'small' assente`, è quello. Aspetta.

**`parec` o `pactl` non trovati.**
`sudo apt install pulseaudio-utils`. Con PipeWire funzionano lo stesso.

**La finestra non resta sopra le altre.**
Su Wayland `set_keep_above` può non funzionare: usa una sessione X11.

---

## 10. Comandi da terminale

Servono per le prove, senza aprire l'interfaccia:

```bash
python3 -m voxpopuli.cli diagnosi                  # dipendenze, modelli, sorgenti audio
python3 -m voxpopuli.cli dispositivi               # elenca monitor e microfoni
python3 -m voxpopuli.cli file audio.mp3 en         # trascrive e traduce un file
python3 -m voxpopuli.cli live                      # cattura dal vivo, stampa a terminale
```

`diagnosi` è il primo comando da eseguire quando qualcosa non va: dice cosa
manca e dove.

`file` accetta come secondo argomento la lingua parlata nel file (una delle 50).
`live` accetta `--remoto NOME`, `--mic NOME` e `--no-half-duplex`.

### Generare le schermate del README

```bash
python3 tools/anteprima.py [cartella_campioni] [cartella_uscita]
```

Fa girare i modelli veri su alcuni campioni audio e fotografa le finestre reali.
Le immagini finiscono in `/tmp` per impostazione predefinita.

---

## 11. Requisiti

- Linux con PulseAudio o PipeWire (`parec` e `pactl`)
- Sessione **X11** — su Wayland la finestra sempre-in-alto può non funzionare
- Python 3.10 o superiore, PyGObject e GTK 3
- Una CPU decente: la trascrizione gira su processore, senza GPU
- ~700 MB liberi per i modelli, e altri ~1,5 GB se installi dal pacchetto,
  che si porta dietro le librerie Python

---

## 12. Licenza

Vox Populi è software libero sotto **GNU AGPL v3.0 o successiva**. Per usi che
non possono rispettarne gli obblighi di copyleft — integrazione in prodotti
chiusi, erogazione come servizio senza pubblicare il sorgente — è disponibile
una [licenza commerciale](COMMERCIAL.md) separata.

Chi vuole contribuire trova le condizioni in [`CLA.md`](../CLA.md).

**Autore**: Daniele Deplano (RedRider21) — deplano.d@gmail.com
