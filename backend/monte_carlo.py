# backend/monte_carlo.py
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple

class MonteCarloEngine:
    """
    Monte Carlo Simulation Engine for Trading Strategies.
    Uses bootstrap resampling of historical trades to generate probability distributions
    of future performance, providing deep insights into tail risk (VaR, CVaR).
    """
    
    def __init__(self, initial_capital: float = 1000.0, num_simulations: int = 5000):
        self.initial_capital = initial_capital
        self.num_simulations = num_simulations

    def run_simulation(self, trades: List[Dict]) -> Dict:
        """
        Run Monte Carlo simulation on a list of historical trades.
        
        Args:
            trades: List of dicts containing 'pnl_pct' (e.g. 0.05 for 5% win, -0.02 for 2% loss)
                    If trading engine logs absolute PnL, convert to % before passing.
                    
        Returns:
            Dictionary with comprehensive risk metrics and chart data.
        """
        if not trades or len(trades) < 5:
            return {"error": "Not enough historical trades for meaningful simulation (minimum 5 required)."}

        # Extract returns array
        returns = np.array([t.get('pnl_pct', 0) / 100.0 if t.get('pnl_pct', 0) > 1 or t.get('pnl_pct', 0) < -1 else t.get('pnl_pct', 0) for t in trades])
        num_trades = len(returns)

        # Pre-allocate array for all simulated equity curves (simulations x trades)
        simulated_paths = np.zeros((self.num_simulations, num_trades + 1))
        simulated_paths[:, 0] = self.initial_capital

        # Bootstrap resampling (with replacement)
        # Randomly pick indices from 0 to num_trades-1, shape (simulations, num_trades)
        random_indices = np.random.randint(0, num_trades, size=(self.num_simulations, num_trades))
        
        # Get the sampled returns
        sampled_returns = returns[random_indices]
        
        # Calculate cumulative equity paths
        # Equity[t] = Equity[t-1] * (1 + return[t])
        # Using cumulative product along the trading axis (axis=1)
        multipliers = 1 + sampled_returns
        simulated_paths[:, 1:] = self.initial_capital * np.cumprod(multipliers, axis=1)

        # Calculate final equity distribution
        final_equities = simulated_paths[:, -1]
        
        # Calculate drawdowns for each path
        # Running max for each path
        running_max = np.maximum.accumulate(simulated_paths, axis=1)
        # Drawdown = (Running Max - Current) / Running Max
        drawdowns = (running_max - simulated_paths) / running_max
        max_drawdowns = np.max(drawdowns, axis=1) * 100  # convert to %

        # --- Compute Institutional Risk Metrics ---
        # 1. Percentiles of Final Equity
        percentiles = [1, 5, 25, 50, 75, 95, 99]
        equity_dist = {f"p{p}": float(np.percentile(final_equities, p)) for p in percentiles}
        
        # 2. Daily/Trade VaR (Value at Risk) — 95% Confidence
        # This means 95% of the time, the strategy will NOT lose more than X%
        var_95 = float(np.percentile(returns, 5)) * 100
        
        # 3. CVaR / Expected Shortfall (95%)
        # The average loss when the loss actually exceeds the VaR threshold (tail risk)
        worst_5_pct_returns = returns[returns < (var_95 / 100)]
        cvar_95 = float(np.mean(worst_5_pct_returns)) * 100 if len(worst_5_pct_returns) > 0 else var_95

        # 4. Probability of Ruin (Ending with less than 80% of initial capital)
        ruin_threshold = self.initial_capital * 0.8
        ruin_prob = float(np.sum(final_equities < ruin_threshold) / self.num_simulations) * 100

        # 5. Kelly Criterion (Optimal fraction of capital to risk)
        win_rate = float(np.mean(returns > 0))
        if win_rate > 0 and win_rate < 1.0:
            avg_win = float(np.mean(returns[returns > 0]))
            avg_loss = abs(float(np.mean(returns[returns < 0])))
            if avg_loss > 0:
                win_loss_ratio = avg_win / avg_loss
                kelly_pct = (win_rate - ((1 - win_rate) / win_loss_ratio)) * 100
            else:
                kelly_pct = 100.0
        else:
            kelly_pct = 0.0

        kelly_pct = max(0, min(100, kelly_pct))  # Clamp between 0 and 100
        half_kelly = kelly_pct / 2.0  # Industry standard is trading Half-Kelly

        # --- Generate Chart Data ---
        # We don't send all 5000 lines to the frontend, just percentiles over time
        chart_data = []
        for step in range(num_trades + 1):
            step_values = simulated_paths[:, step]
            chart_data.append({
                "trade": step,
                "median": float(np.median(step_values)),
                "p5": float(np.percentile(step_values, 5)),    # Lower bound (conservative)
                "p95": float(np.percentile(step_values, 95)),  # Upper bound (optimistic)
            })

        return {
            "metrics": {
                "simulations_run": self.num_simulations,
                "median_final_equity": round(equity_dist["p50"], 2),
                "worst_case_equity_p5": round(equity_dist["p5"], 2),
                "best_case_equity_p95": round(equity_dist["p95"], 2),
                "median_max_drawdown_pct": round(float(np.median(max_drawdowns)), 2),
                "worst_case_drawdown_p95_pct": round(float(np.percentile(max_drawdowns, 95)), 2),
                "probability_of_ruin_pct": round(ruin_prob, 2),
                "var_95_pct": round(var_95, 2),
                "cvar_95_pct": round(cvar_95, 2),
                "kelly_criterion_pct": round(kelly_pct, 2),
                "half_kelly_pct": round(half_kelly, 2),
            },
            "chart_data": chart_data
        }
