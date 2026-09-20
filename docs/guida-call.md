# Guida per il giorno della call

Promemoria operativo. Da tenere aperto sul secondo schermo, o stampato.

---

## Mezz'ora prima

**1. Prova tutto una volta, con calma.**
Apri un video in inglese su YouTube (va bene qualsiasi cosa con parlato
continuo) e avvia Vox Populi come faresti per la call. Serve a verificare che
la catena funzioni *prima* di avere una persona dall'altra parte.

- [ ] Le due finestre si aprono
- [ ] Nel pannello, il menu **Ascolta** punta al monitor giusto
      (cuffie o casse, secondo cosa userai)
- [ ] Nel pannello, il menu **Microfono** punta al tuo microfono
- [ ] Premendo **Avvia** compare `● in ascolto`
- [ ] Parlando tu in italiano, appare la traduzione inglese nel riquadro **TU**
- [ ] Il video in inglese fa comparire la traduzione italiana nel riquadro **LORO**

Se il riquadro LORO resta vuoto, cambia voce nel menu **Ascolta** finché non
appare il testo: è quasi sempre quello.

**2. Prova la condivisione.**
Fai una call di prova con Meet da solo (o con chiunque), condividi la finestra
**"Vox Populi - leggere qui"** e verifica di vederla bene. Impara il percorso
dei menu adesso, non durante la call.

**3. Decidi sulla voce sintetica.**
- [ ] Se la usi, spunta **Voce inglese** prima di avviare
- [ ] Avvia, poi in Meet scegli come microfono **Monitor of VoxPopuli_Mic**
- [ ] Premi **Prova** e verifica che la voce si senta
- [ ] Se non ti serve, lascia l'interruttore spento: i sottotitoli sono più reattivi

**4. Metti le cuffie.**
Risolvono l'eco alla radice. Se non le hai, va bene lo stesso: lascia attiva la
casella *Non trascrivere il microfono mentre l'altro parla*.

---

## La postura giusta

**Parla in frasi brevi e complete.** Il traduttore lavora bene su periodi con
un senso compiuto; si perde sulle subordinate lunghe e sui discorsi che
cambiano direzione a metà. Una frase, un'idea.

**Aspetta il tuo turno.** Non parlare sopra l'interlocutore: il sistema
trascrive una voce alla volta, e con il microfono sospeso mentre lui parla
finiresti per non essere tradotto affatto.

**Accetta il ritardo.** Circa due secondi e mezzo fra la fine di una frase e la
sua traduzione. Nella pratica leggerai la traduzione della frase precedente
mentre lui sta già dicendo la successiva. È normale, non è un guasto: non
aspettare di vedere il testo per rispondere, o la conversazione si inceppa.

**A voce accesa, i turni sono obbligatori.** Lui ti sente solo dopo che la voce
inglese ha parlato, quindi il silenzio che precede la traduzione è normale e non
significa che il microfono sia rotto. Non riempirlo parlando: se ricominci a
parlare mentre la voce sta ancora parlando, la frase dopo si accavalla.

**Fatti vedere mentre parli.** La finestra condivisa mostra il testo: se la
guardi tu invece di farla guardare a lui, non serve a niente. Tieni il pannello
personale sul tuo schermo e lascia la finestra grande a disposizione della call.

---

## Cosa dire all'inizio

Vale la pena spendere trenta secondi per spiegare la situazione. In inglese
semplice, o facendolo tradurre dal pannello:

> "I don't speak English well. I'm using a translation tool: you will see the
> English text of what I say in the shared window. Please speak slowly and in
> short sentences. Thank you."

Messo in chiaro all'inizio, il ritmo più lento non sembra un problema tecnico
ma una scelta condivisa.

---

## Se qualcosa si rompe durante la call

**Il pannello si è fermato.** Premi **Avvia** di nuovo. Il carico dei modelli è
la parte lenta, ma il programma si riprende senza riavviare Meet.

**Le traduzioni sono diventate assurde.** Succede se il microfono capta rumore
continuo o se due voci si sovrappongono. Fai una pausa di qualche secondo e
riprendi: il rilevatore di voce si ricalibra da solo sul rumore di fondo.

**Il programma si è chiuso del tutto.** Riaprilo con `./vox-populi`, ricondividi
la finestra in Meet. La call non si interrompe: perdi solo qualche secondo.

**Non capisci proprio una frase.** Chiedi di ripetere:
*"Sorry, could you repeat that more slowly?"* — con la traduzione a schermo,
la ripetizione arriva quasi sempre comprensibile.

**A voce accesa, l'interlocutore non sente più nulla.**
Se hai spento l'interruttore **Voce inglese** durante la call, il microfono
torna quello vero; verifica che Meet lo segua. Al contrario, se la voce è accesa
ma lui non sente nulla, il microfono di Meet è rimasto su quello fisico: va
messo su `Monitor of VoxPopuli_Mic`.

**La voce sintetica tace.**
Serve Internet. Se la connessione è caduta, i sottotitoli continuano a
funzionare ma la voce no: spegni l'interruttore e prosegui a testo.

---

## Dopo la call

- [ ] Chiudi Vox Populi (Ctrl+C nel terminale, o chiudi il pannello)
- [ ] Se hai usato la voce sintetica, in Meet rimetti il microfono normale
- [ ] Il microfono virtuale viene smontato all'uscita: se hai dei dubbi,
      controlla con `pactl list modules short | grep -E 'null-sink|loopback'`

Le preferenze — dispositivi, posizione delle finestre, dimensione del carattere
— restano salvate per la prossima volta.

---

## Riepilogo in tre righe

1. `./vox-populi`, controlla i due menu, premi **Avvia**
2. In Meet condividi la finestra **"Vox Populi - leggere qui"**
3. Se usi la voce: spunta **Voce inglese** e in Meet scegli
   `Monitor of VoxPopuli_Mic`
4. Parla in frasi brevi, aspetta il tuo turno, accetta i due secondi di ritardo
