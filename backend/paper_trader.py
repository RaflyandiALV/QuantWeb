# backend/paper_trader.py
"""
PAPER TRADING LOOP (Gap 5)
Autonomous trading cycle: Fetch → Compute → Decide → Execute → Log → Feedback.

Configurable interval (default 15min).
All trades stored in SQLite for review and validation.
"""

import os
import time
import json
import sqlite3
import threading
from db_utils import get_db_connection
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Import project modules
from alpha_data import AlphaDataProvider
from alpha_features import AlphaFeatureEngine
from ai_brain import AIBrain
from execution_engine import FuturesExecutionManager
from strategy_core import TradingEngine

# =============================================================================
# CONFIGURATION
# =============================================================================

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paper_trades.db")
DEFAULT_INTERVAL = 900  # 15 minutes in seconds
DEFAULT_WATCHLIST = ["BTC-USDT", "ETH-USDT", "SOL-USDT"]
DEFAULT_TRADE_AMOUNT = 100  # $100 per trade


class PaperTrader:
    """
    Autonomous paper trading system.
    Runs Fetch → Compute → Decide → Execute → Log cycle at configurable intervals.
    """

    def __init__(self, watchlist=None, interval=DEFAULT_INTERVAL,
                 trade_amount=DEFAULT_TRADE_AMOUNT, leverage=1):
        self.watchlist = watchlist or DEFAULT_WATCHLIST
        self.interval = interval
        self.trade_amount = trade_amount
        self.leverage = leverage

        # Initialize components
        self.data_provider = AlphaDataProvider()
        self.feature_engine = AlphaFeatureEngine(self.data_provider)
        self.ai_brain = AIBrain()
        self.executor = FuturesExecutionManager(paper_mode=True, leverage=leverage)
        self.strategy_engine = TradingEngine() # Used for auto-detecting best strategy
        
        # Strategy assignment per symbol
        self.symbol_strategies = {}

        # Runtime state — using threading.Event for proper thread signaling
        self._stop_event = threading.Event()
        self._thread = None
        self._cycle_count = 0
        self._last_cycle_time = None
        self._errors = []
        self._event_log = []  # Live event stream for UI
        self._max_events = 100

        # Init database
        self._init_db()

        print(f"[PAPER TRADER] Initialized")
        print(f"   Watchlist: {self.watchlist}")
        print(f"   Interval: {interval}s ({interval/60:.0f}min)")
        print(f"   Trade Amount: ${trade_amount}")
        print(f"   Leverage: {leverage}x")
        print(f"   AI Mode: {self.ai_brain.mode}")

    def _init_db(self):
        """Create paper trading database tables."""
        try:
            conn = get_db_connection(DB_PATH)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS paper_cycles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    cycle_number INTEGER,
                    features_json TEXT,
                    decision_json TEXT,
                    execution_json TEXT,
                    status TEXT DEFAULT 'completed'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS paper_positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    entry_price REAL,
                    exit_price REAL,
                    qty REAL,
                    pnl REAL,
                    pnl_pct REAL,
                    leverage INTEGER,
                    status TEXT DEFAULT 'open',
                    opened_at TEXT,
                    closed_at TEXT,
                    decision_reasoning TEXT
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[PAPER TRADER] DB init error: {e}")

    # =========================================================================
    # CONTROL: START / STOP
    # =========================================================================

    def start(self) -> dict:
        """Start the paper trading loop in a background thread."""
        if self._thread is not None and self._thread.is_alive():
            return {"status": "already_running", "cycles": self._cycle_count}

        self._stop_event.clear()  # Reset stop signal before launching
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        return {
            "status": "started",
            "watchlist": self.watchlist,
            "interval_seconds": self.interval,
            "ai_mode": self.ai_brain.mode,
            "timestamp": datetime.now().isoformat()
        }

    def stop(self) -> dict:
        """Stop the paper trading loop gracefully."""
        if self._thread is None or not self._thread.is_alive():
            return {"status": "not_running"}

        self._stop_event.set()  # Signal background thread to exit
        self._thread.join(timeout=30)  # Up to 30s: one full cycle can take ~15s

        return {
            "status": "stopped",
            "total_cycles": self._cycle_count,
            "timestamp": datetime.now().isoformat()
        }

    def get_status(self) -> dict:
        """Get current status of the paper trader."""
        positions = self.executor.get_open_positions()
        balance = self.executor.get_balance()
        trade_history = self.executor.get_trade_history()

        # Calculate summary stats
        total_pnl = sum(t.get('pnl', 0) for t in trade_history)
        wins = sum(1 for t in trade_history if t.get('pnl', 0) > 0)
        losses = sum(1 for t in trade_history if t.get('pnl', 0) < 0)
        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0

        return {
            "running": self._thread is not None and self._thread.is_alive(),
            "cycle_count": self._cycle_count,
            "last_cycle": self._last_cycle_time,
            "watchlist": self.watchlist,
            "interval_seconds": self.interval,
            "ai_mode": self.ai_brain.mode,
            "balance": balance,
            "open_positions": len(positions),
            "positions": positions,
            "total_trades": len(trade_history),
            "total_pnl": round(total_pnl, 2),
            "win_rate": round(win_rate, 1),
            "wins": wins,
            "losses": losses,
            "recent_errors": self._errors[-5:],
            "recent_events": self._event_log[-30:],
            "timestamp": datetime.now().isoformat()
        }

    # =========================================================================
    # MAIN LOOP
    # =========================================================================

    def _run_loop(self):
        """Main trading loop — runs in background thread."""
        print(f"[PAPER TRADER] 🚀 Loop started at {datetime.now().isoformat()}")

        while not self._stop_event.is_set():
            try:
                self._run_cycle()
            except Exception as e:
                error_msg = f"Cycle error: {str(e)[:200]}"
                self._errors.append({
                    "time": datetime.now().isoformat(),
                    "error": error_msg
                })
                print(f"[PAPER TRADER] [ERROR] {error_msg}")

            # Wait for next cycle — exits immediately if stop() is called
            self._stop_event.wait(timeout=self.interval)

        print(f"[PAPER TRADER] ⏹️ Loop stopped. Total cycles: {self._cycle_count}")

    def _run_cycle(self):
        """Execute one trading cycle for all watchlist symbols."""
        self._cycle_count += 1
        self._last_cycle_time = datetime.now().isoformat()

        print(f"\n{'='*50}")
        print(f"[PAPER TRADER] Cycle #{self._cycle_count} @ {self._last_cycle_time}")
        print(f"{'='*50}")

        for symbol in self.watchlist:
            try:
                self._process_symbol(symbol)
            except Exception as e:
                print(f"[PAPER TRADER] Error processing {symbol}: {e}")

        # Check SL/TP for all open positions
        self._check_all_positions()

    def _add_event(self, symbol, event_type, message, detail=None):
        """Add a live event to the stream for the frontend."""
        event = {
            "time": datetime.now().isoformat(),
            "symbol": symbol,
            "type": event_type,  # scan, strategy, decision, execute, hold, error
            "message": message,
            "detail": detail
        }
        self._event_log.append(event)
        if len(self._event_log) > self._max_events:
            self._event_log = self._event_log[-self._max_events:]

    def _process_symbol(self, symbol: str):
        """Process one symbol through the full pipeline."""

        # Step 1: FETCH — Get microstructure data
        self._add_event(symbol, "scan", f"Fetching market data for {symbol}...")
        raw_data = self.data_provider.get_full_snapshot(symbol)

        # Step 2: COMPUTE — Generate features
        self._add_event(symbol, "scan", f"Computing alpha features for {symbol}...")
        features_result = self.feature_engine.compute_all_features(symbol, raw_data)

        # Step 3: Get current price
        price = self.executor.get_current_price(symbol)
        if not price:
            self._add_event(symbol, "error", f"Cannot fetch price for {symbol}, skipping")
            print(f"   [ERROR] {symbol}: Cannot get price, skipping")
            return

        # Step 3.5: Strategy Auto-Detection (if not yet assigned)
        if symbol not in self.symbol_strategies:
            self._add_event(symbol, "strategy", f"Auto-detecting best strategy for {symbol}...")
            print(f"   🔍 {symbol}: Auto-detecting best strategy...")
            best_strat = self._detect_best_strategy(symbol)
            self.symbol_strategies[symbol] = best_strat
            self._add_event(symbol, "strategy", f"Best strategy: {best_strat}", {"strategy": best_strat})
            print(f"   🎯 {symbol}: Best strategy detected -> {best_strat}")
            
        assigned_strategy = self.symbol_strategies[symbol]

        # Step 4: DECIDE — AI makes a decision
        self._add_event(symbol, "decision", f"Asking AI for decision on {symbol} @ ${price:,.2f}...")
        market_snapshot = {
            **features_result,
            "price": price,
            "regime": features_result.get("signals", {}).get("overall_bias", "NEUTRAL"),
            "assigned_strategy": assigned_strategy
        }
        decision = self.ai_brain.make_decision(symbol, market_snapshot)

        reasoning = decision.get('reasoning') or decision.get('_fallback_reason') or 'No reasoning provided'
        confidence = decision.get('confidence', 0)

        print(f"   🧠 {symbol}: {decision['decision']} "
              f"(confidence: {confidence}%) "
              f"[{self.ai_brain.mode}]")

        self._add_event(symbol, "decision",
            f"AI: {decision['decision']} ({confidence}% confidence)",
            {
                "decision": decision['decision'],
                "confidence": confidence,
                "reasoning": reasoning,
                "strategy": assigned_strategy,
                "price": price,
                "entry": decision.get('entry'),
                "sl": decision.get('stop_loss'),
                "tp": decision.get('take_profit'),
            }
        )

        # Step 5: EXECUTE — Only if decision is actionable
        execution_result = None
        if decision['decision'] in ('LONG', 'SHORT'):
            # Check if already have an open position
            positions = self.executor.get_open_positions()
            has_position = any(p['symbol'] == symbol for p in positions)

            if has_position:
                self._add_event(symbol, "hold", f"{symbol}: Already has open position, skipping")
                print(f"   📌 {symbol}: Already has open position, skipping")
            else:
                execution_result = self.executor.open_position(
                    symbol=symbol,
                    side=decision['decision'],
                    amount_usd=self.trade_amount,
                    stop_loss=decision.get('stop_loss'),
                    take_profit=decision.get('take_profit')
                )
                self._add_event(symbol, "execute",
                    f"OPENED {decision['decision']} {symbol} @ ${price:,.2f}",
                    {
                        "side": decision['decision'],
                        "entry": price,
                        "sl": decision.get('stop_loss'),
                        "tp": decision.get('take_profit'),
                        "amount": self.trade_amount,
                    }
                )
                print(f"   📊 {symbol}: Executed {decision['decision']} | "
                      f"Entry: ${price:,.2f} | "
                      f"SL: ${decision.get('stop_loss', 0):,.2f} | "
                      f"TP: ${decision.get('take_profit', 0):,.2f}")
        else:
            self._add_event(symbol, "hold",
                f"{symbol}: HOLD — {reasoning[:120]}",
                {"reasoning": reasoning}
            )
            print(f"   [PAUSE] {symbol}: HOLD — no action taken")

        # Step 6: LOG — Store cycle data
        self._log_cycle(symbol, features_result, decision, execution_result)

    def _check_all_positions(self):
        """Check SL/TP triggers for all open positions."""
        positions = self.executor.get_open_positions()
        for pos in positions:
            symbol = pos['symbol']
            result = self.executor.check_sl_tp(symbol)
            if result.get('triggered'):
                trigger = result.get('trigger', 'UNKNOWN')
                pnl = result.get('trade', {}).get('pnl', 0)
                print(f"   [FAST] {symbol}: {trigger} triggered! PnL: ${pnl:,.2f}")

                # Log closed position
                self._log_position_close(symbol, result)

    def _detect_best_strategy(self, symbol: str) -> str:
        """Run a quick 1y backtest on 1h timeframe to find the best strategy for the symbol."""
        strategies_to_test = [
            "MOMENTUM", "MEAN_REVERSAL", "GRID", "MULTITIMEFRAME",
            "MOMENTUM_PRO", "MEAN_REVERSAL_PRO", "GRID_PRO", "MULTITIMEFRAME_PRO",
            "MIX_STRATEGY", "MIX_STRATEGY_PRO"
        ]
        
        try:
            df_raw = self.strategy_engine.fetch_data(symbol, requested_period="1y", interval="1h")
            if df_raw is None or len(df_raw) < 50:
                print(f"   [WARN] Could not fetch enough data for {symbol} backtest, defaulting to MULTITIMEFRAME_PRO")
                return "MULTITIMEFRAME_PRO"
                
            best_strat = "MULTITIMEFRAME_PRO"
            best_profit = -float('inf')
            
            for strat in strategies_to_test:
                # Try cache first to speed up
                cached = self.strategy_engine._get_cached_result(symbol, "1h", "1y", strat)
                if cached:
                    profit = cached.get('net_profit', 0)
                else:
                    _, _, metrics, _ = self.strategy_engine.run_backtest(df_raw, strat, requested_period="1y")
                    profit = metrics.get('net_profit', 0)
                    
                if profit > best_profit:
                    best_profit = profit
                    best_strat = strat
                    
            return best_strat
        except Exception as e:
            print(f"   [WARN] Strategy detection error for {symbol}: {e}")
            return "MULTITIMEFRAME_PRO"

    # =========================================================================
    # LOGGING
    # =========================================================================

    def _log_cycle(self, symbol, features, decision, execution):
        """Log a trading cycle to database."""
        try:
            conn = get_db_connection(DB_PATH)
            conn.execute("""
                INSERT INTO paper_cycles
                (timestamp, symbol, cycle_number, features_json, decision_json, execution_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                symbol,
                self._cycle_count,
                json.dumps(features, default=str)[:3000],
                json.dumps(decision, default=str)[:2000],
                json.dumps(execution, default=str)[:2000] if execution else None
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[PAPER TRADER] Log error: {e}")

    def _log_position_close(self, symbol: str, result: dict):
        """Log a closed position to database."""
        try:
            trade = result.get('trade', {})
            conn = get_db_connection(DB_PATH)
            conn.execute("""
                INSERT INTO paper_positions
                (timestamp, symbol, side, entry_price, exit_price, qty,
                 pnl, pnl_pct, leverage, status, opened_at, closed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                symbol,
                trade.get('side', ''),
                trade.get('entry_price', 0),
                trade.get('exit_price', 0),
                trade.get('qty', 0),
                trade.get('pnl', 0),
                trade.get('pnl_pct', 0),
                trade.get('leverage', 1),
                'closed',
                trade.get('opened_at', ''),
                trade.get('closed_at', '')
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[PAPER TRADER] Position log error: {e}")

    # =========================================================================
    # DATA RETRIEVAL
    # =========================================================================

    def get_trades(self, limit: int = 100) -> list:
        """Get trade history from both in-memory and database."""
        # Combine in-memory trades with DB trades
        memory_trades = self.executor.get_trade_history()

        try:
            conn = get_db_connection(DB_PATH)
            rows = conn.execute(
                "SELECT * FROM paper_positions ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
            conn.close()
            db_trades = [dict(row) for row in rows]
        except Exception:
            db_trades = []

        # Merge, preferring memory trades (more recent)
        all_trades = memory_trades + db_trades
        return all_trades[:limit]

    def get_cycles(self, symbol: str = None, limit: int = 50) -> list:
        """Get cycle history from database."""
        try:
            conn = get_db_connection(DB_PATH)

            if symbol:
                rows = conn.execute(
                    "SELECT * FROM paper_cycles WHERE symbol = ? ORDER BY id DESC LIMIT ?",
                    (symbol, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM paper_cycles ORDER BY id DESC LIMIT ?",
                    (limit,)
                ).fetchall()

            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"[PAPER TRADER] Cycle fetch error: {e}")
            return []

    def run_single_cycle(self) -> dict:
        """
        Run a single cycle manually (for API calls).
        Reuses _process_symbol() so that event log is populated for the Live Feed.
        """
        self._cycle_count += 1
        self._add_event("SYSTEM", "scan", f"▶ Manual cycle #{self._cycle_count} started for {len(self.watchlist)} symbols")

        errors = {}
        for symbol in self.watchlist:
            try:
                self._process_symbol(symbol)
            except Exception as e:
                self._add_event(symbol, "error", f"Error processing {symbol}: {str(e)[:100]}")
                errors[symbol] = str(e)

        # Check SL/TP for open positions
        self._check_all_positions()

        self._last_cycle_time = datetime.now().isoformat()
        self._add_event("SYSTEM", "scan", f"[OK] Manual cycle #{self._cycle_count} completed")

        return {
            "cycle": self._cycle_count,
            "symbols_processed": len(self.watchlist),
            "errors": errors,
            "balance": self.executor.get_balance(),
            "recent_events": self._event_log[-20:],
            "timestamp": datetime.now().isoformat()
        }


# =============================================================================
# STANDALONE TEST
# =============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("PAPER TRADER — Standalone Test")
    print("=" * 60)

    trader = PaperTrader(
        watchlist=["BTC-USDT"],
        interval=60,  # 1 min for testing
        trade_amount=100,
        leverage=2
    )

    print(f"\n📊 Status: {json.dumps(trader.get_status(), indent=2, default=str)}")

    print("\n🔄 Running single cycle...")
    result = trader.run_single_cycle()
    print(f"\n📋 Cycle result:")
    for sym, data in result.get("results", {}).items():
        if "error" not in data:
            print(f"   {sym}: {data['decision'].get('decision', 'N/A')} "
                  f"(confidence: {data['decision'].get('confidence', 0)}%)")
        else:
            print(f"   {sym}: ERROR - {data['error']}")

    print(f"\n💰 Balance: ${result['balance']['total']:,.2f}")
    print("\n[OK] Paper trader test completed!")
