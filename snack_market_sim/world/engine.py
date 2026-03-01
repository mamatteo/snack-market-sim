"""
World Engine — simulatore del mercato snack.

Gestisce:
- 8 SKU in 3 sottocategorie (chips, crackers, healthy)
- Domanda moltiplicativa con stagionalità, lift promozionale, post-promo dip
- Financials per manufacturer e retailer
- Reward calculation per tutti gli agenti
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class SubCategory(str, Enum):
    CHIPS = "chips"
    CRACKERS = "crackers"
    HEALTHY = "healthy"


@dataclass
class SKU:
    id: str
    name: str
    subcategory: SubCategory
    manufacturer_id: str           # "mfr_a", "mfr_b", "mfr_c"
    base_demand: float             # unità/settimana baseline
    manufacturer_cost: float       # costo produzione per unità
    manufacturer_list_price: float # prezzo listino manufacturer → retailer
    retailer_list_price: float     # prezzo al consumatore baseline
    shelf_slots: int = 1           # slot scaffale occupati
    is_listed: bool = True         # se è in assortimento


@dataclass
class PromotionProposal:
    manufacturer_id: str
    sku_id: str
    discount_pct: float            # sconto % su manufacturer_list_price
    duration_weeks: int
    display_fee: float             # fee aggiuntiva pagata dal manufacturer al retailer
    week_proposed: int


@dataclass
class ActivePromotion:
    proposal: PromotionProposal
    week_started: int
    weeks_remaining: int


@dataclass
class WeeklyResult:
    week: int
    sku_id: str
    units_sold: float
    manufacturer_revenue: float
    manufacturer_margin: float
    retailer_revenue: float
    retailer_margin: float
    was_promoted: bool
    promotion_lift: float
    post_promo_dip: float = 0.0


# -----------------------------------------------------------------------
# Configurazione SKU — 3 manufacturer, 3 sottocategorie, 8 SKU
# -----------------------------------------------------------------------

SKUS: dict[str, SKU] = {
    # Manufacturer A — brand premium
    "chips_a":    SKU("chips_a",   "ChipsPremium 150g",   SubCategory.CHIPS,    "mfr_a", 120, 0.80, 1.50, 2.20),
    "crackers_a": SKU("crackers_a","CrackersPremium 200g", SubCategory.CRACKERS, "mfr_a",  80, 0.60, 1.20, 1.80),
    # Manufacturer B — brand mass market
    "chips_b":    SKU("chips_b",   "ChipsMass 200g",      SubCategory.CHIPS,    "mfr_b", 200, 0.50, 0.90, 1.50),
    "crackers_b": SKU("crackers_b","CrackersMass 250g",   SubCategory.CRACKERS, "mfr_b", 150, 0.45, 0.85, 1.40),
    "chips_b2":   SKU("chips_b2",  "ChipsMass Gusto 150g",SubCategory.CHIPS,    "mfr_b", 100, 0.55, 1.00, 1.60),
    # Manufacturer C — challenger healthy
    "healthy_c":  SKU("healthy_c", "ProteinBar 40g",      SubCategory.HEALTHY,  "mfr_c",  60, 1.20, 2.50, 3.80),
    "healthy_c2": SKU("healthy_c2","RiceCakes Bio 100g",  SubCategory.HEALTHY,  "mfr_c",  70, 0.90, 1.80, 2.90),
    # Private label retailer (sempre listato, non negoziabile)
    "pl_chips":   SKU("pl_chips",  "PrivateLabel Chips",  SubCategory.CHIPS,    "retailer", 180, 0.40, 0.40, 1.20),
}

# Stagionalità settimanale (52 settimane)
# Picchi: estate (settimane 24-35), Natale (settimane 48-52 + 1-2)
def _build_seasonality() -> np.ndarray:
    s = np.ones(52)
    # estate
    s[23:35] *= 1.25
    # natale
    s[47:52] *= 1.35
    s[0:2]   *= 1.20
    # gennaio — calo post-feste
    s[2:6]   *= 0.80
    return s

SEASONALITY = _build_seasonality()

# Parametri domanda
PROMO_LIFT_BASE = 1.8          # lift base con promozione (prima del display)
DISPLAY_FEE_LIFT_BONUS = 0.3   # bonus lift se display fee > 400€
POST_PROMO_DIP_FACTOR = 0.20   # % di domanda persa nelle 3 settimane successive
POST_PROMO_DIP_WEEKS = 3
COMPETITOR_REACTION_PROB = 0.20  # probabilità che un competitor promuova nella stessa categoria


class WorldEngine:

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.skus = {k: SKU(**vars(v)) for k, v in SKUS.items()}  # deep copy
        self.active_promotions: list[ActivePromotion] = []
        self.post_promo_dip_tracker: dict[str, int] = {}  # sku_id → weeks remaining
        self.week: int = 0
        self.history: list[WeeklyResult] = []
        self.consumer_trend: dict = {
            "healthy_preference": 0.0,   # -1.0 → +1.0
            "price_sensitivity": 0.0,
            "description": "neutro",
        }

    # -----------------------------------------------------------------------
    # Consumer trend — aggiornato dall'agente consumer
    # -----------------------------------------------------------------------

    def update_consumer_trend(self, healthy_preference: float, price_sensitivity: float, description: str):
        self.consumer_trend["healthy_preference"] = np.clip(healthy_preference, -1.0, 1.0)
        self.consumer_trend["price_sensitivity"] = np.clip(price_sensitivity, -1.0, 1.0)
        self.consumer_trend["description"] = description

    # -----------------------------------------------------------------------
    # Promotion management
    # -----------------------------------------------------------------------

    def apply_promotion(self, proposal: PromotionProposal):
        """Il retailer ha accettato — attiva la promozione."""
        promo = ActivePromotion(
            proposal=proposal,
            week_started=self.week,
            weeks_remaining=proposal.duration_weeks,
        )
        self.active_promotions.append(promo)

    def _get_active_promotion_for_sku(self, sku_id: str) -> Optional[ActivePromotion]:
        for p in self.active_promotions:
            if p.proposal.sku_id == sku_id and p.weeks_remaining > 0:
                return p
        return None

    # -----------------------------------------------------------------------
    # Demand calculation
    # -----------------------------------------------------------------------

    def _compute_demand(self, sku: SKU, week: int) -> tuple[float, float, float]:
        """
        Ritorna (units_sold, promotion_lift_multiplier, post_promo_dip_multiplier)
        """
        base = sku.base_demand
        season = SEASONALITY[week % 52]

        # Consumer trend impact
        trend_mult = 1.0
        if sku.subcategory == SubCategory.HEALTHY:
            trend_mult += self.consumer_trend["healthy_preference"] * 0.3
        price_sensitivity_impact = -self.consumer_trend["price_sensitivity"] * 0.1
        trend_mult += price_sensitivity_impact
        trend_mult = max(0.5, trend_mult)

        # Promotion lift
        promo = self._get_active_promotion_for_sku(sku.id)
        promo_lift = 1.0
        if promo:
            promo_lift = PROMO_LIFT_BASE + (promo.proposal.discount_pct / 100) * 0.5
            if promo.proposal.display_fee > 400:
                promo_lift += DISPLAY_FEE_LIFT_BONUS
            promo_lift = min(promo_lift, 3.0)

        # Post-promo dip
        dip_mult = 1.0
        if sku.id in self.post_promo_dip_tracker and self.post_promo_dip_tracker[sku.id] > 0:
            dip_mult = 1.0 - POST_PROMO_DIP_FACTOR

        # Noise
        noise = self.rng.normal(1.0, 0.05)

        units = base * season * trend_mult * promo_lift * dip_mult * noise
        units = max(0, units)

        return units, promo_lift, dip_mult

    # -----------------------------------------------------------------------
    # Financials
    # -----------------------------------------------------------------------

    def _compute_financials(self, sku: SKU, units: float, promo: Optional[ActivePromotion]) -> WeeklyResult:
        if promo:
            transfer_price = sku.manufacturer_list_price * (1 - promo.proposal.discount_pct / 100)
            retailer_price = transfer_price * 1.30  # retailer mantiene ~30% margin
        else:
            transfer_price = sku.manufacturer_list_price
            retailer_price = sku.retailer_list_price

        display_fee = promo.proposal.display_fee if promo else 0.0

        mfr_revenue = transfer_price * units + display_fee
        mfr_cost = sku.manufacturer_cost * units
        mfr_margin = mfr_revenue - mfr_cost

        ret_revenue = retailer_price * units
        ret_cost = transfer_price * units
        ret_margin = ret_revenue - ret_cost + display_fee

        return WeeklyResult(
            week=self.week,
            sku_id=sku.id,
            units_sold=units,
            manufacturer_revenue=mfr_revenue,
            manufacturer_margin=mfr_margin,
            retailer_revenue=ret_revenue,
            retailer_margin=ret_margin,
            was_promoted=promo is not None,
            promotion_lift=promo and (mfr_revenue / (sku.manufacturer_list_price * units + 1e-6)) or 1.0,
        )

    # -----------------------------------------------------------------------
    # Step — avanza di una settimana
    # -----------------------------------------------------------------------

    def step(self) -> list[WeeklyResult]:
        results = []

        for sku_id, sku in self.skus.items():
            if not sku.is_listed:
                continue

            units, promo_lift, dip_mult = self._compute_demand(sku, self.week)
            promo = self._get_active_promotion_for_sku(sku_id)
            result = self._compute_financials(sku, units, promo)
            result.promotion_lift = promo_lift
            result.post_promo_dip = 1.0 - dip_mult
            results.append(result)
            self.history.append(result)

        # Aggiorna promozioni attive
        still_active = []
        for p in self.active_promotions:
            p.weeks_remaining -= 1
            if p.weeks_remaining > 0:
                still_active.append(p)
            else:
                # promozione finita → attiva post-promo dip
                self.post_promo_dip_tracker[p.proposal.sku_id] = POST_PROMO_DIP_WEEKS

        self.active_promotions = still_active

        # Decrementa post-promo dip tracker
        for sku_id in list(self.post_promo_dip_tracker.keys()):
            self.post_promo_dip_tracker[sku_id] -= 1
            if self.post_promo_dip_tracker[sku_id] <= 0:
                del self.post_promo_dip_tracker[sku_id]

        self.week += 1
        return results

    # -----------------------------------------------------------------------
    # State serialization — per gli agenti
    # -----------------------------------------------------------------------

    def get_state_summary(self) -> str:
        lines = [f"=== STATO MERCATO — Settimana {self.week} ===\n"]

        lines.append(f"🌊 Consumer Trend: {self.consumer_trend['description']}")
        lines.append(f"   Healthy preference: {self.consumer_trend['healthy_preference']:+.2f}")
        lines.append(f"   Price sensitivity: {self.consumer_trend['price_sensitivity']:+.2f}\n")

        lines.append("📦 SKU IN ASSORTIMENTO:")
        for sku_id, sku in self.skus.items():
            if not sku.is_listed:
                continue
            promo = self._get_active_promotion_for_sku(sku_id)
            dip = sku_id in self.post_promo_dip_tracker
            status = ""
            if promo:
                status = f" 🟢 PROMO -{promo.proposal.discount_pct:.0f}% ({promo.weeks_remaining}w rimaste)"
            elif dip:
                status = f" 🔴 POST-PROMO DIP ({self.post_promo_dip_tracker[sku_id]}w rimaste)"
            lines.append(f"  {sku.name} [{sku.manufacturer_id}]{status}")

        # Ultimi risultati
        if self.history:
            recent = self.history[-len(self.skus):]
            lines.append("\n📊 RISULTATI SETTIMANA PRECEDENTE:")
            for r in recent:
                sku = self.skus.get(r.sku_id)
                if sku:
                    lines.append(
                        f"  {sku.name}: {r.units_sold:.0f} unità | "
                        f"MFR margin: €{r.manufacturer_margin:.0f} | "
                        f"RTL margin: €{r.retailer_margin:.0f}"
                    )

        season_idx = self.week % 52
        lines.append(f"\n📅 Moltiplicatore stagionale attuale: {SEASONALITY[season_idx]:.2f}x")

        return "\n".join(lines)

    # -----------------------------------------------------------------------
    # Reward calculation
    # -----------------------------------------------------------------------

    def compute_rewards(self, episode_results: list[WeeklyResult]) -> dict:
        """Calcola reward per ogni agente a fine episodio."""
        rewards = {}

        for mfr_id in ["mfr_a", "mfr_b", "mfr_c"]:
            mfr_results = [r for r in episode_results if self.skus[r.sku_id].manufacturer_id == mfr_id]
            if not mfr_results:
                rewards[mfr_id] = 0.0
                continue

            total_revenue = sum(r.manufacturer_revenue for r in mfr_results)
            total_margin = sum(r.manufacturer_margin for r in mfr_results)
            promo_results = [r for r in mfr_results if r.was_promoted]
            promo_roi = (
                sum(r.manufacturer_margin for r in promo_results) /
                max(1, len(promo_results))
            ) if promo_results else 0.0

            # KPI normalizzati e clippati
            rev_score   = np.clip(total_revenue / 50000, 0, 2.0)
            margin_score = np.clip(total_margin / 20000, -1.0, 2.0)
            roi_score   = np.clip(promo_roi / 500, 0, 3.0)

            rewards[mfr_id] = 0.40 * rev_score + 0.30 * margin_score + 0.30 * roi_score

        # Retailer
        ret_results = [r for r in episode_results]
        total_ret_margin = sum(r.retailer_margin for r in ret_results)
        total_units = sum(r.units_sold for r in ret_results)
        listed_skus = sum(1 for s in self.skus.values() if s.is_listed)

        margin_score  = np.clip(total_ret_margin / 80000, 0, 2.0)
        volume_score  = np.clip(total_units / 100000, 0, 2.0)
        turns_score   = np.clip(total_units / (listed_skus * 52 * 100), 0, 2.0)

        rewards["retailer"] = 0.40 * margin_score + 0.30 * volume_score + 0.30 * turns_score

        # Consumer agent reward — quanto bene ha predetto la domanda
        rewards["consumer"] = 0.5  # placeholder, verrà affinato

        # Sistema efficiency — media dei reward di tutti gli agenti (principio 4)
        all_scores = [v for v in rewards.values()]
        system_efficiency = np.mean(all_scores)

        # Blend 60% individuale + 40% sistemico (come nell'articolo, ma per tutti)
        for agent_id in rewards:
            rewards[agent_id] = 0.60 * rewards[agent_id] + 0.40 * system_efficiency

        return rewards
