# backend/anomaly_scanner.py
"""
ANOMALY DETECTION MODULE (Objective 1)
Detects 3 types of market anomalies to validate trade entries:
1. Volume Spike — Current candle volume > 2x the 20-period Volume SMA
2. Order Book Imbalance — Total Bids > 1.5x Total Asks (top 10 levels)
3. Whale/Iceberg Tracker — Dynamic threshold based on recent avg trade size
"""

import numpy as np
import pandas as pd
from datetime import datetime, timezone
import time


class AnomalyScanner:
    """
    Market anomaly detector using CCXT exchange connection.
    Designed to work with TradingEngine's existing ccxt instance.
    """

    def __init__(self, exchange):
        """
        Args:
            exchange: A connected ccxt exchange instance (e.g., from TradingEngine)
        """
        self.exchange = exchange

    # ================================================================
    # 1. VOLUME SPIKE DETECTION
    # ================================================================
    def detect_volume_spike(self, df, lookback=20, multiplier=2.0):
        """
        Detect if current candle volume exceeds 2x the 20-period Volume SMA.

        Args:
            df: DataFrame with OHLCV data (must have 'volume' column)
            lookback: SMA period for volume average (default: 20)
            multiplier: Threshold multiplier (default: 2.0x)

        Returns:
            dict with detection results
        """
        if df is None or len(df) < lookback + 1:
            return {
                "type": "VOLUME_SPIKE",
                "detected": False,
                "error": "Insufficient data",
                "current_volume": 0,
                "avg_volume": 0,
                "ratio": 0
            }

        # Calculate 20-period Volume SMA
        vol_sma = df['volume'].rolling(lookback).mean()

        current_volume = float(df.iloc[-1]['volume'])
        avg_volume = float(vol_sma.iloc[-1])

        if avg_volume == 0 or pd.isna(avg_volume):
            return {
                "type": "VOLUME_SPIKE",
                "detected": False,
                "error": "Average volume is zero",
                "current_volume": current_volume,
                "avg_volume": 0,
                "ratio": 0
            }

        ratio = current_volume / avg_volume
        is_spike = ratio > multiplier

        return {
            "type": "VOLUME_SPIKE",
            "detected": bool(is_spike),
            "current_volume": round(current_volume, 2),
            "avg_volume": round(avg_volume, 2),
            "ratio": round(ratio, 2),
            "threshold": f"{multiplier}x",
            "signal_strength": "HIGH" if ratio > 3.0 else ("MEDIUM" if ratio > 2.0 else "LOW")
        }

    # ================================================================
    # 2. ORDER BOOK IMBALANCE DETECTION
    # ================================================================
    def detect_order_book_imbalance(self, symbol, levels=10, threshold=1.5):
        """
        Detect if Total Bids > 1.5x Total Asks in top N order book levels.

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            levels: Number of order book levels to analyze (default: 10)
            threshold: Imbalance ratio threshold (default: 1.5x)

        Returns:
            dict with detection results
        """
        try:
            # Normalize symbol format for CCXT
            sym = symbol.replace("-", "/")
            if sym.endswith("/USD") and not sym.endswith("/USDT"):
                sym = sym.replace("/USD", "/USDT")

            # Fetch order book with limit
            order_book = self.exchange.fetch_order_book(sym, limit=levels)

            bids = order_book.get('bids', [])[:levels]
            asks = order_book.get('asks', [])[:levels]

            # Calculate total volume at each side
            # Order book format: [[price, amount], ...]
            total_bid_volume = sum(bid[1] for bid in bids) if bids else 0
            total_ask_volume = sum(ask[1] for ask in asks) if asks else 0

            # Calculate total USD value
            total_bid_usd = sum(bid[0] * bid[1] for bid in bids) if bids else 0
            total_ask_usd = sum(ask[0] * ask[1] for ask in asks) if asks else 0

            # Imbalance ratio
            ratio = total_bid_volume / total_ask_volume if total_ask_volume > 0 else 0
            usd_ratio = total_bid_usd / total_ask_usd if total_ask_usd > 0 else 0

            is_bullish_imbalance = ratio > threshold
            is_bearish_imbalance = (1 / ratio) > threshold if ratio > 0 else False

            # Detect imbalance direction
            direction = "NEUTRAL"
            if is_bullish_imbalance:
                direction = "BULLISH"  # More buyers than sellers
            elif is_bearish_imbalance:
                direction = "BEARISH"  # More sellers than buyers

            return {
                "type": "ORDER_BOOK_IMBALANCE",
                "detected": bool(is_bullish_imbalance or is_bearish_imbalance),
                "direction": direction,
                "bid_volume": round(total_bid_volume, 4),
                "ask_volume": round(total_ask_volume, 4),
                "bid_usd": round(total_bid_usd, 2),
                "ask_usd": round(total_ask_usd, 2),
                "volume_ratio": round(ratio, 3),
                "usd_ratio": round(usd_ratio, 3),
                "threshold": f"{threshold}x",
                "levels_analyzed": min(levels, len(bids), len(asks)),
                "best_bid": bids[0][0] if bids else 0,
                "best_ask": asks[0][0] if asks else 0,
                "spread_pct": round(((asks[0][0] - bids[0][0]) / bids[0][0]) * 100, 4) if bids and asks and bids[0][0] > 0 else 0
            }

        except Exception as e:
            print(f"⚠️ [ANOMALY] Order Book Error for {symbol}: {e}")
            return {
                "type": "ORDER_BOOK_IMBALANCE",
                "detected": False,
                "error": str(e),
                "direction": "UNKNOWN"
            }

    # ================================================================
    # 3. WHALE / ICEBERG TRACKER (DYNAMIC THRESHOLD)
    # ================================================================
    def detect_whale_activity(self, symbol, multiplier=10, window_seconds=1, trade_limit=500):
        """
        Detect whale activity using dynamic threshold based on recent avg trade size.
        Looks for:
        - Single large market orders exceeding dynamic threshold
        - Aggregations of small orders within a 1-second window (iceberg detection)

        Args:
            symbol: Trading pair
            multiplier: Threshold = avg_trade_size * multiplier (default: 10x)
            window_seconds: Time window for iceberg aggregation (default: 1 second)
            trade_limit: Number of recent trades to fetch (default: 500)

        Returns:
            dict with detection results
        """
        try:
            # Normalize symbol
            sym = symbol.replace("-", "/")
            if sym.endswith("/USD") and not sym.endswith("/USDT"):
                sym = sym.replace("/USD", "/USDT")

            # Fetch recent trades
            trades = self.exchange.fetch_trades(sym, limit=trade_limit)

            if not trades or len(trades) < 10:
                return {
                    "type": "WHALE_ACTIVITY",
                    "detected": False,
                    "error": "Insufficient trade data",
                    "whale_trades": [],
                    "iceberg_clusters": []
                }

            # Calculate dynamic threshold
            trade_costs = [t['cost'] for t in trades if t.get('cost') and t['cost'] > 0]

            if not trade_costs:
                return {
                    "type": "WHALE_ACTIVITY",
                    "detected": False,
                    "error": "No valid trade costs found",
                    "whale_trades": [],
                    "iceberg_clusters": []
                }

            avg_trade_size = np.mean(trade_costs)
            median_trade_size = np.median(trade_costs)
            dynamic_threshold = avg_trade_size * multiplier

            # === DETECTION 1: Single Large Orders (Whale) ===
            whale_trades = []
            for t in trades:
                cost = t.get('cost', 0)
                if cost and cost >= dynamic_threshold:
                    whale_trades.append({
                        "timestamp": t.get('datetime', ''),
                        "side": t.get('side', 'unknown'),
                        "price": t.get('price', 0),
                        "amount": t.get('amount', 0),
                        "cost_usd": round(cost, 2),
                        "ratio_to_avg": round(cost / avg_trade_size, 1) if avg_trade_size > 0 else 0
                    })

            # === DETECTION 2: Iceberg Orders (Aggregated Small Orders in 1s Window) ===
            iceberg_clusters = []

            # Group trades by 1-second time windows
            if trades:
                # Sort by timestamp
                sorted_trades = sorted(trades, key=lambda x: x.get('timestamp', 0))

                current_window_start = sorted_trades[0].get('timestamp', 0)
                current_window_trades = []
                current_window_cost = 0

                for t in sorted_trades:
                    ts = t.get('timestamp', 0)

                    if ts - current_window_start <= window_seconds * 1000:  # ms
                        current_window_trades.append(t)
                        current_window_cost += t.get('cost', 0)
                    else:
                        # Check if accumulated cost in this window exceeds threshold
                        if current_window_cost >= dynamic_threshold and len(current_window_trades) >= 3:
                            # Determine dominant side
                            buy_vol = sum(t.get('cost', 0) for t in current_window_trades if t.get('side') == 'buy')
                            sell_vol = sum(t.get('cost', 0) for t in current_window_trades if t.get('side') == 'sell')

                            iceberg_clusters.append({
                                "window_start": datetime.fromtimestamp(current_window_start / 1000, tz=timezone.utc).isoformat(),
                                "order_count": len(current_window_trades),
                                "total_cost_usd": round(current_window_cost, 2),
                                "avg_order_size": round(current_window_cost / len(current_window_trades), 2),
                                "dominant_side": "BUY" if buy_vol > sell_vol else "SELL",
                                "buy_volume_usd": round(buy_vol, 2),
                                "sell_volume_usd": round(sell_vol, 2),
                                "ratio_to_threshold": round(current_window_cost / dynamic_threshold, 2)
                            })

                        # Start new window
                        current_window_start = ts
                        current_window_trades = [t]
                        current_window_cost = t.get('cost', 0)

                # Check last window
                if current_window_cost >= dynamic_threshold and len(current_window_trades) >= 3:
                    buy_vol = sum(t.get('cost', 0) for t in current_window_trades if t.get('side') == 'buy')
                    sell_vol = sum(t.get('cost', 0) for t in current_window_trades if t.get('side') == 'sell')
                    iceberg_clusters.append({
                        "window_start": datetime.fromtimestamp(current_window_start / 1000, tz=timezone.utc).isoformat(),
                        "order_count": len(current_window_trades),
                        "total_cost_usd": round(current_window_cost, 2),
                        "avg_order_size": round(current_window_cost / len(current_window_trades), 2),
                        "dominant_side": "BUY" if buy_vol > sell_vol else "SELL",
                        "buy_volume_usd": round(buy_vol, 2),
                        "sell_volume_usd": round(sell_vol, 2),
                        "ratio_to_threshold": round(current_window_cost / dynamic_threshold, 2)
                    })

            detected = len(whale_trades) > 0 or len(iceberg_clusters) > 0

            # Net whale pressure
            whale_buy_vol = sum(w['cost_usd'] for w in whale_trades if w['side'] == 'buy')
            whale_sell_vol = sum(w['cost_usd'] for w in whale_trades if w['side'] == 'sell')

            return {
                "type": "WHALE_ACTIVITY",
                "detected": bool(detected),
                "dynamic_threshold_usd": round(dynamic_threshold, 2),
                "avg_trade_size_usd": round(avg_trade_size, 2),
                "median_trade_size_usd": round(median_trade_size, 2),
                "multiplier_used": multiplier,
                "total_trades_analyzed": len(trades),
                "whale_trades": whale_trades[:10],  # Limit to top 10
                "whale_count": len(whale_trades),
                "whale_buy_volume": round(whale_buy_vol, 2),
                "whale_sell_volume": round(whale_sell_vol, 2),
                "whale_pressure": "BUY" if whale_buy_vol > whale_sell_vol else ("SELL" if whale_sell_vol > whale_buy_vol else "NEUTRAL"),
                "iceberg_clusters": iceberg_clusters[:5],  # Limit to top 5
                "iceberg_count": len(iceberg_clusters)
            }

        except Exception as e:
            print(f"⚠️ [ANOMALY] Whale Detection Error for {symbol}: {e}")
            return {
                "type": "WHALE_ACTIVITY",
                "detected": False,
                "error": str(e),
                "whale_trades": [],
                "iceberg_clusters": []
            }

    # ================================================================
    # 4. FULL SCAN (COMBINED)
    # ================================================================
    def full_scan(self, symbol, df=None):
        """
        Run all 3 anomaly checks and return combined result.

        Args:
            symbol: Trading pair (e.g., 'BTC-USDT')
            df: Optional DataFrame for volume spike detection

        Returns:
            dict with all anomaly results and overall assessment
        """
        results = {
            "symbol": symbol,
            "scan_time": datetime.now(timezone.utc).isoformat(),
            "anomalies": {}
        }

        # 1. Volume Spike (requires OHLCV DataFrame)
        if df is not None and not df.empty:
            results["anomalies"]["volume_spike"] = self.detect_volume_spike(df)
        else:
            results["anomalies"]["volume_spike"] = {
                "type": "VOLUME_SPIKE",
                "detected": False,
                "error": "No OHLCV data provided"
            }

        # 2. Order Book Imbalance (live)
        results["anomalies"]["order_book"] = self.detect_order_book_imbalance(symbol)

        # 3. Whale Activity (live trades)
        results["anomalies"]["whale_activity"] = self.detect_whale_activity(symbol)

        # === OVERALL ASSESSMENT ===
        anomaly_count = sum(
            1 for a in results["anomalies"].values()
            if a.get("detected", False)
        )

        # Determine if anomalies favor long or short
        ob = results["anomalies"]["order_book"]
        whale = results["anomalies"]["whale_activity"]

        bullish_signals = 0
        bearish_signals = 0

        if ob.get("detected"):
            if ob.get("direction") == "BULLISH":
                bullish_signals += 1
            elif ob.get("direction") == "BEARISH":
                bearish_signals += 1

        if whale.get("detected"):
            if whale.get("whale_pressure") == "BUY":
                bullish_signals += 1
            elif whale.get("whale_pressure") == "SELL":
                bearish_signals += 1

        if results["anomalies"]["volume_spike"].get("detected"):
            bullish_signals += 0.5  # Volume spike is directionally neutral but adds weight
            bearish_signals += 0.5

        results["summary"] = {
            "total_anomalies_detected": anomaly_count,
            "anomaly_level": "HIGH" if anomaly_count >= 3 else ("MEDIUM" if anomaly_count >= 2 else ("LOW" if anomaly_count == 1 else "NONE")),
            "bullish_signals": bullish_signals,
            "bearish_signals": bearish_signals,
            "bias": "BULLISH" if bullish_signals > bearish_signals else ("BEARISH" if bearish_signals > bullish_signals else "NEUTRAL"),
            "trade_validation": {
                "long_validated": bullish_signals >= 1.5,
                "short_validated": bearish_signals >= 1.5
            }
        }

        return results
