# ============================================================
# CRV/USDT — Monte Carlo Price Path Simulation
# Google Colab Ready
#
# Struktur:
#   SECTION 1 — Install & Import
#   SECTION 2 — Fetch Data dari Bybit (4H, match bot config)
#   SECTION 3 — Bootstrap Monte Carlo Engine
#   SECTION 4 — BACKTEST VALIDATION
#               Train: data s/d bulan lalu
#               Test : prediksi bulan ini, bandingkan vs aktual
#   SECTION 5 — FORWARD SIMULATION (1 bulan ke depan)
#   SECTION 6 — Summary Report
# ============================================================


# ╔══════════════════════════════════════════════════════════╗
# ║  SECTION 1 — Install & Import                           ║
# ╚══════════════════════════════════════════════════════════╝

# Jalankan sel ini pertama kali di Colab
# import subprocess, sys
# def install(pkg):
#     subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg])
# install("ccxt")

import sys
import io
# Fix untuk Windows Console Unicode Error (Emoji)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import ccxt
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from datetime import datetime, timezone, timedelta
from scipy import stats
import warnings
warnings.filterwarnings("ignore")

# Colab display config
plt.rcParams.update({
    "figure.facecolor"  : "#0f172a",
    "axes.facecolor"    : "#1e293b",
    "axes.edgecolor"    : "#334155",
    "axes.labelcolor"   : "#94a3b8",
    "xtick.color"       : "#64748b",
    "ytick.color"       : "#64748b",
    "grid.color"        : "#1e3a5f",
    "grid.alpha"        : 0.4,
    "text.color"        : "#e2e8f0",
    "font.family"       : "monospace",
    "font.size"         : 10,
    "legend.facecolor"  : "#1e293b",
    "legend.edgecolor"  : "#334155",
})

print("✅ Libraries loaded.")


# ╔══════════════════════════════════════════════════════════╗
# ║  SECTION 2 — Fetch CRV/USDT 4H dari Bybit              ║
# ╚══════════════════════════════════════════════════════════╝

SYMBOL    = "CRV/USDT:USDT"   # Bybit perpetual — persis dari config.py bot
TIMEFRAME = "4h"
EXCHANGE  = "bybit"

# Ambil data 1 tahun ke belakang untuk sampling yang cukup
FETCH_DAYS = 365

def fetch_ohlcv(symbol=SYMBOL, timeframe=TIMEFRAME, days=FETCH_DAYS) -> pd.DataFrame:
    """
    Fetch historical OHLCV dari Bybit via CCXT.
    Tidak butuh API key — public endpoint.
    """
    exchange = ccxt.bybit({
        "enableRateLimit": True,
        "options": {"defaultType": "swap"},
    })

    since_ms  = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)
    all_ohlcv = []
    limit     = 200  # Bybit max per request

    print(f"📥 Fetching {symbol} [{timeframe}] — last {days} days from Bybit...")

    while True:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since_ms, limit=limit)
        if not ohlcv:
            break
        all_ohlcv.extend(ohlcv)
        last_ts  = ohlcv[-1][0]
        since_ms = last_ts + 1
        if len(ohlcv) < limit:
            break

    df = pd.DataFrame(all_ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df.drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)

    # Drop incomplete last candle
    df = df.iloc[:-1]

    print(f"✅ {len(df)} candles fetched | {df['timestamp'].iloc[0].date()} → {df['timestamp'].iloc[-1].date()}")
    return df


df_full = fetch_ohlcv()

# Tampilkan sample
print("\n📊 Sample data (tail 5):")
print(df_full.tail(5)[["timestamp", "open", "high", "low", "close", "volume"]].to_string(index=False))


# ╔══════════════════════════════════════════════════════════╗
# ║  SECTION 3 — Bootstrap Monte Carlo Engine              ║
# ╚══════════════════════════════════════════════════════════╝

class MonteCarloPathEngine:
    """
    Monte Carlo Price Path via Bootstrap Resampling.

    Kenapa Bootstrap (bukan GBM):
    - Tidak ada asumsi distribusi normal
    - Fat tails crypto otomatis ikut
    - Volatility clustering otomatis ikut
    - Lebih relevan untuk crypto vs saham

    Output: fan chart P5/P25/P50/P75/P95 + probability metrics
    """

    def __init__(self, n_simulations: int = 10_000, random_seed: int = 42):
        self.n_sim = n_simulations
        np.random.seed(random_seed)

    # ── Core: hitung returns dari candle data ──────────────────
    def extract_returns(self, df: pd.DataFrame) -> np.ndarray:
        returns = df["close"].pct_change().dropna().values
        return returns

    def describe_returns(self, returns: np.ndarray, label: str = "Training") -> None:
        print(f"\n{'─'*50}")
        print(f"📈 Return Statistics [{label}]")
        print(f"{'─'*50}")
        print(f"  N candles    : {len(returns):,}")
        print(f"  Mean / candle: {returns.mean()*100:+.4f}%")
        print(f"  Std Dev      : {returns.std()*100:.4f}%")
        print(f"  Min          : {returns.min()*100:+.4f}%")
        print(f"  Max          : {returns.max()*100:+.4f}%")
        print(f"  Skewness     : {stats.skew(returns):.3f}  {'(negative = left tail heavier)' if stats.skew(returns)<0 else '(positive = right tail heavier)'}")
        print(f"  Kurtosis     : {stats.kurtosis(returns):.3f}  {'(fat tails — expected for crypto)' if stats.kurtosis(returns)>3 else '(near-normal)'}")

    # ── Core: simulate N price paths ──────────────────────────
    def simulate(self, returns: np.ndarray, start_price: float,
                 n_periods: int) -> np.ndarray:
        """
        Returns array shape (n_sim, n_periods+1)
        Col 0 = start_price (known)
        Col 1..n_periods = simulated future prices
        """
        # Bootstrap: random sampling with replacement
        idx = np.random.randint(0, len(returns), size=(self.n_sim, n_periods))
        sampled = returns[idx]

        # Compound: price[t] = price[t-1] * (1 + return[t])
        multipliers = 1 + sampled
        cum_mult    = np.cumprod(multipliers, axis=1)

        paths = np.empty((self.n_sim, n_periods + 1))
        paths[:, 0]  = start_price
        paths[:, 1:] = start_price * cum_mult

        return paths

    # ── Percentile fan chart data ──────────────────────────────
    def fan_data(self, paths: np.ndarray) -> dict:
        pcts = [5, 25, 50, 75, 95]
        fan  = {}
        for t in range(paths.shape[1]):
            col = paths[:, t]
            fan[t] = {p: float(np.percentile(col, p)) for p in pcts}
        return fan

    # ── Probability metrics ────────────────────────────────────
    def probability_metrics(self, paths: np.ndarray, start_price: float) -> dict:
        final = paths[:, -1]
        n     = self.n_sim

        def prob_above(target):
            return float((final > target).sum() / n * 100)

        def prob_below(target):
            return float((final < target).sum() / n * 100)

        # Max drawdown per path
        running_max = np.maximum.accumulate(paths, axis=1)
        dd_pct      = (running_max - paths) / running_max * 100
        max_dd      = dd_pct.max(axis=1)

        return {
            "start_price"           : round(start_price, 4),
            "worst_p5"              : round(float(np.percentile(final, 5)), 4),
            "low_p25"               : round(float(np.percentile(final, 25)), 4),
            "base_p50"              : round(float(np.percentile(final, 50)), 4),
            "high_p75"              : round(float(np.percentile(final, 75)), 4),
            "best_p95"              : round(float(np.percentile(final, 95)), 4),
            "change_worst_pct"      : round((np.percentile(final,5)/start_price-1)*100, 2),
            "change_base_pct"       : round((np.percentile(final,50)/start_price-1)*100, 2),
            "change_best_pct"       : round((np.percentile(final,95)/start_price-1)*100, 2),
            "prob_up_pct"           : round(prob_above(start_price), 1),
            "prob_down_pct"         : round(prob_below(start_price), 1),
            "prob_up_10pct"         : round(prob_above(start_price*1.10), 1),
            "prob_down_10pct"       : round(prob_below(start_price*0.90), 1),
            "prob_up_20pct"         : round(prob_above(start_price*1.20), 1),
            "prob_down_20pct"       : round(prob_below(start_price*0.80), 1),
            "prob_up_30pct"         : round(prob_above(start_price*1.30), 1),
            "prob_down_30pct"       : round(prob_below(start_price*0.70), 1),
            "median_max_dd_pct"     : round(float(np.median(max_dd)), 2),
            "worst_max_dd_p95_pct"  : round(float(np.percentile(max_dd, 95)), 2),
        }

    # ── Plot fan chart ─────────────────────────────────────────
    def plot_fan_chart(
        self,
        fan: dict,
        start_price: float,
        metrics: dict,
        timestamps,                # DatetimeIndex for x-axis
        title: str,
        actual_prices=None,        # Optional: actual observed prices
        ax=None,
        show_metrics: bool = True,
    ):
        if ax is None:
            fig, ax = plt.subplots(figsize=(14, 7))
            standalone = True
        else:
            standalone = False

        steps = sorted(fan.keys())
        p5    = [fan[s][5]  for s in steps]
        p25   = [fan[s][25] for s in steps]
        p50   = [fan[s][50] for s in steps]
        p75   = [fan[s][75] for s in steps]
        p95   = [fan[s][95] for s in steps]

        # x-axis: timestamps (must have len = n_periods+1)
        x = timestamps[:len(steps)]

        # Fan bands
        ax.fill_between(x, p5, p95, alpha=0.12, color="#6366f1", label="P5–P95 (90%)")
        ax.fill_between(x, p25, p75, alpha=0.25, color="#6366f1", label="P25–P75 (50%)")

        # Median (base case)
        ax.plot(x, p50, color="#6366f1", linewidth=2.0, label="Base case (P50)")

        # Worst / best
        ax.plot(x, p5,  color="#ef4444", linewidth=1.0, linestyle="--", alpha=0.7, label=f"Worst P5 ({metrics['change_worst_pct']:+.1f}%)")
        ax.plot(x, p95, color="#22c55e", linewidth=1.0, linestyle="--", alpha=0.7, label=f"Best P95 ({metrics['change_best_pct']:+.1f}%)")

        # Start price marker
        ax.axhline(start_price, color="#f59e0b", linewidth=1.0, linestyle=":", alpha=0.6, label=f"Entry {start_price:.4f}")

        # Actual prices overlay (backtest validation)
        if actual_prices is not None:
            x_actual = timestamps[1:len(actual_prices)+1]
            ax.plot(x_actual, actual_prices, color="#f59e0b", linewidth=2.2,
                    label="Actual price", zorder=5)

        ax.set_title(title, fontsize=13, pad=12, color="#e2e8f0")
        ax.set_ylabel("CRV Price (USDT)", color="#94a3b8")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right")
        ax.legend(loc="upper left", fontsize=9, framealpha=0.4)
        ax.grid(True, alpha=0.2)

        if show_metrics and standalone:
            textstr = (
                f"P50 (Base)  : {metrics['base_p50']:.4f}  ({metrics['change_base_pct']:+.1f}%)\n"
                f"P5  (Worst) : {metrics['worst_p5']:.4f}  ({metrics['change_worst_pct']:+.1f}%)\n"
                f"P95 (Best)  : {metrics['best_p95']:.4f}  ({metrics['change_best_pct']:+.1f}%)\n"
                f"Prob UP     : {metrics['prob_up_pct']:.1f}%\n"
                f"Prob DN     : {metrics['prob_down_pct']:.1f}%\n"
                f"Med Max DD  : {metrics['median_max_dd_pct']:.1f}%"
            )
            props = dict(boxstyle="round", facecolor="#1e293b", alpha=0.85, edgecolor="#334155")
            ax.text(0.98, 0.97, textstr, transform=ax.transAxes, fontsize=9,
                    verticalalignment="top", horizontalalignment="right",
                    bbox=props, family="monospace", color="#94a3b8")

        if standalone:
            plt.tight_layout()
            # plt.show() # Di-comment agar tidak mem-block eksekusi di Windows


mc = MonteCarloPathEngine(n_simulations=10_000, random_seed=42)
print("✅ Monte Carlo engine ready.")


# ╔══════════════════════════════════════════════════════════╗
# ║  SECTION 4 — BACKTEST VALIDATION                        ║
# ║  Train: semua data KECUALI bulan terakhir               ║
# ║  Test : simulasikan bulan terakhir, compare vs aktual   ║
# ╚══════════════════════════════════════════════════════════╝

print("\n" + "═"*60)
print("  SECTION 4: BACKTEST VALIDATION")
print("═"*60)

# ── Split: train / test ────────────────────────────────────
# "Bulan terakhir" = 30 hari kalender terakhir = ~180 candles 4H
CANDLES_PER_DAY_4H = 6
TEST_DAYS           = 30
TEST_CANDLES        = TEST_DAYS * CANDLES_PER_DAY_4H  # 180 candles

df_train = df_full.iloc[:-TEST_CANDLES].copy()
df_test  = df_full.iloc[-TEST_CANDLES:].copy()

print(f"\n  Training period: {df_train['timestamp'].iloc[0].date()} → {df_train['timestamp'].iloc[-1].date()}")
print(f"  Test period    : {df_test['timestamp'].iloc[0].date()}  → {df_test['timestamp'].iloc[-1].date()}")
print(f"  Train candles  : {len(df_train)}")
print(f"  Test candles   : {len(df_test)}")

# ── Extract returns dari training data saja ────────────────
train_returns = mc.extract_returns(df_train)
mc.describe_returns(train_returns, label="Training")

# ── Simulasikan periode test ───────────────────────────────
start_price_bt   = float(df_train["close"].iloc[-1])   # harga terakhir training
n_periods_bt     = TEST_CANDLES

print(f"\n  Simulating {n_periods_bt} candles forward from {start_price_bt:.4f}...")
paths_bt = mc.simulate(train_returns, start_price_bt, n_periods_bt)
fan_bt   = mc.fan_data(paths_bt)
met_bt   = mc.probability_metrics(paths_bt, start_price_bt)

# ── Harga aktual selama test period ───────────────────────
actual_prices_bt = df_test["close"].values

# ── Build timestamps untuk x-axis ─────────────────────────
# Start = last training timestamp, then step forward 4H per candle
freq_4h = pd.tseries.frequencies.to_offset("4h")
ts_bt   = pd.date_range(
    start  = df_train["timestamp"].iloc[-1],
    periods= n_periods_bt + 1,
    freq   = freq_4h
)

# ── Print backtest results ────────────────────────────────
actual_final    = float(actual_prices_bt[-1])
actual_change   = (actual_final / start_price_bt - 1) * 100

print(f"\n  {'─'*50}")
print(f"  BACKTEST RESULT SUMMARY")
print(f"  {'─'*50}")
print(f"  Start price      : {start_price_bt:.4f} USDT")
print(f"  Actual end price : {actual_final:.4f} USDT  ({actual_change:+.2f}%)")
print(f"  MC P5  (worst)   : {met_bt['worst_p5']:.4f}  ({met_bt['change_worst_pct']:+.1f}%)")
print(f"  MC P50 (base)    : {met_bt['base_p50']:.4f}  ({met_bt['change_base_pct']:+.1f}%)")
print(f"  MC P95 (best)    : {met_bt['best_p95']:.4f}  ({met_bt['change_best_pct']:+.1f}%)")

# Apakah actual dalam range P5-P95?
in_range = met_bt["worst_p5"] <= actual_final <= met_bt["best_p95"]
verdict  = "✅ Actual DALAM range P5-P95 (model cukup akurat)" if in_range else "⚠️  Actual LUAR range P5-P95 (extreme event / black swan)"
print(f"\n  {verdict}")

# Percentile rank aktual di distribusi simulasi
final_dist  = paths_bt[:, -1]
pctile_rank = float((final_dist < actual_final).mean() * 100)
print(f"  Actual price berada di percentile ke-{pctile_rank:.1f} distribusi MC")

# ── Plot backtest ─────────────────────────────────────────
fig, axes = plt.subplots(2, 1, figsize=(15, 12), gridspec_kw={"height_ratios": [3, 1]})

mc.plot_fan_chart(
    fan          = fan_bt,
    start_price  = start_price_bt,
    metrics      = met_bt,
    timestamps   = ts_bt,
    title        = f"CRV/USDT 4H — Backtest Validation\nTrain: s/d {df_train['timestamp'].iloc[-1].date()} | Test: {TEST_DAYS} hari | {mc.n_sim:,} simulations",
    actual_prices= actual_prices_bt,
    ax           = axes[0],
    show_metrics = False,
)

# Subplot 2: residuals (actual vs P50)
p50_series = [fan_bt[s][50] for s in range(1, n_periods_bt + 1)]
residuals  = actual_prices_bt - np.array(p50_series[:len(actual_prices_bt)])
axes[1].bar(ts_bt[1:len(actual_prices_bt)+1], residuals,
            color=["#22c55e" if r > 0 else "#ef4444" for r in residuals],
            alpha=0.7, width=0.12)
axes[1].axhline(0, color="#64748b", linewidth=0.8)
axes[1].set_title("Actual vs P50 Residual (+ = actual above median prediction)", fontsize=10, color="#94a3b8")
axes[1].set_ylabel("Residual (USDT)", color="#94a3b8")
axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
axes[1].grid(True, alpha=0.2)

# Metrics box di main chart
textstr = (
    f"Entry          : {start_price_bt:.4f}\n"
    f"Actual final   : {actual_final:.4f}  ({actual_change:+.2f}%)\n"
    f"P5  (worst)    : {met_bt['worst_p5']:.4f}  ({met_bt['change_worst_pct']:+.1f}%)\n"
    f"P50 (base)     : {met_bt['base_p50']:.4f}  ({met_bt['change_base_pct']:+.1f}%)\n"
    f"P95 (best)     : {met_bt['best_p95']:.4f}  ({met_bt['change_best_pct']:+.1f}%)\n"
    f"Actual pctile  : {pctile_rank:.1f}th\n"
    f"In P5-P95?     : {'YES' if in_range else 'NO'}"
)
props = dict(boxstyle="round", facecolor="#1e293b", alpha=0.9, edgecolor="#334155")
axes[0].text(0.98, 0.97, textstr, transform=axes[0].transAxes, fontsize=9,
             verticalalignment="top", horizontalalignment="right",
             bbox=props, family="monospace", color="#94a3b8")

plt.tight_layout(pad=2.0)
plt.savefig("backtest_validation.png", dpi=150, bbox_inches="tight",
            facecolor="#0f172a")
# plt.show() # Di-comment agar tidak mem-block
print("\n💾 Saved: backtest_validation.png")


# ╔══════════════════════════════════════════════════════════╗
# ║  SECTION 5 — FORWARD SIMULATION (1 BULAN KE DEPAN)     ║
# ╚══════════════════════════════════════════════════════════╝

print("\n" + "═"*60)
print("  SECTION 5: FORWARD SIMULATION — 1 BULAN KE DEPAN")
print("═"*60)

# ── Pakai SEMUA data historis untuk forward sampling ──────
# (lebih banyak data = distribusi return lebih stabil)
all_returns     = mc.extract_returns(df_full)
mc.describe_returns(all_returns, label="Full Historical (for Forward Sim)")

# ── Setup forward simulation ──────────────────────────────
FORWARD_DAYS    = 30
FORWARD_CANDLES = FORWARD_DAYS * CANDLES_PER_DAY_4H  # 180 candles
start_price_fwd = float(df_full["close"].iloc[-1])
last_ts         = df_full["timestamp"].iloc[-1]

print(f"\n  Start price (latest): {start_price_fwd:.4f} USDT")
print(f"  Last candle         : {last_ts}")
print(f"  Forecast horizon    : {FORWARD_DAYS} days ({FORWARD_CANDLES} × 4H candles)")
print(f"  Simulations         : {mc.n_sim:,}")
print(f"\n  Simulating...")

paths_fwd = mc.simulate(all_returns, start_price_fwd, FORWARD_CANDLES)
fan_fwd   = mc.fan_data(paths_fwd)
met_fwd   = mc.probability_metrics(paths_fwd, start_price_fwd)

# ── Timestamps (future) ───────────────────────────────────
ts_fwd = pd.date_range(
    start   = last_ts,
    periods = FORWARD_CANDLES + 1,
    freq    = freq_4h
)

# ── Print forward results ─────────────────────────────────
print(f"\n  {'─'*55}")
print(f"  FORWARD SIMULATION — CRV/USDT 4H ({FORWARD_DAYS} hari ke depan)")
print(f"  {'─'*55}")
print(f"  Start price     : {start_price_fwd:.4f} USDT")
print(f"  Horizon end     : {ts_fwd[-1].date()}")
print()
print(f"  ┌─────────────────────────────────────────────────┐")
print(f"  │  SCENARIOS (end of {FORWARD_DAYS} days):                   │")
print(f"  │  P5  Worst  : {met_fwd['worst_p5']:>8.4f}  ({met_fwd['change_worst_pct']:>+7.2f}%)           │")
print(f"  │  P25 Low    : {met_fwd['low_p25']:>8.4f}  ({(met_fwd['low_p25']/start_price_fwd-1)*100:>+7.2f}%)           │")
print(f"  │  P50 Base   : {met_fwd['base_p50']:>8.4f}  ({met_fwd['change_base_pct']:>+7.2f}%)           │")
print(f"  │  P75 High   : {met_fwd['high_p75']:>8.4f}  ({(met_fwd['high_p75']/start_price_fwd-1)*100:>+7.2f}%)           │")
print(f"  │  P95 Best   : {met_fwd['best_p95']:>8.4f}  ({met_fwd['change_best_pct']:>+7.2f}%)           │")
print(f"  └─────────────────────────────────────────────────┘")
print()
print(f"  PROBABILITIES:")
print(f"  Prob harga naik   : {met_fwd['prob_up_pct']:.1f}%")
print(f"  Prob harga turun  : {met_fwd['prob_down_pct']:.1f}%")
print(f"  Prob +10%         : {met_fwd['prob_up_10pct']:.1f}%")
print(f"  Prob -10%         : {met_fwd['prob_down_10pct']:.1f}%")
print(f"  Prob +20%         : {met_fwd['prob_up_20pct']:.1f}%")
print(f"  Prob -20%         : {met_fwd['prob_down_20pct']:.1f}%")
print(f"  Prob +30%         : {met_fwd['prob_up_30pct']:.1f}%")
print(f"  Prob -30%         : {met_fwd['prob_down_30pct']:.1f}%")
print()
print(f"  RISK:")
print(f"  Median max DD     : {met_fwd['median_max_dd_pct']:.2f}%")
print(f"  Worst DD (P95)    : {met_fwd['worst_max_dd_p95_pct']:.2f}%")

# ── Plot forward + historical context ────────────────────
fig, ax = plt.subplots(figsize=(15, 7))

# Historical context (last 60 candles)
hist_tail = df_full.tail(60)
ax.plot(hist_tail["timestamp"], hist_tail["close"],
        color="#e2e8f0", linewidth=1.8, label="Historical price", zorder=4)

# Vertical separator: "NOW"
ax.axvline(last_ts, color="#f59e0b", linewidth=1.2, linestyle="--", alpha=0.7)
ax.text(last_ts, ax.get_ylim()[0] if ax.get_ylim()[0] != 0 else start_price_fwd * 0.85,
        " NOW", color="#f59e0b", fontsize=9, va="bottom")

# Forward fan
mc.plot_fan_chart(
    fan         = fan_fwd,
    start_price = start_price_fwd,
    metrics     = met_fwd,
    timestamps  = ts_fwd,
    title       = (f"CRV/USDT 4H — Forward Simulation ({FORWARD_DAYS} hari ke depan)\n"
                   f"From {last_ts.date()} | {mc.n_sim:,} Bootstrap simulations"),
    ax          = ax,
    show_metrics= False,
)

# Metrics box
textstr = (
    f"Entry (NOW)    : {start_price_fwd:.4f}\n"
    f"\nSCENARIOS ({FORWARD_DAYS}d):\n"
    f"P5  Worst  : {met_fwd['worst_p5']:.4f} ({met_fwd['change_worst_pct']:+.1f}%)\n"
    f"P50 Base   : {met_fwd['base_p50']:.4f} ({met_fwd['change_base_pct']:+.1f}%)\n"
    f"P95 Best   : {met_fwd['best_p95']:.4f} ({met_fwd['change_best_pct']:+.1f}%)\n"
    f"\nPROBABILITIES:\n"
    f"P(up)      : {met_fwd['prob_up_pct']:.1f}%\n"
    f"P(+20%)    : {met_fwd['prob_up_20pct']:.1f}%\n"
    f"P(-20%)    : {met_fwd['prob_down_20pct']:.1f}%\n"
    f"\nRISK:\n"
    f"Med DD     : {met_fwd['median_max_dd_pct']:.1f}%\n"
    f"Worst DD   : {met_fwd['worst_max_dd_p95_pct']:.1f}%"
)
props = dict(boxstyle="round", facecolor="#0f172a", alpha=0.92, edgecolor="#334155")
ax.text(0.015, 0.97, textstr, transform=ax.transAxes, fontsize=9,
        verticalalignment="top", bbox=props, family="monospace", color="#94a3b8")

plt.tight_layout()
plt.savefig("forward_simulation.png", dpi=150, bbox_inches="tight", facecolor="#0f172a")
# plt.show() # Di-comment agar tidak mem-block
print("\n💾 Saved: forward_simulation.png")


# ╔══════════════════════════════════════════════════════════╗
# ║  SECTION 6 — BONUS: Return Distribution + TP/SL Check  ║
# ╚══════════════════════════════════════════════════════════╝

print("\n" + "═"*60)
print("  SECTION 6: TP / SL PROBABILITY CHECK")
print("  (Relevan untuk bot CRV Mean Reversion Anda)")
print("═"*60)

# Parameter dari config.py bot Anda
STOP_LOSS_PCT  = 0.20   # -20% dari entry (per config.py)
# Take profit: BB mid biasanya ~5-15% dari lower band, set 10% sebagai proxy
TAKE_PROFIT_PCT = 0.10  # +10% — sesuaikan dengan BB mid jarak aktual

sl_price = start_price_fwd * (1 - STOP_LOSS_PCT)
tp_price = start_price_fwd * (1 + TAKE_PROFIT_PCT)

# Untuk LONG: kapanpun path menyentuh SL atau TP dalam horizon?
def check_tp_sl_probs(paths, start, tp, sl, horizon_candles, is_long=True):
    """
    Berapa % simulasi yang mencapai TP sebelum SL, dan sebaliknya?
    Ini lebih realistic dari cek harga akhir saja.
    """
    n = paths.shape[0]
    hit_tp    = np.zeros(n, dtype=bool)
    hit_sl    = np.zeros(n, dtype=bool)
    tp_first  = np.zeros(n, dtype=bool)

    for i in range(n):
        path = paths[i, 1:horizon_candles+1]  # exclude start
        if is_long:
            tp_idx = np.argmax(path >= tp) if (path >= tp).any() else -1
            sl_idx = np.argmax(path <= sl) if (path <= sl).any() else -1
        else:
            tp_idx = np.argmax(path <= tp) if (path <= tp).any() else -1
            sl_idx = np.argmax(path >= sl) if (path >= sl).any() else -1

        if tp_idx >= 0:
            hit_tp[i] = True
        if sl_idx >= 0:
            hit_sl[i] = True

        # Which hits first?
        if tp_idx >= 0 and sl_idx >= 0:
            tp_first[i] = tp_idx < sl_idx
        elif tp_idx >= 0:
            tp_first[i] = True

    prob_tp         = hit_tp.mean() * 100
    prob_sl         = hit_sl.mean() * 100
    prob_tp_first   = tp_first.mean() * 100
    prob_neither    = (~hit_tp & ~hit_sl).mean() * 100
    expected_rr     = (TAKE_PROFIT_PCT * (prob_tp_first/100)) - (STOP_LOSS_PCT * ((1 - prob_tp_first/100)))

    return {
        "tp_price"         : round(tp, 4),
        "sl_price"         : round(sl, 4),
        "prob_hit_tp_pct"  : round(prob_tp, 1),
        "prob_hit_sl_pct"  : round(prob_sl, 1),
        "prob_tp_first_pct": round(prob_tp_first, 1),
        "prob_sl_first_pct": round(100 - prob_tp_first, 1),
        "prob_neither_pct" : round(prob_neither, 1),
        "expected_rr"      : round(expected_rr, 4),
    }

res_long = check_tp_sl_probs(paths_fwd, start_price_fwd, tp_price, sl_price, FORWARD_CANDLES, is_long=True)

print(f"\n  Posisi  : LONG dari {start_price_fwd:.4f}")
print(f"  TP (+{TAKE_PROFIT_PCT*100:.0f}%) : {res_long['tp_price']:.4f}")
print(f"  SL (-{STOP_LOSS_PCT*100:.0f}%) : {res_long['sl_price']:.4f}")
print(f"  Prob TP kena SEBELUM SL       : {res_long['prob_tp_first_pct']:.1f}%")
print(f"  Expected value per trade      : {res_long['expected_rr']:+.4f} USDT per 1 USDT risked")

sl_price_short = start_price_fwd * (1 + STOP_LOSS_PCT)
tp_price_short = start_price_fwd * (1 - TAKE_PROFIT_PCT)
res_short = check_tp_sl_probs(paths_fwd, start_price_fwd, tp_price_short, sl_price_short, FORWARD_CANDLES, is_long=False)

print(f"\n  Posisi  : SHORT dari {start_price_fwd:.4f}")
print(f"  TP (-{TAKE_PROFIT_PCT*100:.0f}%) : {res_short['tp_price']:.4f}")
print(f"  SL (+{STOP_LOSS_PCT*100:.0f}%) : {res_short['sl_price']:.4f}")
print(f"  Prob TP kena SEBELUM SL       : {res_short['prob_tp_first_pct']:.1f}%")
print(f"  Expected value per trade      : {res_short['expected_rr']:+.4f} USDT per 1 USDT risked")

if res_long["expected_rr"] > res_short["expected_rr"]:
    print(f"\n  💡 KESIMPULAN: Setup LONG secara statistik lebih baik daripada SHORT di kondisi saat ini.")
else:
    print(f"\n  💡 KESIMPULAN: Setup SHORT secara statistik lebih menguntungkan (atau lebih sedikit ruginya) daripada LONG di kondisi saat ini.")

# ── Plot distribution ─────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(15, 5))

# Histogram final price distribution
final_fwd = paths_fwd[:, -1]
axes[0].hist(final_fwd, bins=100, color="#6366f1", alpha=0.7, edgecolor="none")
axes[0].axvline(start_price_fwd, color="#f59e0b", linewidth=1.5, linestyle="--", label=f"Entry {start_price_fwd:.4f}")
axes[0].axvline(tp_price, color="#22c55e", linewidth=1.5, linestyle="--", label=f"TP {tp_price:.4f}")
axes[0].axvline(sl_price, color="#ef4444", linewidth=1.5, linestyle="--", label=f"SL {sl_price:.4f}")
axes[0].axvline(np.percentile(final_fwd, 5), color="#94a3b8", linewidth=1.0, linestyle=":", alpha=0.6, label="P5/P95")
axes[0].axvline(np.percentile(final_fwd, 95), color="#94a3b8", linewidth=1.0, linestyle=":", alpha=0.6)
axes[0].set_title(f"CRV Final Price Distribution ({FORWARD_DAYS}d)", color="#e2e8f0")
axes[0].set_xlabel("Price (USDT)"); axes[0].set_ylabel("Count")
axes[0].legend(fontsize=8); axes[0].grid(True, alpha=0.2)

# Per-candle return distribution
axes[1].hist(all_returns * 100, bins=80, color="#22c55e", alpha=0.7, edgecolor="none")
axes[1].axvline(0, color="#f59e0b", linewidth=1.0, linestyle="--")
axes[1].set_title("Historical 4H Return Distribution (used for sampling)", color="#e2e8f0")
axes[1].set_xlabel("Return per candle (%)"); axes[1].set_ylabel("Count")
axes[1].grid(True, alpha=0.2)

# Overlay normal distribution
x = np.linspace(all_returns.min()*100, all_returns.max()*100, 200)
mu, sigma = all_returns.mean()*100, all_returns.std()*100
normal_y  = stats.norm.pdf(x, mu, sigma)
normal_y *= len(all_returns) * (all_returns.max() - all_returns.min()) * 100 / 80
axes[1].plot(x, normal_y, color="#ef4444", linewidth=1.5, linestyle="--", alpha=0.7,
             label="Normal dist (for comparison)")
axes[1].legend(fontsize=8)

plt.tight_layout()
plt.savefig("distributions.png", dpi=150, bbox_inches="tight", facecolor="#0f172a")
# plt.show() # Di-comment agar tidak mem-block
print("\n💾 Saved: distributions.png")


# ╔══════════════════════════════════════════════════════════╗
# ║  SECTION 7 — FINAL SUMMARY                             ║
# ╚══════════════════════════════════════════════════════════╝

print("\n" + "═"*60)
print("  FINAL SUMMARY")
print("═"*60)
print(f"""
  Symbol    : CRV/USDT:USDT (Bybit Perpetual)
  Timeframe : 4H (sesuai bot config)
  Data      : {df_full['timestamp'].iloc[0].date()} → {df_full['timestamp'].iloc[-1].date()}
  Method    : Bootstrap Monte Carlo ({mc.n_sim:,} simulations)

  BACKTEST VALIDATION ({TEST_DAYS} hari terakhir):
  ├─ Actual final price : {actual_final:.4f}  ({actual_change:+.2f}%)
  ├─ Actual percentile  : {pctile_rank:.1f}th dari distribusi MC
  └─ Dalam range P5-P95 : {'YES ✅' if in_range else 'NO ⚠️ (extreme event)'}

  FORWARD SIMULATION ({FORWARD_DAYS} hari ke depan):
  ├─ Start price  : {start_price_fwd:.4f}
  ├─ P5  (worst)  : {met_fwd['worst_p5']:.4f}  ({met_fwd['change_worst_pct']:+.1f}%)
  ├─ P50 (base)   : {met_fwd['base_p50']:.4f}  ({met_fwd['change_base_pct']:+.1f}%)
  ├─ P95 (best)   : {met_fwd['best_p95']:.4f}  ({met_fwd['change_best_pct']:+.1f}%)
  ├─ P(naik)      : {met_fwd['prob_up_pct']:.1f}%
  └─ Med max DD   : {met_fwd['median_max_dd_pct']:.1f}%

  TP/SL CHECK (LONG setup dari config bot):
  ├─ TP (+{TAKE_PROFIT_PCT*100:.0f}%) prob hit first : {res['prob_tp_first_pct']:.1f}%
  ├─ SL (-{STOP_LOSS_PCT*100:.0f}%) prob hit first : {res['prob_sl_first_pct']:.1f}%
  └─ Expected value     : {res['expected_rr']:+.4f}

  ⚠️  DISCLAIMER:
  Monte Carlo bukan prediksi harga. Ini adalah kuantifikasi
  ketidakpastian berdasarkan volatility historis. Black swan
  events, regulatory news, dan liquidity crisis dapat
  menghasilkan outcome di luar range P5-P95.

  Files saved:
  ├─ backtest_validation.png
  ├─ forward_simulation.png
  └─ distributions.png
""")