# Agentic Category Management

Trade promotions represent on average 15–25% of revenue for consumer goods manufacturers and are the largest cost item after cost of goods sold. Yet planning still happens largely through bilateral negotiations, Excel spreadsheets, and rules of thumb built up over time.

The problem is structurally complex. Manufacturers and retailers sit at the table with partially aligned objectives — both want the category to grow, but with opposing incentives on margin distribution. The retailer's category manager must balance margin per linear meter, inventory turnover, consumer satisfaction, and the quality of relationships with each supplier. The manufacturer's trade promotion manager must decide which SKU to promote, with what discount, for how many weeks, and with what display fee — knowing that every promotion generates an immediate lift but also a post-promo dip, and that competitors are watching and will react.

Adding to the complexity: information is asymmetric (the manufacturer knows its own costs, the retailer knows basket data), decisions are sequential and interdependent, and relevant knowledge accumulates slowly over time — some dynamics (seasonality) are stable, others (competitor tactics) change continuously.

This system models exactly that dynamic. Five LLM agents — three manufacturers, one retailer, one consumer — negotiate assortment, promotions, and shelf space in a simulated Italian snack market. They follow no script. Each knows its own objectives and decides autonomously how to pursue them, week after week, episode after episode.

---

## Design principles

The term *agentic* is used very broadly. It often describes systems where an LLM executes a predefined sequence of steps, calls APIs in a fixed order, or follows a workflow the programmer has already resolved — leaving the LLM only to fill in the fields. This is a legitimate use of the term in automation contexts, but it does not capture the more interesting dimension of agenticity: the ability of a system to make unprescribed decisions, adapt strategy over time, and generate behaviors the designer did not explicitly program.

A practical test: if you removed the LLM from the system and replaced it with hardcoded rules, would the behavior change substantially? If the answer is no — if the LLM is just formatting output or translating instructions into API calls — then the reasoning is not truly distributed across the agents.

In this system the answer is yes. No agent knows in advance what it will propose next week: it depends on what happened this week, what it observed in previous episodes, how the retailer behaved, and what the memory graph suggests. Behavior emerges from the composition of incentives, context, and reasoning — not from a script.

Four principles make this possible:

| Principle | How it applies |
|---|---|
| **Goals, not instructions** | System prompts define who each agent is and what it wants. Never how to get it. The reasoning belongs to the agents. |
| **Rich, non-prescriptive context** | Every week agents receive market state and shared memory. They decide. No hardcoded rules. |
| **Active, verifiable memory** | A knowledge graph persists across episodes and measurably changes agent behavior. |
| **Systemic intelligence** | The system learns as a system, not as a sum of isolated agents. Every interaction deposits knowledge that all agents can use. |

---

## How it works

Each **episode** is a sequence of simulated weeks. Each week, agents act in order:

```
Consumer → Manufacturers → Retailer → World Step → check episode end
    ↑_________________________________________________________________|
```

The **Consumer** updates demand trends (healthy preference, price sensitivity). **Manufacturers** decide whether to propose promotions to the retailer — which SKU, what discount, what display fee. The **Retailer** evaluates proposals: it can accept, reject, or make a counter-offer. The **World Engine** computes demand, revenue, and margins, and advances by one week.

At the end of each episode, the knowledge accumulated is distilled into the memory graph, ready for subsequent episodes.

### The agents

| Agent | Role | KPIs |
|---|---|---|
| **Manufacturer A** | Premium brand — ChipsPremium, CrackersPremium | Revenue, margin, promotional ROI |
| **Manufacturer B** | Mass market brand — 3 chips and crackers SKUs | Volume, revenue, margin |
| **Manufacturer C** | Healthy challenger — ProteinBar, RiceCakes Bio | Penetration, trend alignment |
| **Retailer** | GDO Category Manager | Margin per linear meter, volume, turnover |
| **Consumer** | Aggregate demand + trend signal | Faithful representation of market behavior |

---

## System calibration

Every market has its own laws. This section maps the typical questions from a requirements gathering to system parameters, to transform the generic simulation into a model faithful to a specific context.

All numerical parameters are centralized in `config.py` (project root), the only file to edit to recalibrate the simulation. Two elements are exceptions for structural reasons and are configured directly in `world/market_simulator.py`: the SKU catalog (`SKUS`) and the seasonality profile (`_build_seasonality()`).

### Market structure

**Questions for the client:** How many brands are in the category? How many SKUs per brand? What is the competitive structure (premium vs mass vs private label vs challenger)? What are the reference volumes for each product?

The SKU catalog is defined in the `SKUS` dictionary in `world/market_simulator.py`. For each SKU:

| Field | Meaning |
|---|---|
| `base_demand` | Reference weekly volume in the absence of perturbations |
| `manufacturer_cost` | Production cost per unit |
| `manufacturer_list_price` | Manufacturer → retailer list price |
| `retailer_list_price` | Consumer price in the absence of promotions |
| `manufacturer_id` | Which agent the SKU belongs to (`mfr_a`, `mfr_b`, `mfr_c`, `retailer`) |
| `subcategory` | `chips` \| `crackers` \| `healthy` — determines the impact of the consumer trend |

The retailer's private label is configurable in the same way: `manufacturer_id = "retailer"` and `manufacturer_list_price` equal to cost (direct margin to consumer).

### Seasonality

**Questions for the client:** When are the sales peaks in this category? What is the magnitude? Are there marked seasonal declines?

Seasonality is defined in `_build_seasonality()` in `world/market_simulator.py`. It produces an array of 52 weekly multipliers and is adapted by modifying the week ranges and coefficients:

```python
def _build_seasonality() -> np.ndarray:
    s = np.ones(52)
    s[23:35] *= 1.25   # summer (weeks 24–35): +25%
    s[47:52] *= 1.35   # christmas (weeks 48–52): +35%
    s[0:2]   *= 1.20   # new year: +20%
    s[2:6]   *= 0.80   # post-holiday january: −20%
    return s
```

For a category with a back-to-school peak and no summer effect, simply modify the ranges and multipliers.

### Promotional mechanics

**Questions for the client:** What is the typical lift from a promotion in this category? Does preferential placement (display, end-cap) generate a measurable increase? How long does the post-promo dip last and with what intensity?

```python
# config.py
PROMO_LIFT_BASE        = 1.8   # base demand lift with active promo (×1.8 = +80%)
DISPLAY_FEE_THRESHOLD  = 400   # display fee threshold (€) above which bonus activates
DISPLAY_FEE_LIFT_BONUS = 0.3   # lift bonus for premium shelf positioning
PROMO_LIFT_CAP         = 3.0   # maximum allowed lift
POST_PROMO_DIP_FACTOR  = 0.20  # post-promotion demand drop (−20%)
POST_PROMO_DIP_WEEKS   = 3     # duration of the post-promo dip in weeks
```

### Consumer behavior

**Questions for the client:** Is the healthy segment growing in your market? How strongly do consumption trends influence purchases? Are consumers price-elastic in this category?

```python
# config.py
HEALTHY_TREND_SENSITIVITY = 0.3   # +1 healthy_preference → +30% demand for healthy products
PRICE_SENSITIVITY_IMPACT  = 0.1   # +1 price_sensitivity  → −10% overall demand
DEMAND_NOISE_SIGMA        = 0.05  # weekly volatility (σ of Gaussian noise)
```

### Financial structure

**Questions for the client:** What is the retailer's typical gross margin on promoted products? How does the display fee work — flat or percentage?

```python
# config.py
RETAILER_MARGIN_ON_PROMO = 0.30  # retailer margin on reduced transfer price (~30% in Italian GDO)
```

Costs and list prices for each SKU are configured directly in `SKUS` (`world/market_simulator.py`).

### KPIs and reward

**Questions for the client:** What measures success for each actor? Revenue, margin, promotional ROI? How much does systemic performance (category) weigh against individual performance? Is there a joint business planning agreement that rewards shared growth?

```python
# config.py — manufacturer reward weights (revenue, margin, promo ROI)
MFR_REWARD_WEIGHT_REVENUE   = 0.40
MFR_REWARD_WEIGHT_MARGIN    = 0.30
MFR_REWARD_WEIGHT_PROMO_ROI = 0.30

# retailer reward weights (category margin, volume, turnover)
RTL_REWARD_WEIGHT_MARGIN = 0.40
RTL_REWARD_WEIGHT_VOLUME = 0.30
RTL_REWARD_WEIGHT_TURNS  = 0.30

# individual/systemic blend in the final reward
SYSTEM_BLEND_RATIO = 0.40  # 0.0 = purely competitive · 1.0 = purely cooperative
```

Normalization thresholds (`MFR_REVENUE_NORM`, `RTL_MARGIN_NORM`, etc.) determine the KPI scale and must be adapted to the real dimensions of the simulated market.

### Learning speed

**Questions for the client:** How many seasons must confirm a pattern before it becomes a "market law"? How quickly should unconfirmed tactical observations decay?

```python
# config.py
MEMORY_PROMOTION_EVIDENCE   = 5     # episodes required for Layer 2 → Layer 1
MEMORY_PROMOTION_CONFIDENCE = 0.75  # minimum confidence for promotion
MEMORY_CONFIRMATION_BOOST   = 0.08  # confidence increment per confirmation
MEMORY_CONTRADICTION_DECAY  = 0.15  # confidence decrement per contradiction
MEMORY_TACTICAL_DECAY       = 0.05  # per-episode decay for unconfirmed tactical edges
```

With default values, the first structural laws appear after 5–10 episodes. Reducing `MEMORY_PROMOTION_EVIDENCE` accelerates learning; increasing `MEMORY_TACTICAL_DECAY` makes the system more reactive to market changes.

### Simulation horizon

**Questions for the client:** How many weeks per scenario? One month, one quarter, one year? What level of LLM quality and speed is acceptable?

```python
# config.py
EPISODE_LENGTH_WEEKS    = 4          # weeks per episode (4 = monthly, 13 = quarterly, 52 = annual)
SHORT_TERM_MEMORY_SIZE  = 10         # sliding window size for short-term memory
SHORT_TERM_CONTEXT_SIZE = 5          # entries included in the agent prompt
DEFAULT_MODEL           = "qwen3:8b" # default LLM model
```

---

## Memory as the core component

The most important component of the system is not any single agent — it is the memory structure that agents share and feed over time. But "memory" is not a uniform concept: there are two types with radically different time horizons, functions, and access logic, and the choice to design them asymmetrically is not arbitrary.

**Short-term memory, private, per-episode.** Each agent maintains a sliding window of its last 10 weekly decisions (`short_term_memory` in `agent_base_class.py`), reset at the start of each new episode. It is working memory: "last week I proposed a 20% discount on ChipsPremium and the retailer refused, this week I'll change tactics." It is private because in a competitive market each agent guards its own moves. A manufacturer does not share with competitors how much it is discounting, nor does the retailer expose its preference function to those negotiating against it. Short-term memory captures strategies, and it is right that it remains opaque to others.

**Long-term memory, shared, cross-episode.** The `MarketMemoryGraph` (`memory/system_memory.py`) is a knowledge graph that persists on disk across all episodes. It does not contain raw event logs, but distilled patterns: quantified relationships between market entities (SKUs, seasons, manufacturers, categories), each with confidence and evidence count accumulated over time. It is the cognitive patrimony of the system, growing episode after episode. Here the choice is the opposite of short-term memory: the graph is shared across all agents. The reason is contextual. In real GDO, aggregate market patterns — seasonality, promotional lift per category, price elasticity — are often commercially available through providers like Nielsen or IRI, accessible to all actors. They are not secrets: they are the background knowledge on which everyone reasons. Individual strategies remain proprietary; market laws do not. The graph models exactly this distinction: each agent deposits publicly observable observations, not its own tactics.

Connecting the two: the `MemoryExtractor` (`memory/agent_memory.py`), which at the end of each episode analyzes weekly results and agent decisions, and deposits new observations into the long-term graph. It is the bridge between what happened in the episode and the knowledge that persists.

### The structure of the long-term graph

Long-term memory is organized in two layers with different dynamics:

- **Layer 1 — Structural Knowledge:** market laws confirmed over time. They decay slowly, nearly permanent. *E.g.: "Demand peaks in weeks 24–35 (summer) and 48–52 (Christmas)."*
- **Layer 2 — Tactical Knowledge:** contingent patterns, current agent behaviors. They decay per episode if not confirmed. *E.g.: "Manufacturer A tends to dump prices in the last weeks of the episode."*

Every observation is born in Layer 2. If confirmed with confidence ≥ 75% for at least 5 episodes, it is **automatically promoted to Layer 1**. The system autonomously decides what becomes a market law and what remains contingent.

```
Promotion Layer 2 → Layer 1:  evidence_count ≥ 5  AND  confidence ≥ 0.75
```

In early episodes agents operate nearly blind: short-term memory captures only recent moves, long-term is still empty. After 5–10 episodes structural laws start to appear: promotional lift per SKU, confirmed seasonality, competitor behavioral patterns. Agents read both memories every week, and their decisions change accordingly. It is this accumulation that transforms a sequence of isolated negotiations into something resembling learning.

The choice of a single shared graph is consciously simplistic: in a system oriented toward pure competition, one would have a graph per agent with observations filtered by perspective. That direction is viable in the current architecture and represents a natural extension for more adversarial simulations.

---

## Market model

Market behavior is modeled by the `MarketSimulator` class (`world/market_simulator.py`), which manages 8 SKUs across 3 subcategories (chips, crackers, healthy) and computes, week by week, demand, revenue, and margins for each actor. It is the reality layer on which agents exercise their decisions, and the source of the data that the `MemoryExtractor` distills into the long-term graph.

### Multiplicative demand

The demand for each SKU in each week is the product of six independent factors:

```
units = base_demand × seasonality × consumer_trend × promo_lift × post_promo_dip × noise
```

**Base demand** — expected sales under neutral conditions, specific to each SKU. Reflects positioning: mass market (ChipsMass) starts at 200 units/week, premium (ChipsPremium) at 120, healthy products at 60–70. The retailer's private label sits at 180.

**Seasonality** — an array of 52 weekly multipliers, built once in `_build_seasonality()` and applied deterministically to all SKUs. Reflects real Italian GDO peaks: +25% summer (weeks 24–35), +35% Christmas (weeks 48–52), +20% year-end, −20% in weeks 3–6 (post-holiday decline). Seasonality is the same for all SKUs — it is the calendar structure, not a product characteristic.

**Consumer trend** — two continuous parameters in [-1.0, +1.0] updated each week by the Consumer agent: `healthy_preference` and `price_sensitivity`. Healthy preference amplifies or dampens demand for healthy subcategory SKUs (up to ±30%). Price sensitivity reduces overall demand when high (up to −10%), modeling the phenomenon where price-conscious consumers delay purchases in the absence of promotions.

**Promotional lift** — when a promotion is active, demand rises. Base lift is ×1.8, increased proportionally to the applied discount. If the manufacturer has paid a display fee above €400, an additional +0.3× is added for premium shelf positioning. Lift is capped at ×3.0 to avoid unrealistic effects. With a 25% discount and €500 display fee, the typical lift is around ×2.3.

**Post-promo dip** — the demand contraction in the 3 weeks following the end of a promotion (−20%). Models the real pantry-loading phenomenon: consumers stocked up during the promo and buy less in subsequent days. The simulator automatically tracks SKUs in dip state via `post_promo_dip_tracker`, without agents needing to manage it explicitly.

**Noise** — Gaussian perturbation (μ=1.0, σ=0.05) that introduces realistic variability. Prevents the system from converging on identical deterministic patterns and makes each episode distinct.

### Price and margin structure

Each SKU has three prices: production cost, manufacturer→retailer list price, and base consumer price. When a promotion is active, the transfer price is reduced by the agreed discount percentage. The retailer calculates its consumer price maintaining a margin of ~30% on the reduced transfer price. The display fee acts as a direct transfer: the manufacturer pays it, the retailer receives it, regardless of volume sold.

| SKU | Mfr | Subcategory | Base demand | Prod. cost | MFR→RTL price | Consumer price |
|---|---|---|---|---|---|---|
| ChipsPremium 150g | mfr_a | chips | 120 | €0.80 | €1.50 | €2.20 |
| CrackersPremium 200g | mfr_a | crackers | 80 | €0.60 | €1.20 | €1.80 |
| ChipsMass 200g | mfr_b | chips | 200 | €0.50 | €0.90 | €1.50 |
| CrackersMass 250g | mfr_b | crackers | 150 | €0.45 | €0.85 | €1.40 |
| ChipsMass Gusto 150g | mfr_b | chips | 100 | €0.55 | €1.00 | €1.60 |
| ProteinBar 40g | mfr_c | healthy | 60 | €1.20 | €2.50 | €3.80 |
| RiceCakes Bio 100g | mfr_c | healthy | 70 | €0.90 | €1.80 | €2.90 |
| PrivateLabel Chips | retailer | chips | 180 | €0.40 | — | €1.20 |

The private label is always listed and not subject to negotiation. Its production cost equals the transfer price (the retailer produces and distributes directly), so the margin is entirely the difference between consumer price and cost. It is not an agent but a benchmark of perennial competitive pressure on the chips subcategory — its presence forces manufacturers to justify the price differential with perceived quality or promotions.

### Reward and incentives

At the end of each episode, `compute_rewards()` calculates the reward for each agent from the accumulated KPIs. For manufacturers: a combination of normalized revenue (40%), normalized margin (30%), and promotional ROI (30%). For the retailer: category margin (40%), total volume (30%), inventory turnover (30%).

The final reward is a **60% individual / 40% systemic blend**: the individual KPI is mixed with the average reward of all agents. This choice models the partnership dynamic typical of GDO, where manufacturers and retailers have an interest in the health of the entire category, not just their own share — and prevents the system from converging on purely adversarial strategies where one agent maximizes by eroding value from others.

---

## Output

| File | Content |
|---|---|
| `results.json` | Reward per agent and new structural knowledge for each episode |
| `output_data/knowledge_graph.json` | Persistent memory graph — nodes, edges, confidence, layer |

At the end of each episode, the system prints to the terminal the rewards per agent (scale ~0–2, 60% individual + 40% systemic blend), the accumulated structural knowledge, and the Layer 2 → Layer 1 promotions that occurred in that episode.

> Low rewards in early episodes are normal: KPIs are normalized on an annual basis, so with few weeks the numerator is small. Behavior becomes meaningful after 5–10 episodes.

---

## Sample Results

After 10 episodes (40 simulated weeks), a typical run produces the following outputs.

### Terminal output — end of episode

```
Episode 10 complete — Week 40
──────────────────────────────────────────────────────────
Agent              Individual    Systemic     Final
──────────────────────────────────────────────────────────
Manufacturer A        1.42         1.21        1.33
Manufacturer B        0.91         1.21        1.03
Manufacturer C        1.58         1.21        1.43
Retailer              1.26         1.21        1.24
──────────────────────────────────────────────────────────

Layer 2 → Layer 1 promotions this episode:
  • ChipsPremium :: summer_demand_lift      confidence=0.81  evidence=6
  • mfr_a :: end_of_episode_discount_push  confidence=0.77  evidence=5
```

Rewards are read as normalized performance across the episode: 1.0 represents a neutral result aligned with normalization thresholds; values above 1.0 indicate above-average performance. Manufacturer C consistently outperforms from episode 5 onward due to the compounding healthy trend. Manufacturer B's lower individual score reflects volume-driven margins under pressure from the private label.

### Knowledge graph — after 10 episodes

```json
{
  "nodes": [
    "ChipsPremium", "ChipsMass", "ProteinBar", "RiceCakes Bio",
    "summer", "christmas", "mfr_a", "mfr_b", "mfr_c"
  ],
  "edges": [
    {
      "source": "ChipsPremium", "target": "summer",
      "relation": "demand_lift", "value": 1.27,
      "confidence": 0.81, "layer": 1, "evidence_count": 6
    },
    {
      "source": "mfr_a", "target": "ChipsPremium",
      "relation": "promo_roi", "value": 2.31,
      "confidence": 0.79, "layer": 1, "evidence_count": 5
    },
    {
      "source": "ProteinBar", "target": "healthy_trend",
      "relation": "demand_sensitivity", "value": 0.34,
      "confidence": 0.68, "layer": 2, "evidence_count": 3
    },
    {
      "source": "mfr_b", "target": "ChipsMass",
      "relation": "avg_discount_rate", "value": 0.21,
      "confidence": 0.72, "layer": 2, "evidence_count": 4
    }
  ]
}
```

Layer 1 edges (e.g. summer demand lift for ChipsPremium, confirmed promotional ROI for Manufacturer A) represent market laws that agents treat as reliable background knowledge. Layer 2 edges (e.g. Manufacturer B's discount tendency) are still contingent — they influence agent reasoning but can be contradicted and will decay if not reconfirmed.

### How rewards evolve across episodes

```
Episode  |  mfr_a  |  mfr_b  |  mfr_c  | retailer
---------+---------+---------+---------+---------
    1    |   0.41  |   0.38  |   0.44  |   0.52
    2    |   0.58  |   0.51  |   0.63  |   0.67
    3    |   0.74  |   0.62  |   0.81  |   0.79
    5    |   1.02  |   0.85  |   1.14  |   1.03
    8    |   1.28  |   0.96  |   1.38  |   1.19
   10    |   1.33  |   1.03  |   1.43  |   1.24
```

The ramp-up from episodes 1–3 reflects KPI normalization: with only 4 weeks of activity, absolute values are low. The inflection around episode 5 corresponds to the first structural knowledge appearing in Layer 1 — agents begin incorporating confirmed market laws into their decisions, making proposals more targeted and acceptance rates higher.

---

## Project structure

```
main.py
src/
├── agents/
│   ├── agent_base_class.py  # Base class: LLM call + JSON parsing + private short-term memory
│   └── agents.py            # The 5 agents
├── memory/
│   ├── system_memory.py     # MarketMemoryGraph — shared long-term memory (Layer 1/Layer 2 graph)
│   └── agent_memory.py      # MemoryExtractor — bridge between short-term and long-term memory
├── orchestrator/
│   └── graph.py             # LangGraph orchestrator — weekly cycle
└── world/
    └── market_simulator.py  # Simulator: demand, financials, rewards
```

---

## Setup

**Requirements:** Python 3.11+, [Ollama](https://ollama.ai) installed and running.

```bash
git clone https://github.com/mamatteo/agentic_category_management.git
cd agentic_category_management
pip install -r requirements.txt
ollama pull qwen3:8b
```

### Supported models

| Model | Size | Notes |
|---|---|---|
| `qwen3:8b` | ~5 GB | Recommended — balanced quality and speed |
| `qwen3:14b` | ~9 GB | Higher quality, requires ≥ 16 GB RAM |
| `qwen2.5:latest` | ~5 GB | Stable alternative |
| `llama3.2:latest` | ~2 GB | Faster, less reliable JSON parsing |

---

## Usage

```bash
# Single episode
python main.py

# N consecutive episodes — memory accumulates across all of them
python main.py --episodes 10

# Specific episode
python main.py --episode 5

# Alternative model
python main.py --model qwen2.5:latest

# Resume from a specific episode
python main.py --episodes 5 --start-from 11
```

Each week requires 5 LLM calls. With local models on consumer hardware, a 4-week episode typically takes 5–15 minutes. Episode duration is configurable in `orchestrator/graph.py` → `node_check_episode_end`.

---

## Stack

| Component | Technology |
|---|---|
| Agent orchestration | [LangGraph](https://github.com/langchain-ai/langgraph) |
| LLM inference | [Ollama](https://ollama.ai) + Qwen3 (local, no API key required) |
| Memory graph | [NetworkX](https://networkx.org) |
| Structured data | [Pydantic v2](https://docs.pydantic.dev) |
| Terminal output | [Rich](https://github.com/Textualize/rich) |

---

## Possible extensions

**Per-agent strategy journal.** Currently each agent maintains a history of its own weekly decisions but does not synthesize long-term insights. A persistent journal, fed by the LLM at the end of each episode, would allow each agent to reason about multi-episode patterns: *"in the last 5 summer seasons, promotions on ChipsPremium generated above-average ROI."* It would transform memory from a log into genuine strategic intelligence.

**Multi-round negotiation.** The current protocol provides a single proposal–response cycle per week. Real GDO negotiation is far more articulated: annual joint business plans, framework agreements across multiple SKUs, renegotiation of conditions when volume targets are reached. Extending the protocol to multiple rounds would expose negotiating power dynamics that the current model does not capture.

**Multi-retailer topology.** With a single retailer, manufacturers do not face the real problem of allocating promotional budget across different chains. Adding multiple retailers in competition — with distinct consumer profiles and category policies — would introduce realistic portfolio choices and inter-channel tensions.

**Supply chain mechanics.** Promotions generate demand spikes that must be anticipated in production and logistics planning. Lead times, stockout risk, and safety stock costs are concrete constraints the simulator currently ignores. Integrating them would make manufacturer promotional decisions structurally more faithful to operational reality.

**Macroeconomic shocks.** Inflation erodes the real value of discounts and alters consumer price sensitivity. Supply disruptions shift the balance of power between manufacturers and retailers. Introducing these shocks would allow testing the robustness of the system's accumulated knowledge under distribution shift — a benchmark for the quality of the memory graph.

**RL loop with statistical policy evaluation.** The current system uses LLM reasoning without formal policy optimization. A reinforcement learning loop with experience replay would allow separating the learned structural knowledge from agent behavior, statistically evaluating the effectiveness of promotional strategies, and rigorously comparing alternative policies.

---

*Built as an exploration of genuinely agentic systems in enterprise contexts, where multiple actors with competing incentives make sequential decisions under uncertainty — and intelligence accumulates over time.*
