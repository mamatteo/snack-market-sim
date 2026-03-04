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

Il componente più importante del sistema non è nessun singolo agente — è la struttura di memoria che gli agenti condividono e alimentano nel tempo. Ma "memoria" in questo sistema non è un concetto uniforme: esistono due tipi con orizzonti temporali e funzioni radicalmente diverse.

**Memoria a breve termine — privata, per-episodio.** Ogni agente mantiene una sliding window delle proprie ultime 10 decisioni settimanali (`short_term_memory` in `agent_base_class.py`), azzerata a inizio di ogni nuovo episodio. È la memoria di lavoro dell'agente: "la settimana scorsa ho proposto uno sconto del 20% su ChipsPremium e il retailer ha rifiutato — questa settimana provo diversamente". Privata — gli altri agenti non la vedono. Volatile — non sopravvive all'episodio.

**Memoria a lungo termine — condivisa, cross-episodio.** Il `MarketMemoryGraph` (`memory/system_memory.py`) è un grafo di conoscenza che persiste su disco tra tutti gli episodi. Non contiene log grezzi di eventi, ma pattern distillati: relazioni quantificate tra entità di mercato (SKU, stagioni, manufacturer, categorie), ciascuna con confidenza e conteggio delle evidenze. È il patrimonio cognitivo del sistema — cresce episodio dopo episodio e cambia il comportamento di tutti gli agenti in modo misurabile.

A collegare le due: il `MemoryExtractor` (`memory/agent_memory.py`), che a fine episodio analizza i risultati settimanali e le decisioni degli agenti, e deposita nuove osservazioni nel grafo a lungo termine. È il bridge tra ciò che è successo nell'episodio e la conoscenza che persiste.

### La struttura del grafo a lungo termine

La memoria a lungo termine è organizzata in due layer con dinamiche diverse:

- **Layer 1 — Conoscenza Strutturale:** leggi di mercato confermate nel tempo. Decadono lentamente, quasi permanenti. *Es: "La domanda picca nelle settimane 24–35 (estate) e 48–52 (Natale)."*
- **Layer 2 — Conoscenza Tattica:** pattern contingenti, comportamenti correnti degli agenti. Decadono per episodio se non confermati. *Es: "Manufacturer A tende a fare dumping nelle ultime settimane dell'episodio."*

Ogni osservazione nasce nel Layer 2. Se viene confermata con confidenza ≥ 75% per almeno 5 episodi, viene **promossa automaticamente al Layer 1**. Il sistema decide autonomamente cosa diventa legge di mercato e cosa rimane contingente.

```
Promozione Layer 2 → Layer 1:  evidence_count ≥ 5  AND  confidence ≥ 0.75
```

Nei primi episodi gli agenti operano quasi al buio: la memoria a breve termine cattura solo le ultime mosse, e quella a lungo termine è ancora vuota. Dopo 5–10 episodi iniziano a comparire leggi strutturali: lift promozionale per SKU, stagionalità confermata, pattern comportamentali dei competitor. Gli agenti leggono entrambe le memorie ogni settimana — e le loro decisioni cambiano di conseguenza.

### Memoria privata e memoria condivisa

La memoria a breve termine è privata per design: ogni agente conosce le proprie mosse recenti, non quelle degli altri. La memoria a lungo termine — il grafo — è invece condivisa tra tutti.

Questa scelta non è ovvia. In un contesto competitivo puro, la memoria privata sarebbe naturale anche per il lungo periodo: ogni agente accumula conoscenza proprietaria sulle proprie strategie e sulle reazioni dei competitor, senza condividere nulla che potrebbe essere usato contro di lui. In un contesto cooperativo, invece, la memoria condivisa accelera l'apprendimento collettivo.

Il caso GDO si colloca tra i due estremi. Manufacturer e retailer hanno incentivi parzialmente allineati (entrambi vogliono che la categoria cresca) ma anche contrapposti (la distribuzione del margine è una somma zero). Nella realtà, i pattern di mercato aggregati — stagionalità, lift promozionale per categoria, elasticità al prezzo — sono spesso commercialmente disponibili tramite provider come Nielsen o IRI, accessibili a tutti gli attori. Le strategie individuali, invece, restano proprietarie.

Il grafo condiviso riflette questa distinzione: ciascun agente alimenta la memoria con osservazioni di mercato pubblicamente osservabili, ma le proprie tattiche emergono dal ragionamento individuale e dalla memoria a breve termine privata, non dal grafo. La memoria breve cattura le strategie; il grafo cattura le leggi del mercato.

La scelta di un grafo unico condiviso è consapevolmente semplificativa: in un sistema orientato alla competizione pura, si avrebbe invece un grafo per agente, con osservazioni filtrate per prospettiva. Quella direzione è percorribile nell'architettura attuale e rappresenta un'estensione naturale per simulazioni più adversariali.

---

## Modello di mercato

8 SKU in 3 sottocategorie, con domanda modellata in modo moltiplicativo:

```
unità = domanda_base × stagionalità × trend_consumer × lift_promozionale × dip_post_promo × rumore
```

| SKU | Manufacturer | Sottocategoria | Domanda base/sett. |
|---|---|---|---|
| ChipsPremium 150g | mfr_a | chips | 120 |
| CrackersPremium 200g | mfr_a | crackers | 80 |
| ChipsMass 200g | mfr_b | chips | 200 |
| CrackersMass 250g | mfr_b | crackers | 150 |
| ChipsMass Gusto 150g | mfr_b | chips | 100 |
| ProteinBar 40g | mfr_c | healthy | 60 |
| RiceCakes Bio 100g | mfr_c | healthy | 70 |
| PrivateLabel Chips | retailer | chips | 180 |

La stagionalità riflette i picchi reali della GDO italiana: +25% estate (settimane 24–35), +35% Natale (settimane 48–52), −20% gennaio post-feste. Il reward finale di ogni agente è un blend 60/40 tra KPI individuale e media sistemica — per modellare la dinamica di partnership di lungo periodo tra manufacturer e retailer, impedendo strategie puramente avversariali.

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
