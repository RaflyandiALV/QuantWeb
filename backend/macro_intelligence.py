# backend/macro_intelligence.py
"""
MACRO INTELLIGENCE MODULE (Objective 5)
Automated Top-Down Market Screening Engine.

Fetches and analyzes:
- SPX (S&P 500) — via yfinance
- USDT.D (Tether Dominance) — via CoinGecko
- BTC.D (Bitcoin Dominance) — via CoinGecko
- TOTAL3 (Total Crypto MCap excl. BTC & ETH) — computed from CoinGecko
- OTHERS (Altcoin Market Cap) — computed from CoinGecko

Provides:
- Automated Support/Resistance levels
- Strict Regime Logic (BULLISH / BEARISH / NEUTRAL)
"""

import numpy as np
import pandas as pd
import requests
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor
import time

# Lazy import yfinance — will warn if not installed
try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False
    print("⚠️ [MACRO] yfinance not installed. SPX data will be unavailable.")
    print("   Install with: pip install yfinance")


class MacroIntelligence:
    """
    Automated Macro Market Screening Engine.
    Performs top-down analysis across US equity and crypto markets.
    """

    COINGECKO_BASE = "https://api.coingecko.com/api/v3"

    def __init__(self):
        self._cache = {}
        self._cache_ttl = 300  # 5 minute cache for API responses

    # ================================================================
    # INTERNAL: CACHING LAYER
    # ================================================================
    def _get_cached(self, key):
        """Return cached value if still valid."""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return data
        return None

    def _set_cached(self, key, data):
        """Store data in cache."""
        self._cache[key] = (data, time.time())

    # ================================================================
    # 1. SPX (S&P 500) DATA via yfinance
    # ================================================================
    def fetch_spx_data(self, period="3mo"):
        """
        Fetch S&P 500 data via Yahoo Finance.

        Returns:
            dict with price data, premarket status, and trend
        """
        cached = self._get_cached("spx")
        if cached:
            return cached

        if not HAS_YFINANCE:
            return {
                "symbol": "SPX",
                "available": False,
                "error": "yfinance not installed",
                "trend": "UNKNOWN",
                "premarket": "UNKNOWN"
            }

        try:
            spx = yf.Ticker("^GSPC")
            hist = spx.history(period=period, interval="1d")

            if hist.empty:
                return {
                    "symbol": "SPX",
                    "available": False,
                    "error": "No data returned"
                }

            # Calculate SMA20 for trend
            hist['sma_20'] = hist['Close'].rolling(20).mean()
            last = hist.iloc[-1]
            prev = hist.iloc[-2] if len(hist) > 1 else last

            current_price = float(last['Close'])
            sma_20 = float(last['sma_20']) if not pd.isna(last['sma_20']) else current_price
            prev_close = float(prev['Close'])

            # Trend: current > SMA20 = UP, else DOWN
            trend = "UP" if current_price > sma_20 else "DOWN"

            # Premarket proxy: compare today's close vs yesterday's close
            daily_change = ((current_price - prev_close) / prev_close) * 100
            premarket_status = "GREEN" if daily_change > 0 else "RED"

            # Generate price series for charting
            price_series = []
            for idx, row in hist.tail(60).iterrows():
                price_series.append({
                    "date": idx.strftime("%Y-%m-%d"),
                    "close": round(float(row['Close']), 2),
                    "sma_20": round(float(row['sma_20']), 2) if not pd.isna(row['sma_20']) else None
                })

            result = {
                "symbol": "SPX",
                "available": True,
                "current_price": round(current_price, 2),
                "sma_20": round(sma_20, 2),
                "prev_close": round(prev_close, 2),
                "daily_change_pct": round(daily_change, 2),
                "trend": trend,
                "premarket": premarket_status,
                "price_series": price_series
            }
            self._set_cached("spx", result)
            return result

        except Exception as e:
            print(f"⚠️ [MACRO] SPX fetch error: {e}")
            return {
                "symbol": "SPX",
                "available": False,
                "error": str(e),
                "trend": "UNKNOWN",
                "premarket": "UNKNOWN"
            }

    # ================================================================
    # 2. CRYPTO DOMINANCE DATA via CoinGecko
    # ================================================================
    def fetch_dominance_data(self):
        """
        Fetch BTC.D and USDT dominance from CoinGecko global endpoint.

        Returns:
            dict with current dominance values and trends
        """
        cached = self._get_cached("dominance")
        if cached:
            return cached

        try:
            # CoinGecko Global endpoint — no API key needed
            resp = requests.get(
                f"{self.COINGECKO_BASE}/global",
                timeout=15,
                headers={"Accept": "application/json"}
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})

            market_cap_pct = data.get("market_cap_percentage", {})

            btc_dominance = market_cap_pct.get("btc", 0)
            eth_dominance = market_cap_pct.get("eth", 0)
            usdt_dominance = market_cap_pct.get("usdt", 0)

            total_market_cap = data.get("total_market_cap", {}).get("usd", 0)
            total_volume_24h = data.get("total_volume", {}).get("usd", 0)

            # Market cap change 24h
            mcap_change_24h = data.get("market_cap_change_percentage_24h_usd", 0)

            result = {
                "btc_dominance": round(btc_dominance, 2),
                "eth_dominance": round(eth_dominance, 2),
                "usdt_dominance": round(usdt_dominance, 2),
                "total_market_cap_usd": total_market_cap,
                "total_volume_24h_usd": total_volume_24h,
                "mcap_change_24h_pct": round(mcap_change_24h, 2),
                "available": True
            }
            self._set_cached("dominance", result)
            return result

        except Exception as e:
            print(f"⚠️ [MACRO] CoinGecko dominance error: {e}")
            return {
                "btc_dominance": 0,
                "usdt_dominance": 0,
                "available": False,
                "error": str(e)
            }

    # ================================================================
    # 3. TOTAL3 & OTHERS (Computed from CoinGecko)
    # ================================================================
    def fetch_total3_and_others(self):
        """
        Compute TOTAL3 (Total MCap excl. BTC & ETH) and OTHERS (Altcoin MCap).
        Uses CoinGecko market data for top coins.

        Returns:
            dict with TOTAL3, OTHERS values and trends
        """
        cached = self._get_cached("total3_others")
        if cached:
            return cached

        try:
            # Get dominance data first
            dom = self.fetch_dominance_data()
            if not dom.get("available"):
                return {"available": False, "error": "Dominance data unavailable"}

            total_mcap = dom.get("total_market_cap_usd", 0)
            btc_dom = dom.get("btc_dominance", 0)
            eth_dom = dom.get("eth_dominance", 0)

            # TOTAL3 = Total MCap - BTC MCap - ETH MCap
            btc_mcap = total_mcap * (btc_dom / 100)
            eth_mcap = total_mcap * (eth_dom / 100)
            total3 = total_mcap - btc_mcap - eth_mcap

            # Get top 10 coins to compute OTHERS
            resp = requests.get(
                f"{self.COINGECKO_BASE}/coins/markets",
                params={
                    "vs_currency": "usd",
                    "order": "market_cap_desc",
                    "per_page": 10,
                    "page": 1,
                    "sparkline": False
                },
                timeout=15,
                headers={"Accept": "application/json"}
            )
            resp.raise_for_status()
            top_10 = resp.json()

            top_10_mcap = sum(c.get("market_cap", 0) for c in top_10 if c.get("market_cap"))
            others = total_mcap - top_10_mcap

            # 24h changes for trend detection
            # Use top 10's average price change as a proxy for OTHERS direction
            altcoin_changes = [
                c.get("price_change_percentage_24h", 0)
                for c in top_10[2:]  # Skip BTC and ETH
                if c.get("price_change_percentage_24h") is not None
            ]
            avg_alt_change_24h = np.mean(altcoin_changes) if altcoin_changes else 0

            result = {
                "total3": {
                    "value_usd": round(total3, 0),
                    "pct_of_total": round(((total3 / total_mcap) * 100) if total_mcap > 0 else 0, 2),
                    "trend": "UP" if avg_alt_change_24h > 0 else "DOWN"
                },
                "others": {
                    "value_usd": round(others, 0),
                    "pct_of_total": round(((others / total_mcap) * 100) if total_mcap > 0 else 0, 2),
                    "trend": "UP" if avg_alt_change_24h > 0 else "DOWN"
                },
                "avg_altcoin_change_24h": round(avg_alt_change_24h, 2),
                "available": True
            }
            self._set_cached("total3_others", result)
            return result

        except Exception as e:
            print(f"⚠️ [MACRO] TOTAL3/OTHERS error: {e}")
            return {"available": False, "error": str(e)}

    # ================================================================
    # 4. HISTORICAL DOMINANCE for Trend Detection
    # ================================================================
    def fetch_btc_dominance_history(self, days=30):
        """
        Fetch historical BTC dominance data from CoinGecko.
        Used to determine if BTC.D is trending UP or DOWN.

        Returns:
            dict with trend direction and data points
        """
        cached = self._get_cached("btc_d_history")
        if cached:
            return cached

        try:
            resp = requests.get(
                f"{self.COINGECKO_BASE}/coins/bitcoin/market_chart",
                params={"vs_currency": "usd", "days": days},
                timeout=15,
                headers={"Accept": "application/json"}
            )
            resp.raise_for_status()
            data = resp.json()

            # We use BTC market cap relative to total to derive BTC.D trend
            mcaps = data.get("market_caps", [])
            if len(mcaps) < 5:
                return {"available": False, "error": "Insufficient history"}

            # BTC market cap series
            btc_mcap_series = [m[1] for m in mcaps]

            # Fetch total market cap history
            total_resp = requests.get(
                f"{self.COINGECKO_BASE}/global",
                timeout=15,
                headers={"Accept": "application/json"}
            )
            total_resp.raise_for_status()
            current_total = total_resp.json().get("data", {}).get("total_market_cap", {}).get("usd", 1)

            # Current vs 7 days ago
            if len(btc_mcap_series) >= 7:
                recent_btc = np.mean(btc_mcap_series[-3:])
                week_ago_btc = np.mean(btc_mcap_series[-10:-7]) if len(btc_mcap_series) >= 10 else btc_mcap_series[0]
                btc_d_trend = "UP" if recent_btc > week_ago_btc else "DOWN"
            else:
                btc_d_trend = "UNKNOWN"

            result = {
                "btc_d_trend": btc_d_trend,
                "available": True,
                "data_points": len(btc_mcap_series)
            }
            self._set_cached("btc_d_history", result)
            return result

        except Exception as e:
            print(f"⚠️ [MACRO] BTC.D history error: {e}")
            return {"available": False, "error": str(e), "btc_d_trend": "UNKNOWN"}

    # ================================================================
    # 5. USDT DOMINANCE TREND
    # ================================================================
    def fetch_usdt_dominance_trend(self):
        """
        Determine USDT.D trend (UP or DOWN).
        Uses Tether's market cap history as a proxy.

        Returns:
            dict with USDT.D trend direction
        """
        cached = self._get_cached("usdt_d_trend")
        if cached:
            return cached

        try:
            resp = requests.get(
                f"{self.COINGECKO_BASE}/coins/tether/market_chart",
                params={"vs_currency": "usd", "days": 14},
                timeout=15,
                headers={"Accept": "application/json"}
            )
            resp.raise_for_status()
            data = resp.json()

            mcaps = data.get("market_caps", [])
            if len(mcaps) < 5:
                return {"available": False, "usdt_d_trend": "UNKNOWN"}

            mcap_values = [m[1] for m in mcaps]
            recent = np.mean(mcap_values[-3:])
            earlier = np.mean(mcap_values[:3])

            # USDT MCap increasing = money flowing into stablecoins = USDT.D UP (bearish for crypto)
            trend = "UP" if recent > earlier * 1.005 else ("DOWN" if recent < earlier * 0.995 else "FLAT")

            result = {
                "usdt_d_trend": trend,
                "usdt_mcap_recent": round(recent, 0),
                "usdt_mcap_14d_ago": round(earlier, 0),
                "available": True
            }
            self._set_cached("usdt_d_trend", result)
            return result

        except Exception as e:
            print(f"⚠️ [MACRO] USDT.D trend error: {e}")
            return {"available": False, "usdt_d_trend": "UNKNOWN", "error": str(e)}

    # ================================================================
    # 6. AUTOMATED SUPPORT / RESISTANCE
    # ================================================================
    def compute_support_resistance(self, price_series, window=20):
        """
        Automatically identify horizontal Support and Resistance levels
        using rolling max/min and pivot points.

        Args:
            price_series: list of dicts with 'close', 'high', 'low' keys
                          OR a pandas DataFrame with those columns
            window: Rolling window for level detection (default: 20)

        Returns:
            list of {level, type, strength} dicts
        """
        if isinstance(price_series, list):
            if not price_series:
                return []
            df = pd.DataFrame(price_series)
        else:
            df = price_series.copy()

        if len(df) < window:
            return []

        levels = []

        # Method 1: Rolling Max/Min
        rolling_high = df['close'].rolling(window).max() if 'close' in df.columns else df['Close'].rolling(window).max()
        rolling_low = df['close'].rolling(window).min() if 'close' in df.columns else df['Close'].rolling(window).min()

        # Current resistance = recent rolling high
        if not rolling_high.empty:
            resistance_1 = float(rolling_high.iloc[-1])
            levels.append({
                "level": round(resistance_1, 2),
                "type": "resistance",
                "method": "rolling_max",
                "strength": "STRONG"
            })

        # Current support = recent rolling low
        if not rolling_low.empty:
            support_1 = float(rolling_low.iloc[-1])
            levels.append({
                "level": round(support_1, 2),
                "type": "support",
                "method": "rolling_min",
                "strength": "STRONG"
            })

        # Method 2: Pivot Points (Classic)
        # Pivot = (High + Low + Close) / 3
        if all(col in df.columns for col in ['high', 'low', 'close']):
            h = float(df['high'].iloc[-1])
            l = float(df['low'].iloc[-1])
            c = float(df['close'].iloc[-1])
        elif all(col in df.columns for col in ['High', 'Low', 'Close']):
            h = float(df['High'].iloc[-1])
            l = float(df['Low'].iloc[-1])
            c = float(df['Close'].iloc[-1])
        else:
            return levels

        pivot = (h + l + c) / 3
        r1 = (2 * pivot) - l
        s1 = (2 * pivot) - h
        r2 = pivot + (h - l)
        s2 = pivot - (h - l)

        levels.extend([
            {"level": round(pivot, 2), "type": "pivot", "method": "pivot_point", "strength": "MODERATE"},
            {"level": round(r1, 2), "type": "resistance", "method": "pivot_r1", "strength": "MODERATE"},
            {"level": round(s1, 2), "type": "support", "method": "pivot_s1", "strength": "MODERATE"},
            {"level": round(r2, 2), "type": "resistance", "method": "pivot_r2", "strength": "WEAK"},
            {"level": round(s2, 2), "type": "support", "method": "pivot_s2", "strength": "WEAK"},
        ])

        # Remove duplicates and sort
        seen = set()
        unique_levels = []
        for lv in levels:
            key = f"{lv['level']}_{lv['type']}"
            if key not in seen:
                seen.add(key)
                unique_levels.append(lv)

        unique_levels.sort(key=lambda x: x['level'], reverse=True)
        return unique_levels

    # ================================================================
    # 7. STRICT REGIME EVALUATOR
    # ================================================================
    def evaluate_regime(self):
        """
        Evaluate market regime based on strict conditions:

        BULLISH: USDT.D ↓, BTC.D ↓, TOTAL3 ↑, OTHERS ↑, SPX ↑, Premarket GREEN
        BEARISH: USDT.D ↑, BTC.D ↑, TOTAL3 ↓, OTHERS ↓, SPX ↓, Premarket RED
        Otherwise: NEUTRAL

        Returns:
            dict with regime, indicators breakdown, and confidence
        """
        # Fetch all indicators IN PARALLEL for performance
        with ThreadPoolExecutor(max_workers=5) as pool:
            f_spx = pool.submit(self.fetch_spx_data)
            f_dom = pool.submit(self.fetch_dominance_data)
            f_t3 = pool.submit(self.fetch_total3_and_others)
            f_btc_h = pool.submit(self.fetch_btc_dominance_history)
            f_usdt_t = pool.submit(self.fetch_usdt_dominance_trend)

            spx = f_spx.result()
            dominance = f_dom.result()
            total3_others = f_t3.result()
            btc_d_history = f_btc_h.result()
            usdt_d_trend = f_usdt_t.result()

        # Extract indicator directions
        indicators = {}

        # SPX
        spx_trend = spx.get("trend", "UNKNOWN")
        spx_premarket = spx.get("premarket", "UNKNOWN")
        indicators["spx"] = {
            "value": spx.get("current_price", 0),
            "trend": spx_trend,
            "premarket": spx_premarket,
            "daily_change": spx.get("daily_change_pct", 0),
            "available": spx.get("available", False)
        }

        # USDT.D
        usdt_trend = usdt_d_trend.get("usdt_d_trend", "UNKNOWN")
        indicators["usdt_d"] = {
            "value": dominance.get("usdt_dominance", 0),
            "trend": usdt_trend,
            "available": usdt_d_trend.get("available", False)
        }

        # BTC.D
        btc_trend = btc_d_history.get("btc_d_trend", "UNKNOWN")
        indicators["btc_d"] = {
            "value": dominance.get("btc_dominance", 0),
            "trend": btc_trend,
            "available": btc_d_history.get("available", False)
        }

        # TOTAL3
        total3_trend = total3_others.get("total3", {}).get("trend", "UNKNOWN")
        indicators["total3"] = {
            "value": total3_others.get("total3", {}).get("value_usd", 0),
            "pct_of_total": total3_others.get("total3", {}).get("pct_of_total", 0),
            "trend": total3_trend,
            "available": total3_others.get("available", False)
        }

        # OTHERS
        others_trend = total3_others.get("others", {}).get("trend", "UNKNOWN")
        indicators["others"] = {
            "value": total3_others.get("others", {}).get("value_usd", 0),
            "pct_of_total": total3_others.get("others", {}).get("pct_of_total", 0),
            "trend": others_trend,
            "available": total3_others.get("available", False)
        }

        # === STRICT REGIME LOGIC ===
        # BULLISH: USDT.D DOWN, BTC.D DOWN, TOTAL3 UP, OTHERS UP, SPX UP, Premarket GREEN
        bullish_conditions = {
            "usdt_d_down": usdt_trend == "DOWN",
            "btc_d_down": btc_trend == "DOWN",
            "total3_up": total3_trend == "UP",
            "others_up": others_trend == "UP",
            "spx_up": spx_trend == "UP",
            "premarket_green": spx_premarket == "GREEN"
        }

        # BEARISH: USDT.D UP, BTC.D UP, TOTAL3 DOWN, OTHERS DOWN, SPX DOWN, Premarket RED
        bearish_conditions = {
            "usdt_d_up": usdt_trend == "UP",
            "btc_d_up": btc_trend == "UP",
            "total3_down": total3_trend == "DOWN",
            "others_down": others_trend == "DOWN",
            "spx_down": spx_trend == "DOWN",
            "premarket_red": spx_premarket == "RED"
        }

        bullish_score = sum(1 for v in bullish_conditions.values() if v)
        bearish_score = sum(1 for v in bearish_conditions.values() if v)

        total_conditions = 6

        # Strict: ALL conditions must be met
        if bullish_score == total_conditions:
            regime = "BULLISH"
            confidence = 100
        elif bearish_score == total_conditions:
            regime = "BEARISH"
            confidence = 100
        # Relaxed: 5 out of 6 = leaning
        elif bullish_score >= 5:
            regime = "BULLISH"
            confidence = round((bullish_score / total_conditions) * 100)
        elif bearish_score >= 5:
            regime = "BEARISH"
            confidence = round((bearish_score / total_conditions) * 100)
        else:
            regime = "NEUTRAL"
            confidence = round(max(bullish_score, bearish_score) / total_conditions * 100)

        # S/R levels for SPX
        spx_sr = []
        if spx.get("price_series"):
            spx_sr = self.compute_support_resistance(
                pd.DataFrame(spx["price_series"]).rename(
                    columns={"close": "close"}
                )
            )

        return {
            "regime": regime,
            "confidence": confidence,
            "indicators": indicators,
            "bullish_conditions": bullish_conditions,
            "bearish_conditions": bearish_conditions,
            "bullish_score": f"{bullish_score}/{total_conditions}",
            "bearish_score": f"{bearish_score}/{total_conditions}",
            "spx_support_resistance": spx_sr,
            "recommendation": {
                "direction": "LONG" if regime == "BULLISH" else ("SHORT" if regime == "BEARISH" else "HOLD"),
                "note": f"Market regime is {regime} with {confidence}% confidence. "
                        + ("Execute LONG signals only." if regime == "BULLISH"
                           else "Execute SHORT signals only." if regime == "BEARISH"
                           else "Mixed signals — consider reducing exposure or staying flat.")
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    # ================================================================
    # 8. GET DIRECTION FOR STRATEGY ENGINE
    # ================================================================
    def get_regime_direction(self):
        """
        Simple helper that returns the recommended trade direction
        based on macro regime. Used by the strategy engine.

        Returns:
            str: "LONG", "SHORT", or "BOTH"
        """
        try:
            regime_data = self.evaluate_regime()
            regime = regime_data.get("regime", "NEUTRAL")

            if regime == "BULLISH":
                return "LONG"
            elif regime == "BEARISH":
                return "SHORT"
            else:
                return "BOTH"  # Neutral = allow both directions
        except Exception as e:
            print(f"⚠️ [MACRO] Regime direction error: {e}")
            return "BOTH"  # Safe fallback
