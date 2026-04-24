import backtest
import pandas as pd
import builtins

def dummy_print(*args, **kwargs):
    pass

orig_print = builtins.print

def run_optimization():
    orig_print("Fetching data (this takes a moment)...")
    builtins.print = dummy_print
    df_raw = backtest.fetch_ohlcv_1y()
    df_ind = backtest.compute_indicators(df_raw)
    builtins.print = orig_print
    
    cb_values = range(5, 70, 5) # 5%, 10%, ..., 65%
    results = []
    
    orig_print("Running optimization loop...")
    orig_print(f"{'CB %':<5} | {'Final Eq':<12} | {'Return %':<10} | {'Max DD %':<10} | {'Trades':<8} | {'Win Rate':<8} | {'CB Hits':<8}")
    orig_print("-" * 75)
    
    for cb in cb_values:
        backtest.CIRCUIT_BREAKER_DD = cb / 100.0
        
        # Mute prints inside run_backtest and compute_stats
        builtins.print = dummy_print 
        
        df_res, trades, sig_l, sig_s, sig_sl, sig_cb = backtest.run_backtest(df_ind)
        equity_curve = df_res["equity"]
        stats = backtest.compute_stats(trades, backtest.INITIAL_CAPITAL, equity_curve)
        
        # Restore print
        builtins.print = orig_print
        
        final_eq = stats.get('final_equity', backtest.INITIAL_CAPITAL)
        ret_pct = stats.get('total_return_pct', 0)
        max_dd = stats.get('max_drawdown_pct', 0)
        num_trades = stats.get('total_trades', 0)
        win_rate = stats.get('win_rate', 0)
        cb_hits = stats.get('cb_count', 0)
        
        results.append({
            'cb': cb,
            'final_equity': final_eq,
            'total_return': ret_pct,
            'max_drawdown': max_dd,
            'total_trades': num_trades,
            'win_rate': win_rate,
            'cb_hits': cb_hits
        })
        
        orig_print(f"{cb:>3}% | ${final_eq:<11,.2f} | {ret_pct:>+8.2f}% | {max_dd:>+8.2f}% | {num_trades:<8} | {win_rate:>6.1f}% | {cb_hits:<8}")

    best_ret = max(results, key=lambda x: x['total_return'])
    orig_print("\n==============================================")
    orig_print(">>> BEST PERFORMER BY TOTAL RETURN <<<")
    orig_print("==============================================")
    orig_print(f"Circuit Breaker Parameter: {best_ret['cb']}%")
    orig_print(f"Final Equity             : ${best_ret['final_equity']:,.2f}")
    orig_print(f"Total Return             : {best_ret['total_return']:+.2f}%")
    orig_print(f"Max Drawdown             : {best_ret['max_drawdown']:+.2f}%")
    orig_print(f"Win Rate                 : {best_ret['win_rate']:.1f}%")

if __name__ == "__main__":
    run_optimization()
