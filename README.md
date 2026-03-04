# Agentic Category Management

Le promozioni trade rappresentano in media il 15–25% del fatturato dei manufacturer di largo consumo e costituiscono la principale voce di costo dopo il costo del venduto. Eppure la loro pianificazione avviene ancora in buona parte attraverso negoziazioni bilaterali, fogli Excel e regole empiriche consolidate nel tempo.

Il problema è strutturalmente complesso. Manufacturer e retailer siedono al tavolo con obiettivi parzialmente allineati — entrambi vogliono che la categoria cresca — ma con incentivi contrapposti sulla distribuzione del margine. Il category manager del retailer deve bilanciare margine per metro lineare, rotazione dell'inventario, soddisfazione del consumatore e qualità della relazione con ciascun fornitore. Il trade promotion manager del manufacturer deve decidere quale SKU promuovere, con quale sconto, per quante settimane e con quale display fee — sapendo che ogni promozione genera un lift immediato ma anche un post-promo dip, e che i competitor osservano le sue mosse e reagiscono.

A complicare il quadro: l'informazione è asimmetrica (il manufacturer conosce i propri costi, il retailer conosce i dati di basket), le decisioni sono sequenziali e interdipendenti, e la conoscenza rilevante si accumula lentamente nel tempo — alcune dinamiche (la stagionalità) sono stabili, altre (le tattiche dei competitor) cambiano continuamente.

Questo sistema modella esattamente quella dinamica. Cinque agenti LLM — tre manufacturer, un retailer, un consumer — negoziano assortimento, promozioni e spazio scaffale su un mercato snack italiano simulato. Non seguono script. Ognuno conosce i propri obiettivi e decide autonomamente come perseguirli, settimana dopo settimana, episodio dopo episodio.

---

## Principi di design

Il termine *agentico* viene usato in modo molto ampio. Spesso descrive sistemi in cui un LLM esegue una sequenza di step predefiniti, chiama API in ordine fisso, o segue un workflow che il programmatore ha già risolto — lasciando all'LLM solo il compito di riempire i campi. È un uso legittimo del termine in contesti di automazione, ma non cattura la dimensione più interessante dell'agentività: la capacità di un sistema di prendere decisioni non prescritte, adattare la strategia nel tempo, e generare comportamenti che il progettista non ha esplicitamente programmato.

Un test pratico: se rimuovessi l'LLM dal sistema e lo sostituissi con regole hardcodate, il comportamento cambierebbe in modo sostanziale? Se la risposta è no — se l'LLM sta solo formattando output o traducendo istruzioni in API call — allora il ragionamento non è davvero distribuito negli agenti.

In questo sistema la risposta è sì. Nessun agente sa in anticipo cosa proporrà la settimana prossima: dipende da cosa è successo quella corrente, da cosa ha osservato negli episodi precedenti, da come si è comportato il retailer, da cosa suggerisce il grafo di memoria. Il comportamento emerge dalla composizione di incentivi, contesto e ragionamento — non da uno script.

Quattro principi rendono questo possibile:

| Principio | Come si applica |
|---|---|
| **Obiettivi, non istruzioni** | I system prompt definiscono chi è ogni agente e cosa vuole. Mai come ottenerlo. Il ragionamento appartiene agli agenti. |
| **Contesto ricco, non prescrittivo** | Ogni settimana gli agenti ricevono lo stato del mercato e la memoria condivisa. Decidono loro. Nessuna regola hardcodata. |
| **Memoria attiva e verificabile** | Un grafo di conoscenza persiste tra gli episodi e cambia il comportamento degli agenti in modo misurabile. |
| **Intelligenza sistemica** | Il sistema impara come sistema, non come somma di agenti isolati. Ogni interazione deposita conoscenza che tutti gli agenti possono usare. |

---

## Come funziona

Ogni **episodio** è una sequenza di settimane simulate. A ogni settimana, gli agenti agiscono in ordine:

```
Consumer → Manufacturers → Retailer → World Step → verifica fine episodio
    ↑_________________________________________________________________|
```

Il **Consumer** aggiorna i trend di domanda (preferenza healthy, sensibilità al prezzo). I **Manufacturer** decidono se proporre promozioni al retailer — quale SKU, che sconto, che display fee. Il **Retailer** valuta le proposte: può accettare, rifiutare, o fare un counter-offer. Il **World Engine** calcola domanda, fatturato e margini, e avanza di una settimana.

A fine episodio, la conoscenza emersa viene distillata nel grafo di memoria, pronta per gli episodi successivi.

### Gli agenti

| Agente | Ruolo | KPI |
|---|---|---|
| **Manufacturer A** | Brand premium — ChipsPremium, CrackersPremium | Revenue, margine, ROI promozionale |
| **Manufacturer B** | Brand mass market — 3 SKU chips e crackers | Volume, revenue, margine |
| **Manufacturer C** | Challenger healthy — ProteinBar, RiceCakes Bio | Penetrazione, allineamento ai trend |
| **Retailer** | Category Manager GDO | Margine per metro lineare, volume, rotazione |
| **Consumer** | Domanda aggregata + segnale di trend | Rappresentazione fedele del comportamento di mercato |

---

## La memoria come protagonista

Il componente più importante del sistema non è nessun singolo agente — è la struttura di memoria che gli agenti condividono e alimentano nel tempo. Ma "memoria" non è un concetto uniforme: esistono due tipi con orizzonti temporali, funzioni e logiche di accesso radicalmente diverse, e la scelta di progettarli in modo asimmetrico non è arbitraria.

**Memoria a breve termine — privata, per-episodio.** Ogni agente mantiene una sliding window delle proprie ultime 10 decisioni settimanali (`short_term_memory` in `agent_base_class.py`), azzerata a inizio di ogni nuovo episodio. È la memoria di lavoro: "la settimana scorsa ho proposto uno sconto del 20% su ChipsPremium e il retailer ha rifiutato — questa settimana cambio tattica". È privata perché in un mercato competitivo ogni agente custodisce le proprie mosse. Un manufacturer non condivide con i competitor quanto sta scontando, né il retailer espone la propria funzione di preferenza a chi ci negozia contro. La breve termine cattura le strategie, ed è giusto che resti opaca agli altri.

**Memoria a lungo termine — condivisa, cross-episodio.** Il `MarketMemoryGraph` (`memory/system_memory.py`) è un grafo di conoscenza che persiste su disco tra tutti gli episodi. Non contiene log grezzi di eventi, ma pattern distillati: relazioni quantificate tra entità di mercato (SKU, stagioni, manufacturer, categorie), ciascuna con confidenza e conteggio delle evidenze accumulate nel tempo. È il patrimonio cognitivo del sistema — cresce episodio dopo episodio. Qui la scelta è opposta rispetto alla breve termine: il grafo è condiviso tra tutti gli agenti. La ragione è contestuale. Nella GDO reale, i pattern di mercato aggregati — stagionalità, lift promozionale per categoria, elasticità al prezzo — sono spesso commercialmente disponibili tramite provider come Nielsen o IRI, accessibili a tutti gli attori. Non sono segreti: sono la conoscenza di sfondo su cui tutti ragionano. Le strategie individuali restano proprietarie; le leggi del mercato no. Il grafo modella esattamente questa distinzione: ogni agente vi deposita osservazioni pubblicamente osservabili, non le proprie tattiche.

A collegare le due: il `MemoryExtractor` (`memory/agent_memory.py`), che a fine episodio analizza i risultati settimanali e le decisioni degli agenti, e deposita nuove osservazioni nel grafo a lungo termine. È il bridge tra ciò che è successo nell'episodio e la conoscenza che persiste.

### La struttura del grafo a lungo termine

La memoria a lungo termine è organizzata in due layer con dinamiche diverse:

- **Layer 1 — Conoscenza Strutturale:** leggi di mercato confermate nel tempo. Decadono lentamente, quasi permanenti. *Es: "La domanda picca nelle settimane 24–35 (estate) e 48–52 (Natale)."*
- **Layer 2 — Conoscenza Tattica:** pattern contingenti, comportamenti correnti degli agenti. Decadono per episodio se non confermati. *Es: "Manufacturer A tende a fare dumping nelle ultime settimane dell'episodio."*

Ogni osservazione nasce nel Layer 2. Se viene confermata con confidenza ≥ 75% per almeno 5 episodi, viene **promossa automaticamente al Layer 1**. Il sistema decide autonomamente cosa diventa legge di mercato e cosa rimane contingente.

```
Promozione Layer 2 → Layer 1:  evidence_count ≥ 5  AND  confidence ≥ 0.75
```

Nei primi episodi gli agenti operano quasi al buio: la breve termine cattura solo le ultime mosse, la lunga è ancora vuota. Dopo 5–10 episodi iniziano a comparire leggi strutturali: lift promozionale per SKU, stagionalità confermata, pattern comportamentali dei competitor. Gli agenti leggono entrambe le memorie ogni settimana — e le loro decisioni cambiano di conseguenza. È questo accumulo che trasforma una sequenza di negoziazioni isolate in qualcosa che assomiglia all'apprendimento.

La scelta di un grafo unico condiviso è consapevolmente semplificativa: in un sistema orientato alla competizione pura, si avrebbe un grafo per agente, con osservazioni filtrate per prospettiva. Quella direzione è percorribile nell'architettura attuale e rappresenta un'estensione naturale per simulazioni più adversariali.

---

## Modello di mercato

Il comportamento di mercato è modellato dalla classe `MarketSimulator` (`world/market_simulator.py`), che gestisce 8 SKU in 3 sottocategorie (chips, crackers, healthy) e calcola, settimana per settimana, domanda, ricavi e margini per ogni attore. È il layer di realtà su cui gli agenti esercitano le proprie decisioni — e la fonte dei dati che il `MemoryExtractor` distilla nel grafo a lungo termine.

### Domanda moltiplicativa

La domanda di ogni SKU in ogni settimana è il prodotto di sei fattori indipendenti:

```
unità = domanda_base × stagionalità × trend_consumer × lift_promozionale × dip_post_promo × rumore
```

**Domanda base** — la vendita attesa in condizioni neutrali, specifica per SKU. Riflette il posizionamento: il mass market (ChipsMass) parte da 200 unità/settimana, il premium (ChipsPremium) da 120, i prodotti healthy da 60–70. La private label del retailer si colloca a 180.

**Stagionalità** — un array di 52 moltiplicatori settimanali, costruito una volta sola in `_build_seasonality()` e applicato deterministicamente a tutti gli SKU. Riflette i picchi reali della GDO italiana: +25% estate (settimane 24–35), +35% Natale (settimane 48–52), +20% a cavallo d'anno, −20% nelle settimane 3–6 (calo post-feste). La stagionalità è uguale per tutti gli SKU — è la struttura del calendario, non una caratteristica di prodotto.

**Trend consumer** — due parametri continui in [-1.0, +1.0] aggiornati ogni settimana dall'agente Consumer: `healthy_preference` e `price_sensitivity`. La preferenza healthy amplifica o smorza la domanda degli SKU in sottocategoria healthy (fino a ±30%). La sensibilità al prezzo riduce la domanda complessiva quando alta (fino a −10%) — modellando il fenomeno per cui i consumatori molto attenti al prezzo rinviano gli acquisti in assenza di promozioni.

**Lift promozionale** — quando una promozione è attiva, la domanda sale. Il lift base è ×1.8, incrementato proporzionalmente allo sconto applicato. Se il manufacturer ha pagato una display fee superiore a 400€, si aggiunge un ulteriore +0.3× per il posizionamento premium in scaffale. Il lift è cappato a ×3.0 per evitare effetti irrealistici. Con uno sconto del 25% e display fee 500€, il lift tipico è intorno a ×2.3.

**Post-promo dip** — la contrazione della domanda nelle 3 settimane successive alla fine di una promozione (−20%). Modella il fenomeno reale di pantry loading: i consumatori si sono riforniti durante la promo e nei giorni successivi acquistano meno. Il simulatore traccia automaticamente le SKU in stato di dip tramite `post_promo_dip_tracker`, senza che gli agenti debbano gestirlo esplicitamente.

**Rumore** — perturbazione gaussiana (μ=1.0, σ=0.05) che introduce variabilità realistica. Previene che il sistema converga su pattern deterministici identici e rende ogni episodio distinto.

### Struttura dei prezzi e dei margini

Ogni SKU ha tre prezzi: costo di produzione, prezzo di listino manufacturer→retailer, e prezzo al consumatore di base. Quando una promozione è attiva, il transfer price si riduce della percentuale di sconto concordata. Il retailer calcola il proprio prezzo al consumatore mantenendo un margine del ~30% sul transfer price ridotto. La display fee agisce come trasferimento diretto: il manufacturer la paga, il retailer la riceve, indipendentemente dal volume venduto.

| SKU | Mfr | Sottocategoria | Domanda base | Costo prod. | Prezzo MFR→RTL | Prezzo consumatore |
|---|---|---|---|---|---|---|
| ChipsPremium 150g | mfr_a | chips | 120 | €0.80 | €1.50 | €2.20 |
| CrackersPremium 200g | mfr_a | crackers | 80 | €0.60 | €1.20 | €1.80 |
| ChipsMass 200g | mfr_b | chips | 200 | €0.50 | €0.90 | €1.50 |
| CrackersMass 250g | mfr_b | crackers | 150 | €0.45 | €0.85 | €1.40 |
| ChipsMass Gusto 150g | mfr_b | chips | 100 | €0.55 | €1.00 | €1.60 |
| ProteinBar 40g | mfr_c | healthy | 60 | €1.20 | €2.50 | €3.80 |
| RiceCakes Bio 100g | mfr_c | healthy | 70 | €0.90 | €1.80 | €2.90 |
| PrivateLabel Chips | retailer | chips | 180 | €0.40 | — | €1.20 |

La private label è sempre listata e non soggetta a negoziazione. Il suo costo di produzione coincide con il transfer price (il retailer produce e distribuisce direttamente), quindi il margine è interamente la differenza tra prezzo al consumatore e costo. Non è un agente ma un benchmark di pressione competitiva perenne sulla sottocategoria chips — la sua presenza costringe i manufacturer a giustificare il differenziale di prezzo con qualità percepita o promozioni.

### Reward e incentivi

A fine episodio, `compute_rewards()` calcola il reward per ogni agente a partire dai KPI accumulati. Per i manufacturer: combinazione di revenue normalizzata (40%), margine normalizzato (30%) e ROI promozionale (30%). Per il retailer: margine di categoria (40%), volume totale (30%), rotazione dell'inventario (30%).

Il reward finale è un **blend 60% individuale / 40% sistemico**: il KPI individuale viene mescolato con la media dei reward di tutti gli agenti. Questa scelta modella la dinamica di partnership tipica della GDO — in cui manufacturer e retailer hanno interesse alla salute dell'intera categoria, non solo alla propria quota — e impedisce che il sistema converga su strategie puramente avversariali dove un agente massimizza erodendo il valore degli altri.

---

## Output

| File | Contenuto |
|---|---|
| `results.json` | Reward per agente e nuova conoscenza strutturale per ogni episodio |
| `output_data/knowledge_graph.json` | Grafo di memoria persistente — nodi, archi, confidenza, layer |

A fine episodio il sistema stampa nel terminale i reward per agente (scala ~0–2, blend 60% individuale + 40% sistemico), la conoscenza strutturale accumulata, e le promozioni Layer 2 → Layer 1 avvenute in quell'episodio.

> I reward bassi nei primi episodi sono normali: i KPI sono normalizzati su base annuale, con poche settimane il numeratore è piccolo. Il comportamento diventa significativo dopo 5–10 episodi.

---

## Struttura del progetto

```
main.py
src/
├── agents/
│   ├── agent_base_class.py  # Classe base: chiamata LLM + parsing JSON + memoria a breve termine privata
│   └── agents.py        # I 5 agenti
├── memory/
│   ├── system_memory.py # MarketMemoryGraph — memoria a lungo termine condivisa (grafo Layer 1/Layer 2)
│   └── agent_memory.py  # MemoryExtractor — bridge tra breve termine e lungo termine
├── orchestrator/
│   └── graph.py         # Orchestratore LangGraph — ciclo settimanale
└── world/
    └── market_simulator.py  # Simulatore: domanda, financials, reward
```

---

## Setup

**Requisiti:** Python 3.11+, [Ollama](https://ollama.ai) installato e in esecuzione.

```bash
git clone https://github.com/mamatteo/agentic_category_management.git
cd agentic_category_management
pip install -r requirements.txt
ollama pull qwen3:8b
```

### Modelli supportati

| Modello | Dimensione | Note |
|---|---|---|
| `qwen3:8b` | ~5 GB | Raccomandato — qualità e velocità bilanciate |
| `qwen3:14b` | ~9 GB | Qualità superiore, richiede ≥ 16 GB RAM |
| `qwen2.5:latest` | ~5 GB | Alternativa stabile |
| `llama3.2:latest` | ~2 GB | Più veloce, parsing JSON meno affidabile |

---

## Utilizzo

```bash
# Episodio singolo
python main.py

# N episodi consecutivi — la memoria si accumula tra tutti
python main.py --episodes 10

# Episodio specifico
python main.py --episode 5

# Modello alternativo
python main.py --model qwen2.5:latest

# Riprendi da un episodio specifico
python main.py --episodes 5 --start-from 11
```

Ogni settimana richiede 5 chiamate LLM. Con modelli locali su hardware consumer, un episodio da 4 settimane dura tipicamente 5–15 minuti. La durata dell'episodio è configurabile in `orchestrator/graph.py` → `node_check_episode_end`.

---

## Stack

| Componente | Tecnologia |
|---|---|
| Orchestrazione agenti | [LangGraph](https://github.com/langchain-ai/langgraph) |
| Inferenza LLM | [Ollama](https://ollama.ai) + Qwen3 (locale, no API key) |
| Grafo di memoria | [NetworkX](https://networkx.org) |
| Dati strutturati | [Pydantic v2](https://docs.pydantic.dev) |
| Output terminale | [Rich](https://github.com/Textualize/rich) |

---

## Possibili nuovi sviluppi

**Strategy journal per agente.** Attualmente ogni agente mantiene uno storico delle proprie decisioni settimanali, ma non sintetizza insight di lungo periodo. Un journal persistente — alimentato dall'LLM a fine episodio — permetterebbe a ciascun agente di ragionare su pattern multi-episodio: *"nelle ultime 5 stagioni estive, le promozioni su ChipsPremium hanno generato ROI superiore alla media"*. Trasformerebbe la memoria da log a vera intelligenza strategica.

**Negoziazione multi-round.** Il protocollo attuale prevede un singolo ciclo proposta–risposta per settimana. La negoziazione reale in GDO è molto più articolata: joint business plan annuali, accordi quadro su più SKU, rinegoziazione delle condizioni al raggiungimento di target di volume. Estendere il protocollo a più round esporrebbe dinamiche di potere negoziale che il modello attuale non cattura.

**Topologia multi-retailer.** Con un solo retailer, i manufacturer non affrontano il problema reale dell'allocazione del budget promozionale tra catene diverse. Aggiungere più retailer in competizione — con profili di consumatori e politiche di categoria distinti — introdurrebbe scelte di portafoglio realistiche e tensioni tra canali.

**Meccaniche di supply chain.** Le promozioni generano picchi di domanda che devono essere anticipati nella pianificazione produttiva e logistica. Lead time, rischio di stockout e costi di safety stock sono vincoli concreti che oggi il simulatore ignora. Integrarli renderebbe le decisioni promozionali dei manufacturer strutturalmente più fedeli alla realtà operativa.

**Shock macroeconomici.** L'inflazione erode il valore reale degli sconti e altera la sensibilità al prezzo dei consumatori. Le disruption dell'offerta cambiano i rapporti di forza tra manufacturer e retailer. Introdurre questi shock permetterebbe di testare la robustezza della conoscenza accumulata dal sistema in presenza di distribution shift — un banco di prova per la qualità del grafo di memoria.

**Loop RL con valutazione statistica delle policy.** Il sistema attuale usa ragionamento LLM senza ottimizzazione formale delle policy. Un loop di reinforcement learning con experience replay consentirebbe di separare la conoscenza strutturale appresa dal comportamento degli agenti, valutare statisticamente l'efficacia delle strategie promozionali, e confrontare policy alternative in modo rigoroso.

---

*Costruito come esplorazione di sistemi genuinamente agentici in contesti enterprise — dove più attori con incentivi concorrenti prendono decisioni sequenziali in condizioni di incertezza, e l'intelligenza si accumula nel tempo.*
