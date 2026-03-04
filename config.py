"""
config.py — Parametri di calibrazione del sistema.

Questo file centralizza tutti i parametri modificabili della simulazione.
Per adattare il sistema a un mercato reale è sufficiente editare questo file
prima di eseguire `python main.py` — senza toccare la logica degli agenti.

Le sezioni corrispondono alle aree tipiche di raccolta requisiti con un cliente:
  1. Meccaniche promozionali   → come funzionano le promo in questo mercato?
  2. Comportamento consumer    → quanto pesa il trend healthy? quanto è price-elastic il mercato?
  3. Struttura finanziaria     → quali sono i margini attesi?
  4. KPI e reward              → cosa significa "vincere" per ogni attore?
  5. Velocità di apprendimento → quanti episodi per consolidare una legge di mercato?
  6. Orizzonte della simulazione → durata degli scenari e modello LLM

Nota: il catalogo SKU e la stagionalità non sono in questo file perché
richiedono strutture dati Python (dict e array). Sono configurabili
direttamente in `world/market_simulator.py` → `SKUS` e `_build_seasonality()`.
"""

# ============================================================================
# 1. MECCANICHE PROMOZIONALI
#
# Domande al cliente:
#   - Qual è il lift tipico di una promozione in questa categoria?
#   - Un'esposizione preferenziale (display, testa di gondola) genera
#     incremento misurabile rispetto a una promo senza visibilità extra?
#   - Quanto dura il calo post-promo e con che intensità?
# ============================================================================

PROMO_LIFT_BASE = 1.8
# Lift base sulla domanda quando un prodotto è in promozione (×1.8 = +80%).
# Valori tipici di mercato: 1.5–2.5 a seconda della categoria e del retailer.
# Snack confezionati in GDO: 1.7–2.0 è un range ragionevole.

DISPLAY_FEE_THRESHOLD = 400
# Display fee minima (€) oltre la quale scatta il bonus di posizionamento.
# Rappresenta la soglia sotto cui la fee è considerata "simbolica".

DISPLAY_FEE_LIFT_BONUS = 0.3
# Incremento aggiuntivo al lift quando display_fee > DISPLAY_FEE_THRESHOLD.
# Modella il vantaggio di un posizionamento premium (testa di gondola, display dedicato).

PROMO_LIFT_CAP = 3.0
# Lift massimo consentito — soglia di realismo.
# Incrementi oltre ×3 sono rari anche con promozioni aggressive.

POST_PROMO_DIP_FACTOR = 0.20
# Riduzione percentuale della domanda nelle settimane successive alla fine di una promo.
# Modella il pantry loading: i consumatori si sono riforniti e acquistano meno.
# Tipicamente 10–30% a seconda del grado di stock-up della categoria.

POST_PROMO_DIP_WEEKS = 3
# Durata del post-promo dip in settimane.
# In GDO snack il dip tende a esaurirsi in 2–4 settimane.

COMPETITOR_REACTION_PROB = 0.20
# Probabilità che un competitor promuova nella stessa categoria in risposta.
# Non ancora implementato nella domanda — predisposto per estensioni future.

# ============================================================================
# 2. COMPORTAMENTO CONSUMER
#
# Domande al cliente:
#   - Il segmento healthy è in crescita nel vostro mercato? Con che intensità?
#   - I consumatori sono price-elastic? Rinviano gli acquisti in assenza di promo?
#   - Quanto è volatile la domanda settimana per settimana?
# ============================================================================

HEALTHY_TREND_SENSITIVITY = 0.3
# Quanto un'unità di healthy_preference (+1.0) amplifica la domanda dei prodotti healthy.
# Es: 0.3 → +30% di domanda healthy con preferenza massima.
# Range consigliato: 0.1 (categoria matura) – 0.5 (categoria in forte trasformazione).

PRICE_SENSITIVITY_IMPACT = 0.1
# Quanto un'unità di price_sensitivity (+1.0) riduce la domanda complessiva.
# Es: 0.1 → −10% di domanda con sensibilità al prezzo massima.
# Range consigliato: 0.05 (categoria necessità) – 0.20 (categoria discrezionale).

DEMAND_NOISE_SIGMA = 0.05
# Deviazione standard del rumore gaussiano sulla domanda settimanale.
# 0.05 = ±5% di variabilità attorno alla media.
# Aumentare (es. 0.10–0.15) per mercati più volatili o con forte variabilità promozionale.

DEMAND_FLOOR_MULTIPLIER = 0.5
# Moltiplicatore minimo per il trend consumer — evita domanda negativa.
# Non modificare salvo casi estremi.

# ============================================================================
# 3. STRUTTURA FINANZIARIA
#
# Domande al cliente:
#   - Qual è il margine lordo tipico del retailer su prodotti in promozione?
#   - Come funziona la display fee — flat o percentuale? Inclusa o separata?
# ============================================================================

RETAILER_MARGIN_ON_PROMO = 0.30
# Margine che il retailer applica sul transfer price ridotto durante una promozione.
# Es: 0.30 → il retailer vende al consumatore a transfer_price × 1.30.
# In GDO italiana il margine lordo tipico è 25–35%.
# I prezzi e costi per SKU sono configurati in `world/market_simulator.py` → SKUS.

# ============================================================================
# 4. KPI E REWARD
#
# Domande al cliente:
#   - Quali KPI guidano davvero le decisioni di un trade promotion manager?
#   - E quelle di un category manager? Margine, volume, rotazione?
#   - Quanto conta la performance dell'intera categoria rispetto alla quota individuale?
# ============================================================================

# --- Pesi reward manufacturer: revenue, margine, ROI promozionale ---
MFR_REWARD_WEIGHT_REVENUE   = 0.40
MFR_REWARD_WEIGHT_MARGIN    = 0.30
MFR_REWARD_WEIGHT_PROMO_ROI = 0.30
# Somma deve essere 1.0. Spostare peso verso PROMO_ROI per enfatizzare
# l'efficienza promozionale; verso MARGIN per un manufacturer margin-driven.

# --- Pesi reward retailer: margine categoria, volume, rotazione ---
RTL_REWARD_WEIGHT_MARGIN = 0.40
RTL_REWARD_WEIGHT_VOLUME = 0.30
RTL_REWARD_WEIGHT_TURNS  = 0.30
# Aumentare TURNS per un retailer con problemi di rotazione inventario.

# --- Blend individuale/sistemico nel reward finale ---
SYSTEM_BLEND_RATIO = 0.40
# Quota (0.0–1.0) del reward determinata dalla media sistemica di tutti gli agenti.
# 0.40 = 60% individuale + 40% sistemico.
# 0.0 = puramente competitivo. 1.0 = puramente cooperativo.
# Aumentare per simulare accordi di joint business planning.

# --- Soglie di normalizzazione KPI (base mensile per episodio da 4 settimane) ---
# I reward sono calcolati come KPI / soglia, clippati a [0, 2].
# Adattare alle dimensioni reali del mercato simulato.
MFR_REVENUE_NORM  = 50_000   # €  — revenue manufacturer al di sopra del quale il reward satura
MFR_MARGIN_NORM   = 20_000   # €  — margine manufacturer
MFR_ROI_NORM      = 500      # €  — margine medio per settimana promozionale
RTL_MARGIN_NORM   = 80_000   # €  — margine retailer di categoria
RTL_VOLUME_NORM   = 100_000  # u  — unità totali vendute
RTL_TURNS_NORM    = 100      # u/slot/anno — rotazione per slot scaffale

# ============================================================================
# 5. VELOCITÀ DI APPRENDIMENTO
#
# Domande al cliente:
#   - Quante stagioni servono per considerare un pattern "legge di mercato"?
#   - Con che velocità devono decadere le osservazioni tattiche non confermate?
#   - Quanto è robusto un pattern prima di essere smentito da una contraddizione?
# ============================================================================

MEMORY_PROMOTION_EVIDENCE   = 5
# Numero minimo di conferme (episodi) per promuovere un pattern da tattico a strutturale.
# Ridurre (es. 3) per sistemi che devono imparare velocemente con pochi dati.

MEMORY_PROMOTION_CONFIDENCE = 0.75
# Soglia di confidenza (0.0–1.0) per la promozione Layer 2 → Layer 1.

MEMORY_CONFIRMATION_BOOST   = 0.08
# Quanto cresce la confidenza di un arco per ogni episodio che lo conferma.

MEMORY_CONTRADICTION_DECAY  = 0.15
# Quanto decade la confidenza di un arco per ogni episodio che lo contraddice.
# Valore alto (>0.20) → il sistema "dimentica" velocemente le certezze smentite.

MEMORY_TACTICAL_DECAY       = 0.05
# Decay per episodio degli archi tattici (Layer 2) non confermati.
# Con 0.05: un arco con confidenza iniziale 0.5 scompare dopo ~10 episodi senza conferma.
# Aumentare per un sistema più reattivo ai cambiamenti di mercato.

# ============================================================================
# 6. ORIZZONTE DELLA SIMULAZIONE
#
# Domande al cliente:
#   - Quante settimane per scenario? Un mese (4), un trimestre (13), un anno (52)?
#   - Quale trade-off qualità/velocità LLM è accettabile?
# ============================================================================

EPISODE_LENGTH_WEEKS = 4
# Numero di settimane per episodio.
# 4  = scenario mensile    (~5–15 min con hardware consumer)
# 13 = scenario trimestrale (~20–50 min)
# 52 = scenario annuale    (~80–200 min)

SHORT_TERM_MEMORY_SIZE = 10
# Dimensione massima della sliding window di memoria a breve termine per agente.
# Aumentare per episodi più lunghi (es. 20 per episodi trimestrali).

SHORT_TERM_CONTEXT_SIZE = 5
# Quante voci della memoria a breve termine vengono incluse nel prompt dell'agente.
# Aumentare se gli agenti devono ragionare su pattern multi-settimana più lunghi.

DEFAULT_MODEL = "qwen3:8b"
# Modello LLM di default. Vedere tabella "Modelli supportati" nel README.
# Sostituibile via CLI: python main.py --model qwen3:14b
