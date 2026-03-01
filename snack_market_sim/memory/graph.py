"""
Memory Graph — il protagonista del sistema.

Due layer:
- Layer 1: Conoscenza Strutturale (decay lento, leggi del mercato)
- Layer 2: Conoscenza Tattica (decay rapido, pattern contingenti)

Un'osservazione nasce sempre nel Layer 2.
Se confermata per K episodi con alta confidenza → promossa a Layer 1.
"""

import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import networkx as nx


class MemoryLayer(str, Enum):
    STRUCTURAL = "structural"   # Layer 1 — leggi del mercato
    TACTICAL = "tactical"       # Layer 2 — pattern contingenti


class NodeType(str, Enum):
    SKU = "sku"
    MANUFACTURER = "manufacturer"
    RETAILER = "retailer"
    CONSUMER_TREND = "consumer_trend"
    SEASON = "season"
    CATEGORY = "category"
    OBSERVATION = "observation"


class MemoryNode(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    node_type: NodeType
    label: str
    attributes: dict = Field(default_factory=dict)


class MemoryEdge(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    source_id: str
    target_id: str
    relation: str                          # es. "lift_in", "competes_with", "trend_impacts"
    layer: MemoryLayer = MemoryLayer.TACTICAL
    confidence: float = 0.5                # 0.0 → 1.0
    evidence_count: int = 1                # quante volte osservato
    first_seen_episode: int = 0
    last_seen_episode: int = 0
    value: Optional[float] = None          # valore numerico associato (es. lift +35%)
    description: str = ""
    contradictions: int = 0               # volte in cui è stato contraddetto


# Soglie per promozione Layer 2 → Layer 1
PROMOTION_THRESHOLD_EVIDENCE = 5       # almeno 5 conferme
PROMOTION_THRESHOLD_CONFIDENCE = 0.75  # confidenza > 75%
CONTRADICTION_DECAY = 0.15             # quanto decade la confidenza per ogni contraddizione
CONFIRMATION_BOOST = 0.08              # quanto cresce la confidenza per ogni conferma
TACTICAL_DECAY_PER_EPISODE = 0.05      # decay per episodio senza conferma (solo Layer 2)


class MarketMemoryGraph:
    """
    Grafo di memoria del sistema.
    Unico, condiviso tra tutti gli agenti.
    Gli agenti lo consumano e lo alimentano.
    """

    def __init__(self):
        self.graph = nx.DiGraph()
        self.nodes: dict[str, MemoryNode] = {}
        self.edges: dict[str, MemoryEdge] = {}
        self.current_episode: int = 0
        self._promotion_log: list[dict] = []

    # -------------------------------------------------------------------------
    # Node management
    # -------------------------------------------------------------------------

    def add_node(self, node: MemoryNode) -> str:
        self.nodes[node.id] = node
        self.graph.add_node(node.id, **node.model_dump())
        return node.id

    def get_or_create_node(self, node_type: NodeType, label: str, attributes: dict = {}) -> str:
        """Evita duplicati — se il nodo esiste già lo restituisce."""
        for nid, node in self.nodes.items():
            if node.node_type == node_type and node.label == label:
                return nid
        return self.add_node(MemoryNode(node_type=node_type, label=label, attributes=attributes))

    # -------------------------------------------------------------------------
    # Edge management
    # -------------------------------------------------------------------------

    def observe(
        self,
        source_id: str,
        target_id: str,
        relation: str,
        episode: int,
        value: Optional[float] = None,
        description: str = "",
        contradicts: bool = False,
    ) -> MemoryEdge:
        """
        Registra un'osservazione come arco nel grafo.
        Se l'arco esiste già, aggiorna confidenza e evidence.
        Se viene contraddetto, decade la confidenza.
        Se raggiunge le soglie, promuove a Layer 1.
        """
        existing = self._find_edge(source_id, target_id, relation)

        if existing:
            edge = existing
            if contradicts:
                edge.contradictions += 1
                edge.confidence = max(0.0, edge.confidence - CONTRADICTION_DECAY)
            else:
                edge.evidence_count += 1
                edge.confidence = min(1.0, edge.confidence + CONFIRMATION_BOOST)
                if value is not None:
                    # media mobile del valore
                    edge.value = (
                        (edge.value * (edge.evidence_count - 1) + value) / edge.evidence_count
                        if edge.value is not None else value
                    )
            edge.last_seen_episode = episode
            self._maybe_promote(edge)
        else:
            edge = MemoryEdge(
                source_id=source_id,
                target_id=target_id,
                relation=relation,
                layer=MemoryLayer.TACTICAL,
                confidence=0.5,
                evidence_count=1,
                first_seen_episode=episode,
                last_seen_episode=episode,
                value=value,
                description=description,
            )
            self.edges[edge.id] = edge
            self.graph.add_edge(source_id, target_id, key=edge.id, **edge.model_dump())

        return edge

    def _find_edge(self, source_id: str, target_id: str, relation: str) -> Optional[MemoryEdge]:
        for edge in self.edges.values():
            if (
                edge.source_id == source_id
                and edge.target_id == target_id
                and edge.relation == relation
            ):
                return edge
        return None

    def _maybe_promote(self, edge: MemoryEdge):
        """Promuove un arco da Layer 2 (tattico) a Layer 1 (strutturale)."""
        if (
            edge.layer == MemoryLayer.TACTICAL
            and edge.evidence_count >= PROMOTION_THRESHOLD_EVIDENCE
            and edge.confidence >= PROMOTION_THRESHOLD_CONFIDENCE
        ):
            edge.layer = MemoryLayer.STRUCTURAL
            self._promotion_log.append({
                "episode": self.current_episode,
                "edge_id": edge.id,
                "relation": edge.relation,
                "description": edge.description,
                "confidence": edge.confidence,
                "evidence_count": edge.evidence_count,
            })

    # -------------------------------------------------------------------------
    # Decay — chiamato a fine episodio
    # -------------------------------------------------------------------------

    def apply_decay(self, episode: int):
        """
        Applica decay agli archi tattici che non sono stati confermati
        nell'episodio corrente. Gli archi strutturali non decadono.
        """
        self.current_episode = episode
        to_remove = []
        for edge in self.edges.values():
            if edge.layer == MemoryLayer.TACTICAL:
                episodes_since_seen = episode - edge.last_seen_episode
                if episodes_since_seen > 0:
                    edge.confidence = max(
                        0.0,
                        edge.confidence - TACTICAL_DECAY_PER_EPISODE * episodes_since_seen,
                    )
                if edge.confidence < 0.1:
                    to_remove.append(edge.id)

        for eid in to_remove:
            edge = self.edges.pop(eid)
            if self.graph.has_edge(edge.source_id, edge.target_id):
                self.graph.remove_edge(edge.source_id, edge.target_id)

    # -------------------------------------------------------------------------
    # Query — usate dagli agenti per leggere la memoria
    # -------------------------------------------------------------------------

    def get_context_for_agent(self, agent_id: str, top_k: int = 10) -> str:
        """
        Serializza la memoria rilevante per un agente in linguaggio naturale.
        Prioritizza: Layer 1 > Layer 2 ad alta confidenza.
        """
        relevant_edges = []

        for edge in self.edges.values():
            score = edge.confidence
            if edge.layer == MemoryLayer.STRUCTURAL:
                score += 1.0  # boost Layer 1
            relevant_edges.append((score, edge))

        relevant_edges.sort(key=lambda x: x[0], reverse=True)
        top_edges = relevant_edges[:top_k]

        if not top_edges:
            return "Nessuna conoscenza accumulata ancora."

        lines = ["=== MEMORIA DI MERCATO ===\n"]

        structural = [(s, e) for s, e in top_edges if e.layer == MemoryLayer.STRUCTURAL]
        tactical = [(s, e) for s, e in top_edges if e.layer == MemoryLayer.TACTICAL]

        if structural:
            lines.append("📚 LEGGI DI MERCATO (conoscenza strutturale confermata):")
            for score, edge in structural:
                src = self.nodes.get(edge.source_id)
                tgt = self.nodes.get(edge.target_id)
                src_label = src.label if src else edge.source_id
                tgt_label = tgt.label if tgt else edge.target_id
                value_str = f" → valore medio: {edge.value:.2f}" if edge.value is not None else ""
                lines.append(
                    f"  • [{edge.relation}] {src_label} → {tgt_label}{value_str} "
                    f"(confidenza: {edge.confidence:.0%}, osservato {edge.evidence_count}x)"
                )
                if edge.description:
                    lines.append(f"    Nota: {edge.description}")

        if tactical:
            lines.append("\n⚡ PATTERN RECENTI (conoscenza tattica):")
            for score, edge in tactical:
                src = self.nodes.get(edge.source_id)
                tgt = self.nodes.get(edge.target_id)
                src_label = src.label if src else edge.source_id
                tgt_label = tgt.label if tgt else edge.target_id
                value_str = f" → valore: {edge.value:.2f}" if edge.value is not None else ""
                lines.append(
                    f"  • [{edge.relation}] {src_label} → {tgt_label}{value_str} "
                    f"(confidenza: {edge.confidence:.0%})"
                )

        lines.append(f"\nEpisodio corrente: {self.current_episode}")
        return "\n".join(lines)

    def get_structural_knowledge(self) -> list[MemoryEdge]:
        return [e for e in self.edges.values() if e.layer == MemoryLayer.STRUCTURAL]

    def get_tactical_knowledge(self) -> list[MemoryEdge]:
        return [e for e in self.edges.values() if e.layer == MemoryLayer.TACTICAL]

    def promotion_log(self) -> list[dict]:
        return self._promotion_log

    # -------------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------------

    def save(self, path: str):
        data = {
            "current_episode": self.current_episode,
            "nodes": {k: v.model_dump() for k, v in self.nodes.items()},
            "edges": {k: v.model_dump() for k, v in self.edges.items()},
            "promotion_log": self._promotion_log,
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> "MarketMemoryGraph":
        with open(path) as f:
            data = json.load(f)
        g = cls()
        g.current_episode = data["current_episode"]
        g._promotion_log = data.get("promotion_log", [])
        for nid, ndata in data["nodes"].items():
            node = MemoryNode(**ndata)
            g.nodes[nid] = node
            g.graph.add_node(nid, **ndata)
        for eid, edata in data["edges"].items():
            edge = MemoryEdge(**edata)
            g.edges[eid] = edge
            g.graph.add_edge(edge.source_id, edge.target_id, key=eid, **edata)
        return g
