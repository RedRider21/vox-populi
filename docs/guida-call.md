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

**3. Metti le cuffie.**
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

---

## Dopo la call

- [ ] Chiudi Vox Populi (Ctrl+C nel terminale, o chiudi il pannello)
- [ ] Verifica che il microfono di sistema sia tornato normale, se hai usato
      la voce sintetica (in questa versione non è attiva)

Le preferenze — dispositivi, posizione delle finestre, dimensione del carattere
— restano salvate per la prossima volta.

---

## Riepilogo in tre righe

1. `./vox-populi`, controlla i due menu, premi **Avvia**
2. In Meet condividi la finestra **"Vox Populi - leggere qui"**
3. Parla in frasi brevi, aspetta il tuo turno, accetta i due secondi di ritardo
