"""
Orchestratore LangGraph — coordina i 5 agenti.

Non è un workflow fisso. L'orchestratore:
- Gestisce il ciclo settimanale
- Decide l'ordine di esecuzione basandosi sullo stato
- Raccoglie decisioni e le passa al world engine
- Distilla conoscenza nella memoria condivisa a fine episodio

Principio 3: memoria attiva e verificabile
Principio 4: compound intelligence — la memoria cresce episodio dopo episodio
"""

import json
import os
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from config import EPISODE_LENGTH_WEEKS

from src.agents.agents import (
    ManufacturerAgentA,
    ManufacturerAgentB,
    ManufacturerAgentC,
    RetailerAgent,
    ConsumerAgent,
)
from src.world.market_simulator import MarketSimulator, PromotionProposal
from src.memory.system_memory import MarketMemoryGraph
from src.memory.agent_memory import MemoryExtractor

console = Console()

MEMORY_PATH = "output_data/knowledge_graph.json"
EPISODE_LOG_PATH = "results.json"

os.makedirs("output_data", exist_ok=True)


# ============================================================================
# State — stato condiviso del grafo LangGraph
# ============================================================================

class SimState(TypedDict):
    week: int
    episode: int
    world_state: str
    memory_context: str
    consumer_decision: dict
    manufacturer_proposals: list[dict]
    retailer_decisions: dict
    weekly_results: list[dict]
    episode_results: list[dict]
    agent_decisions_log: list[dict]
    done: bool


# ============================================================================
# Nodi del grafo
# ============================================================================

def node_consumer(state: SimState, consumer: ConsumerAgent, world: MarketSimulator, memory: MarketMemoryGraph) -> SimState:
    """Il consumer agent aggiorna i trend di mercato."""
    world_state = world.get_state_summary()
    memory_context = memory.get_context_for_agent("consumer")

    decision = consumer.decide(world_state, memory_context, state["week"])

    # Aggiorna il world engine con i trend consumer
    world.update_consumer_trend(
        healthy_preference=decision.get("healthy_preference", 0.0),
        price_sensitivity=decision.get("price_sensitivity", 0.0),
        description=decision.get("description", ""),
    )

    console.print(f"  [cyan]Consumer[/cyan]: {decision.get('description', '')} "
                  f"(healthy: {decision.get('healthy_preference', 0):+.2f})")

    return {
        **state,
        "consumer_decision": decision,
        "world_state": world_state,
        "memory_context": memory_context,
    }


def node_manufacturers(state: SimState, mfr_a: ManufacturerAgentA, mfr_b: ManufacturerAgentB,
                       mfr_c: ManufacturerAgentC, world: MarketSimulator, memory: MarketMemoryGraph) -> SimState:
    """I tre manufacturer decidono se proporre promozioni."""
    world_state = state["world_state"]
    memory_context = memory.get_context_for_agent("manufacturers")
    week = state["week"]

    proposals = []
    log_entries = []

    for agent, agent_id in [(mfr_a, "mfr_a"), (mfr_b, "mfr_b"), (mfr_c, "mfr_c")]:
        decision = agent.decide(world_state, memory_context, week)

        if decision.get("action") == "propose" and decision.get("sku_id"):
            proposal = {
                "manufacturer_id": agent_id,
                "sku_id": decision["sku_id"],
                "discount_pct": decision.get("discount_pct", 20),
                "duration_weeks": decision.get("duration_weeks", 2),
                "display_fee": decision.get("display_fee", 300),
                "week_proposed": week,
            }
            proposals.append(proposal)
            console.print(f"  [yellow]{agent_id}[/yellow]: propone {decision['sku_id']} "
                          f"-{decision.get('discount_pct')}% fee={decision.get('display_fee')}€")
            log_entries.append({"type": "proposal", **proposal})
        else:
            console.print(f"  [yellow]{agent_id}[/yellow]: hold — {decision.get('reasoning', '')[:60]}")
            log_entries.append({"type": "hold", "manufacturer_id": agent_id, "week": week})

    return {
        **state,
        "manufacturer_proposals": proposals,
        "agent_decisions_log": state.get("agent_decisions_log", []) + log_entries,
    }


def node_retailer(state: SimState, retailer: RetailerAgent, world: MarketSimulator, memory: MarketMemoryGraph) -> SimState:
    """Il retailer valuta le proposte e decide."""
    world_state = state["world_state"]
    memory_context = memory.get_context_for_agent("retailer")
    week = state["week"]
    proposals = state["manufacturer_proposals"]

    decision = retailer.decide(world_state, memory_context, week, proposals)

    log_entries = []
    for d in decision.get("decisions", []):
        action = d.get("decision")
        mfr_id = d.get("manufacturer_id")
        sku_id = d.get("sku_id")

        console.print(f"  [green]Retailer[/green]: {action} → {sku_id} ({mfr_id})")

        # Trova la proposta corrispondente
        matching_proposal = next(
            (p for p in proposals if p["manufacturer_id"] == mfr_id and p["sku_id"] == sku_id),
            None
        )

        if matching_proposal and action == "accept":
            promo = PromotionProposal(
                manufacturer_id=mfr_id,
                sku_id=sku_id,
                discount_pct=matching_proposal["discount_pct"],
                duration_weeks=matching_proposal["duration_weeks"],
                display_fee=matching_proposal["display_fee"],
                week_proposed=week,
            )
            world.apply_promotion(promo)

        elif matching_proposal and action == "counter":
            # Counter-offer: applica con i parametri modificati
            promo = PromotionProposal(
                manufacturer_id=mfr_id,
                sku_id=sku_id,
                discount_pct=d.get("counter_discount_pct", matching_proposal["discount_pct"]),
                duration_weeks=matching_proposal["duration_weeks"],
                display_fee=d.get("counter_display_fee", matching_proposal["display_fee"]),
                week_proposed=week,
            )
            world.apply_promotion(promo)
            console.print(f"    [green]Counter-offer accettato[/green]: -"
                          f"{promo.discount_pct}% fee={promo.display_fee}€")

        log_entries.append({"type": "response", **d, "week": week})

    # Gestione assortimento (delist/list)
    assortment_action = decision.get("assortment_action")
    if assortment_action:
        sku_id = assortment_action.get("sku_id")
        action = assortment_action.get("action")
        if sku_id in world.skus:
            world.skus[sku_id].is_listed = (action == "list")
            console.print(f"  [green]Retailer[/green]: {action} SKU {sku_id}")

    return {
        **state,
        "retailer_decisions": decision,
        "agent_decisions_log": state.get("agent_decisions_log", []) + log_entries,
    }


def node_world_step(state: SimState, world: MarketSimulator) -> SimState:
    """Avanza il world engine di una settimana e calcola i risultati."""
    results = world.step()

    results_dicts = [
        {
            "week": r.week,
            "sku_id": r.sku_id,
            "units_sold": r.units_sold,
            "manufacturer_revenue": r.manufacturer_revenue,
            "manufacturer_margin": r.manufacturer_margin,
            "retailer_revenue": r.retailer_revenue,
            "retailer_margin": r.retailer_margin,
            "was_promoted": r.was_promoted,
            "promotion_lift": r.promotion_lift,
        }
        for r in results
    ]

    total_mfr_margin = sum(r.manufacturer_margin for r in results)
    total_ret_margin = sum(r.retailer_margin for r in results)
    total_units = sum(r.units_sold for r in results)

    console.print(f"  [dim]World step W{state['week']}: "
                  f"{total_units:.0f} unità | MFR margin €{total_mfr_margin:.0f} | "
                  f"RTL margin €{total_ret_margin:.0f}[/dim]")

    return {
        **state,
        "weekly_results": results_dicts,
        "episode_results": state.get("episode_results", []) + results_dicts,
        "week": state["week"] + 1,
    }


def node_check_episode_end(state: SimState) -> SimState:
    """Controlla se l'episodio è finito (durata configurabile in config.py → EPISODE_LENGTH_WEEKS)."""
    done = state["week"] >= EPISODE_LENGTH_WEEKS
    return {**state, "done": done}


def node_end_episode(state: SimState, world: MarketSimulator, memory: MarketMemoryGraph,
                     extractor: MemoryExtractor, episode: int) -> SimState:
    """Fine episodio: distilla conoscenza, salva memoria, stampa report."""
    from src.world.market_simulator import WeeklyResult

    episode_results_raw = state.get("episode_results", [])
    episode_results = [
        WeeklyResult(
            week=r["week"],
            sku_id=r["sku_id"],
            units_sold=r["units_sold"],
            manufacturer_revenue=r["manufacturer_revenue"],
            manufacturer_margin=r["manufacturer_margin"],
            retailer_revenue=r["retailer_revenue"],
            retailer_margin=r["retailer_margin"],
            was_promoted=r["was_promoted"],
            promotion_lift=r["promotion_lift"],
        )
        for r in episode_results_raw
    ]

    # Distilla conoscenza nel grafo
    extractor.extract_from_episode(
        episode=episode,
        results=episode_results,
        agent_decisions=state.get("agent_decisions_log", []),
    )

    # Salva memoria su disco
    memory.save(MEMORY_PATH)

    # Calcola reward
    rewards = world.compute_rewards(episode_results)

    # Report episodio
    _print_episode_report(episode, rewards, memory, episode_results)

    # Log episodio
    _save_episode_log(episode, rewards, memory.promotion_log())

    return {**state, "done": True}


# ============================================================================
# Report e logging
# ============================================================================

def _print_episode_report(episode: int, rewards: dict, memory: MarketMemoryGraph, results):
    console.rule(f"[bold]FINE EPISODIO {episode}[/bold]")

    table = Table(title="Reward per Agente")
    table.add_column("Agente", style="cyan")
    table.add_column("Reward", style="green")
    for agent_id, reward in rewards.items():
        table.add_row(agent_id, f"{reward:.3f}")
    console.print(table)

    structural = memory.get_structural_knowledge()
    if structural:
        console.print(f"\n[bold]📚 Conoscenza Strutturale accumulata ({len(structural)} leggi):[/bold]")
        for edge in structural[:5]:
            src = memory.nodes.get(edge.source_id)
            tgt = memory.nodes.get(edge.target_id)
            console.print(f"  • {edge.description} (confidenza: {edge.confidence:.0%})")

    promotions = memory.promotion_log()
    if promotions:
        new_promotions = [p for p in promotions if p["episode"] == episode]
        if new_promotions:
            console.print(f"\n[bold yellow]⬆️  Nuove promozioni a Layer 1 questo episodio:[/bold yellow]")
            for p in new_promotions:
                console.print(f"  • {p['description']}")


def _save_episode_log(episode: int, rewards: dict, promotion_log: list):
    log = []
    if os.path.exists(EPISODE_LOG_PATH):
        with open(EPISODE_LOG_PATH) as f:
            log = json.load(f)

    log.append({
        "episode": episode,
        "rewards": rewards,
        "new_structural_knowledge": [p for p in promotion_log if p["episode"] == episode],
    })

    with open(EPISODE_LOG_PATH, "w") as f:
        json.dump(log, f, indent=2)


# ============================================================================
# Costruzione del grafo LangGraph
# ============================================================================

def build_graph(world: MarketSimulator, memory: MarketMemoryGraph, episode: int, model: str = "qwen3:8b"):
    mfr_a = ManufacturerAgentA(model)
    mfr_b = ManufacturerAgentB(model)
    mfr_c = ManufacturerAgentC(model)
    retailer = RetailerAgent(model)
    consumer = ConsumerAgent(model)
    extractor = MemoryExtractor(memory, world)

    builder = StateGraph(SimState)

    # Nodi
    builder.add_node("consumer", lambda s: node_consumer(s, consumer, world, memory))
    builder.add_node("manufacturers", lambda s: node_manufacturers(s, mfr_a, mfr_b, mfr_c, world, memory))
    builder.add_node("retailer", lambda s: node_retailer(s, retailer, world, memory))
    builder.add_node("world_step", lambda s: node_world_step(s, world))
    builder.add_node("check_end", node_check_episode_end)
    builder.add_node("end_episode", lambda s: node_end_episode(s, world, memory, extractor, episode))

    # Edges
    builder.set_entry_point("consumer")
    builder.add_edge("consumer", "manufacturers")
    builder.add_edge("manufacturers", "retailer")
    builder.add_edge("retailer", "world_step")
    builder.add_edge("world_step", "check_end")

    # Edge condizionale: fine episodio o prossima settimana?
    builder.add_conditional_edges(
        "check_end",
        lambda s: "end_episode" if s["done"] else "consumer",
        {"end_episode": "end_episode", "consumer": "consumer"},
    )

    builder.add_edge("end_episode", END)

    return builder.compile()


# ============================================================================
# Runner principale
# ============================================================================

def run_episode(episode: int, model: str = "qwen3:8b"):
    console.rule(f"[bold blue]EPISODIO {episode}[/bold blue]")

    # Carica o crea la memoria persistente
    if os.path.exists(MEMORY_PATH):
        memory = MarketMemoryGraph.load(MEMORY_PATH)
        console.print(f"[green]Memoria caricata:[/green] "
                      f"{len(memory.edges)} archi, "
                      f"{len(memory.get_structural_knowledge())} leggi strutturali")
    else:
        memory = MarketMemoryGraph()
        console.print("[yellow]Nuova memoria inizializzata[/yellow]")

    world = MarketSimulator(seed=episode * 42)

    graph = build_graph(world, memory, episode, model)

    initial_state: SimState = {
        "week": 0,
        "episode": episode,
        "world_state": "",
        "memory_context": "",
        "consumer_decision": {},
        "manufacturer_proposals": [],
        "retailer_decisions": {},
        "weekly_results": [],
        "episode_results": [],
        "agent_decisions_log": [],
        "done": False,
    }

    final_state = graph.invoke(initial_state, config={"recursion_limit": 500})
    return final_state


if __name__ == "__main__":
    import sys
    episode = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    model = sys.argv[2] if len(sys.argv) > 2 else "qwen3:8b"
    run_episode(episode, model)
