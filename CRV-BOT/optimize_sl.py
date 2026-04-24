import backtest
import pandas as pd
import builtins

def dummy_print(*args, **kwargs):
    pass

orig_print = builtins.print

def run_sl_optimization():
    orig_print("Fetching data (1 year) for Stop Loss optimization...")
    builtins.print = dummy_print
    df_raw = backtest.fetch_ohlcv_1y()
    df_ind = backtest.compute_indicators(df_raw)
    builtins.print = orig_print
    
    sl_values = range(5, 55, 5) # 5%, 10%, ..., 50%
    results = []
    
    orig_print("Running SL optimization loop (CB fixed at 50%)...")
    orig_print(f"{'SL %':<5} | {'Final Eq ($)':<12} | {'Return %':<10} | {'Max DD %':<10} | {'Trades':<8} | {'Win Rate':<8} | {'SL Hits':<8}")
    orig_print("-" * 80)
    
    backtest.CIRCUIT_BREAKER_DD = 0.50
    
    for sl in sl_values:
        backtest.STOP_LOSS_PCT = sl / 100.0
        
        builtins.print = dummy_print 
        df_res, trades, sig_l, sig_s, sig_sl, sig_cb = backtest.run_backtest(df_ind)
        equity_curve = df_res["equity"]
        stats = backtest.compute_stats(trades, backtest.INITIAL_CAPITAL, equity_curve)
        builtins.print = orig_print
        
        final_eq = stats.get('final_equity', backtest.INITIAL_CAPITAL)
        ret_pct = stats.get('total_return_pct', 0)
        max_dd = stats.get('max_drawdown_pct', 0)
        num_trades = stats.get('total_trades', 0)
        win_rate = stats.get('win_rate', 0)
        sl_hits = sum(1 for t in trades if t['exit_reason'] == 'stop_loss')
        
        results.append({
            'sl': sl,
            'final_equity': final_eq,
            'total_return': ret_pct,
            'max_drawdown': max_dd,
            'total_trades': num_trades,
            'win_rate': win_rate,
            'sl_hits': sl_hits
        })
        
        orig_print(f"{sl:>3}% | {final_eq:<12,.2f} | {ret_pct:>+8.2f}% | {max_dd:>+8.2f}% | {num_trades:<8} | {win_rate:>6.1f}% | {sl_hits:<8}")

    best_ret = max(results, key=lambda x: x['total_return'])
    orig_print("\n==============================================")
    orig_print(">>> BEST PERFORMER BY TOTAL RETURN <<<")
    orig_print("==============================================")
    orig_print(f"Stop Loss Parameter      : {best_ret['sl']}%")
    orig_print(f"Final Equity             : ${best_ret['final_equity']:,.2f}")
    orig_print(f"Total Return             : {best_ret['total_return']:+.2f}%")
    orig_print(f"Max Drawdown             : {best_ret['max_drawdown']:+.2f}%")
    orig_print(f"Win Rate                 : {best_ret['win_rate']:.1f}%")

if __name__ == "__main__":
    run_sl_optimization()
