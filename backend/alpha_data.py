# backend/alpha_data.py
"""
ALPHA DATA PIPELINE (Gap 1)
Microstructure data from Binance Futures API (/fapi/v1/).

Fetches:
- aggTrades      → Buyer/Seller aggressor (real-time delta)
- Funding Rate   → Market positioning bias (crowded longs/shorts)
- Open Interest  → Total leverage in market
- Long/Short Ratio → Retail sentiment
- Taker Buy/Sell Vol → Smart money aggression

Uses ccxt Futures mode + direct REST for data not in ccxt.
"""

import ccxt
import os
import time
import requests
import numpy as np
import urllib3
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Suppress SSL warnings for local dev (Windows/Anaconda certificate issue)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

BINANCE_FAPI_BASE = "https://fapi.binance.com"
CACHE_TTL_SECONDS = 300  # 5-minute cache


class AlphaDataProvider:
    """
    Fetches microstructure data from Binance Futures API.
    Provides raw data for AlphaFeatureEngine consumption.
    """

    def __init__(self):
        self.api_key = os.getenv("BINANCE_API_KEY")
        self.api_secret = os.getenv("BINANCE_SECRET_KEY")
        self._cache = {}

        # ccxt exchange instance (Futures mode)
        try:
            self.exchange = ccxt.binance({
                'apiKey': self.api_key,
                'secret': self.api_secret,
                'enableRateLimit': True,
                'options': {'defaultType': 'future'},
                'timeout': 30000,
            })
            self._exchange_ready = True
            print("[ALPHA DATA] Provider initialized (Binance Futures)")
        except Exception as e:
            print(f"[ALPHA DATA] Exchange init failed: {e}")
            self._exchange_ready = False

    # =========================================================================
    # CACHE HELPERS
    # =========================================================================

    def _get_cached(self, key):
        """Return cached value if still valid."""
        if key in self._cache:
            data, ts = self._cache[key]
            if time.time() - ts < CACHE_TTL_SECONDS:
                return data
        return None

    def _set_cached(self, key, data):
        """Store data in cache."""
        self._cache[key] = (data, time.time())

    def _normalize_symbol(self, symbol: str) -> str:
        """Convert 'BTC-USDT' → 'BTCUSDT' for Binance Futures API."""
        return symbol.replace("-", "").replace("/", "")

    def _ccxt_symbol(self, symbol: str) -> str:
        """Convert 'BTC-USDT' → 'BTC/USDT:USDT' for ccxt futures."""
        base = symbol.replace("-", "/")
        if ":USDT" not in base:
            base = base + ":USDT" if "USDT" in base else base
        return base

    # =========================================================================
    # 1. AGGREGATED TRADES → Buy/Sell Delta
    # =========================================================================

    def fetch_agg_trades(self, symbol: str, limit: int = 1000) -> dict:
        """
        Fetch recent aggregated trades from Binance Futures.
        Separates buyer-initiated vs seller-initiated trades.

        Returns:
            {
                total_trades: int,
                buy_volume: float,
                sell_volume: float,
                buy_count: int,
                sell_count: int,
                delta: float,          # buy_vol - sell_vol
                delta_pct: float,      # delta as % of total
                avg_trade_size: float,
                large_trades: int,     # trades > 2x average
                timestamp: str
            }
        """
        cache_key = f"agg_trades_{symbol}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            fapi_symbol = self._normalize_symbol(symbol)
            url = f"{BINANCE_FAPI_BASE}/fapi/v1/aggTrades"
            params = {"symbol": fapi_symbol, "limit": limit}
            resp = requests.get(url, params=params, timeout=15, verify=False)
            resp.raise_for_status()
            trades = resp.json()

            if not trades:
                return self._empty_agg_trades()

            buy_vol = 0.0
            sell_vol = 0.0
            buy_count = 0
            sell_count = 0
            trade_sizes = []

            for t in trades:
                qty = float(t['q'])
                price = float(t['p'])
                notional = qty * price
                trade_sizes.append(notional)

                if t['m']:  # isBuyerMaker = True → seller aggressor
                    sell_vol += notional
                    sell_count += 1
                else:  # buyer aggressor
                    buy_vol += notional
                    buy_count += 1

            total_vol = buy_vol + sell_vol
            avg_size = np.mean(trade_sizes) if trade_sizes else 0
            large_trades = sum(1 for s in trade_sizes if s > avg_size * 2)

            result = {
                "total_trades": len(trades),
                "buy_volume": round(buy_vol, 2),
                "sell_volume": round(sell_vol, 2),
                "buy_count": buy_count,
                "sell_count": sell_count,
                "delta": round(buy_vol - sell_vol, 2),
                "delta_pct": round(((buy_vol - sell_vol) / total_vol) * 100, 2) if total_vol > 0 else 0,
                "avg_trade_size": round(avg_size, 2),
                "large_trades": large_trades,
                "timestamp": datetime.now().isoformat()
            }

            self._set_cached(cache_key, result)
            return result

        except Exception as e:
            print(f"[ALPHA DATA] aggTrades error for {symbol}: {e}")
            return self._empty_agg_trades()

    def _empty_agg_trades(self):
        return {
            "total_trades": 0, "buy_volume": 0, "sell_volume": 0,
            "buy_count": 0, "sell_count": 0, "delta": 0, "delta_pct": 0,
            "avg_trade_size": 0, "large_trades": 0,
            "timestamp": datetime.now().isoformat()
        }

    # =========================================================================
    # 2. FUNDING RATE
    # =========================================================================

    def fetch_funding_rate(self, symbol: str, limit: int = 20) -> dict:
        """
        Fetch funding rate history.

        Returns:
            {
                current_rate: float,
                rates_history: list,
                avg_rate_8h: float,
                trend: str,            # "POSITIVE" / "NEGATIVE" / "NEUTRAL"
                annualized_pct: float,
                timestamp: str
            }
        """
        cache_key = f"funding_{symbol}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            fapi_symbol = self._normalize_symbol(symbol)
            url = f"{BINANCE_FAPI_BASE}/fapi/v1/fundingRate"
            params = {"symbol": fapi_symbol, "limit": limit}
            resp = requests.get(url, params=params, timeout=15, verify=False)
            resp.raise_for_status()
            data = resp.json()

            if not data:
                return self._empty_funding()

            rates = [float(d['fundingRate']) for d in data]
            current = rates[-1]
            avg_rate = np.mean(rates)

            # Annualized: rate × 3 (8h periods/day) × 365
            annualized = current * 3 * 365 * 100

            # Trend: recent vs historical average
            recent_avg = np.mean(rates[-5:]) if len(rates) >= 5 else current
            if recent_avg > 0.0001:
                trend = "POSITIVE"   # Longs pay shorts → crowded longs
            elif recent_avg < -0.0001:
                trend = "NEGATIVE"   # Shorts pay longs → crowded shorts
            else:
                trend = "NEUTRAL"

            result = {
                "current_rate": round(current, 6),
                "rates_history": [round(r, 6) for r in rates],
                "avg_rate_8h": round(avg_rate, 6),
                "trend": trend,
                "annualized_pct": round(annualized, 2),
                "timestamp": datetime.now().isoformat()
            }

            self._set_cached(cache_key, result)
            return result

        except Exception as e:
            print(f"[ALPHA DATA] Funding rate error for {symbol}: {e}")
            return self._empty_funding()

    def _empty_funding(self):
        return {
            "current_rate": 0, "rates_history": [], "avg_rate_8h": 0,
            "trend": "NEUTRAL", "annualized_pct": 0,
            "timestamp": datetime.now().isoformat()
        }

    # =========================================================================
    # 3. OPEN INTEREST HISTORY
    # =========================================================================

    def fetch_open_interest(self, symbol: str, period: str = "5m", limit: int = 30) -> dict:
        """
        Fetch open interest history.

        Returns:
            {
                current_oi: float,
                oi_history: list of {timestamp, oi, oi_value},
                change_pct: float,
                trend: str,
                timestamp: str
            }
        """
        cache_key = f"oi_{symbol}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            fapi_symbol = self._normalize_symbol(symbol)
            url = f"{BINANCE_FAPI_BASE}/futures/data/openInterestHist"
            params = {"symbol": fapi_symbol, "period": period, "limit": limit}
            resp = requests.get(url, params=params, timeout=15, verify=False)
            resp.raise_for_status()
            data = resp.json()

            if not data:
                # Fallback: use ccxt for current OI
                return self._fetch_oi_ccxt(symbol)

            oi_values = [float(d['sumOpenInterest']) for d in data]
            oi_notional = [float(d['sumOpenInterestValue']) for d in data]

            current_oi = oi_values[-1] if oi_values else 0
            oldest_oi = oi_values[0] if oi_values else 0
            change_pct = ((current_oi - oldest_oi) / oldest_oi * 100) if oldest_oi > 0 else 0

            # Trend: compare recent half vs older half
            mid = len(oi_values) // 2
            recent_avg = np.mean(oi_values[mid:]) if mid > 0 else current_oi
            older_avg = np.mean(oi_values[:mid]) if mid > 0 else current_oi
            trend = "INCREASING" if recent_avg > older_avg * 1.02 else ("DECREASING" if recent_avg < older_avg * 0.98 else "STABLE")

            history = []
            for d in data[-10:]:  # last 10 for frontend display
                history.append({
                    "timestamp": d['timestamp'],
                    "oi": float(d['sumOpenInterest']),
                    "oi_value": float(d['sumOpenInterestValue'])
                })

            result = {
                "current_oi": round(current_oi, 4),
                "current_oi_value": round(oi_notional[-1], 2) if oi_notional else 0,
                "oi_history": history,
                "change_pct": round(change_pct, 2),
                "trend": trend,
                "timestamp": datetime.now().isoformat()
            }

            self._set_cached(cache_key, result)
            return result

        except Exception as e:
            print(f"[ALPHA DATA] OI error for {symbol}: {e}")
            return self._fetch_oi_ccxt(symbol)

    def _fetch_oi_ccxt(self, symbol: str) -> dict:
        """Fallback: get current OI via ccxt."""
        try:
            if not self._exchange_ready:
                return self._empty_oi()
            ccxt_sym = self._ccxt_symbol(symbol)
            oi = self.exchange.fetch_open_interest(ccxt_sym)
            return {
                "current_oi": oi.get('openInterestAmount', 0),
                "current_oi_value": oi.get('openInterestValue', 0),
                "oi_history": [],
                "change_pct": 0,
                "trend": "UNKNOWN",
                "timestamp": datetime.now().isoformat()
            }
        except Exception:
            return self._empty_oi()

    def _empty_oi(self):
        return {
            "current_oi": 0, "current_oi_value": 0, "oi_history": [],
            "change_pct": 0, "trend": "UNKNOWN",
            "timestamp": datetime.now().isoformat()
        }

    # =========================================================================
    # 4. LONG/SHORT RATIO (Global Account)
    # =========================================================================

    def fetch_long_short_ratio(self, symbol: str, period: str = "5m", limit: int = 30) -> dict:
        """
        Fetch global long/short account ratio.

        Returns:
            {
                long_ratio: float,
                short_ratio: float,
                long_short_ratio: float,
                history: list,
                bias: str,            # "LONG_CROWDED" / "SHORT_CROWDED" / "BALANCED"
                timestamp: str
            }
        """
        cache_key = f"ls_ratio_{symbol}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            fapi_symbol = self._normalize_symbol(symbol)
            url = f"{BINANCE_FAPI_BASE}/futures/data/globalLongShortAccountRatio"
            params = {"symbol": fapi_symbol, "period": period, "limit": limit}
            resp = requests.get(url, params=params, timeout=15, verify=False)
            resp.raise_for_status()
            data = resp.json()

            if not data:
                return self._empty_ls_ratio()

            latest = data[-1]
            long_ratio = float(latest['longAccount'])
            short_ratio = float(latest['shortAccount'])
            ls_ratio = float(latest['longShortRatio'])

            # Bias classification
            if long_ratio > 0.60:
                bias = "LONG_CROWDED"
            elif short_ratio > 0.60:
                bias = "SHORT_CROWDED"
            else:
                bias = "BALANCED"

            history = []
            for d in data[-10:]:
                history.append({
                    "timestamp": d['timestamp'],
                    "long_ratio": float(d['longAccount']),
                    "short_ratio": float(d['shortAccount']),
                    "ls_ratio": float(d['longShortRatio'])
                })

            result = {
                "long_ratio": round(long_ratio, 4),
                "short_ratio": round(short_ratio, 4),
                "long_short_ratio": round(ls_ratio, 4),
                "history": history,
                "bias": bias,
                "timestamp": datetime.now().isoformat()
            }

            self._set_cached(cache_key, result)
            return result

        except Exception as e:
            print(f"[ALPHA DATA] L/S ratio error for {symbol}: {e}")
            return self._empty_ls_ratio()

    def _empty_ls_ratio(self):
        return {
            "long_ratio": 0.5, "short_ratio": 0.5, "long_short_ratio": 1.0,
            "history": [], "bias": "BALANCED",
            "timestamp": datetime.now().isoformat()
        }

    # =========================================================================
    # 5. TAKER BUY/SELL VOLUME
    # =========================================================================

    def fetch_taker_volume(self, symbol: str, period: str = "5m", limit: int = 30) -> dict:
        """
        Fetch taker buy/sell volume ratio.

        Returns:
            {
                buy_vol: float,
                sell_vol: float,
                buy_sell_ratio: float,
                imbalance: float,
                history: list,
                aggression: str,  # "BUYERS_AGGRESSIVE" / "SELLERS_AGGRESSIVE" / "BALANCED"
                timestamp: str
            }
        """
        cache_key = f"taker_vol_{symbol}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            fapi_symbol = self._normalize_symbol(symbol)
            url = f"{BINANCE_FAPI_BASE}/futures/data/takerlongshortRatio"
            params = {"symbol": fapi_symbol, "period": period, "limit": limit}
            resp = requests.get(url, params=params, timeout=15, verify=False)
            resp.raise_for_status()
            data = resp.json()

            if not data:
                return self._empty_taker_vol()

            latest = data[-1]
            buy_vol = float(latest.get('buyVol', 0))
            sell_vol = float(latest.get('sellVol', 0))
            total = buy_vol + sell_vol

            buy_sell_ratio = float(latest.get('buySellRatio', 1.0))
            imbalance = ((buy_vol - sell_vol) / total) if total > 0 else 0

            if buy_sell_ratio > 1.15:
                aggression = "BUYERS_AGGRESSIVE"
            elif buy_sell_ratio < 0.85:
                aggression = "SELLERS_AGGRESSIVE"
            else:
                aggression = "BALANCED"

            history = []
            for d in data[-10:]:
                history.append({
                    "timestamp": d['timestamp'],
                    "buy_vol": float(d.get('buyVol', 0)),
                    "sell_vol": float(d.get('sellVol', 0)),
                    "ratio": float(d.get('buySellRatio', 1.0))
                })

            result = {
                "buy_vol": round(buy_vol, 2),
                "sell_vol": round(sell_vol, 2),
                "buy_sell_ratio": round(buy_sell_ratio, 4),
                "imbalance": round(imbalance, 4),
                "history": history,
                "aggression": aggression,
                "timestamp": datetime.now().isoformat()
            }

            self._set_cached(cache_key, result)
            return result

        except Exception as e:
            print(f"[ALPHA DATA] Taker volume error for {symbol}: {e}")
            return self._empty_taker_vol()

    def _empty_taker_vol(self):
        return {
            "buy_vol": 0, "sell_vol": 0, "buy_sell_ratio": 1.0,
            "imbalance": 0, "history": [], "aggression": "BALANCED",
            "timestamp": datetime.now().isoformat()
        }

    # =========================================================================
    # MASTER: GET ALL MICROSTRUCTURE DATA
    # =========================================================================

    def get_full_snapshot(self, symbol: str) -> dict:
        """
        Fetch ALL microstructure data for a symbol.
        Returns combined dict for AlphaFeatureEngine consumption.
        """
        return {
            "symbol": symbol,
            "agg_trades": self.fetch_agg_trades(symbol),
            "funding": self.fetch_funding_rate(symbol),
            "open_interest": self.fetch_open_interest(symbol),
            "long_short_ratio": self.fetch_long_short_ratio(symbol),
            "taker_volume": self.fetch_taker_volume(symbol),
            "timestamp": datetime.now().isoformat()
        }


# =============================================================================
# STANDALONE TEST
# =============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("ALPHA DATA PIPELINE — Standalone Test")
    print("=" * 60)

    provider = AlphaDataProvider()
    symbol = "BTC-USDT"

    print(f"\n--- Testing {symbol} ---")

    print("\n1. Aggregated Trades:")
    agg = provider.fetch_agg_trades(symbol)
    print(f"   Buy Vol: ${agg['buy_volume']:,.0f} | Sell Vol: ${agg['sell_volume']:,.0f}")
    print(f"   Delta: ${agg['delta']:,.0f} ({agg['delta_pct']:+.1f}%)")
    print(f"   Large Trades: {agg['large_trades']}")

    print("\n2. Funding Rate:")
    fund = provider.fetch_funding_rate(symbol)
    print(f"   Current: {fund['current_rate']:.6f} | Annualized: {fund['annualized_pct']:.1f}%")
    print(f"   Trend: {fund['trend']}")

    print("\n3. Open Interest:")
    oi = provider.fetch_open_interest(symbol)
    print(f"   Current OI: {oi['current_oi']:,.2f} | Value: ${oi['current_oi_value']:,.0f}")
    print(f"   Change: {oi['change_pct']:+.1f}% | Trend: {oi['trend']}")

    print("\n4. Long/Short Ratio:")
    ls = provider.fetch_long_short_ratio(symbol)
    print(f"   Long: {ls['long_ratio']:.1%} | Short: {ls['short_ratio']:.1%}")
    print(f"   Bias: {ls['bias']}")

    print("\n5. Taker Buy/Sell Volume:")
    tv = provider.fetch_taker_volume(symbol)
    print(f"   Buy/Sell Ratio: {tv['buy_sell_ratio']:.3f}")
    print(f"   Aggression: {tv['aggression']}")

    print("\n✅ All alpha data tests completed!")
