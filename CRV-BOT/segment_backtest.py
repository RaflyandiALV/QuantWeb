import backtest
import pandas as pd
import builtins

def dummy_print(*args, **kwargs):
    pass

orig_print = builtins.print

def run_segment_analysis():
    orig_print("Fetching max history data...")
    builtins.print = dummy_print
    df_raw = backtest.fetch_ohlcv_1y()
    df_ind = backtest.compute_indicators(df_raw)
    builtins.print = orig_print
    
    quarters = [
        ("2023 Q1", "2023-01-01", "2023-03-31"),
        ("2023 Q2", "2023-04-01", "2023-06-30"),
        ("2023 Q3", "2023-07-01", "2023-09-30"),
        ("2023 Q4", "2023-10-01", "2023-12-31"),
        ("2024 Q1", "2024-01-01", "2024-03-31"),
        ("2024 Q2", "2024-04-01", "2024-06-30"),
        ("2024 Q3", "2024-07-01", "2024-09-30"),
        ("2024 Q4", "2024-10-01", "2024-12-31"),
        ("2025 Q1", "2025-01-01", "2025-03-31"),
        ("2025 Q2", "2025-04-01", "2025-06-30"),
        ("2025 Q3", "2025-07-01", "2025-09-30"),
        ("2025 Q4", "2025-10-01", "2025-12-31"),
        ("2026 Q1", "2026-01-01", "2026-03-31"),
    ]
    
    results = []
    
    orig_print("Running quarterly analysis loop (Fixed capital $10k per Quarter)...")
    orig_print(f"{'Period':<10} | {'Final Eq ($)':<12} | {'Return %':<10} | {'Max DD %':<10} | {'Trades':<8} | {'Win Rate %':<10}")
    orig_print("-" * 78)
    
    # Ensure optimal parameters
    backtest.CIRCUIT_BREAKER_DD = 0.50
    backtest.STOP_LOSS_PCT = 0.15
    
    for label, start, end in quarters:
        start_dt = pd.to_datetime(start).tz_localize('UTC')
        end_dt = pd.to_datetime(end + " 23:59:59").tz_localize('UTC')
        
        mask = (df_ind["timestamp"] >= start_dt) & (df_ind["timestamp"] <= end_dt)
        df_quarter = df_ind.loc[mask].copy().reset_index(drop=True)
        
        if len(df_quarter) < 50:
            continue
            
        builtins.print = dummy_print 
        df_res, trades, sig_l, sig_s, sig_sl, sig_cb = backtest.run_backtest(df_quarter)
        equity_curve = df_res["equity"]
        stats = backtest.compute_stats(trades, backtest.INITIAL_CAPITAL, equity_curve)
        builtins.print = orig_print
        
        final_eq = stats.get('final_equity', backtest.INITIAL_CAPITAL)
        ret_pct = stats.get('total_return_pct', 0)
        max_dd = stats.get('max_drawdown_pct', 0)
        num_trades = stats.get('total_trades', 0)
        win_rate = stats.get('win_rate', 0)
        
        orig_print(f"{label:<10} | {final_eq:<12,.2f} | {ret_pct:>+8.2f}% | {max_dd:>+8.2f}% | {num_trades:<8} | {win_rate:>8.1f}%")

if __name__ == "__main__":
    run_segment_analysis()
