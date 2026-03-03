# Agentic Category Management

La gestione delle categorie in GDO è un problema di negoziazione multi-stakeholder: i manufacturer vogliono spazio a scaffale e promozioni redditizie, il retailer vuole margine per metro lineare, i consumatori spingono la domanda attraverso trend che cambiano nel tempo. Le decisioni sono sequenziali, gli incentivi sono disallineati, e la conoscenza si accumula episodio dopo episodio.

Questo sistema modella esattamente quella dinamica. Cinque agenti LLM — tre manufacturer, un retailer, un consumer — negoziano assortimento, promozioni e spazio scaffale su un mercato snack italiano simulato. Non seguono script. Ognuno conosce i propri obiettivi e decide autonomamente come perseguirli, settimana dopo settimana.

---

## Principi di design

La maggior parte dei sistemi multi-agente in letteratura e in produzione delegano all'LLM l'esecuzione di step predefiniti in sequenza fissa. Il ragionamento è apparente: gli agenti non negoziano, non apprendono, non adattano la strategia nel tempo.

Questo sistema è costruito su quattro principi che cercano di colmare quel gap:

| Principio | Come si applica |
|---|---|
| **Obiettivi, non istruzioni** | I system prompt definiscono chi è ogni agente e cosa vuole. Mai come ottenerlo. Il ragionamento appartiene agli agenti. |
| **Contesto ricco, non prescrittivo** | Ogni settimana gli agenti ricevono lo stato del mercato e la memoria condivisa. Decidono loro. Nessuna regola hardcodata. |
| **Memoria attiva e verificabile** | Un grafo di conoscenza persiste tra gli episodi e cambia il comportamento degli agenti in modo misurabile. |
| **Compound Intelligence** | Il sistema impara come sistema, non come somma di agenti isolati. Ogni interazione deposita conoscenza che tutti gli agenti possono usare. |

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

Il componente più importante del sistema non è nessun singolo agente — è il grafo di memoria condiviso.

La conoscenza è organizzata in due layer con dinamiche diverse:

- **Layer 1 — Conoscenza Strutturale:** leggi di mercato confermate nel tempo. Decadono lentamente, quasi permanenti. *Es: "La domanda picca nelle settimane 24–35 (estate) e 48–52 (Natale)."*
- **Layer 2 — Conoscenza Tattica:** pattern contingenti, comportamenti correnti degli agenti. Decadono per episodio se non confermati. *Es: "Manufacturer A tende a fare dumping nelle ultime settimane dell'episodio."*

Ogni osservazione nasce nel Layer 2. Se viene confermata con confidenza ≥ 75% per almeno 5 episodi, viene **promossa automaticamente al Layer 1**. Il sistema decide autonomamente cosa diventa legge di mercato e cosa rimane contingente.

```
Promozione Layer 2 → Layer 1:  evidence_count ≥ 5  AND  confidence ≥ 0.75
```

Questo significa che nei primi episodi gli agenti operano quasi al buio. Dopo 5–10 episodi iniziano a comparire leggi strutturali: lift promozionale per SKU, stagionalità confermata, pattern comportamentali dei competitor. Gli agenti leggono questa memoria ogni settimana — e le loro decisioni cambiano di conseguenza.

### Memoria individuale e memoria sistemica

Nei sistemi multi-agente esiste una tensione di design fondamentale: la memoria deve essere privata a ciascun agente, o condivisa tra tutti?

In un contesto competitivo puro — dove gli agenti si contendono risorse con incentivi contrapposti — la memoria privata è la scelta naturale: ogni agente accumula conoscenza proprietaria sulle proprie strategie, sulle reazioni dei competitor, sui propri KPI. Nessuno condivide informazioni che potrebbero essere usate contro di lui.

In un contesto cooperativo, invece, la memoria condivisa accelera l'apprendimento collettivo: tutti gli agenti convergono più rapidamente su rappresentazioni accurate del mercato perché ogni osservazione beneficia l'intero sistema.

Il caso d'uso GDO si colloca tra i due estremi. Manufacturer e retailer hanno incentivi parzialmente allineati (entrambi vogliono che la categoria cresca) ma anche interessi contrapposti (la distribuzione del margine è una somma zero). Nella realtà, i pattern di mercato aggregati — stagionalità, lift promozionale per categoria, elasticità al prezzo — sono spesso commercialmente disponibili tramite provider come Nielsen o IRI, accessibili a tutti gli attori. Le strategie individuali, invece, restano proprietarie.

Questo sistema riflette quella distinzione con due livelli di memoria separati:

- **Memoria individuale** (`agents/agent.py`): ogni agente mantiene uno storico privato delle proprie decisioni settimanali — azioni proposte, risposte ricevute, pattern osservati. Questo storico non è visibile agli altri agenti, modellando la conoscenza proprietaria di ciascun player.
- **Memoria sistemica** (`memory/shared_memory.py`): il grafo di mercato è condiviso tra tutti gli agenti e contiene conoscenza osservabile pubblicamente — pattern di domanda, effetti promozionali, tendenze di categoria. Ogni agente legge e alimenta lo stesso grafo.

La scelta di rendere il grafo condiviso è consapevolmente semplificativa: in un sistema orientato alla competizione pura, si avrebbe invece un grafo per agente, con osservazioni filtrate per prospettiva. Quella direzione è percorribile nell'architettura attuale e rappresenta un'estensione naturale per simulazioni più adversariali.

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
| `episode_log.json` | Reward per agente e nuova conoscenza strutturale per ogni episodio |
| `market_memory.json` | Grafo di memoria persistente — nodi, archi, confidenza, layer |

A fine episodio il sistema stampa nel terminale i reward per agente (scala ~0–2, blend 60% individuale + 40% sistemico), la conoscenza strutturale accumulata, e le promozioni Layer 2 → Layer 1 avvenute in quell'episodio.

> I reward bassi nei primi episodi sono normali: i KPI sono normalizzati su base annuale, con poche settimane il numeratore è piccolo. Il comportamento diventa significativo dopo 5–10 episodi.

---

## Struttura del progetto

```
agentic_category_management/
├── main.py
├── agents/
│   ├── agent.py         # Classe base: chiamata LLM + parsing JSON + history privata
│   └── agents.py        # I 5 agenti
├── memory/
│   ├── shared_memory.py # MarketMemoryGraph — grafo di conoscenza condiviso
│   └── extractor.py     # Distilla conoscenza dagli episodi nel grafo
├── orchestrator/
│   └── graph.py         # Orchestratore LangGraph — ciclo settimanale
└── world/
    └── engine.py        # Simulatore: domanda, financials, reward
```

---

## Setup

**Requisiti:** Python 3.11+, [Ollama](https://ollama.ai) installato e in esecuzione.

```bash
git clone https://github.com/mamatteo/snack-market-sim.git
cd snack-market-sim
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

## Roadmap

- [ ] Strategy journal persistente — insight degli episodi sintetizzati dall'LLM e consultabili dagli agenti
- [ ] Protocollo di negoziazione multi-round — counter-offer, joint business plan, termini contrattuali
- [ ] Topologia multi-retailer — competizione tra catene GDO
- [ ] Meccaniche di supply chain — lead time, stockout, penali
- [ ] Shock macroeconomici — inflazione, disruption dell'offerta, variazioni di costo
- [ ] Loop RL con experience replay e valutazione statistica delle policy

---

*Costruito come esplorazione di sistemi genuinamente agentici in contesti enterprise — dove più attori con incentivi concorrenti prendono decisioni sequenziali in condizioni di incertezza, e l'intelligenza si accumula nel tempo.*
