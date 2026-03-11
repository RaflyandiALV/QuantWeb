# backend/alpha_features.py
"""
ALPHA FEATURE ENGINE v2 (Gap 2)
Computes derived features from raw microstructure data (alpha_data.py).

Features:
- CVD (Cumulative Volume Delta)      → Price-volume divergence
- Delta Momentum                     → Acceleration of buying/selling
- Funding Pressure                   → Dollar cost of holding position
- OI Change Rate                     → New money entering/exiting
- Long/Short Skew                    → Crowd positioning extreme
- Taker Imbalance                    → Smart money direction
- Volatility Regime                  → High/Low vol environment

All features normalized to z-scores for AI consumption.
"""

import numpy as np
from datetime import datetime
from alpha_data import AlphaDataProvider


class AlphaFeatureEngine:
    """
    Transforms raw microstructure data into normalized trading features.
    Output is a MarketSnapshot dict ready for AI Brain consumption.
    """

    def __init__(self, alpha_provider: AlphaDataProvider = None):
        self.provider = alpha_provider or AlphaDataProvider()
        # Rolling history for z-score computation (in-memory)
        self._feature_history = {}  # {symbol: {feature_name: [values]}}
        self._max_history = 100  # Keep last 100 snapshots per symbol

    # =========================================================================
    # INDIVIDUAL FEATURE COMPUTATIONS
    # =========================================================================

    def compute_cvd(self, agg_trades: dict) -> float:
        """
        Cumulative Volume Delta = buy_volume - sell_volume.
        Positive → buyers dominating, Negative → sellers dominating.
        """
        return agg_trades.get("delta", 0)

    def compute_delta_momentum(self, agg_trades: dict, symbol: str) -> float:
        """
        Delta Momentum = slope of CVD over recent snapshots.
        Uses linear regression on stored CVD history.
        Positive slope → buying accelerating, Negative → selling accelerating.
        """
        cvd = self.compute_cvd(agg_trades)
        history = self._get_feature_history(symbol, "cvd")
        history.append(cvd)
        self._set_feature_history(symbol, "cvd", history)

        if len(history) < 3:
            return 0.0

        # Linear regression slope on last 10 CVD values
        recent = history[-10:]
        x = np.arange(len(recent))
        try:
            slope, _ = np.polyfit(x, recent, 1)
            return float(slope)
        except Exception:
            return 0.0

    def compute_funding_pressure(self, funding: dict, oi: dict) -> float:
        """
        Funding Pressure = funding_rate × open_interest_value.
        Represents the dollar cost of holding the market's net position.
        High positive → expensive to be long → potential squeeze.
        High negative → expensive to be short → potential short squeeze.
        """
        rate = funding.get("current_rate", 0)
        oi_value = oi.get("current_oi_value", 0)
        return rate * oi_value

    def compute_oi_change_rate(self, oi: dict) -> float:
        """
        OI Change Rate = ΔOI / OI as percentage.
        Positive → new money entering, Negative → positions closing.
        """
        return oi.get("change_pct", 0) / 100.0  # Convert from % to decimal

    def compute_long_short_skew(self, ls_ratio: dict) -> float:
        """
        Long/Short Skew = (long_ratio - 0.5) × 2.
        Range: -1 to +1.
        +1 → everyone long (contrarian bearish), -1 → everyone short (contrarian bullish).
        """
        long_ratio = ls_ratio.get("long_ratio", 0.5)
        return (long_ratio - 0.5) * 2

    def compute_taker_imbalance(self, taker_vol: dict) -> float:
        """
        Taker Imbalance = (buy_vol - sell_vol) / total_vol.
        Range: -1 to +1.
        Positive → smart money buying, Negative → smart money selling.
        """
        buy = taker_vol.get("buy_vol", 0)
        sell = taker_vol.get("sell_vol", 0)
        total = buy + sell
        if total == 0:
            return 0.0
        return (buy - sell) / total

    def compute_volatility_regime(self, symbol: str, agg_trades: dict) -> float:
        """
        Volatility Regime = percentile rank of current volatility vs history.
        Uses trade size standard deviation as volatility proxy.
        Range: 0 (low vol) to 1 (high vol).
        """
        avg_size = agg_trades.get("avg_trade_size", 0)
        history = self._get_feature_history(symbol, "avg_trade_size")
        history.append(avg_size)
        self._set_feature_history(symbol, "avg_trade_size", history)

        if len(history) < 5:
            return 0.5  # Default to medium vol when insufficient data

        # Percentile rank
        current = history[-1]
        sorted_hist = sorted(history)
        rank = sorted_hist.index(current) if current in sorted_hist else len(sorted_hist) // 2
        return rank / max(len(sorted_hist) - 1, 1)

    # =========================================================================
    # Z-SCORE NORMALIZATION
    # =========================================================================

    def _zscore(self, value: float, history_key: str, symbol: str) -> float:
        """
        Compute z-score of value against its rolling history.
        z = (x - mean) / std
        """
        history = self._get_feature_history(symbol, history_key)
        history.append(value)
        self._set_feature_history(symbol, history_key, history)

        if len(history) < 5:
            return 0.0

        mean = np.mean(history)
        std = np.std(history)
        if std == 0:
            return 0.0
        return float((value - mean) / std)

    # =========================================================================
    # FEATURE HISTORY MANAGEMENT
    # =========================================================================

    def _get_feature_history(self, symbol: str, feature: str) -> list:
        if symbol not in self._feature_history:
            self._feature_history[symbol] = {}
        return self._feature_history[symbol].get(feature, [])

    def _set_feature_history(self, symbol: str, feature: str, values: list):
        if symbol not in self._feature_history:
            self._feature_history[symbol] = {}
        # Trim to max history
        self._feature_history[symbol][feature] = values[-self._max_history:]

    # =========================================================================
    # MASTER: COMPUTE ALL FEATURES
    # =========================================================================

    def compute_all_features(self, symbol: str, raw_data: dict = None) -> dict:
        """
        Compute ALL derived features for a symbol.

        Args:
            symbol: Trading pair (e.g. "BTC-USDT")
            raw_data: Pre-fetched data from AlphaDataProvider.get_full_snapshot().
                      If None, will fetch fresh data.

        Returns:
            {
                symbol: str,
                features: {
                    cvd: float,
                    delta_momentum: float,
                    funding_pressure: float,
                    oi_change_rate: float,
                    long_short_skew: float,
                    taker_imbalance: float,
                    volatility_regime: float
                },
                z_scores: {
                    cvd_z: float,
                    funding_pressure_z: float,
                    oi_change_rate_z: float,
                    long_short_skew_z: float,
                    taker_imbalance_z: float
                },
                signals: {
                    overall_bias: str,       # "BULLISH" / "BEARISH" / "NEUTRAL"
                    confidence: float,       # 0-100
                    key_signals: list[str]
                },
                raw_data_summary: dict,
                timestamp: str
            }
        """
        if raw_data is None:
            raw_data = self.provider.get_full_snapshot(symbol)

        agg = raw_data.get("agg_trades", {})
        funding = raw_data.get("funding", {})
        oi = raw_data.get("open_interest", {})
        ls = raw_data.get("long_short_ratio", {})
        taker = raw_data.get("taker_volume", {})

        # --- Compute raw features ---
        cvd = self.compute_cvd(agg)
        delta_mom = self.compute_delta_momentum(agg, symbol)
        funding_pressure = self.compute_funding_pressure(funding, oi)
        oi_change = self.compute_oi_change_rate(oi)
        ls_skew = self.compute_long_short_skew(ls)
        taker_imb = self.compute_taker_imbalance(taker)
        vol_regime = self.compute_volatility_regime(symbol, agg)

        features = {
            "cvd": round(cvd, 2),
            "delta_momentum": round(delta_mom, 4),
            "funding_pressure": round(funding_pressure, 2),
            "oi_change_rate": round(oi_change, 4),
            "long_short_skew": round(ls_skew, 4),
            "taker_imbalance": round(taker_imb, 4),
            "volatility_regime": round(vol_regime, 4)
        }

        # --- Z-score normalization ---
        z_scores = {
            "cvd_z": round(self._zscore(cvd, "cvd_zscore", symbol), 2),
            "funding_pressure_z": round(self._zscore(funding_pressure, "fp_zscore", symbol), 2),
            "oi_change_rate_z": round(self._zscore(oi_change, "oi_zscore", symbol), 2),
            "long_short_skew_z": round(self._zscore(ls_skew, "ls_zscore", symbol), 2),
            "taker_imbalance_z": round(self._zscore(taker_imb, "ti_zscore", symbol), 2),
        }

        # --- Signal synthesis ---
        signals = self._synthesize_signals(features, z_scores, funding, ls, taker)

        # --- Raw data summary for frontend display ---
        raw_summary = {
            "agg_trades_delta": agg.get("delta_pct", 0),
            "funding_trend": funding.get("trend", "NEUTRAL"),
            "funding_annualized": funding.get("annualized_pct", 0),
            "oi_trend": oi.get("trend", "UNKNOWN"),
            "oi_change": oi.get("change_pct", 0),
            "ls_bias": ls.get("bias", "BALANCED"),
            "taker_aggression": taker.get("aggression", "BALANCED"),
        }

        return {
            "symbol": symbol,
            "features": features,
            "z_scores": z_scores,
            "signals": signals,
            "raw_data_summary": raw_summary,
            "timestamp": datetime.now().isoformat()
        }

    def _synthesize_signals(self, features: dict, z_scores: dict,
                            funding: dict, ls: dict, taker: dict) -> dict:
        """
        Combine individual features into an overall trading signal.
        Uses a weighted scoring system.
        """
        score = 0
        key_signals = []

        # 1. CVD / Delta momentum
        if features["cvd"] > 0 and features["delta_momentum"] > 0:
            score += 20
            key_signals.append("📈 Buyers dominating with increasing momentum")
        elif features["cvd"] < 0 and features["delta_momentum"] < 0:
            score -= 20
            key_signals.append("📉 Sellers dominating with increasing pressure")

        # 2. Funding Rate (contrarian)
        funding_trend = funding.get("trend", "NEUTRAL")
        if funding_trend == "POSITIVE" and features["long_short_skew"] > 0.2:
            score -= 15  # Crowded longs = contrarian bearish
            key_signals.append("⚠️ Crowded longs — funding positive, potential squeeze down")
        elif funding_trend == "NEGATIVE" and features["long_short_skew"] < -0.2:
            score += 15  # Crowded shorts = contrarian bullish
            key_signals.append("🔄 Crowded shorts — potential short squeeze")

        # 3. OI + Taker flow
        if features["oi_change_rate"] > 0.02 and features["taker_imbalance"] > 0.1:
            score += 15
            key_signals.append("💰 New money entering + buyers aggressive")
        elif features["oi_change_rate"] > 0.02 and features["taker_imbalance"] < -0.1:
            score -= 15
            key_signals.append("⚡ New money entering + sellers aggressive")
        elif features["oi_change_rate"] < -0.02:
            key_signals.append("🚪 Positions closing — deleveraging")

        # 4. Taker imbalance
        taker_aggression = taker.get("aggression", "BALANCED")
        if taker_aggression == "BUYERS_AGGRESSIVE":
            score += 10
        elif taker_aggression == "SELLERS_AGGRESSIVE":
            score -= 10

        # 5. Volatility regime
        if features["volatility_regime"] > 0.8:
            key_signals.append("🔥 High volatility regime — increased risk")

        # Overall bias
        if score >= 25:
            bias = "BULLISH"
        elif score <= -25:
            bias = "BEARISH"
        else:
            bias = "NEUTRAL"

        confidence = min(abs(score), 100)

        return {
            "overall_bias": bias,
            "confidence": confidence,
            "score": score,
            "key_signals": key_signals
        }


# =============================================================================
# STANDALONE TEST
# =============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("ALPHA FEATURE ENGINE v2 — Standalone Test")
    print("=" * 60)

    engine = AlphaFeatureEngine()
    symbol = "BTC-USDT"

    print(f"\n--- Computing features for {symbol} ---")
    result = engine.compute_all_features(symbol)

    print("\n📊 Features (Raw):")
    for k, v in result["features"].items():
        print(f"   {k}: {v}")

    print("\n📐 Z-Scores:")
    for k, v in result["z_scores"].items():
        print(f"   {k}: {v}")

    print(f"\n🎯 Signal: {result['signals']['overall_bias']} "
          f"(confidence: {result['signals']['confidence']}%)")

    print("\n💡 Key Signals:")
    for sig in result["signals"]["key_signals"]:
        print(f"   {sig}")

    print("\n📋 Raw Data Summary:")
    for k, v in result["raw_data_summary"].items():
        print(f"   {k}: {v}")

    print("\n✅ Feature engine test completed!")
