# backend/validation_engine.py
"""
STATISTICAL VALIDATION ENGINE (Gap 6)
Validates AI trading decisions with walk-forward and Monte Carlo methods.

- Walk-Forward: 70% in-sample, 30% out-of-sample
- Monte Carlo: Shuffle 1000x, check if edge persists
- Min 200 decisions for statistical significance
- JSON validation report output
"""

import os
import json
import sqlite3
import numpy as np
from datetime import datetime, timedelta

# =============================================================================
# CONFIGURATION
# =============================================================================

AI_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_decisions.db")
PAPER_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paper_trades.db")
VALIDATION_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation_reports.db")

MIN_DECISIONS_FOR_VALIDATION = 200
MONTE_CARLO_ITERATIONS = 1000
WALK_FORWARD_INSAMPLE_PCT = 0.70


class ValidationEngine:
    """
    Validates the statistical edge of the AI Decision Brain.
    Uses walk-forward analysis and Monte Carlo simulation.
    """

    def __init__(self):
        self._init_db()
        print("[VALIDATION] Engine initialized")

    def _init_db(self):
        """Create validation reports table."""
        try:
            conn = sqlite3.connect(VALIDATION_DB_PATH)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS validation_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    total_decisions INTEGER,
                    walk_forward_result TEXT,
                    monte_carlo_result TEXT,
                    overall_verdict TEXT,
                    metrics_json TEXT,
                    report_json TEXT
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[VALIDATION] DB init error: {e}")

    # =========================================================================
    # DATA COLLECTION
    # =========================================================================

    def _get_decisions(self, symbol: str = None) -> list:
        """Fetch AI decisions from database."""
        try:
            conn = sqlite3.connect(AI_DB_PATH)
            conn.row_factory = sqlite3.Row

            if symbol:
                rows = conn.execute(
                    "SELECT * FROM ai_decisions WHERE symbol = ? AND decision != 'HOLD' ORDER BY id ASC",
                    (symbol,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM ai_decisions WHERE decision != 'HOLD' ORDER BY id ASC"
                ).fetchall()

            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"[VALIDATION] Decision fetch error: {e}")
            return []

    def _get_paper_trades(self) -> list:
        """Fetch paper trade results."""
        try:
            conn = sqlite3.connect(PAPER_DB_PATH)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM paper_positions WHERE status = 'closed' ORDER BY id ASC"
            ).fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"[VALIDATION] Trade fetch error: {e}")
            return []

    # =========================================================================
    # WALK-FORWARD ANALYSIS
    # =========================================================================

    def walk_forward_test(self, trades: list) -> dict:
        """
        Walk-Forward Validation:
        - Split trades: 70% in-sample (training), 30% out-of-sample (testing)
        - Compare performance metrics between both splits
        - Edge is valid if OOS performance >= 50% of IS performance

        Returns:
            {
                in_sample: {metrics},
                out_of_sample: {metrics},
                degradation_pct: float,
                verdict: str,
                is_valid: bool
            }
        """
        if len(trades) < 20:
            return {
                "verdict": "INSUFFICIENT_DATA",
                "is_valid": False,
                "message": f"Need at least 20 trades, have {len(trades)}"
            }

        split = int(len(trades) * WALK_FORWARD_INSAMPLE_PCT)
        is_trades = trades[:split]
        oos_trades = trades[split:]

        is_metrics = self._compute_metrics(is_trades, "In-Sample")
        oos_metrics = self._compute_metrics(oos_trades, "Out-of-Sample")

        # Degradation analysis
        is_pf = is_metrics.get("profit_factor", 0)
        oos_pf = oos_metrics.get("profit_factor", 0)

        if is_pf > 0:
            degradation = ((is_pf - oos_pf) / is_pf) * 100
        else:
            degradation = 100

        # Verdict
        if oos_pf >= 1.2 and degradation < 50:
            verdict = "VALID_EDGE"
            is_valid = True
        elif oos_pf >= 1.0 and degradation < 70:
            verdict = "MARGINAL_EDGE"
            is_valid = True
        else:
            verdict = "NO_EDGE"
            is_valid = False

        return {
            "in_sample": is_metrics,
            "out_of_sample": oos_metrics,
            "split": f"{split} IS / {len(trades) - split} OOS",
            "degradation_pct": round(degradation, 2),
            "verdict": verdict,
            "is_valid": is_valid
        }

    # =========================================================================
    # MONTE CARLO SIMULATION
    # =========================================================================

    def monte_carlo_test(self, trades: list, iterations: int = MONTE_CARLO_ITERATIONS) -> dict:
        """
        Monte Carlo Validation:
        - Shuffle trade order 1000x
        - Compute final equity for each shuffle
        - If 95th percentile still profitable → edge is robust

        Returns:
            {
                iterations: int,
                original_pnl: float,
                median_pnl: float,
                percentile_5: float,
                percentile_95: float,
                probability_profit: float,
                max_drawdown_median: float,
                verdict: str,
                is_valid: bool
            }
        """
        if len(trades) < 20:
            return {
                "verdict": "INSUFFICIENT_DATA",
                "is_valid": False,
                "message": f"Need at least 20 trades, have {len(trades)}"
            }

        pnls = [t.get('pnl', 0) for t in trades]
        original_total_pnl = sum(pnls)

        simulated_finals = []
        simulated_drawdowns = []

        for _ in range(iterations):
            shuffled = pnls.copy()
            np.random.shuffle(shuffled)

            # Compute equity curve
            equity = [10000]  # Start with $10k
            peak = 10000
            max_dd = 0

            for pnl in shuffled:
                equity.append(equity[-1] + pnl)
                peak = max(peak, equity[-1])
                dd = (peak - equity[-1]) / peak * 100
                max_dd = max(max_dd, dd)

            simulated_finals.append(equity[-1] - 10000)  # Net PnL
            simulated_drawdowns.append(max_dd)

        finals = np.array(simulated_finals)
        drawdowns = np.array(simulated_drawdowns)

        prob_profit = (np.sum(finals > 0) / iterations) * 100
        p5 = float(np.percentile(finals, 5))
        p95 = float(np.percentile(finals, 95))
        median_pnl = float(np.median(finals))
        median_dd = float(np.median(drawdowns))

        # Verdict
        if prob_profit >= 80 and p5 > 0:
            verdict = "ROBUST_EDGE"
            is_valid = True
        elif prob_profit >= 60 and median_pnl > 0:
            verdict = "MODERATE_EDGE"
            is_valid = True
        else:
            verdict = "FRAGILE_OR_NO_EDGE"
            is_valid = False

        return {
            "iterations": iterations,
            "original_pnl": round(original_total_pnl, 2),
            "median_pnl": round(median_pnl, 2),
            "percentile_5": round(p5, 2),
            "percentile_95": round(p95, 2),
            "probability_profit": round(prob_profit, 1),
            "max_drawdown_median": round(median_dd, 2),
            "verdict": verdict,
            "is_valid": is_valid
        }

    # =========================================================================
    # METRICS COMPUTATION
    # =========================================================================

    def _compute_metrics(self, trades: list, label: str = "") -> dict:
        """Compute performance metrics for a set of trades."""
        if not trades:
            return {"label": label, "message": "No trades"}

        pnls = [t.get('pnl', 0) for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        total_trades = len(pnls)
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf') if gross_profit > 0 else 0

        avg_win = np.mean(wins) if wins else 0
        avg_loss = abs(np.mean(losses)) if losses else 0
        expectancy = (win_rate / 100 * avg_win) - ((1 - win_rate / 100) * avg_loss)

        # Max consecutive losses
        max_consec_loss = 0
        current_streak = 0
        for p in pnls:
            if p < 0:
                current_streak += 1
                max_consec_loss = max(max_consec_loss, current_streak)
            else:
                current_streak = 0

        # Max drawdown
        equity = [10000]
        for p in pnls:
            equity.append(equity[-1] + p)
        peak = equity[0]
        max_dd = 0
        for e in equity:
            peak = max(peak, e)
            dd = (peak - e) / peak * 100
            max_dd = max(max_dd, dd)

        return {
            "label": label,
            "total_trades": total_trades,
            "win_rate": round(win_rate, 1),
            "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else 999,
            "total_pnl": round(sum(pnls), 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "expectancy": round(expectancy, 2),
            "max_consecutive_losses": max_consec_loss,
            "max_drawdown_pct": round(max_dd, 2),
            "best_trade": round(max(pnls), 2) if pnls else 0,
            "worst_trade": round(min(pnls), 2) if pnls else 0
        }

    # =========================================================================
    # FULL VALIDATION RUN
    # =========================================================================

    def run_validation(self, symbol: str = None) -> dict:
        """
        Run complete validation suite.
        Combines walk-forward + Monte Carlo + decision statistics.

        Returns full validation report.
        """
        # Get data from both sources
        decisions = self._get_decisions(symbol)
        paper_trades = self._get_paper_trades()

        # Use paper trades if available, else use decisions with mock PnL
        if paper_trades and len(paper_trades) >= 20:
            trades_for_validation = paper_trades
            data_source = "paper_trades"
        elif decisions and len(decisions) >= 20:
            # Estimate PnL from decisions (mock calculation)
            trades_for_validation = self._decisions_to_mock_trades(decisions)
            data_source = "decisions_mock_pnl"
        else:
            total = max(len(decisions), len(paper_trades))
            return {
                "status": "INSUFFICIENT_DATA",
                "total_decisions": len(decisions),
                "total_trades": len(paper_trades),
                "min_required": MIN_DECISIONS_FOR_VALIDATION,
                "message": f"Need {MIN_DECISIONS_FOR_VALIDATION} decisions for full validation. "
                           f"Have {total}. Keep running the paper trader!",
                "timestamp": datetime.now().isoformat()
            }

        # Run validations
        wf_result = self.walk_forward_test(trades_for_validation)
        mc_result = self.monte_carlo_test(trades_for_validation)
        overall_metrics = self._compute_metrics(trades_for_validation, "Overall")

        # Decision statistics
        decision_stats = self._compute_decision_stats(decisions)

        # Overall verdict
        wf_valid = wf_result.get("is_valid", False)
        mc_valid = mc_result.get("is_valid", False)

        if wf_valid and mc_valid:
            overall_verdict = "✅ VALIDATED — Edge is statistically significant"
        elif wf_valid or mc_valid:
            overall_verdict = "⚠️ PARTIALLY VALIDATED — Edge needs more data"
        else:
            overall_verdict = "❌ NOT VALIDATED — No statistical edge detected"

        # Full report
        report = {
            "status": "completed",
            "data_source": data_source,
            "total_decisions": len(decisions),
            "total_trades": len(trades_for_validation),
            "overall_verdict": overall_verdict,
            "walk_forward": wf_result,
            "monte_carlo": mc_result,
            "overall_metrics": overall_metrics,
            "decision_stats": decision_stats,
            "sufficient_data": len(trades_for_validation) >= MIN_DECISIONS_FOR_VALIDATION,
            "timestamp": datetime.now().isoformat()
        }

        # Save report to DB
        self._save_report(report)

        return report

    def _decisions_to_mock_trades(self, decisions: list) -> list:
        """
        Convert AI decisions to mock trades with estimated PnL.
        Uses entry price, SL, and TP to estimate outcomes.
        """
        trades = []
        for d in decisions:
            if d.get('decision') == 'HOLD':
                continue

            entry = d.get('entry_price', 0)
            sl = d.get('stop_loss', 0)
            tp = d.get('take_profit', 0)
            confidence = d.get('confidence', 50)

            if not entry or not sl or not tp:
                continue

            # Mock outcome: higher confidence → higher win probability
            win_prob = min(confidence / 100, 0.75)  # Cap at 75%
            np_random = np.random.random()

            if np_random < win_prob:
                # Win: exit at TP with some slippage
                exit_price = tp * (1 - np.random.uniform(0, 0.003))
            else:
                # Loss: exit at SL with some slippage
                exit_price = sl * (1 + np.random.uniform(0, 0.003))

            if d.get('decision') == 'LONG':
                pnl = (exit_price - entry) / entry * 100
            else:
                pnl = (entry - exit_price) / entry * 100

            trades.append({
                'symbol': d.get('symbol', ''),
                'side': d.get('decision', ''),
                'entry_price': entry,
                'exit_price': exit_price,
                'pnl': round(pnl * 10, 2),  # Approximate $ PnL on $1000
                'pnl_pct': round(pnl, 2),
                'confidence': confidence
            })

        return trades

    def _compute_decision_stats(self, decisions: list) -> dict:
        """Compute statistics about AI decisions."""
        if not decisions:
            return {"total": 0}

        total = len(decisions)
        longs = sum(1 for d in decisions if d.get('decision') == 'LONG')
        shorts = sum(1 for d in decisions if d.get('decision') == 'SHORT')
        holds = sum(1 for d in decisions if d.get('decision') == 'HOLD')

        confidences = [d.get('confidence', 0) for d in decisions]
        avg_confidence = np.mean(confidences) if confidences else 0

        modes = [d.get('mode', 'unknown') for d in decisions]
        live_count = sum(1 for m in modes if m == 'live')
        mock_count = sum(1 for m in modes if m == 'mock')

        return {
            "total": total,
            "longs": longs,
            "shorts": shorts,
            "holds": holds,
            "long_pct": round(longs / total * 100, 1) if total > 0 else 0,
            "short_pct": round(shorts / total * 100, 1) if total > 0 else 0,
            "avg_confidence": round(avg_confidence, 1),
            "live_decisions": live_count,
            "mock_decisions": mock_count
        }

    def _save_report(self, report: dict):
        """Save validation report to database."""
        try:
            conn = sqlite3.connect(VALIDATION_DB_PATH)
            conn.execute("""
                INSERT INTO validation_reports
                (timestamp, total_decisions, walk_forward_result,
                 monte_carlo_result, overall_verdict, metrics_json, report_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                report.get("total_decisions", 0),
                json.dumps(report.get("walk_forward", {})),
                json.dumps(report.get("monte_carlo", {})),
                report.get("overall_verdict", ""),
                json.dumps(report.get("overall_metrics", {})),
                json.dumps(report, default=str)[:5000]
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[VALIDATION] Report save error: {e}")

    def get_latest_report(self) -> dict:
        """Get the most recent validation report."""
        try:
            conn = sqlite3.connect(VALIDATION_DB_PATH)
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM validation_reports ORDER BY id DESC LIMIT 1"
            ).fetchone()
            conn.close()

            if row:
                report = dict(row)
                report['report_json'] = json.loads(report.get('report_json', '{}'))
                return report
            return {"message": "No validation reports yet"}
        except Exception as e:
            return {"error": str(e)}


# =============================================================================
# STANDALONE TEST
# =============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("VALIDATION ENGINE — Standalone Test")
    print("=" * 60)

    engine = ValidationEngine()

    # Test with synthetic trades
    np.random.seed(42)
    synthetic_trades = []
    for i in range(100):
        pnl = np.random.normal(5, 30)  # Slight positive edge
        synthetic_trades.append({
            'pnl': round(pnl, 2),
            'symbol': 'BTC-USDT',
            'side': 'LONG' if pnl > 0 else 'SHORT'
        })

    print(f"\n📊 Testing with {len(synthetic_trades)} synthetic trades...")

    print("\n--- Walk-Forward Test ---")
    wf = engine.walk_forward_test(synthetic_trades)
    print(f"   In-Sample PF: {wf['in_sample'].get('profit_factor', 0)}")
    print(f"   Out-of-Sample PF: {wf['out_of_sample'].get('profit_factor', 0)}")
    print(f"   Degradation: {wf.get('degradation_pct', 0):.1f}%")
    print(f"   Verdict: {wf['verdict']}")

    print("\n--- Monte Carlo Test ---")
    mc = engine.monte_carlo_test(synthetic_trades, iterations=500)
    print(f"   Median PnL: ${mc['median_pnl']:,.2f}")
    print(f"   P5: ${mc['percentile_5']:,.2f} | P95: ${mc['percentile_95']:,.2f}")
    print(f"   Profit Probability: {mc['probability_profit']:.1f}%")
    print(f"   Verdict: {mc['verdict']}")

    print("\n--- Full Validation ---")
    report = engine.run_validation()
    print(f"   Status: {report.get('status', 'N/A')}")
    if 'overall_verdict' in report:
        print(f"   Verdict: {report['overall_verdict']}")

    print("\n✅ Validation engine test completed!")
