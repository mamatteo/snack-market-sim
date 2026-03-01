"""
Memory Extractor — distilla conoscenza dagli episodi nel grafo di memoria.

Questo è il modulo che implementa il Principio 4 (Compound Intelligence):
ogni episodio deposita conoscenza strutturata nel grafo condiviso.
"""

from snack_market_sim.world.engine import WorldEngine, WeeklyResult, SEASONALITY, SKUS
from snack_market_sim.memory.graph import MarketMemoryGraph, NodeType
import numpy as np


class MemoryExtractor:

    def __init__(self, memory: MarketMemoryGraph, world: WorldEngine):
        self.memory = memory
        self.world = world
        self._ensure_base_nodes()

    def _ensure_base_nodes(self):
        """Crea i nodi base del grafo (SKU, manufacturer, stagioni, categorie)."""
        # Categorie
        for cat in ["chips", "crackers", "healthy"]:
            self.memory.get_or_create_node(NodeType.CATEGORY, cat)

        # Stagioni
        for season in ["Q1_inverno", "Q2_primavera", "Q3_estate", "Q4_autunno_natale"]:
            self.memory.get_or_create_node(NodeType.SEASON, season)

        # Manufacturer
        for mfr in ["mfr_a", "mfr_b", "mfr_c", "retailer"]:
            self.memory.get_or_create_node(NodeType.MANUFACTURER, mfr)

        # SKU
        for sku_id, sku in SKUS.items():
            self.memory.get_or_create_node(NodeType.SKU, sku_id, {"name": sku.name, "subcategory": sku.subcategory})

    def _week_to_season(self, week: int) -> str:
        w = week % 52
        if w < 13:
            return "Q1_inverno"
        elif w < 26:
            return "Q2_primavera"
        elif w < 39:
            return "Q3_estate"
        else:
            return "Q4_autunno_natale"

    def extract_from_episode(self, episode: int, results: list[WeeklyResult], agent_decisions: list[dict]):
        """
        Analizza i risultati dell'episodio e deposita osservazioni nel grafo.
        Chiamato a fine episodio dall'orchestratore.
        """
        # Raggruppa risultati per SKU e per stagione
        by_sku: dict[str, list[WeeklyResult]] = {}
        for r in results:
            by_sku.setdefault(r.sku_id, []).append(r)

        # 1. Pattern di lift promozionale per SKU e stagione
        self._extract_promo_lift_patterns(episode, by_sku)

        # 2. Pattern post-promo dip
        self._extract_post_promo_dip_patterns(episode, by_sku)

        # 3. Pattern stagionali
        self._extract_seasonal_patterns(episode, by_sku)

        # 4. Pattern relazionali tra manufacturer e retailer
        self._extract_relational_patterns(episode, agent_decisions)

        # 5. Pattern di competizione (private label vs brand)
        self._extract_competition_patterns(episode, by_sku)

        # Applica decay agli archi tattici vecchi
        self.memory.apply_decay(episode)

    def _extract_promo_lift_patterns(self, episode: int, by_sku: dict):
        for sku_id, results in by_sku.items():
            promo_results = [r for r in results if r.was_promoted]
            non_promo_results = [r for r in results if not r.was_promoted]

            if not promo_results or not non_promo_results:
                continue

            avg_promo_units = np.mean([r.units_sold for r in promo_results])
            avg_base_units = np.mean([r.units_sold for r in non_promo_results])

            if avg_base_units > 0:
                lift = avg_promo_units / avg_base_units

                sku_node = self.memory.get_or_create_node(NodeType.SKU, sku_id)
                obs_node = self.memory.get_or_create_node(
                    NodeType.OBSERVATION, f"promo_lift_{sku_id}"
                )

                self.memory.observe(
                    source_id=sku_node,
                    target_id=obs_node,
                    relation="promo_generates_lift",
                    episode=episode,
                    value=lift,
                    description=f"{sku_id}: lift medio {lift:.2f}x con promozione",
                )

    def _extract_post_promo_dip_patterns(self, episode: int, by_sku: dict):
        for sku_id, results in by_sku.items():
            # Cerca settimane dove c'è un dip dopo promozione
            dip_weeks = [r for r in results if r.post_promo_dip > 0]
            if not dip_weeks:
                continue

            avg_dip = np.mean([r.post_promo_dip for r in dip_weeks])
            sku_node = self.memory.get_or_create_node(NodeType.SKU, sku_id)
            obs_node = self.memory.get_or_create_node(
                NodeType.OBSERVATION, f"post_dip_{sku_id}"
            )

            self.memory.observe(
                source_id=sku_node,
                target_id=obs_node,
                relation="post_promo_dip",
                episode=episode,
                value=avg_dip,
                description=f"{sku_id}: dip medio {avg_dip:.1%} dopo promozione",
            )

    def _extract_seasonal_patterns(self, episode: int, by_sku: dict):
        # Aggrega per stagione
        season_demand: dict[str, list[float]] = {
            "Q1_inverno": [], "Q2_primavera": [], "Q3_estate": [], "Q4_autunno_natale": []
        }

        for sku_id, results in by_sku.items():
            sku = SKUS.get(sku_id)
            if not sku or sku.manufacturer_id == "retailer":
                continue
            for r in results:
                if not r.was_promoted:  # solo settimane senza promo per isolare stagionalità
                    season = self._week_to_season(r.week)
                    season_demand[season].append(r.units_sold)

        for season, demands in season_demand.items():
            if not demands:
                continue
            avg_demand = np.mean(demands)
            season_node = self.memory.get_or_create_node(NodeType.SEASON, season)
            obs_node = self.memory.get_or_create_node(
                NodeType.OBSERVATION, f"demand_{season}"
            )
            self.memory.observe(
                source_id=season_node,
                target_id=obs_node,
                relation="seasonal_demand_level",
                episode=episode,
                value=avg_demand,
                description=f"Domanda media in {season}: {avg_demand:.0f} unità/settimana",
            )

    def _extract_relational_patterns(self, episode: int, agent_decisions: list[dict]):
        """Estrae pattern di comportamento dei manufacturer e del retailer."""
        proposals = [d for d in agent_decisions if d.get("type") == "proposal"]
        responses = [d for d in agent_decisions if d.get("type") == "response"]

        # Tasso di accettazione per manufacturer
        for mfr_id in ["mfr_a", "mfr_b", "mfr_c"]:
            mfr_proposals = [p for p in proposals if p.get("manufacturer_id") == mfr_id]
            mfr_accepted = [
                r for r in responses
                if r.get("manufacturer_id") == mfr_id and r.get("decision") == "accept"
            ]

            if not mfr_proposals:
                continue

            acceptance_rate = len(mfr_accepted) / len(mfr_proposals)
            mfr_node = self.memory.get_or_create_node(NodeType.MANUFACTURER, mfr_id)
            retailer_node = self.memory.get_or_create_node(NodeType.RETAILER, "retailer")

            self.memory.observe(
                source_id=mfr_node,
                target_id=retailer_node,
                relation="proposal_acceptance_rate",
                episode=episode,
                value=acceptance_rate,
                description=f"{mfr_id}: {acceptance_rate:.0%} delle proposte accettate dal retailer",
            )

            # Sconto medio proposto
            if mfr_proposals:
                avg_discount = np.mean([p.get("discount_pct", 0) for p in mfr_proposals])
                self.memory.observe(
                    source_id=mfr_node,
                    target_id=retailer_node,
                    relation="avg_discount_proposed",
                    episode=episode,
                    value=avg_discount,
                    description=f"{mfr_id}: sconto medio proposto {avg_discount:.1f}%",
                )

    def _extract_competition_patterns(self, episode: int, by_sku: dict):
        """Analizza competizione tra brand e private label."""
        pl_results = by_sku.get("pl_chips", [])
        brand_chips_results = []
        for sku_id in ["chips_a", "chips_b", "chips_b2"]:
            brand_chips_results.extend(by_sku.get(sku_id, []))

        if not pl_results or not brand_chips_results:
            return

        pl_units = np.mean([r.units_sold for r in pl_results])
        brand_units = np.mean([r.units_sold for r in brand_chips_results])

        pl_node = self.memory.get_or_create_node(NodeType.SKU, "pl_chips")
        cat_node = self.memory.get_or_create_node(NodeType.CATEGORY, "chips")

        if brand_units > 0:
            pl_share = pl_units / (pl_units + brand_units)
            self.memory.observe(
                source_id=pl_node,
                target_id=cat_node,
                relation="private_label_share",
                episode=episode,
                value=pl_share,
                description=f"Private label share in chips: {pl_share:.1%}",
            )
