"""
Extended Cooldown Optimization: 1-14 hari (6 - 84 candles @ 4H)
SL=20%, CB=50% fixed.
"""
import backtest
import pandas as pd
import builtins

def dummy_print(*args, **kwargs):
    pass
orig_print = builtins.print

def run():
    orig_print("Fetching data (1 year) for Extended Cooldown optimization...")
    builtins.print = dummy_print
    df_raw = backtest.fetch_ohlcv_1y()
    df_ind = backtest.compute_indicators(df_raw)
    builtins.print = orig_print

    # 0 candles (no cooldown) + 1-14 days
    cd_values = [0] + [d * 6 for d in range(1, 15)]  # 0, 6, 12, 18, ..., 84
    results = []

    backtest.STOP_LOSS_PCT = 0.20
    backtest.CIRCUIT_BREAKER_DD = 0.50

    orig_print(f"{'Hari':<6} | {'CD':<4} | {'Final Eq ($)':<16} | {'Return %':<12} | {'Max DD %':<10} | {'Trades':<8} | {'Win %':<7} | {'SL':<4} | {'CB':<4} | {'PF':<6} | {'Sharpe':<7} | {'Calmar':<8}")
    orig_print("-" * 120)

    for cd in cd_values:
        backtest.COOLDOWN_CANDLES = cd

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
        pf = stats.get('profit_factor', 0)
        sharpe = stats.get('sharpe_ratio', 0)
        calmar = stats.get('calmar_ratio', 0)
        sl_hits = sum(1 for t in trades if t['exit_reason'] == 'stop_loss')
        cb_hits = sum(1 for t in trades if t['exit_reason'] == 'circuit_breaker')
        days = cd * 4 / 24

        results.append({
            'days': days, 'cd': cd, 'final_equity': final_eq,
            'total_return': ret_pct, 'max_drawdown': max_dd,
            'total_trades': num_trades, 'win_rate': win_rate,
            'sl_hits': sl_hits, 'cb_hits': cb_hits,
            'pf': pf, 'sharpe': sharpe, 'calmar': calmar
        })

        orig_print(f"{days:<6.0f} | {cd:<4} | {final_eq:<16,.2f} | {ret_pct:>+10.2f}% | {max_dd:>+8.2f}% | {num_trades:<8} | {win_rate:>5.1f}% | {sl_hits:<4} | {cb_hits:<4} | {pf:<5.2f}x | {sharpe:<6.2f} | {calmar:<8.2f}")

    best_ret = max(results, key=lambda x: x['total_return'])
    best_risk = max(results, key=lambda x: x['total_return'] / abs(x['max_drawdown']) if x['max_drawdown'] != 0 else 0)

    orig_print("\n" + "=" * 60)
    orig_print(">>> BEST BY TOTAL RETURN <<<")
    orig_print(f"    Cooldown: {best_ret['days']:.0f} hari ({best_ret['cd']} candles)")
    orig_print(f"    Return: {best_ret['total_return']:+.2f}% | Equity: ${best_ret['final_equity']:,.2f}")
    orig_print(f"    Max DD: {best_ret['max_drawdown']:+.2f}% | Win Rate: {best_ret['win_rate']:.1f}%")
    orig_print(f"    Calmar: {best_ret['calmar']:.2f} | Sharpe: {best_ret['sharpe']:.2f}")

    orig_print("\n>>> BEST RISK-ADJUSTED (Calmar) <<<")
    orig_print(f"    Cooldown: {best_risk['days']:.0f} hari ({best_risk['cd']} candles)")
    orig_print(f"    Return: {best_risk['total_return']:+.2f}% | Equity: ${best_risk['final_equity']:,.2f}")
    orig_print(f"    Max DD: {best_risk['max_drawdown']:+.2f}% | Win Rate: {best_risk['win_rate']:.1f}%")
    orig_print(f"    Calmar: {best_risk['calmar']:.2f} | Sharpe: {best_risk['sharpe']:.2f}")

if __name__ == "__main__":
    run()
