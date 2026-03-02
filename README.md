# Simulazione Multi-Agente del Mercato Snack

Una simulazione genuinamente agentica della gestione delle categorie snack nel mercato GDO italiano.

Cinque agenti LLM negoziano spazio scaffale, promozioni e assortimento in episodi configurabili (default: 4 settimane). Un grafo di memoria condiviso accumula conoscenza tra gli episodi — il sistema impara come sistema, non come somma di agenti isolati.

---

## Perché questo è diverso da un workflow

La maggior parte delle demo "agentiche" sono pipeline glorificate: l'LLM riempie box in una sequenza fissa. Questo sistema è diverso.

**Quattro principi di design rispettati in ogni scelta implementativa:**

1. **Obiettivi, non istruzioni** — I system prompt definiscono chi è ogni agente e cosa vuole. Mai come ottenerlo. Il ragionamento appartiene agli agenti.
2. **Contesto ricco, non prescrittivo** — Gli agenti ricevono stato e memoria. Decidono loro. Nessuna regola hardcodata.
3. **Memoria attiva e verificabile** — Il grafo di memoria persiste tra gli episodi e cambia il comportamento in modo misurabile nel tempo.
4. **Compound Intelligence** — Il sistema impara come sistema. La memoria è condivisa, stratificata e attiva. Ogni interazione deposita conoscenza che tutti gli agenti possono usare.

> *"Ogni agente costruito come soluzione isolata è debito tecnico in attesa di esplodere. Ciò di cui le enterprise hanno davvero bisogno sono piattaforme che contestualizzano e distillano la memoria attraverso ogni interazione. Non agenti che dimenticano. Sistemi che imparano."*

---

## Architettura

```
snack_market_sim/
├── main.py                    # Entry point
├── memory/
│   ├── graph.py               # MarketMemoryGraph — il protagonista
│   └── extractor.py           # Distilla conoscenza dagli episodi nel grafo
├── world/
│   └── engine.py              # Simulatore di mercato (domanda, financials, reward)
├── agents/
│   ├── base.py                # Classe base agenti
│   └── agents.py              # I 5 agenti
├── orchestrator/
│   └── graph.py               # Orchestratore LangGraph
└── requirements.txt
```

### I 5 agenti

| Agente | Ruolo | Obiettivi |
|---|---|---|
| **Manufacturer A** | Brand premium (ChipsPremium, CrackersPremium) | Revenue, margine, ROI promozionale |
| **Manufacturer B** | Brand mass market (ChipsMass x3) | Volume, revenue, margine |
| **Manufacturer C** | Challenger healthy (ProteinBar, RiceCakes Bio) | Penetrazione, allineamento ai trend |
| **Retailer** | Category Manager GDO | Margine per metro lineare, volume, rotazione inventario |
| **Consumer** | Domanda di mercato + segnale di trend | Rappresentazione fedele del comportamento dei consumatori |

### Il grafo di memoria

Il grafo di memoria è il cuore del sistema — non gli agenti.

Due layer:

- **Layer 1 — Conoscenza Strutturale** (decay lento, quasi permanente): Leggi di mercato scoperte attraverso osservazioni ripetute. *"La domanda di snack picca in agosto e a dicembre."*
- **Layer 2 — Conoscenza Tattica** (decay rapido, aggiornamento continuo): Pattern contingenti specifici agli agenti e alle dinamiche di mercato correnti. *"Manufacturer A tende a fare dumping nelle ultime settimane dell'episodio."*

Un'osservazione nasce sempre nel Layer 2. Se confermata con alta confidenza per K episodi, viene **promossa al Layer 1**. Il sistema stesso decide cosa diventa legge e cosa rimane contingente.

### Orchestratore LangGraph

Il ciclo settimanale:

```
Consumer → Manufacturer → Retailer → World Step → Verifica Fine
    ↑_________________________________________________| (se episodio non finito)
```

L'orchestratore coordina ma non decide. Il ragionamento strategico appartiene agli agenti.

---

## Setup

### Requisiti

- Python 3.11+
- [Ollama](https://ollama.ai) installato e in esecuzione
- Un modello compatibile scaricato (vedi sotto)

### Installazione

```bash
git clone https://github.com/mamatteo/snack-market-sim.git
cd snack-market-sim
pip install -r requirements.txt
```

### Modelli supportati

Il sistema è testato con i seguenti modelli Ollama:

| Modello | Dimensione | Note |
|---|---|---|
| `qwen3:8b` | ~5 GB | Raccomandato — qualità e velocità bilanciate |
| `qwen3:14b` | ~9 GB | Qualità superiore, richiede 16GB+ RAM |
| `qwen2.5:latest` | ~5 GB | Alternativa funzionante se qwen3 non disponibile |
| `llama3.2:latest` | ~2 GB | Più veloce, qualità JSON meno affidabile |

```bash
ollama pull qwen3:8b   # o il modello preferito
```

### Esecuzione

```bash
# Singolo episodio (4 settimane, modello default qwen3:8b)
python3 main.py

# Modello alternativo
python3 main.py --model qwen2.5:latest

# 10 episodi consecutivi (la memoria si accumula tra tutti)
python3 main.py --episodes 10

# Episodio specifico
python3 main.py --episode 5

# Parte da un numero di episodio specifico
python3 main.py --episodes 5 --start-from 11
```

> **Nota sulla durata:** ogni settimana richiede 5 chiamate LLM (una per agente). Con modelli locali su hardware consumer, un episodio da 4 settimane dura tipicamente 5–15 minuti. La durata dell'episodio è configurabile in `orchestrator/graph.py` → `node_check_episode_end` (costante `>= 4`).

### Output generati

| File | Contenuto |
|---|---|
| `episode_log.json` | Reward per agente e nuova conoscenza strutturale per ogni episodio |
| `market_memory.json` | Grafo di memoria persistente — nodi, archi, confidenza, layer |

### Cosa osservare

Dopo ogni episodio il sistema stampa nel terminale:
- Reward per agente (scala ~0–2, blend 60% individuale + 40% sistemico)
- Conoscenza strutturale accumulata (leggi Layer 1)
- Nuove promozioni da Layer 2 → Layer 1 in questo episodio

I **reward bassi nei primi episodi sono normali**: i KPI sono normalizzati su base annuale, quindi con poche settimane il numeratore è piccolo.

Dopo 5–10 episodi si inizia a vedere emergere conoscenza strutturale: lift promozionale per SKU, tasso di accettazione del retailer per manufacturer, domanda stagionale. Gli agenti leggono questa memoria ad ogni settimana e adattano le loro decisioni.

---

## Simulazione di mercato

**8 SKU in 3 sottocategorie:**

| SKU | Manufacturer | Sottocategoria | Domanda base/settimana |
|---|---|---|---|
| ChipsPremium 150g | mfr_a | chips | 120 |
| CrackersPremium 200g | mfr_a | crackers | 80 |
| ChipsMass 200g | mfr_b | chips | 200 |
| CrackersMass 250g | mfr_b | crackers | 150 |
| ChipsMass Gusto 150g | mfr_b | chips | 100 |
| ProteinBar 40g | mfr_c | healthy | 60 |
| RiceCakes Bio 100g | mfr_c | healthy | 70 |
| PrivateLabel Chips | retailer | chips | 180 |

**Modello di domanda (moltiplicativo):**
```
unità = domanda_base × stagionalità × trend_consumer × lift_promozionale × dip_post_promo × rumore
```

**Blend del reward (60/40):**
Il reward finale di ogni agente = 60% KPI individuale + 40% media di sistema. Questo impedisce comportamenti puramente avversariali e cattura la dinamica di partnership di lungo periodo tra manufacturer e retailer.

---

## Roadmap

- [ ] Strategy journal persistente con insight degli episodi sintetizzati dall'LLM
- [ ] Protocollo di negoziazione più ricco (multi-round, counter-offer, joint business plan)
- [ ] Topologia multi-retailer
- [ ] Meccaniche di supply chain (lead time, stockout)
- [ ] Shock macroeconomici (inflazione, disruption dell'offerta)
- [ ] Loop RL con experience replay e valutazione statistica delle policy

---

## Stack

- **Python** + **LangGraph** per l'orchestrazione
- **Ollama** + **Qwen3** per l'inferenza LLM locale
- **NetworkX** per il grafo di memoria
- **Pydantic** per gli output strutturati
- **Rich** per la visualizzazione nel terminale

---

*Costruito come esplorazione di sistemi genuinamente agentici in contesti enterprise — dove più attori con incentivi concorrenti prendono decisioni sequenziali in condizioni di incertezza, e l'intelligenza si accumula nel tempo.*
