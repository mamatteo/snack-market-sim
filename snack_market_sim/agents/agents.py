"""
I 5 agenti del sistema.

Principio 1 applicato: system prompt definisce obiettivi, non procedure.
Principio 2 applicato: contesto ricco ma non prescrittivo.
"""

import json
from snack_market_sim.agents.base import BaseAgent
from snack_market_sim.world.engine import PromotionProposal


# ============================================================================
# MANUFACTURER A — Brand Premium
# ============================================================================

class ManufacturerAgentA(BaseAgent):

    def __init__(self, model: str = "qwen3:8b"):
        super().__init__("mfr_a", model)

    @property
    def system_prompt(self) -> str:
        return """Sei il Trade Promotion Manager di un brand premium di snack (ChipsPremium e CrackersPremium).

Il tuo obiettivo è far crescere il fatturato e il margine del tuo portfolio nel lungo periodo, 
mantenendo il posizionamento premium del brand.

Gestisci due SKU: ChipsPremium 150g e CrackersPremium 200g.
Ogni settimana puoi proporre una promozione al retailer o non fare nulla.

Il tuo successo dipende da: revenue, margine, e ritorno sull'investimento promozionale.
Hai un competitor mass market (Manufacturer B) e un challenger healthy (Manufacturer C).
Il retailer ha anche una private label che compete con i tuoi prodotti.

Ragiona in modo strategico. Le tue decisioni di oggi influenzano le settimane future."""

    def decide(self, world_state: str, memory_context: str, week: int) -> dict:
        history = self.get_history_summary()

        prompt = f"""{world_state}

{memory_context}

{history}

Settimana corrente: {week}

Decidi la tua azione per questa settimana.
Puoi proporre UNA promozione su uno dei tuoi SKU, oppure non fare nulla.

Rispondi SOLO con un JSON in questo formato:
{{
  "action": "propose" | "hold",
  "sku_id": "chips_a" | "crackers_a" | null,
  "discount_pct": 10-40 | null,
  "duration_weeks": 1-4 | null,
  "display_fee": 0-800 | null,
  "reasoning": "breve spiegazione del ragionamento"
}}"""

        response = self._call_llm(prompt)
        result = self._extract_json(response)
        self.add_to_history({"week": week, "summary": f"action={result.get('action')} sku={result.get('sku_id')} discount={result.get('discount_pct')}%"})
        return result


# ============================================================================
# MANUFACTURER B — Brand Mass Market
# ============================================================================

class ManufacturerAgentB(BaseAgent):

    def __init__(self, model: str = "qwen3:8b"):
        super().__init__("mfr_b", model)

    @property
    def system_prompt(self) -> str:
        return """Sei il Trade Promotion Manager di un brand mass market di snack (ChipsMass, CrackersMass, ChipsMass Gusto).

Il tuo obiettivo è dominare il volume di vendita nella categoria snack e difendere la tua quota di scaffale.

Gestisci tre SKU: ChipsMass 200g, CrackersMass 250g, ChipsMass Gusto 150g.
Ogni settimana puoi proporre una promozione al retailer o non fare nulla.

Il tuo successo dipende da: volume, revenue e margine.
Hai un competitor premium (Manufacturer A) e un challenger healthy (Manufacturer C).
La private label del retailer compete direttamente con i tuoi prodotti sul prezzo.

Le promozioni aggressive possono conquistare volume ma erodono il margine.
Ragiona su come bilanciare volume e profittabilità nel lungo periodo."""

    def decide(self, world_state: str, memory_context: str, week: int) -> dict:
        history = self.get_history_summary()

        prompt = f"""{world_state}

{memory_context}

{history}

Settimana corrente: {week}

Decidi la tua azione per questa settimana.
Puoi proporre UNA promozione su uno dei tuoi SKU, oppure non fare nulla.

Rispondi SOLO con un JSON in questo formato:
{{
  "action": "propose" | "hold",
  "sku_id": "chips_b" | "crackers_b" | "chips_b2" | null,
  "discount_pct": 10-40 | null,
  "duration_weeks": 1-4 | null,
  "display_fee": 0-800 | null,
  "reasoning": "breve spiegazione del ragionamento"
}}"""

        response = self._call_llm(prompt)
        result = self._extract_json(response)
        self.add_to_history({"week": week, "summary": f"action={result.get('action')} sku={result.get('sku_id')} discount={result.get('discount_pct')}%"})
        return result


# ============================================================================
# MANUFACTURER C — Challenger Healthy
# ============================================================================

class ManufacturerAgentC(BaseAgent):

    def __init__(self, model: str = "qwen3:8b"):
        super().__init__("mfr_c", model)

    @property
    def system_prompt(self) -> str:
        return """Sei il Trade Promotion Manager di un brand challenger nel segmento healthy snack (ProteinBar e RiceCakes Bio).

Il tuo obiettivo è conquistare spazio nell'assortimento del retailer e far crescere la penetrazione 
del segmento healthy nella categoria snack.

Gestisci due SKU: ProteinBar 40g e RiceCakes Bio 100g.
Ogni settimana puoi proporre una promozione al retailer o non fare nulla.

I tuoi prodotti hanno margini più alti ma volumi più bassi.
Il tuo vantaggio competitivo è l'allineamento con i trend consumer di salute e sostenibilità.
I tuoi competitor sono brand consolidati con più potere negoziale e maggiore spazio a scaffale.

Ragiona su come usare i trend consumer a tuo vantaggio e come costruire una relazione 
di lungo periodo con il retailer."""

    def decide(self, world_state: str, memory_context: str, week: int) -> dict:
        history = self.get_history_summary()

        prompt = f"""{world_state}

{memory_context}

{history}

Settimana corrente: {week}

Decidi la tua azione per questa settimana.
Puoi proporre UNA promozione su uno dei tuoi SKU, oppure non fare nulla.

Rispondi SOLO con un JSON in questo formato:
{{
  "action": "propose" | "hold",
  "sku_id": "healthy_c" | "healthy_c2" | null,
  "discount_pct": 10-40 | null,
  "duration_weeks": 1-4 | null,
  "display_fee": 0-800 | null,
  "reasoning": "breve spiegazione del ragionamento"
}}"""

        response = self._call_llm(prompt)
        result = self._extract_json(response)
        self.add_to_history({"week": week, "summary": f"action={result.get('action')} sku={result.get('sku_id')} discount={result.get('discount_pct')}%"})
        return result


# ============================================================================
# RETAILER — Category Manager GDO
# ============================================================================

class RetailerAgent(BaseAgent):

    def __init__(self, model: str = "qwen3:8b"):
        super().__init__("retailer", model)

    @property
    def system_prompt(self) -> str:
        return """Sei il Category Manager snack di una grande catena GDO italiana.

Il tuo obiettivo è massimizzare il margine per metro lineare della categoria snack 
e garantire un assortimento che soddisfi i consumatori nel lungo periodo.

Gestisci uno scaffale con slot limitati. Ogni settimana ricevi proposte promozionali 
dai manufacturer e devi decidere quali accettare, rifiutare, o contrattare.

Puoi anche decidere di rimuovere SKU dall'assortimento o aggiungerne di nuovi.
Hai una private label (PrivateLabel Chips) che compete con i brand nazionali.

Il tuo successo dipende da: margine di categoria, volume, rotazione dell'inventario.
Una promozione accettata male può aumentare il volume ma distruggere il margine.
Una promozione rifiutata male può perdere un'opportunità e danneggiare la relazione con il manufacturer.

Ragiona sul lungo periodo. I manufacturer sono partner strategici, non avversari."""

    def decide(self, world_state: str, memory_context: str, week: int, proposals: list[dict]) -> dict:
        history = self.get_history_summary()

        proposals_text = json.dumps(proposals, indent=2, ensure_ascii=False) if proposals else "Nessuna proposta questa settimana."

        prompt = f"""{world_state}

{memory_context}

{history}

Settimana corrente: {week}

PROPOSTE RICEVUTE DAI MANUFACTURER:
{proposals_text}

Decidi la tua risposta per ogni proposta.
Puoi accettare, rifiutare, o fare un counter-offer (modificando discount_pct o display_fee).

Rispondi SOLO con un JSON in questo formato:
{{
  "decisions": [
    {{
      "manufacturer_id": "mfr_a" | "mfr_b" | "mfr_c",
      "sku_id": "...",
      "decision": "accept" | "reject" | "counter",
      "counter_discount_pct": null | number,
      "counter_display_fee": null | number,
      "reasoning": "breve spiegazione"
    }}
  ],
  "assortment_action": null | {{"action": "delist" | "list", "sku_id": "..."}},
  "overall_reasoning": "strategia generale questa settimana"
}}"""

        response = self._call_llm(prompt)
        result = self._extract_json(response)
        n_accepted = sum(1 for d in result.get("decisions", []) if d.get("decision") == "accept")
        self.add_to_history({"week": week, "summary": f"proposals={len(proposals)} accepted={n_accepted}"})
        return result


# ============================================================================
# CONSUMER AGENT — Demand + Trend
# ============================================================================

class ConsumerAgent(BaseAgent):

    def __init__(self, model: str = "qwen3:8b"):
        super().__init__("consumer", model)

    @property
    def system_prompt(self) -> str:
        return """Sei un agente che rappresenta il mercato dei consumatori di snack in Italia.

Il tuo ruolo è duplice:
1. Generare la domanda settimanale reagendo a prezzi, promozioni e disponibilità
2. Introdurre e aggiornare i trend di consumo che influenzano le preferenze nel medio periodo

I trend che puoi influenzare:
- healthy_preference: quanto i consumatori preferiscono prodotti salutari (-1.0 = nessuna preferenza, +1.0 = forte preferenza)
- price_sensitivity: quanto i consumatori sono sensibili al prezzo (-1.0 = non sensibili, +1.0 = molto sensibili)

I trend cambiano lentamente ma persistono. Sono influenzati da fattori come:
stagione, notizie di salute pubblica, crisi economiche, tendenze social, novità di prodotto.

Il tuo obiettivo è rappresentare fedelmente il comportamento aggregato dei consumatori,
non massimizzare nessun KPI specifico."""

    def decide(self, world_state: str, memory_context: str, week: int) -> dict:
        history = self.get_history_summary()

        prompt = f"""{world_state}

{memory_context}

{history}

Settimana corrente: {week}

Basandoti sullo stato del mercato e sui trend storici, aggiorna i parametri di domanda consumer.

Considera: stagionalità, promozioni attive, trend recenti, e qualsiasi evento di mercato rilevante.

Rispondi SOLO con un JSON in questo formato:
{{
  "healthy_preference": -1.0 to 1.0,
  "price_sensitivity": -1.0 to 1.0,
  "description": "descrizione del sentiment consumer questa settimana",
  "trend_signal": "emerging" | "stable" | "declining",
  "reasoning": "breve spiegazione del ragionamento"
}}"""

        response = self._call_llm(prompt)
        result = self._extract_json(response)
        self.add_to_history({"week": week, "summary": f"healthy={result.get('healthy_preference',0):+.2f} price_sens={result.get('price_sensitivity',0):+.2f}"})
        return result
