# backend/global_market.py
"""
GLOBAL MARKET ANALYSIS MODULE
Tracks cross-asset price changes (%) across multiple timeframes to identify:
- Capital rotation patterns (Risk-On vs Risk-Off)
- Relative strength between asset classes
- Investor preference shifts (Safe Haven vs Growth)

Assets tracked:
- Commodities: Gold (GC=F), Silver (SI=F), Crude Oil (CL=F)
- Equities: S&P 500 (^GSPC), Emerging Markets (EEM)
- Currencies: US Dollar Index (DX-Y.NYB)
- Bonds: US 10Y Treasury Yield (^TNX)
- Crypto: BTC/USD, ETH/USD (via ccxt)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import time
import traceback

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False
    print("⚠️ [GLOBAL] yfinance not installed. Global Market data unavailable.")


# ============================================================
# ASSET REGISTRY
# ============================================================
ASSETS = {
    # --- Commodities ---
    "GOLD": {
        "ticker": "GC=F",
        "label": "Gold (XAU/USD)",
        "category": "COMMODITY",
        "icon": "🥇",
        "color": "#FFD700",
        "description": "Safe haven asset — rises during uncertainty",
    },
    "SILVER": {
        "ticker": "SI=F",
        "label": "Silver (XAG/USD)",
        "category": "COMMODITY",
        "icon": "🥈",
        "color": "#C0C0C0",
        "description": "Industrial + precious metal hybrid",
    },
    "OIL": {
        "ticker": "CL=F",
        "label": "Crude Oil (WTI)",
        "category": "COMMODITY",
        "icon": "🛢️",
        "color": "#8B4513",
        "description": "Energy — demand proxy for global growth",
    },
    # --- Equities ---
    "SPX": {
        "ticker": "^GSPC",
        "label": "S&P 500",
        "category": "EQUITY",
        "icon": "📈",
        "color": "#4CAF50",
        "description": "US large-cap benchmark",
    },
    "EEM": {
        "ticker": "EEM",
        "label": "Emerging Markets ETF",
        "category": "EQUITY",
        "icon": "🌍",
        "color": "#FF9800",
        "description": "Developing economies — risk-on indicator",
    },
    # --- Currencies ---
    "DXY": {
        "ticker": "DX-Y.NYB",
        "label": "US Dollar Index",
        "category": "CURRENCY",
        "icon": "💵",
        "color": "#2196F3",
        "description": "Dollar strength — inverse to risk assets",
    },
    # --- Bonds ---
    "US10Y": {
        "ticker": "^TNX",
        "label": "US 10Y Treasury Yield",
        "category": "BOND",
        "icon": "🏛️",
        "color": "#9C27B0",
        "description": "Risk-free rate — higher yield = tighter liquidity",
    },
    # --- Crypto (fetched via ccxt, not yfinance) ---
    "BTC": {
        "ticker": "BTC-USD",
        "label": "Bitcoin",
        "category": "CRYPTO",
        "icon": "₿",
        "color": "#F7931A",
        "description": "Digital gold — risk-on/risk-off hybrid",
    },
    "ETH": {
        "ticker": "ETH-USD",
        "label": "Ethereum",
        "category": "CRYPTO",
        "icon": "Ξ",
        "color": "#627EEA",
        "description": "Smart contract platform — tech risk-on",
    },
}


class GlobalMarketAnalyzer:
    """
    Cross-asset market analyzer.
    Fetches historical data for 9 asset classes and computes:
    - % price changes across 1D/7D/30D/90D/YTD
    - Rolling correlation matrix
    - Capital rotation regime (RISK_ON / RISK_OFF / MIXED)
    """

    def __init__(self):
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes

    def _get_cached(self, key):
        """Return cached value if still valid."""
        if key in self._cache:
            data, ts = self._cache[key]
            if time.time() - ts < self._cache_ttl:
                return data
        return None

    def _set_cached(self, key, data):
        """Store data in cache."""
        self._cache[key] = (data, time.time())

    def fetch_asset_data(self, asset_key, period="6mo"):
        """
        Fetch historical price data for a single asset via yfinance.

        Args:
            asset_key: Key from ASSETS dict (e.g. 'GOLD', 'SPX')
            period: yfinance period string (e.g. '6mo', '1y')

        Returns:
            DataFrame with date index and 'close' column, or None
        """
        if not HAS_YFINANCE:
            return None

        asset = ASSETS.get(asset_key)
        if not asset:
            return None

        cache_key = f"asset_{asset_key}_{period}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            ticker = yf.Ticker(asset["ticker"])
            hist = ticker.history(period=period)

            if hist is None or hist.empty:
                print(f"⚠️ [GLOBAL] No data for {asset_key} ({asset['ticker']})")
                return None

            df = pd.DataFrame({
                "close": hist["Close"].values,
                "high": hist["High"].values,
                "low": hist["Low"].values,
                "volume": hist["Volume"].values if "Volume" in hist.columns else 0,
            }, index=hist.index)

            df.index = pd.to_datetime(df.index).tz_localize(None)
            df = df.dropna(subset=["close"])

            self._set_cached(cache_key, df)
            return df

        except Exception as e:
            print(f"❌ [GLOBAL] Error fetching {asset_key}: {e}")
            return None

    def compute_pct_changes(self, df):
        """
        Compute % price change over multiple timeframes.

        Returns:
            dict with keys: 1d, 7d, 30d, 90d, ytd, current_price
        """
        if df is None or df.empty or len(df) < 2:
            return {
                "current_price": None,
                "1d": None, "7d": None, "30d": None, "90d": None, "ytd": None
            }

        current_price = float(df["close"].iloc[-1])
        result = {"current_price": round(current_price, 4)}

        # Helper to safely compute % change
        def pct(days_ago):
            if len(df) < days_ago + 1:
                return None
            old_price = float(df["close"].iloc[-(days_ago + 1)])
            if old_price == 0:
                return None
            return round(((current_price - old_price) / old_price) * 100, 2)

        result["1d"] = pct(1)
        result["7d"] = pct(5)     # 5 trading days ≈ 1 week
        result["30d"] = pct(22)   # 22 trading days ≈ 1 month
        result["90d"] = pct(63)   # 63 trading days ≈ 3 months

        # YTD: from Jan 1 of current year
        try:
            year_start = datetime(datetime.now().year, 1, 1)
            ytd_data = df[df.index >= year_start]
            if len(ytd_data) >= 2:
                first_close = float(ytd_data["close"].iloc[0])
                if first_close > 0:
                    result["ytd"] = round(((current_price - first_close) / first_close) * 100, 2)
                else:
                    result["ytd"] = None
            else:
                result["ytd"] = None
        except:
            result["ytd"] = None

        return result

    def get_all_assets_data(self):
        """
        Fetch data and compute % changes for ALL tracked assets.

        Returns:
            dict: {asset_key: {label, category, icon, color, price_changes, ...}}
        """
        cache_key = "all_assets_data"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        results = {}

        for key, meta in ASSETS.items():
            try:
                df = self.fetch_asset_data(key, period="6mo")
                changes = self.compute_pct_changes(df)

                results[key] = {
                    "label": meta["label"],
                    "category": meta["category"],
                    "icon": meta["icon"],
                    "color": meta["color"],
                    "description": meta["description"],
                    "current_price": changes["current_price"],
                    "changes": {
                        "1d": changes["1d"],
                        "7d": changes["7d"],
                        "30d": changes["30d"],
                        "90d": changes["90d"],
                        "ytd": changes["ytd"],
                    }
                }
            except Exception as e:
                print(f"⚠️ [GLOBAL] Skipped {key}: {e}")
                results[key] = {
                    "label": meta["label"],
                    "category": meta["category"],
                    "icon": meta["icon"],
                    "color": meta["color"],
                    "description": meta["description"],
                    "current_price": None,
                    "changes": {"1d": None, "7d": None, "30d": None, "90d": None, "ytd": None}
                }

        self._set_cached(cache_key, results)
        return results

    def compute_correlation_matrix(self, period="3mo"):
        """
        Compute a rolling correlation matrix between all assets.

        Returns:
            dict: {asset1: {asset2: correlation_value, ...}, ...}
        """
        cache_key = f"corr_matrix_{period}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        # Collect close prices for all assets
        closes = {}
        for key in ASSETS:
            df = self.fetch_asset_data(key, period=period)
            if df is not None and not df.empty:
                closes[key] = df["close"]

        if len(closes) < 2:
            return {}

        # Build combined DataFrame and compute correlation
        combined = pd.DataFrame(closes)
        # Forward-fill gaps (different trading schedules)
        combined = combined.ffill().dropna()

        if len(combined) < 10:
            return {}

        # Use daily returns for correlation (more stationary than prices)
        returns = combined.pct_change().dropna()
        corr = returns.corr()

        # Convert to serializable dict
        result = {}
        for col in corr.columns:
            result[col] = {}
            for row in corr.index:
                result[col][row] = round(float(corr.loc[row, col]), 3)

        self._set_cached(cache_key, result)
        return result

    def classify_regime(self, assets_data):
        """
        Classify current global market regime based on cross-asset % changes.

        Logic:
        - RISK_ON: SPX↑ + Crypto↑ + Gold↓ + DXY↓ (investors prefer growth)
        - RISK_OFF: SPX↓ + Crypto↓ + Gold↑ + DXY↑ (investors flee to safety)
        - ROTATION: Mixed signals — selective positioning
        - UNCERTAINTY: Insufficient data

        Returns:
            dict with regime, confidence, signals, interpretation
        """
        if not assets_data:
            return {
                "regime": "UNKNOWN",
                "confidence": 0,
                "signals": {},
                "interpretation": "Insufficient data for regime classification"
            }

        def get_change(key, timeframe="7d"):
            asset = assets_data.get(key, {})
            changes = asset.get("changes", {})
            return changes.get(timeframe)

        # Use 7-day changes for regime detection (balances noise vs relevance)
        spx_7d = get_change("SPX", "7d")
        btc_7d = get_change("BTC", "7d")
        eth_7d = get_change("ETH", "7d")
        gold_7d = get_change("GOLD", "7d")
        dxy_7d = get_change("DXY", "7d")
        eem_7d = get_change("EEM", "7d")
        oil_7d = get_change("OIL", "7d")
        us10y_7d = get_change("US10Y", "7d")

        signals = {}
        risk_on_count = 0
        risk_off_count = 0
        total_signals = 0

        # Signal 1: SPX direction
        if spx_7d is not None:
            total_signals += 1
            if spx_7d > 0.5:
                signals["spx"] = {"direction": "UP", "value": spx_7d, "implication": "RISK_ON"}
                risk_on_count += 1
            elif spx_7d < -0.5:
                signals["spx"] = {"direction": "DOWN", "value": spx_7d, "implication": "RISK_OFF"}
                risk_off_count += 1
            else:
                signals["spx"] = {"direction": "FLAT", "value": spx_7d, "implication": "NEUTRAL"}

        # Signal 2: BTC direction
        if btc_7d is not None:
            total_signals += 1
            if btc_7d > 1.0:
                signals["btc"] = {"direction": "UP", "value": btc_7d, "implication": "RISK_ON"}
                risk_on_count += 1
            elif btc_7d < -1.0:
                signals["btc"] = {"direction": "DOWN", "value": btc_7d, "implication": "RISK_OFF"}
                risk_off_count += 1
            else:
                signals["btc"] = {"direction": "FLAT", "value": btc_7d, "implication": "NEUTRAL"}

        # Signal 3: Gold direction (inverse — rising gold = risk-off)
        if gold_7d is not None:
            total_signals += 1
            if gold_7d > 0.5:
                signals["gold"] = {"direction": "UP", "value": gold_7d, "implication": "RISK_OFF"}
                risk_off_count += 1
            elif gold_7d < -0.5:
                signals["gold"] = {"direction": "DOWN", "value": gold_7d, "implication": "RISK_ON"}
                risk_on_count += 1
            else:
                signals["gold"] = {"direction": "FLAT", "value": gold_7d, "implication": "NEUTRAL"}

        # Signal 4: DXY direction (inverse — rising dollar = risk-off)
        if dxy_7d is not None:
            total_signals += 1
            if dxy_7d > 0.3:
                signals["dxy"] = {"direction": "UP", "value": dxy_7d, "implication": "RISK_OFF"}
                risk_off_count += 1
            elif dxy_7d < -0.3:
                signals["dxy"] = {"direction": "DOWN", "value": dxy_7d, "implication": "RISK_ON"}
                risk_on_count += 1
            else:
                signals["dxy"] = {"direction": "FLAT", "value": dxy_7d, "implication": "NEUTRAL"}

        # Signal 5: EEM vs SPX (Emerging > SPX = risk appetite expanding)
        if eem_7d is not None and spx_7d is not None:
            total_signals += 1
            eem_spread = eem_7d - spx_7d
            if eem_spread > 1.0:
                signals["eem_vs_spx"] = {"direction": "EEM_LEADING", "value": round(eem_spread, 2), "implication": "RISK_ON"}
                risk_on_count += 1
            elif eem_spread < -1.0:
                signals["eem_vs_spx"] = {"direction": "SPX_LEADING", "value": round(eem_spread, 2), "implication": "RISK_OFF"}
                risk_off_count += 1
            else:
                signals["eem_vs_spx"] = {"direction": "INLINE", "value": round(eem_spread, 2), "implication": "NEUTRAL"}

        # Signal 6: 10Y Yield direction
        if us10y_7d is not None:
            total_signals += 1
            if us10y_7d > 2.0:
                signals["us10y"] = {"direction": "RISING", "value": us10y_7d, "implication": "RISK_OFF"}
                risk_off_count += 1
            elif us10y_7d < -2.0:
                signals["us10y"] = {"direction": "FALLING", "value": us10y_7d, "implication": "RISK_ON"}
                risk_on_count += 1
            else:
                signals["us10y"] = {"direction": "STABLE", "value": us10y_7d, "implication": "NEUTRAL"}

        # === REGIME CLASSIFICATION ===
        if total_signals == 0:
            regime = "UNKNOWN"
            confidence = 0
            interpretation = "No data available for regime classification."
        elif risk_on_count >= 4:
            regime = "RISK_ON"
            confidence = min(95, int((risk_on_count / total_signals) * 100))
            interpretation = "Capital flowing into growth assets. Investors prefer equities + crypto over safe havens. Favorable for LONG positions."
        elif risk_off_count >= 4:
            regime = "RISK_OFF"
            confidence = min(95, int((risk_off_count / total_signals) * 100))
            interpretation = "Capital rotating into safe havens (Gold, Dollar, Bonds). Risk assets under pressure. Consider SHORT or CASH."
        elif abs(risk_on_count - risk_off_count) <= 1:
            regime = "MIXED"
            confidence = 40
            interpretation = "Conflicting signals across asset classes. Markets uncertain about direction. Selective positioning recommended."
        elif risk_on_count > risk_off_count:
            regime = "LEANING_RISK_ON"
            confidence = min(75, int((risk_on_count / total_signals) * 100))
            interpretation = "Slightly more risk-on than risk-off. Growth assets favored but not unanimously."
        else:
            regime = "LEANING_RISK_OFF"
            confidence = min(75, int((risk_off_count / total_signals) * 100))
            interpretation = "Slightly more risk-off signals. Caution warranted but not full defensive mode."

        return {
            "regime": regime,
            "confidence": confidence,
            "risk_on_count": risk_on_count,
            "risk_off_count": risk_off_count,
            "total_signals": total_signals,
            "signals": signals,
            "interpretation": interpretation,
        }

    def get_full_analysis(self):
        """
        Master method: returns everything for the frontend.

        Returns:
            dict with: assets, regime, correlation, timestamp
        """
        cache_key = "full_analysis"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        print("🌍 [GLOBAL] Computing full global market analysis...")

        # 1. Get all asset price data + % changes
        assets_data = self.get_all_assets_data()

        # 2. Classify regime
        regime = self.classify_regime(assets_data)

        # 3. Compute correlation matrix
        correlation = self.compute_correlation_matrix(period="3mo")

        # 4. Generate cross-asset insights
        insights = self._generate_insights(assets_data, regime)

        result = {
            "assets": assets_data,
            "regime": regime,
            "correlation": correlation,
            "insights": insights,
            "timestamp": datetime.now().isoformat(),
        }

        self._set_cached(cache_key, result)
        return result

    def _generate_insights(self, assets_data, regime):
        """
        Generate human-readable insights about capital rotation.
        """
        insights = []

        def get_change(key, tf="7d"):
            a = assets_data.get(key, {})
            return a.get("changes", {}).get(tf)

        # Insight 1: Gold vs Crypto divergence
        gold_7d = get_change("GOLD", "7d")
        btc_7d = get_change("BTC", "7d")
        if gold_7d is not None and btc_7d is not None:
            if gold_7d > 1 and btc_7d < -1:
                insights.append({
                    "type": "WARNING",
                    "title": "Gold↑ / Crypto↓ Divergence",
                    "message": f"Gold +{gold_7d}% vs BTC {btc_7d}% (7D). Classic risk-off rotation — capital fleeing to safe havens.",
                    "impact": "BEARISH_CRYPTO"
                })
            elif gold_7d < -1 and btc_7d > 1:
                insights.append({
                    "type": "BULLISH",
                    "title": "Crypto Leading, Gold Lagging",
                    "message": f"BTC +{btc_7d}% vs Gold {gold_7d}% (7D). Risk appetite strong — crypto attracting capital over traditional safe havens.",
                    "impact": "BULLISH_CRYPTO"
                })

        # Insight 2: SPX vs EEM spread
        spx_7d = get_change("SPX", "7d")
        eem_7d = get_change("EEM", "7d")
        if spx_7d is not None and eem_7d is not None:
            spread = eem_7d - spx_7d
            if spread > 2:
                insights.append({
                    "type": "INFO",
                    "title": "Emerging Markets Outpacing US",
                    "message": f"EEM +{eem_7d}% vs SPX +{spx_7d}% (7D). Capital rotating into higher-risk/higher-reward emerging economies.",
                    "impact": "RISK_ON"
                })
            elif spread < -2:
                insights.append({
                    "type": "INFO",
                    "title": "US Equities Dominating",
                    "message": f"SPX +{spx_7d}% vs EEM {eem_7d}% (7D). Flight to quality — investors prefer established US markets.",
                    "impact": "CAUTIOUS"
                })

        # Insight 3: DXY + Crypto inverse correlation check
        dxy_7d = get_change("DXY", "7d")
        if dxy_7d is not None and btc_7d is not None:
            if dxy_7d > 0.5 and btc_7d > 2:
                insights.append({
                    "type": "UNUSUAL",
                    "title": "DXY↑ + BTC↑ Anomaly",
                    "message": f"Dollar +{dxy_7d}% AND Bitcoin +{btc_7d}% (7D). Unusual — normally inversely correlated. Watch for breakout or reversal.",
                    "impact": "WATCH"
                })

        # Insight 4: Oil as growth proxy
        oil_7d = get_change("OIL", "7d")
        if oil_7d is not None:
            if oil_7d > 3:
                insights.append({
                    "type": "INFO",
                    "title": "Oil Surging",
                    "message": f"Crude Oil +{oil_7d}% (7D). Rising energy prices signal either demand growth or supply disruption. Watch inflation implications.",
                    "impact": "INFLATIONARY"
                })
            elif oil_7d < -5:
                insights.append({
                    "type": "WARNING",
                    "title": "Oil Crash",
                    "message": f"Crude Oil {oil_7d}% (7D). Demand destruction signal — potential recession indicator.",
                    "impact": "DEFLATIONARY"
                })

        # Insight 5: 10Y Yield spike
        us10y_7d = get_change("US10Y", "7d")
        if us10y_7d is not None:
            if us10y_7d > 5:
                insights.append({
                    "type": "WARNING",
                    "title": "Treasury Yields Spiking",
                    "message": f"10Y Yield +{us10y_7d}% (7D). Liquidity tightening — headwind for risk assets including crypto.",
                    "impact": "BEARISH"
                })

        return insights
