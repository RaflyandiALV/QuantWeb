# backend/ai_brain.py
"""
AI DECISION BRAIN (Gap 3) — Hybrid Mode
Claude 3 Haiku as primary, rule-based mock as fallback.

Receives MarketSnapshot (OHLCV + microstructure features + regime):
→ Returns structured JSON: {decision, confidence, reasoning, entry, sl, tp, rr}

Risk rules encoded as hard constraints in system prompt.
Every decision logged with full reasoning for review.
"""

import os
import json
import time
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Try importing anthropic
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    print("⚠️ [AI BRAIN] anthropic package not installed. Running in MOCK mode.")
    print("   Install with: pip install anthropic")


# =============================================================================
# CONFIGURATION
# =============================================================================

AI_MODEL = "claude-3-haiku-20240307"
AI_MAX_TOKENS = 1024
AI_TEMPERATURE = 0.3  # Low temp for consistent decisions
MIN_CONFIDENCE = 70  # Minimum confidence threshold (%)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_decisions.db")

SYSTEM_PROMPT = """You are QuantTrade AI Analyst — a professional crypto trading analyst focusing on Binance Futures.

ROLE: Analyze market microstructure data and provide ONE clear trading decision.

HARD RULES (NEVER VIOLATE):
1. Risk per trade: MAX 1% of account equity
2. Risk:Reward ratio: MINIMUM 1:2 (prefer 1:3+)
3. Stop loss: MANDATORY on every trade
4. If confidence < 70%, decision MUST be "HOLD" (no trade)
5. Never chase pumps — if price moved >5% in last hour, flagged as chase
6. In EXTREME_BEARISH regime: only SHORT or HOLD allowed
7. If funding rate annualized > 50%: flag as extreme, reduce confidence by 20%

REQUIRED OUTPUT FORMAT (strict JSON):
{
    "decision": "LONG" | "SHORT" | "HOLD",
    "confidence": 0-100,
    "reasoning": "2-3 sentence explanation",
    "entry": price_number or null,
    "stop_loss": price_number or null,
    "take_profit": price_number or null,
    "risk_reward": "1:X.X" or null,
    "risk_factors": ["factor1", "factor2"],
    "timeframe": "15m" | "1h" | "4h" | "1d"
}

ONLY output valid JSON. No markdown, no explanation outside JSON."""


class AIBrain:
    """
    Hybrid AI Decision Engine.
    Primary: Claude 3 Haiku via Anthropic API.
    Fallback: Rule-based mock engine using same feature inputs.
    """

    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self._client = None
        self._init_mode()
        self._init_db()
        self._decision_count = 0
        self._last_call_time = 0

    def _init_mode(self):
        """Detect mode: live (Claude API) or mock (rule-based)."""
        if HAS_ANTHROPIC and self.api_key and self.api_key.startswith("sk-ant-"):
            try:
                self._client = anthropic.Anthropic(api_key=self.api_key)
                self.mode = "live"
                self.model = AI_MODEL
                print(f"[AI BRAIN] ✅ Live mode (Claude 3 Haiku)")
            except Exception as e:
                print(f"[AI BRAIN] ⚠️ Client init failed: {e}. Falling back to mock.")
                self.mode = "mock"
                self.model = "mock-rule-engine"
        else:
            self.mode = "mock"
            self.model = "mock-rule-engine"
            if not HAS_ANTHROPIC:
                print("[AI BRAIN] 🎭 Mock mode (anthropic not installed)")
            elif not self.api_key:
                print("[AI BRAIN] 🎭 Mock mode (no ANTHROPIC_API_KEY)")
            else:
                print("[AI BRAIN] 🎭 Mock mode (invalid key format)")

    def _init_db(self):
        """Create decision log table."""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    confidence REAL,
                    reasoning TEXT,
                    entry_price REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    risk_reward TEXT,
                    risk_factors TEXT,
                    timeframe TEXT,
                    raw_input TEXT,
                    raw_output TEXT
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[AI BRAIN] DB init error: {e}")

    # =========================================================================
    # STATUS
    # =========================================================================

    def get_status(self) -> dict:
        """Return AI service status."""
        return {
            "mode": self.mode,
            "model": self.model,
            "key_present": bool(self.api_key),
            "anthropic_installed": HAS_ANTHROPIC,
            "decisions_made": self._decision_count,
            "min_confidence": MIN_CONFIDENCE,
            "timestamp": datetime.now().isoformat()
        }

    # =========================================================================
    # MAIN DECISION METHOD
    # =========================================================================

    def make_decision(self, symbol: str, market_snapshot: dict) -> dict:
        """
        Main entry point: analyze market data and return trading decision.

        Args:
            symbol: Trading pair (e.g. "BTC-USDT")
            market_snapshot: Dict containing:
                - features: from AlphaFeatureEngine
                - regime: from MacroIntelligence or strategy_core
                - price: current price
                - any other context

        Returns:
            Structured decision dict
        """
        self._decision_count += 1

        if self.mode == "live":
            decision = self._call_claude(symbol, market_snapshot)
        else:
            decision = self._mock_decision(symbol, market_snapshot)

        # Apply minimum confidence filter
        if decision.get("confidence", 0) < MIN_CONFIDENCE and decision.get("decision") != "HOLD":
            decision["original_decision"] = decision["decision"]
            decision["decision"] = "HOLD"
            decision["reasoning"] += f" [OVERRIDDEN: confidence {decision['confidence']}% below {MIN_CONFIDENCE}% threshold]"

        # Log decision
        self._log_decision(symbol, market_snapshot, decision)

        decision["mode"] = self.mode
        decision["symbol"] = symbol
        decision["timestamp"] = datetime.now().isoformat()

        return decision

    # =========================================================================
    # CLAUDE API (LIVE MODE)
    # =========================================================================

    def _call_claude(self, symbol: str, snapshot: dict) -> dict:
        """Call Claude 3 Haiku for trading decision."""
        try:
            # Rate limit: min 1 second between calls
            elapsed = time.time() - self._last_call_time
            if elapsed < 1.0:
                time.sleep(1.0 - elapsed)

            # Build prompt with key metrics only (keep tokens low)
            user_prompt = self._build_prompt(symbol, snapshot)

            response = self._client.messages.create(
                model=AI_MODEL,
                max_tokens=AI_MAX_TOKENS,
                temperature=AI_TEMPERATURE,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}]
            )

            self._last_call_time = time.time()

            # Parse response
            raw_text = response.content[0].text.strip()
            parsed = self._parse_decision(raw_text)
            parsed["_raw_response"] = raw_text

            return parsed

        except Exception as e:
            error_type = type(e).__name__
            print(f"[AI BRAIN] Claude API error ({error_type}): {e}")
            print("[AI BRAIN] Falling back to mock decision...")

            # Fallback to mock on any API error
            decision = self._mock_decision(symbol, snapshot)
            decision["_fallback_reason"] = f"{error_type}: {str(e)[:100]}"
            return decision

    def _build_prompt(self, symbol: str, snapshot: dict) -> str:
        """Build concise prompt from market snapshot (~500 tokens)."""
        features = snapshot.get("features", {})
        signals = snapshot.get("signals", {})
        z_scores = snapshot.get("z_scores", {})
        raw_summary = snapshot.get("raw_data_summary", {})
        price = snapshot.get("price", 0)
        regime = snapshot.get("regime", "UNKNOWN")

        prompt = f"""SYMBOL: {symbol}
CURRENT PRICE: ${price:,.2f}
MARKET REGIME: {regime}

MICROSTRUCTURE FEATURES:
- CVD (Volume Delta): {features.get('cvd', 0):,.0f} (z={z_scores.get('cvd_z', 0):.1f})
- Delta Momentum: {features.get('delta_momentum', 0):.4f}
- Funding Pressure: {features.get('funding_pressure', 0):,.0f} (z={z_scores.get('funding_pressure_z', 0):.1f})
- OI Change Rate: {features.get('oi_change_rate', 0):.4f} (z={z_scores.get('oi_change_rate_z', 0):.1f})
- L/S Skew: {features.get('long_short_skew', 0):.3f} (z={z_scores.get('long_short_skew_z', 0):.1f})
- Taker Imbalance: {features.get('taker_imbalance', 0):.3f} (z={z_scores.get('taker_imbalance_z', 0):.1f})
- Volatility Regime: {features.get('volatility_regime', 0.5):.2f}

RAW DATA:
- Funding: {raw_summary.get('funding_trend', 'NEUTRAL')} ({raw_summary.get('funding_annualized', 0):.1f}% annualized)
- OI Trend: {raw_summary.get('oi_trend', 'UNKNOWN')} ({raw_summary.get('oi_change', 0):+.1f}%)
- L/S Bias: {raw_summary.get('ls_bias', 'BALANCED')}
- Taker: {raw_summary.get('taker_aggression', 'BALANCED')}

FEATURE ENGINE SIGNAL: {signals.get('overall_bias', 'NEUTRAL')} (confidence: {signals.get('confidence', 0)}%)
KEY SIGNALS:
{chr(10).join('- ' + s for s in signals.get('key_signals', ['None detected']))}

Analyze this data and provide your trading decision as JSON."""

        return prompt

    def _parse_decision(self, raw_text: str) -> dict:
        """Parse Claude's JSON response into decision dict."""
        try:
            # Try direct JSON parse
            decision = json.loads(raw_text)
            return self._validate_decision(decision)
        except json.JSONDecodeError:
            # Try extracting JSON from response
            try:
                start = raw_text.index('{')
                end = raw_text.rindex('}') + 1
                decision = json.loads(raw_text[start:end])
                return self._validate_decision(decision)
            except (ValueError, json.JSONDecodeError):
                return {
                    "decision": "HOLD",
                    "confidence": 0,
                    "reasoning": f"Failed to parse AI response: {raw_text[:200]}",
                    "entry": None,
                    "stop_loss": None,
                    "take_profit": None,
                    "risk_reward": None,
                    "risk_factors": ["parse_error"],
                    "timeframe": "1h"
                }

    def _validate_decision(self, decision: dict) -> dict:
        """Ensure decision has all required fields and valid values."""
        valid_decisions = {"LONG", "SHORT", "HOLD"}
        if decision.get("decision") not in valid_decisions:
            decision["decision"] = "HOLD"

        decision.setdefault("confidence", 50)
        decision.setdefault("reasoning", "No reasoning provided")
        decision.setdefault("entry", None)
        decision.setdefault("stop_loss", None)
        decision.setdefault("take_profit", None)
        decision.setdefault("risk_reward", None)
        decision.setdefault("risk_factors", [])
        decision.setdefault("timeframe", "1h")

        # Clamp confidence to 0-100
        decision["confidence"] = max(0, min(100, decision["confidence"]))

        return decision

    # =========================================================================
    # MOCK DECISION ENGINE (FALLBACK)
    # =========================================================================

    def _mock_decision(self, symbol: str, snapshot: dict) -> dict:
        """
        Rule-based mock decision engine.
        Uses the same feature inputs as Claude but with deterministic rules.
        """
        features = snapshot.get("features", {})
        signals = snapshot.get("signals", {})
        price = snapshot.get("price", 0)
        regime = snapshot.get("regime", "UNKNOWN")

        overall_bias = signals.get("overall_bias", "NEUTRAL")
        feature_confidence = signals.get("confidence", 0)
        score = signals.get("score", 0)

        # --- Decision Logic ---
        decision = "HOLD"
        confidence = 50
        reasoning_parts = []
        risk_factors = []

        # Rule 1: Regime check
        if "EXTREME_BEARISH" in str(regime) or "BEARISH" in str(regime):
            if overall_bias == "BEARISH":
                decision = "SHORT"
                confidence += 15
                reasoning_parts.append(f"Market regime is {regime} and microstructure confirms bearish pressure")
            else:
                decision = "HOLD"
                reasoning_parts.append(f"Market regime is {regime} — waiting for clearer setup")
                risk_factors.append("bearish_regime")
        elif "BULLISH" in str(regime):
            if overall_bias == "BULLISH":
                decision = "LONG"
                confidence += 15
                reasoning_parts.append(f"Market regime is {regime} and buyers are in control")
            elif overall_bias == "BEARISH":
                decision = "HOLD"
                reasoning_parts.append("Conflicting signals: bullish regime but bearish microstructure")
                risk_factors.append("conflicting_signals")

        # Rule 2: Feature-based adjustments
        cvd = features.get("cvd", 0)
        funding_pressure = features.get("funding_pressure", 0)
        ls_skew = features.get("long_short_skew", 0)
        taker_imb = features.get("taker_imbalance", 0)

        if decision != "HOLD":
            # Boost confidence with confirming features
            if decision == "LONG" and cvd > 0 and taker_imb > 0:
                confidence += 10
                reasoning_parts.append("buyers dominating with positive CVD and taker imbalance")
            elif decision == "SHORT" and cvd < 0 and taker_imb < 0:
                confidence += 10
                reasoning_parts.append("sellers dominating with negative CVD and taker imbalance")

            # Contrarian warning: crowded positioning
            if ls_skew > 0.3 and decision == "LONG":
                confidence -= 10
                risk_factors.append("crowded_longs")
                reasoning_parts.append("⚠️ Long positioning crowded — reduced confidence")
            elif ls_skew < -0.3 and decision == "SHORT":
                confidence -= 10
                risk_factors.append("crowded_shorts")
                reasoning_parts.append("⚠️ Short positioning crowded — reduced confidence")

        # Rule 3: If still HOLD with NEUTRAL, check if features are strong enough
        if decision == "HOLD" and overall_bias != "NEUTRAL":
            if feature_confidence >= 40:
                direction = "LONG" if overall_bias == "BULLISH" else "SHORT"
                decision = direction
                confidence = 50 + feature_confidence // 2
                reasoning_parts.append(f"Features suggest {direction} with moderate conviction")

        # Cap confidence
        confidence = max(0, min(95, confidence))

        # --- Entry/SL/TP Calculation ---
        entry = None
        sl = None
        tp = None
        rr = None

        if price and price > 0 and decision != "HOLD":
            entry = price
            if decision == "LONG":
                sl = round(price * 0.98, 2)   # 2% stop
                tp = round(price * 1.06, 2)   # 6% target (1:3 RR)
            elif decision == "SHORT":
                sl = round(price * 1.02, 2)   # 2% stop above
                tp = round(price * 0.94, 2)   # 6% target below
            rr = "1:3.0"

        reasoning = ". ".join(reasoning_parts) if reasoning_parts else "Insufficient signal strength for a clear trade."

        return {
            "decision": decision,
            "confidence": confidence,
            "reasoning": f"[MOCK] {reasoning}",
            "entry": entry,
            "stop_loss": sl,
            "take_profit": tp,
            "risk_reward": rr,
            "risk_factors": risk_factors,
            "timeframe": "1h"
        }

    # =========================================================================
    # DECISION LOGGING
    # =========================================================================

    def _log_decision(self, symbol: str, snapshot: dict, decision: dict):
        """Log every decision to SQLite for audit trail."""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("""
                INSERT INTO ai_decisions
                (timestamp, symbol, mode, decision, confidence, reasoning,
                 entry_price, stop_loss, take_profit, risk_reward,
                 risk_factors, timeframe, raw_input, raw_output)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                symbol,
                self.mode,
                decision.get("decision", "HOLD"),
                decision.get("confidence", 0),
                decision.get("reasoning", ""),
                decision.get("entry"),
                decision.get("stop_loss"),
                decision.get("take_profit"),
                decision.get("risk_reward"),
                json.dumps(decision.get("risk_factors", [])),
                decision.get("timeframe", "1h"),
                json.dumps(snapshot, default=str)[:2000],  # Truncate large snapshots
                json.dumps(decision, default=str)[:2000]
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[AI BRAIN] Decision log error: {e}")

    def get_decision_history(self, symbol: str = None, limit: int = 50) -> list:
        """Retrieve decision history from database."""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row

            if symbol:
                rows = conn.execute(
                    "SELECT * FROM ai_decisions WHERE symbol = ? ORDER BY id DESC LIMIT ?",
                    (symbol, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM ai_decisions ORDER BY id DESC LIMIT ?",
                    (limit,)
                ).fetchall()

            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"[AI BRAIN] History fetch error: {e}")
            return []

    # =========================================================================
    # GENERAL ANALYSIS (for AI Insights panel)
    # =========================================================================

    def analyze_context(self, context: str, data: dict) -> dict:
        """
        General-purpose analysis for the AI Insights frontend panel.

        Args:
            context: "market" | "signal" | "portfolio" | "risk"
            data: Relevant data for the context

        Returns:
            { insight: str, mode: str, context: str, timestamp: str }
        """
        if self.mode == "live":
            insight = self._claude_analyze_context(context, data)
        else:
            insight = self._mock_analyze_context(context, data)

        return {
            "insight": insight,
            "mode": self.mode,
            "context": context,
            "timestamp": datetime.now().isoformat()
        }

    def _claude_analyze_context(self, context: str, data: dict) -> str:
        """Use Claude for general context analysis."""
        try:
            context_prompts = {
                "market": "Analyze this market regime data and provide a 3-5 sentence insight about current conditions and what traders should watch for.",
                "signal": "Analyze this trading signal data and provide a 3-5 sentence assessment of signal quality and actionability.",
                "portfolio": "Analyze this portfolio data and provide a 3-5 sentence health assessment with recommendations.",
                "risk": "Analyze this risk data and provide a 3-5 sentence risk assessment with key warnings."
            }

            system = "You are QuantTrade AI Analyst. Provide concise, actionable insights in 3-5 sentences. Be specific with numbers when available."
            prompt = f"{context_prompts.get(context, 'Analyze this data.')}\n\nData:\n{json.dumps(data, indent=2, default=str)[:1500]}"

            response = self._client.messages.create(
                model=AI_MODEL,
                max_tokens=300,
                temperature=0.4,
                system=system,
                messages=[{"role": "user", "content": prompt}]
            )

            return response.content[0].text.strip()

        except Exception as e:
            print(f"[AI BRAIN] Context analysis error: {e}")
            return self._mock_analyze_context(context, data)

    def _mock_analyze_context(self, context: str, data: dict) -> str:
        """Generate mock insights based on context and data values."""
        if context == "market":
            regime = data.get("regime", data.get("condition", "UNKNOWN"))
            confidence = data.get("confidence", data.get("score", 50))
            return (
                f"[MOCK] Market regime is currently **{regime}** with {confidence}% confidence. "
                f"Based on cross-asset analysis, capital flows suggest "
                f"{'risk-on appetite with potential for continued upside' if 'BULL' in str(regime) else 'risk-off sentiment with defensive positioning recommended' if 'BEAR' in str(regime) else 'mixed signals — a wait-and-see approach is prudent'}. "
                f"Key indicators to watch: BTC dominance trend, funding rates, and taker buy/sell ratio for early directional clues."
            )

        elif context == "signal":
            symbol = data.get("symbol", "UNKNOWN")
            win_rate = data.get("win_rate", 0)
            strategy = data.get("strategy", "AUTO")
            return (
                f"[MOCK] Signal analysis for **{symbol}** using {strategy} strategy shows "
                f"a historical win rate of {win_rate:.1f}%. "
                f"{'This is above the 60% threshold — consider this a quality setup.' if win_rate >= 60 else 'This is below the ideal threshold — exercise caution and reduce position size.'} "
                f"Validate with microstructure data (CVD, funding rate) before entering."
            )

        elif context == "portfolio":
            total = data.get("total_value", data.get("usdt_balance", 0))
            positions = data.get("positions_count", data.get("open_positions", 0))
            return (
                f"[MOCK] Portfolio total value: **${total:,.2f}** across {positions} positions. "
                f"{'Portfolio is well-diversified.' if positions >= 3 else 'Consider adding more positions for better diversification.'} "
                f"Recommendation: Maintain maximum 20% allocation per single position and keep at least 30% in stablecoins as dry powder."
            )

        elif context == "risk":
            drawdown = data.get("max_drawdown", data.get("current_drawdown", 0))
            exposure = data.get("exposure_pct", data.get("total_exposure", 0))
            return (
                f"[MOCK] Current max drawdown: **{drawdown:.1f}%** | Portfolio exposure: **{exposure:.1f}%**. "
                f"{'⚠️ Drawdown exceeds 10% — consider reducing exposure.' if drawdown > 10 else '✅ Risk levels within acceptable parameters.'} "
                f"Ensure stop losses are set on all active positions and monitor funding rates for overnight risk."
            )

        return "[MOCK] Insufficient data for analysis. Please provide more market context."


# =============================================================================
# STANDALONE TEST
# =============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("AI DECISION BRAIN — Standalone Test")
    print("=" * 60)

    brain = AIBrain()

    print(f"\n📊 Status: {json.dumps(brain.get_status(), indent=2)}")

    # Test with mock data
    test_snapshot = {
        "features": {
            "cvd": 150000,
            "delta_momentum": 0.0025,
            "funding_pressure": 50000,
            "oi_change_rate": 0.03,
            "long_short_skew": 0.15,
            "taker_imbalance": 0.12,
            "volatility_regime": 0.6
        },
        "z_scores": {
            "cvd_z": 1.2,
            "funding_pressure_z": 0.5,
            "oi_change_rate_z": 0.8,
            "long_short_skew_z": 0.3,
            "taker_imbalance_z": 0.9
        },
        "signals": {
            "overall_bias": "BULLISH",
            "confidence": 65,
            "score": 35,
            "key_signals": [
                "📈 Buyers dominating with increasing momentum",
                "💰 New money entering + buyers aggressive"
            ]
        },
        "raw_data_summary": {
            "funding_trend": "POSITIVE",
            "funding_annualized": 12.5,
            "oi_trend": "INCREASING",
            "oi_change": 3.2,
            "ls_bias": "BALANCED",
            "taker_aggression": "BUYERS_AGGRESSIVE"
        },
        "price": 67500.00,
        "regime": "BULLISH"
    }

    print(f"\n🧠 Making decision for BTC-USDT...")
    decision = brain.make_decision("BTC-USDT", test_snapshot)
    print(f"\n📋 Decision: {json.dumps(decision, indent=2, default=str)}")

    # Test context analysis
    print(f"\n💡 Testing context analysis (market)...")
    insight = brain.analyze_context("market", {"regime": "BULLISH", "confidence": 75})
    print(f"   Insight: {insight['insight']}")

    print("\n✅ AI Brain test completed!")
