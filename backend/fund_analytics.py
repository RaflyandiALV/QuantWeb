# backend/fund_analytics.py
"""
FundAnalytics — Advanced hedge fund performance metrics.

Calculates:
- Sharpe Ratio, Sortino Ratio, Calmar Ratio
- Max Drawdown
- Win Rate, Avg Win/Loss
- Monthly Returns Heatmap
- Total Return, CAGR (Projected)
"""
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

DB_FILE = "market_data.db"

def _get_db_conn():
    try:
        return sqlite3.connect(DB_FILE, check_same_thread=False)
    except Exception as e:
        print(f"❌ FundAnalytics DB Error: {e}")
        return None

def get_fund_performance():
    """
    Calculate comprehensive fund performance metrics.
    returns: dict of metrics
    """
    metrics = {
        "total_return_pct": 0.0,
        "sharpe_ratio": 0.0,
        "sortino_ratio": 0.0,
        "max_drawdown_pct": 0.0,
        "calmar_ratio": 0.0,
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "avg_win": 0.0,
        "avg_loss": 0.0,
        "trades_count": 0,
        "monthly_returns": {}
    }

    try:
        conn = _get_db_conn()
        if not conn: return metrics

        # 1. Trade Analysis (Win Rate, Profit Factor, etc.)
        trades_df = pd.read_sql_query("SELECT pnl, close_time FROM trade_log WHERE status='FILLED' OR status='CLOSED' ORDER BY id ASC", conn)
        
        if not trades_df.empty:
            pnl = trades_df['pnl'].fillna(0)
            wins = pnl[pnl > 0]
            losses = pnl[pnl <= 0]
            
            metrics['trades_count'] = len(pnl)
            if len(pnl) > 0:
                metrics['win_rate'] = (len(wins) / len(pnl)) * 100
                metrics['avg_win'] = wins.mean() if not wins.empty else 0
                metrics['avg_loss'] = losses.mean() if not losses.empty else 0
                
                gross_profit = wins.sum()
                gross_loss = abs(losses.sum())
                metrics['profit_factor'] = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0)

        # 2. Portfolio/Equity Analysis (Sharpe, Drawdown, Returns)
        # We need daily snapshots for these metrics to be accurate
        # For now, we'll resample existing snapshots to daily close
        snapshots_df = pd.read_sql_query("SELECT total_equity, created_at FROM portfolio_snapshots ORDER BY id ASC", conn)
        
        if not snapshots_df.empty:
            snapshots_df['created_at'] = pd.to_datetime(snapshots_df['created_at'])
            snapshots_df.set_index('created_at', inplace=True)
            
            # Resample to daily frequency (taking the last value of each day)
            daily_equity = snapshots_df['total_equity'].resample('D').last().dropna()
            
            if len(daily_equity) > 1:
                # Calculate Daily Returns
                daily_returns = daily_equity.pct_change().dropna()
                
                # Total Return
                start_eq = daily_equity.iloc[0]
                end_eq = daily_equity.iloc[-1]
                if start_eq > 0:
                    metrics['total_return_pct'] = ((end_eq - start_eq) / start_eq) * 100

                # Max Drawdown
                rolling_max = daily_equity.cummax()
                drawdown = (daily_equity - rolling_max) / rolling_max
                metrics['max_drawdown_pct'] = abs(drawdown.min()) * 100

                # Sharpe Ratio (assuming risk-free rate = 0 for simplicity, annualized)
                if daily_returns.std() > 0:
                    metrics['sharpe_ratio'] = (daily_returns.mean() / daily_returns.std()) * np.sqrt(365) # Crypto trades 24/7/365

                # Sortino Ratio (downside deviation only)
                negative_returns = daily_returns[daily_returns < 0]
                if not negative_returns.empty and negative_returns.std() > 0:
                     metrics['sortino_ratio'] = (daily_returns.mean() / negative_returns.std()) * np.sqrt(365)

                # Calmar Ratio
                if metrics['max_drawdown_pct'] > 0:
                    # Annualized Return approx
                    days = (daily_equity.index[-1] - daily_equity.index[0]).days
                    if days > 0:
                        annual_ret = metrics['total_return_pct'] / (days / 365.0)
                        metrics['calmar_ratio'] = annual_ret / metrics['max_drawdown_pct']

                # Monthly Returns Heatmap
                # Group by Year-Month
                monthly_groups = daily_returns.groupby(pd.Grouper(freq='M'))
                monthly_data = {}
                
                for date, monthly_ret in monthly_groups:
                    # Compounding daily returns to get monthly return
                    # (1+r1)*(1+r2)... - 1
                    m_ret = (1 + monthly_ret).prod() - 1
                    
                    year = date.year
                    month_name = date.strftime('%b') # Jan, Feb...
                    
                    if year not in monthly_data:
                        monthly_data[year] = {}
                    
                    monthly_data[year][month_name] = round(m_ret * 100, 2)
                
                metrics['monthly_returns'] = monthly_data

        conn.close()
        
        # Rounding
        for k, v in metrics.items():
            if isinstance(v, float):
                metrics[k] = round(v, 2)
                
    except Exception as e:
        print(f"⚠️ Fund Calc Error: {e}")

    return metrics
