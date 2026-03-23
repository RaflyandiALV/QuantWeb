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

            # Capture ALL individual trade details for frontend filtering
            all_trade_details = []
            for t in trades:
                qty = float(t['q'])
                price = float(t['p'])
                notional = qty * price
                all_trade_details.append({
                    "timestamp": t.get('T', t.get('t', 0)),
                    "price": price,
                    "size": round(notional, 2),
                    "side": "sell" if t['m'] else "buy"
                })

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
                "all_trade_details": all_trade_details,
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
            "avg_trade_size": 0, "large_trades": 0, "all_trade_details": [],
            "timestamp": datetime.now().isoformat()
        }

    # =========================================================================
    # 1B. KLINE / CANDLESTICK DATA
    # =========================================================================

    def fetch_klines(self, symbol: str, interval: str = "5m", limit: int = 100) -> dict:
        """Fetch kline/candlestick data for price chart."""
        cache_key = f"klines_{symbol}_{interval}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            fapi_symbol = self._normalize_symbol(symbol)
            url = f"{BINANCE_FAPI_BASE}/fapi/v1/klines"
            params = {"symbol": fapi_symbol, "interval": interval, "limit": limit}
            resp = requests.get(url, params=params, timeout=15, verify=False)
            resp.raise_for_status()
            data = resp.json()

            if not data:
                return {"candles": [], "timestamp": datetime.now().isoformat()}

            candles = []
            for k in data:
                candles.append({
                    "timestamp": k[0],      # open time
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                    "close_time": k[6],
                })

            result = {
                "candles": candles,
                "current_price": candles[-1]["close"] if candles else 0,
                "price_change": round(((candles[-1]["close"] - candles[0]["open"]) / candles[0]["open"] * 100), 2) if candles else 0,
                "high": max(c["high"] for c in candles) if candles else 0,
                "low": min(c["low"] for c in candles) if candles else 0,
                "timestamp": datetime.now().isoformat()
            }

            self._set_cached(cache_key, result)
            return result

        except Exception as e:
            print(f"[ALPHA DATA] Klines error for {symbol}: {e}")
            return {"candles": [], "current_price": 0, "price_change": 0, "high": 0, "low": 0, "timestamp": datetime.now().isoformat()}

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

            # Build structured history with timestamps
            history = []
            for d in data[-30:]:
                history.append({
                    "timestamp": d.get('fundingTime', d.get('timestamp', 0)),
                    "rate": float(d['fundingRate'])
                })

            result = {
                "current_rate": round(current, 6),
                "history": history,
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
            "current_rate": 0, "history": [], "rates_history": [],
            "avg_rate_8h": 0, "trend": "NEUTRAL", "annualized_pct": 0,
            "timestamp": datetime.now().isoformat()
        }

    # =========================================================================
    # 3. OPEN INTEREST HISTORY
    # =========================================================================

    def fetch_open_interest(self, symbol: str, period: str = "5m", limit: int = 50) -> dict:
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
        cache_key = f"oi_{symbol}_{period}"
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
            for d in data[-30:]:  # last 30 for frontend display
                history.append({
                    "timestamp": d['timestamp'],
                    "oi": float(d['sumOpenInterest']),
                    "oi_value": float(d['sumOpenInterestValue'])
                })

            result = {
                "current_oi": round(current_oi, 4),
                "current_oi_value": round(oi_notional[-1], 2) if oi_notional else 0,
                "history": history,
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

    def fetch_long_short_ratio(self, symbol: str, period: str = "5m", limit: int = 50) -> dict:
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
            for d in data[-30:]:
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

    def fetch_taker_volume(self, symbol: str, period: str = "5m", limit: int = 50) -> dict:
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
        cache_key = f"taker_vol_{symbol}_{period}"
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
            for d in data[-30:]:
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

    def get_full_snapshot(self, symbol: str, period: str = "5m") -> dict:
        """
        Fetch ALL microstructure data for a symbol.
        Returns combined dict for AlphaFeatureEngine consumption.
        Period is used for OI, L/S ratio, and taker volume granularity.
        """
        return {
            "symbol": symbol,
            "agg_trades": self.fetch_agg_trades(symbol),
            "funding_rate": self.fetch_funding_rate(symbol),
            "open_interest": self.fetch_open_interest(symbol, period=period),
            "long_short_ratio": self.fetch_long_short_ratio(symbol, period=period),
            "taker_volume": self.fetch_taker_volume(symbol, period=period),
            "klines": self.fetch_klines(symbol, interval=period),
            "orderbook_pressure": self.fetch_orderbook_depth(symbol),
            "timestamp": datetime.now().isoformat()
        }

    # =========================================================================
    # 8. ORDERBOOK DEPTH → Buy/Sell Pressure
    # =========================================================================

    def fetch_orderbook_depth(self, symbol: str, limit: int = 500) -> dict:
        """
        Fetch order book depth from Binance Futures and calculate
        buy/sell pressure at multiple tiers from current price.
        
        Returns:
            {
                current_price: float,
                tiers: [
                    { pct: 1, bid_vol: float, ask_vol: float, ratio: float },
                    { pct: 2.5, ... },
                    { pct: 5, ... },
                    { pct: 10, ... },
                ],
                bid_walls: [ { price: float, size: float } ],
                ask_walls: [ { price: float, size: float } ],
                total_bid_vol: float,
                total_ask_vol: float,
                pressure_ratio: float,
            }
        """
        cache_key = f"orderbook_{symbol}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            fapi_symbol = self._normalize_symbol(symbol)
            url = f"{BINANCE_FAPI_BASE}/fapi/v1/depth"
            params = {"symbol": fapi_symbol, "limit": limit}
            resp = requests.get(url, params=params, timeout=15, verify=False)
            resp.raise_for_status()
            book = resp.json()

            bids = [(float(p), float(q)) for p, q in book.get('bids', [])]
            asks = [(float(p), float(q)) for p, q in book.get('asks', [])]

            if not bids or not asks:
                return self._empty_orderbook()

            best_bid = bids[0][0]
            best_ask = asks[0][0]
            mid_price = (best_bid + best_ask) / 2

            # Calculate pressure at tiers
            tier_pcts = [1, 2.5, 5, 10]
            tiers = []
            for pct in tier_pcts:
                lower = mid_price * (1 - pct / 100)
                upper = mid_price * (1 + pct / 100)
                bid_vol = sum(p * q for p, q in bids if p >= lower)
                ask_vol = sum(p * q for p, q in asks if p <= upper)
                total = bid_vol + ask_vol
                ratio = round(bid_vol / total, 4) if total > 0 else 0.5
                tiers.append({
                    "pct": pct,
                    "bid_vol": round(bid_vol, 2),
                    "ask_vol": round(ask_vol, 2),
                    "ratio": ratio,
                })

            # Find significant walls (top 5 levels by notional value)
            bid_levels = sorted([(p, p * q) for p, q in bids], key=lambda x: x[1], reverse=True)[:5]
            ask_levels = sorted([(p, p * q) for p, q in asks], key=lambda x: x[1], reverse=True)[:5]

            total_bid = sum(p * q for p, q in bids)
            total_ask = sum(p * q for p, q in asks)

            result = {
                "current_price": mid_price,
                "tiers": tiers,
                "bid_walls": [{"price": p, "size": round(s, 2)} for p, s in bid_levels],
                "ask_walls": [{"price": p, "size": round(s, 2)} for p, s in ask_levels],
                "total_bid_vol": round(total_bid, 2),
                "total_ask_vol": round(total_ask, 2),
                "pressure_ratio": round(total_bid / (total_bid + total_ask), 4) if (total_bid + total_ask) > 0 else 0.5,
            }

            self._set_cached(cache_key, result)
            return result

        except Exception as e:
            print(f"[ALPHA DATA] orderbook depth error for {symbol}: {e}")
            return self._empty_orderbook()

    def _empty_orderbook(self):
        return {
            "current_price": 0,
            "tiers": [],
            "bid_walls": [],
            "ask_walls": [],
            "total_bid_vol": 0,
            "total_ask_vol": 0,
            "pressure_ratio": 0.5,
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
