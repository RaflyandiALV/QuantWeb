# =============================================================
# backtest.py - CRV-USDT Mean Reversion Bot Backtesting
#
# Strategi PERSIS sama dengan bot live:
#   LONG  entry  : RSI < 30  AND close < BB_lower
#   SHORT entry  : RSI > 70  AND close > BB_upper
#   Flip logic   : close opposite -> open new (1 candle)
#   Stop Loss    : -20% dari entry price
#   Circuit Breaker: -50% dari all-time peak equity -> halt
#   Leverage     : 2x
#   Position Size: 92% equity per trade (notional = equity * 0.92 * 2)
#   Timeframe    : 4H
#   Modal        : $10,000 USDT
#
# Data source: ccxt (Bybit) - 1 tahun terakhir CRV/USDT:USDT
#
# Run: python backtest.py
# =============================================================

import sys
import os
import io
import time
import warnings
warnings.filterwarnings("ignore")

# Fix Windows console encoding for emoji/unicode
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Use non-interactive backend to avoid plt.show() blocking
import matplotlib
matplotlib.use("Agg")

# -- Install check --
REQUIRED = ["ccxt", "pandas", "numpy", "matplotlib"]
missing  = []
for pkg in REQUIRED:
    try:
        __import__(pkg)
    except ImportError:
        missing.append(pkg)

if missing:
    print(f"[ERROR] Package belum terinstall: {', '.join(missing)}")
    print(f"Jalankan: pip install {' '.join(missing)}")
    sys.exit(1)

import ccxt
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from datetime import datetime, timezone, timedelta

# -----------------------------------------------------------------
# PARAMETER (persis dari config.py)
# -----------------------------------------------------------------
INITIAL_CAPITAL    = 10_000.0
LEVERAGE           = 2         
POSITION_SIZE_PCT  = 0.92      # 92% of equity per trade (optimal)
STOP_LOSS_PCT      = 0.20      # Ported from crv_bot config
CIRCUIT_BREAKER_DD = 0.50      # Ported from crv_bot config
RSI_PERIOD         = 14
RSI_OVERSOLD       = 30
RSI_OVERBOUGHT     = 71
COOLDOWN_CANDLES   = 6          # Jeda 6 candle (24 jam) setelah SL/CB sebelum boleh entry lagi
BB_PERIOD          = 17
BB_STD_DEV         = 1.8
TRADING_FEE        = 0.00055    # 0.055% taker fee per side (Bybit futures)
TIMEFRAME          = "4h"

# -----------------------------------------------------------------
# WARNA / TEMA
# -----------------------------------------------------------------
DARK_BG       = "#0D1117"
PANEL_BG      = "#161B22"
GRID_COLOR    = "#21262D"
TEXT_COLOR    = "#C9D1D9"
ACCENT_BLUE   = "#58A6FF"
ACCENT_GREEN  = "#3FB950"
ACCENT_RED    = "#F85149"
ACCENT_GOLD   = "#D29922"
ACCENT_PURPLE = "#BC8CFF"
LINE_WHITE    = "#ECEFF4"


# =================================================================
# STEP 1: FETCH DATA (1 TAHUN PENUH)
# =================================================================

def fetch_ohlcv_1y() -> pd.DataFrame:
    """
    Fetch 1 tahun penuh data 4H CRV/USDT dari Bybit.
    Retry logic + paginate agar mendapat seluruh data.
    """
    print("[1/6] Fetching 1 year CRV/USDT 4H data from Bybit...")

    since_dt     = datetime.now(timezone.utc) - timedelta(days=365)
    since_ms     = int(since_dt.timestamp() * 1000)
    now_ms       = int(datetime.now(timezone.utc).timestamp() * 1000)

    # Daftar konfigurasi yang dicoba berurutan
    configs = [
        ({"enableRateLimit": True, "options": {"defaultType": "swap"}},
         "CRV/USDT:USDT", "Perpetual Swap"),
        ({"enableRateLimit": True, "options": {"defaultType": "linear"}},
         "CRVUSDT", "Linear Perpetual"),
        ({"enableRateLimit": True, "options": {"defaultType": "spot"}},
         "CRV/USDT", "Spot (fallback)"),
    ]

    for opts, symbol, label in configs:
        print(f"  -> Trying {label} ({symbol})...")
        try:
            exchange   = ccxt.bybit(opts)
            all_ohlcv  = []
            cursor     = since_ms
            page       = 0

            while cursor < now_ms:
                page += 1
                batch = exchange.fetch_ohlcv(symbol, TIMEFRAME,
                                             since=cursor, limit=200)
                if not batch:
                    break
                all_ohlcv.extend(batch)
                last_ts = batch[-1][0]
                # Jika last candle tidak maju, stop
                if last_ts <= cursor:
                    break
                cursor = last_ts + 1
                if page % 5 == 0:
                    print(f"     ... page {page}, {len(all_ohlcv)} candles so far")
                # Polite delay
                import time
                time.sleep(1.0)

            if len(all_ohlcv) < 100:
                print(f"  [!] Only {len(all_ohlcv)} candles from {label}, skipping...")
                continue

            df = pd.DataFrame(all_ohlcv,
                              columns=["timestamp","open","high","low","close","volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            df = df.drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)
            df = df[df["timestamp"] >= since_dt].reset_index(drop=True)

            print(f"  [OK] {label}: {len(df)} candles "
                  f"({df['timestamp'].iloc[0].strftime('%Y-%m-%d')} to "
                  f"{df['timestamp'].iloc[-1].strftime('%Y-%m-%d')})")
            return df

        except Exception as e:
            print(f"  [FAIL] {label}: {type(e).__name__}: {str(e)[:150]}")
            continue

    raise RuntimeError(
        "Gagal ambil data dari Bybit. Pastikan VPN aktif / koneksi stabil."
    )


# =================================================================
# STEP 2: INDICATORS
# =================================================================

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    print("[2/6] Computing indicators (BB20, RSI14)...")
    df = df.copy()

    # Bollinger Bands (ddof=1 sample std — persis QuantWeb)
    df["bb_mid"]   = df["close"].rolling(BB_PERIOD).mean()
    bb_std         = df["close"].rolling(BB_PERIOD).std()  # ddof=1 default
    df["bb_upper"] = df["bb_mid"] + BB_STD_DEV * bb_std
    df["bb_lower"] = df["bb_mid"] - BB_STD_DEV * bb_std

    # RSI (SMA Rolling — persis QuantWeb strategy_core.py)
    delta    = df["close"].diff()
    gain     = (delta.where(delta > 0, 0)).rolling(RSI_PERIOD).mean()
    loss     = (-delta.where(delta < 0, 0)).rolling(RSI_PERIOD).mean()
    rs       = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))

    df = df.dropna().reset_index(drop=True)

    return df


# =================================================================
# STEP 3: BACKTEST ENGINE
# =================================================================

def run_backtest(df: pd.DataFrame):
    """
    Jalankan backtest persis logika bot live.
    Returns: (df, trades, signals_long, signals_short, signals_sl, signals_cb)
    """
    print("[3/6] Running backtest engine...")

    equity            = INITIAL_CAPITAL
    peak_equity       = INITIAL_CAPITAL
    circuit_breaker   = False
    cooldown_until    = -1         # Index candle sampai mana harus jeda
    position          = "NONE"
    entry_price       = None
    entry_idx         = None
    position_notional = 0.0

    trades        = []
    equity_curve  = []
    signals_long  = []
    signals_short = []
    signals_sl    = []
    signals_cb    = []

    df = df.copy()
    df["signal"]   = "HOLD"
    df["equity"]   = np.nan
    df["position"] = "NONE"

    WARMUP = BB_PERIOD + RSI_PERIOD + 5

    for i in range(len(df)):
        row   = df.iloc[i]
        ts    = row["timestamp"]
        close = row["close"]

        # -- Calculate current equity (mark to market) --
        if position == "LONG":
            pnl_pct = (close - entry_price) / entry_price
            unrealized = position_notional * pnl_pct  # notional P&L
            current_equity = equity + unrealized
        elif position == "SHORT":
            pnl_pct = (entry_price - close) / entry_price
            unrealized = position_notional * pnl_pct
            current_equity = equity + unrealized
        else:
            current_equity = equity

        df.at[i, "equity"]   = current_equity
        df.at[i, "position"] = position
        equity_curve.append(current_equity)

        # -- Warmup skip --
        if i < WARMUP:
            continue

        rsi      = row["rsi"]
        bb_upper = row["bb_upper"]
        bb_lower = row["bb_lower"]

        if pd.isna(rsi) or pd.isna(bb_upper):
            continue

        # -- Circuit Breaker (removed permanent halt) --
        # (bot will now resume trading after safety trips)
        # -- Update peak equity --
        if current_equity > peak_equity:
            peak_equity = current_equity

        # -- Circuit Breaker check --
        dd_from_peak = (peak_equity - current_equity) / peak_equity
        if dd_from_peak >= CIRCUIT_BREAKER_DD:
            signals_cb.append((ts, close))
            if position != "NONE":
                fee = position_notional * TRADING_FEE
                if position == "LONG":
                    pnl_pct_r = (close - entry_price) / entry_price
                else:
                    pnl_pct_r = (entry_price - close) / entry_price
                realized = position_notional * pnl_pct_r - fee
                equity  += realized
                trades.append({
                    "entry_time"  : df.iloc[entry_idx]["timestamp"],
                    "exit_time"   : ts,
                    "direction"   : position,
                    "entry_price" : entry_price,
                    "exit_price"  : close,
                    "pnl_pct"     : pnl_pct_r * 100,
                    "pnl_usdt"    : realized,
                    "exit_reason" : "circuit_breaker",
                    "equity_after": equity,
                })
                position    = "NONE"
                entry_price = None
            
            # Reset peak equity so it doesn't immediately CB again and can resume trading
            peak_equity = equity
            equity_curve[-1] = equity
            cooldown_until = i + COOLDOWN_CANDLES
            print(f"  [!] Circuit Breaker @ {ts.strftime('%Y-%m-%d %H:%M')} | "
                  f"Equity ${equity:.2f} | DD {dd_from_peak*100:.1f}% -> Resuming (cooldown {COOLDOWN_CANDLES} candles)")
            continue

        # -- Stop Loss check --
        sl_hit = False
        if position == "LONG" and entry_price:
            if (entry_price - close) / entry_price >= STOP_LOSS_PCT:
                sl_hit = True
        elif position == "SHORT" and entry_price:
            if (close - entry_price) / entry_price >= STOP_LOSS_PCT:
                sl_hit = True

        if sl_hit:
            fee = position_notional * TRADING_FEE
            if position == "LONG":
                pnl_pct_r = (close - entry_price) / entry_price
            else:
                pnl_pct_r = (entry_price - close) / entry_price
            realized = position_notional * pnl_pct_r - fee
            equity  += realized
            trades.append({
                "entry_time"  : df.iloc[entry_idx]["timestamp"],
                "exit_time"   : ts,
                "direction"   : position,
                "entry_price" : entry_price,
                "exit_price"  : close,
                "pnl_pct"     : pnl_pct_r * 100,
                "pnl_usdt"    : realized,
                "exit_reason" : "stop_loss",
                "equity_after": equity,
            })
            signals_sl.append((ts, close))
            position    = "NONE"
            entry_price = None
            df.at[i, "signal"] = "CLOSE_SL"
            equity_curve[-1] = equity
            cooldown_until = i + COOLDOWN_CANDLES
            continue

        # -- Cooldown check: skip entry if still in cooldown period --
        if i < cooldown_until:
            continue

        # -- Signal Logic --
        oversold_entry   = (rsi < RSI_OVERSOLD)  and (close < bb_lower)
        overbought_entry = (rsi > RSI_OVERBOUGHT) and (close > bb_upper)

        def close_pos(reason_tag):
            nonlocal equity, position, entry_price, entry_idx, position_notional
            fee = position_notional * TRADING_FEE
            if position == "LONG":
                pnl_r = (close - entry_price) / entry_price
            else:
                pnl_r = (entry_price - close) / entry_price
            realized = position_notional * pnl_r - fee
            equity  += realized
            trades.append({
                "entry_time"  : df.iloc[entry_idx]["timestamp"],
                "exit_time"   : ts,
                "direction"   : position,
                "entry_price" : entry_price,
                "exit_price"  : close,
                "pnl_pct"     : pnl_r * 100,
                "pnl_usdt"    : realized,
                "exit_reason" : reason_tag,
                "equity_after": equity,
            })
            position    = "NONE"
            entry_price = None
            entry_idx   = None

        def open_pos(direction):
            nonlocal equity, position, entry_price, entry_idx, position_notional
            notional = equity * POSITION_SIZE_PCT * LEVERAGE
            fee_open = notional * TRADING_FEE
            equity  -= fee_open
            position          = direction
            entry_price       = close
            entry_idx         = i
            position_notional = notional

        # -- No position: fresh entry --
        if position == "NONE":
            if oversold_entry:
                open_pos("LONG")
                signals_long.append((ts, close))
                df.at[i, "signal"] = "LONG"
            elif overbought_entry:
                open_pos("SHORT")
                signals_short.append((ts, close))
                df.at[i, "signal"] = "SHORT"

        # -- Currently LONG --
        elif position == "LONG":
            if overbought_entry:
                close_pos("flip")
                open_pos("SHORT")
                signals_short.append((ts, close))
                df.at[i, "signal"] = "FLIP_SHORT"

        # -- Currently SHORT --
        elif position == "SHORT":
            if oversold_entry:
                close_pos("flip")
                open_pos("LONG")
                signals_long.append((ts, close))
                df.at[i, "signal"] = "FLIP_LONG"

    # Pad equity curve
    while len(equity_curve) < len(df):
        equity_curve.append(equity_curve[-1])
    df["equity"] = equity_curve

    print(f"  [OK] Backtest done: {len(trades)} trades | "
          f"Final equity: ${equity:.2f}")

    return df, trades, signals_long, signals_short, signals_sl, signals_cb


# =================================================================
# STEP 4: ANALYTICS
# =================================================================

def compute_stats(trades, initial_capital, equity_curve):
    print("[4/6] Computing statistics...")
    if not trades:
        return {}

    tdf  = pd.DataFrame(trades)
    wins = tdf[tdf["pnl_usdt"] > 0]
    loss = tdf[tdf["pnl_usdt"] <= 0]

    final_eq    = tdf["equity_after"].iloc[-1]
    total_ret   = (final_eq - initial_capital) / initial_capital * 100
    total_pnl   = final_eq - initial_capital
    win_rate    = len(wins) / len(tdf) * 100
    avg_win     = wins["pnl_usdt"].mean() if len(wins) > 0 else 0
    avg_loss    = loss["pnl_usdt"].mean() if len(loss) > 0 else 0
    pf          = (wins["pnl_usdt"].sum() / abs(loss["pnl_usdt"].sum())
                   if len(loss) > 0 and loss["pnl_usdt"].sum() != 0 else float("inf"))

    # Max drawdown
    rmax = equity_curve.cummax()
    dd   = (equity_curve - rmax) / rmax * 100
    max_dd = dd.min()

    # Sharpe (annualized, 4H candles -> 6/day -> 2190/year)
    rets = equity_curve.pct_change().dropna()
    sharpe = (rets.mean() / rets.std() * np.sqrt(2190)) if rets.std() > 0 else 0

    calmar = (total_ret / abs(max_dd)) if max_dd != 0 else 0

    tdf["dur_h"] = (pd.to_datetime(tdf["exit_time"]) -
                    pd.to_datetime(tdf["entry_time"])).dt.total_seconds() / 3600

    sl_cnt   = len(tdf[tdf["exit_reason"] == "stop_loss"])
    flip_cnt = len(tdf[tdf["exit_reason"] == "flip"])
    cb_cnt   = len(tdf[tdf["exit_reason"] == "circuit_breaker"])
    lt       = tdf[tdf["direction"] == "LONG"]
    st       = tdf[tdf["direction"] == "SHORT"]

    return {
        "total_trades":     len(tdf),
        "win_trades":       len(wins),
        "loss_trades":      len(loss),
        "win_rate":         win_rate,
        "avg_win_usdt":     avg_win,
        "avg_loss_usdt":    avg_loss,
        "profit_factor":    pf,
        "total_return_pct": total_ret,
        "total_pnl_usdt":   total_pnl,
        "final_equity":     final_eq,
        "max_drawdown_pct": max_dd,
        "sharpe_ratio":     sharpe,
        "calmar_ratio":     calmar,
        "avg_duration_h":   tdf["dur_h"].mean(),
        "max_win_usdt":     wins["pnl_usdt"].max() if len(wins) > 0 else 0,
        "max_loss_usdt":    loss["pnl_usdt"].min() if len(loss) > 0 else 0,
        "sl_count":         sl_cnt,
        "flip_count":       flip_cnt,
        "cb_count":         cb_cnt,
        "long_trades":      len(lt),
        "short_trades":     len(st),
        "long_win_rate":    (len(lt[lt["pnl_usdt"]>0])/len(lt)*100) if len(lt)>0 else 0,
        "short_win_rate":   (len(st[st["pnl_usdt"]>0])/len(st)*100) if len(st)>0 else 0,
    }


# =================================================================
# STEP 5: VISUALIZATION
# =================================================================

def plot_backtest(df, trades, stats, sig_l, sig_s, sig_sl, sig_cb):
    print("[5/6] Creating visualization...")

    matplotlib.rcParams.update({
        "font.family"     : "DejaVu Sans",
        "axes.facecolor"  : PANEL_BG,
        "figure.facecolor": DARK_BG,
        "axes.edgecolor"  : GRID_COLOR,
        "axes.labelcolor" : TEXT_COLOR,
        "xtick.color"     : TEXT_COLOR,
        "ytick.color"     : TEXT_COLOR,
        "text.color"      : TEXT_COLOR,
        "grid.color"      : GRID_COLOR,
        "grid.linestyle"  : "--",
        "grid.alpha"      : 0.4,
    })

    fig = plt.figure(figsize=(24, 40), facecolor=DARK_BG)
    fig.suptitle(
        "CRV/USDT Mean Reversion Bot  -  Backtest 1 Tahun (4H)",
        fontsize=20, fontweight="bold", color=LINE_WHITE, y=0.995
    )

    gs = gridspec.GridSpec(
        7, 1, figure=fig,
        height_ratios=[3, 1.2, 1.5, 1.5, 1.5, 1.5, 1.5],
        hspace=0.45,
        left=0.06, right=0.97, top=0.97, bottom=0.03
    )

    ax_price   = fig.add_subplot(gs[0, 0])
    ax_rsi     = fig.add_subplot(gs[1, 0], sharex=ax_price)
    ax_equity  = fig.add_subplot(gs[2, 0])
    ax_dd      = fig.add_subplot(gs[3, 0])
    ax_pnl     = fig.add_subplot(gs[4, 0])
    ax_monthly = fig.add_subplot(gs[5, 0])
    ax_stats   = fig.add_subplot(gs[6, 0])

    dates  = df["timestamp"].values
    closes = df["close"].values
    rsi    = df["rsi"].values
    equity = df["equity"].values

    # ===============================================
    # [1] PRICE + BB + SIGNALS
    # ===============================================
    ax_price.fill_between(dates, df["bb_upper"], df["bb_lower"],
                          alpha=0.08, color=ACCENT_BLUE, label=f"BB Band ({BB_PERIOD},{BB_STD_DEV})")
    ax_price.plot(dates, df["bb_upper"], color=ACCENT_BLUE, lw=0.7, alpha=0.5, ls="--")
    ax_price.plot(dates, df["bb_mid"],   color=ACCENT_GOLD, lw=0.6, alpha=0.4, ls=":")
    ax_price.plot(dates, df["bb_lower"], color=ACCENT_BLUE, lw=0.7, alpha=0.5, ls="--")
    ax_price.plot(dates, closes, color=LINE_WHITE, lw=1.0, label="CRV/USDT Close", alpha=0.95)

    if sig_l:
        lx,ly = zip(*sig_l)
        ax_price.scatter(lx,ly, marker="^", color=ACCENT_GREEN, s=90, zorder=5,
                         label=f"LONG Entry ({len(sig_l)})", edgecolors="white", lw=0.5)
    if sig_s:
        sx,sy = zip(*sig_s)
        ax_price.scatter(sx,sy, marker="v", color=ACCENT_RED, s=90, zorder=5,
                         label=f"SHORT Entry ({len(sig_s)})", edgecolors="white", lw=0.5)
    if sig_sl:
        slx,sly = zip(*sig_sl)
        ax_price.scatter(slx,sly, marker="x", color=ACCENT_GOLD, s=110, zorder=6,
                         label=f"Stop Loss ({len(sig_sl)})", lw=2)
    if sig_cb:
        cx,cy = zip(*sig_cb)
        ax_price.scatter(cx,cy, marker="*", color=ACCENT_PURPLE, s=180, zorder=6,
                         label=f"Circuit Breaker ({len(sig_cb)})", edgecolors="white", lw=0.5)

    ax_price.set_ylabel("Price (USDT)", fontsize=10)
    ax_price.set_title("Harga CRV/USDT + Bollinger Bands + Entry/Exit Signals",
                       color=TEXT_COLOR, fontsize=12, pad=8)
    ax_price.legend(loc="upper left", framealpha=0.3, facecolor=PANEL_BG,
                    edgecolor=GRID_COLOR, fontsize=8, ncol=3)
    ax_price.grid(True, alpha=0.25)
    ax_price.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
    ax_price.xaxis.set_major_locator(mdates.MonthLocator())
    plt.setp(ax_price.xaxis.get_majorticklabels(), rotation=30, ha="right")

    # ===============================================
    # [2] RSI
    # ===============================================
    ax_rsi.plot(dates, rsi, color=ACCENT_PURPLE, lw=1.0, label="RSI(14)")
    ax_rsi.axhline(70, color=ACCENT_RED,   lw=1, ls="--", alpha=0.7, label="Overbought 70")
    ax_rsi.axhline(30, color=ACCENT_GREEN, lw=1, ls="--", alpha=0.7, label="Oversold 30")
    rsi_arr = np.array(rsi, dtype=float)
    ax_rsi.fill_between(dates, rsi_arr, 70, where=rsi_arr > 70, alpha=0.12, color=ACCENT_RED)
    ax_rsi.fill_between(dates, rsi_arr, 30, where=rsi_arr < 30, alpha=0.12, color=ACCENT_GREEN)
    ax_rsi.set_ylim(0, 100)
    ax_rsi.set_ylabel("RSI", fontsize=10)
    ax_rsi.set_title("RSI(14) - Signal Trigger Zones", color=TEXT_COLOR, fontsize=12, pad=6)
    ax_rsi.legend(loc="upper left", framealpha=0.3, facecolor=PANEL_BG,
                  edgecolor=GRID_COLOR, fontsize=8)
    ax_rsi.grid(True, alpha=0.25)

    # ===============================================
    # [3] EQUITY CURVE
    # ===============================================
    eq_s = pd.Series(equity, index=pd.to_datetime(dates)).dropna()
    eq_d = eq_s.index
    eq_v = eq_s.values

    ax_equity.fill_between(eq_d, INITIAL_CAPITAL, eq_v,
                           where=eq_v >= INITIAL_CAPITAL, alpha=0.20, color=ACCENT_GREEN)
    ax_equity.fill_between(eq_d, INITIAL_CAPITAL, eq_v,
                           where=eq_v < INITIAL_CAPITAL, alpha=0.20, color=ACCENT_RED)
    ax_equity.plot(eq_d, eq_v, color=ACCENT_BLUE, lw=1.8, label="Equity Curve")
    ax_equity.axhline(INITIAL_CAPITAL, color=ACCENT_GOLD, lw=1.2, ls="--", alpha=0.8,
                      label=f"Modal Awal ${INITIAL_CAPITAL:,.0f}")

    if len(eq_v) > 0:
        fv = eq_v[-1]
        fc = ACCENT_GREEN if fv >= INITIAL_CAPITAL else ACCENT_RED
        ax_equity.scatter([eq_d[-1]], [fv], color=fc, s=80, zorder=5)
        ax_equity.annotate(
            f"${fv:,.2f}", xy=(eq_d[-1], fv),
            xytext=(-70, 15 if fv >= INITIAL_CAPITAL else -25),
            textcoords="offset points", fontsize=10, color=fc, fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=fc, lw=1)
        )

    ax_equity.set_ylabel("Equity (USDT)", fontsize=10)
    ax_equity.set_title("Equity Curve - Pertumbuhan Modal", color=TEXT_COLOR, fontsize=12, pad=6)
    ax_equity.legend(loc="upper left", framealpha=0.3, facecolor=PANEL_BG,
                     edgecolor=GRID_COLOR, fontsize=8)
    ax_equity.grid(True, alpha=0.25)
    ax_equity.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
    ax_equity.xaxis.set_major_locator(mdates.MonthLocator())
    plt.setp(ax_equity.xaxis.get_majorticklabels(), rotation=30, ha="right")
    ax_equity.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,p: f"${x:,.0f}"))

    # ===============================================
    # [4] P&L PER TRADE
    # ===============================================
    if trades:
        tdf = pd.DataFrame(trades)
        pnl = tdf["pnl_usdt"].values
        clr = [ACCENT_GREEN if p > 0 else ACCENT_RED for p in pnl]
        ax_pnl.bar(range(len(pnl)), pnl, color=clr, alpha=0.85, width=0.8)
        ax_pnl.axhline(0, color=TEXT_COLOR, lw=0.8, alpha=0.5)

        # Annotate each bar
        for idx, val in enumerate(pnl):
            va = "bottom" if val >= 0 else "top"
            ax_pnl.text(idx, val, f"${val:+.0f}", ha="center", va=va,
                        fontsize=7, color=ACCENT_GREEN if val > 0 else ACCENT_RED,
                        fontweight="bold")

    ax_pnl.set_xlabel("Trade #", fontsize=9)
    ax_pnl.set_ylabel("P&L (USDT)", fontsize=9)
    ax_pnl.set_title("P&L per Trade", color=TEXT_COLOR, fontsize=12, pad=6)
    ax_pnl.grid(True, alpha=0.25, axis="y")
    ax_pnl.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,p: f"${x:,.0f}"))

    # ===============================================
    # [5] MONTHLY RETURNS
    # ===============================================
    eq_monthly = eq_s.resample("ME").last().pct_change() * 100
    eq_monthly = eq_monthly.dropna()
    if len(eq_monthly) > 0:
        m_clrs = [ACCENT_GREEN if r > 0 else ACCENT_RED for r in eq_monthly.values]
        labels = [d.strftime("%b\n'%y") for d in eq_monthly.index]
        bars = ax_monthly.bar(labels, eq_monthly.values, color=m_clrs, alpha=0.85, width=0.7)
        ax_monthly.axhline(0, color=TEXT_COLOR, lw=0.8, alpha=0.5)

        for bar_rect, val in zip(bars, eq_monthly.values):
            va = "bottom" if val >= 0 else "top"
            offset = 0.3 if val >= 0 else -0.3
            ax_monthly.text(
                bar_rect.get_x() + bar_rect.get_width() / 2,
                val + offset, f"{val:.1f}%",
                ha="center", va=va, fontsize=7,
                color=ACCENT_GREEN if val >= 0 else ACCENT_RED,
                fontweight="bold"
            )

    ax_monthly.set_ylabel("Return (%)", fontsize=9)
    ax_monthly.set_title("Monthly Returns (%)", color=TEXT_COLOR, fontsize=12, pad=6)
    ax_monthly.grid(True, alpha=0.25, axis="y")
    ax_monthly.tick_params(axis="x", labelsize=7)

    # ===============================================
    # [6] DRAWDOWN
    # ===============================================
    rmax = eq_s.cummax()
    dd_p = (eq_s - rmax) / rmax * 100

    ax_dd.fill_between(dd_p.index, dd_p.values, 0, alpha=0.5, color=ACCENT_RED, label="Drawdown")
    ax_dd.plot(dd_p.index, dd_p.values, color=ACCENT_RED, lw=0.8)
    ax_dd.axhline(-CIRCUIT_BREAKER_DD * 100, color=ACCENT_PURPLE, lw=1.2, ls="--", alpha=0.8,
                  label=f"Circuit Breaker -{CIRCUIT_BREAKER_DD*100:.0f}%")
    ax_dd.axhline(-STOP_LOSS_PCT * 100, color=ACCENT_GOLD, lw=1, ls=":", alpha=0.7,
                  label=f"Per-Trade SL -{STOP_LOSS_PCT*100:.0f}%")
    ax_dd.set_ylabel("Drawdown (%)", fontsize=9)
    ax_dd.set_title("Portfolio Drawdown", color=TEXT_COLOR, fontsize=12, pad=6)
    ax_dd.legend(loc="lower left", framealpha=0.3, facecolor=PANEL_BG,
                 edgecolor=GRID_COLOR, fontsize=7)
    ax_dd.grid(True, alpha=0.25)
    ax_dd.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
    ax_dd.xaxis.set_major_locator(mdates.MonthLocator())
    plt.setp(ax_dd.xaxis.get_majorticklabels(), rotation=30, ha="right")

    # ===============================================
    # [7] STATS BOX
    # ===============================================
    ax_stats.set_facecolor(PANEL_BG)
    ax_stats.axis("off")

    if stats:
        rc = ACCENT_GREEN if stats.get("total_return_pct", 0) >= 0 else ACCENT_RED

        info = [
            ("=== HASIL BACKTEST ===",           LINE_WHITE,    13, "bold"),
            ("",                                  TEXT_COLOR,     6, "normal"),
            (f"Modal Awal     : ${INITIAL_CAPITAL:>10,.2f}",   TEXT_COLOR, 9.5, "normal"),
            (f"Equity Akhir   : ${stats['final_equity']:>10,.2f}",   rc, 9.5, "bold"),
            (f"Total Return   : {stats['total_return_pct']:>+10.2f}%",  rc, 9.5, "bold"),
            (f"Total P&L      : ${stats['total_pnl_usdt']:>+10.2f}",   rc, 9.5, "bold"),
            ("",                                  TEXT_COLOR,     5, "normal"),
            ("--- Trade Stats ---",    ACCENT_BLUE, 9.5, "bold"),
            (f"Total Trades   : {stats['total_trades']:>10}",     TEXT_COLOR, 9.5, "normal"),
            (f"  Long         : {stats.get('long_trades',0):>10}",   TEXT_COLOR, 9, "normal"),
            (f"  Short        : {stats.get('short_trades',0):>10}",  TEXT_COLOR, 9, "normal"),
            (f"Win Rate       : {stats['win_rate']:>10.1f}%",     ACCENT_GREEN, 9.5, "normal"),
            (f"Profit Factor  : {stats['profit_factor']:>10.2f}x", ACCENT_GOLD, 9.5, "bold"),
            (f"Avg Win        : ${stats['avg_win_usdt']:>+10.2f}",   ACCENT_GREEN, 9, "normal"),
            (f"Avg Loss       : ${stats['avg_loss_usdt']:>+10.2f}",  ACCENT_RED,   9, "normal"),
            (f"Max Win        : ${stats['max_win_usdt']:>+10.2f}",   ACCENT_GREEN, 9, "normal"),
            (f"Max Loss       : ${stats['max_loss_usdt']:>+10.2f}",  ACCENT_RED,   9, "normal"),
            ("",                                  TEXT_COLOR,     5, "normal"),
            ("--- Risk Metrics ---",   ACCENT_BLUE, 9.5, "bold"),
            (f"Max Drawdown   : {stats['max_drawdown_pct']:>10.2f}%", ACCENT_RED, 9.5, "bold"),
            (f"Sharpe Ratio   : {stats['sharpe_ratio']:>10.2f}",   ACCENT_GOLD, 9.5, "normal"),
            (f"Calmar Ratio   : {stats['calmar_ratio']:>10.2f}",   ACCENT_GOLD, 9.5, "normal"),
            (f"Avg Duration   : {stats['avg_duration_h']:>9.1f}h", TEXT_COLOR,  9, "normal"),
            ("",                                  TEXT_COLOR,     5, "normal"),
            ("--- Exit Reasons ---",   ACCENT_BLUE, 9.5, "bold"),
            (f"Flip (Signal)  : {stats['flip_count']:>10}",       TEXT_COLOR,    9, "normal"),
            (f"Stop Loss      : {stats['sl_count']:>10}",         ACCENT_RED,   9, "normal"),
            (f"Circuit Breaker: {stats['cb_count']:>10}",         ACCENT_PURPLE, 9, "normal"),
            ("",                                  TEXT_COLOR,     5, "normal"),
            ("--- Win Rate by Side ---", ACCENT_BLUE, 9.5, "bold"),
            (f"Long Win Rate  : {stats['long_win_rate']:>10.1f}%", ACCENT_GREEN, 9, "normal"),
            (f"Short Win Rate : {stats['short_win_rate']:>10.1f}%",ACCENT_GREEN, 9, "normal"),
        ]

        y = 0.98
        for text, color, size, weight in info:
            ax_stats.text(0.05, y, text, transform=ax_stats.transAxes,
                          fontsize=size, color=color, fontweight=weight,
                          fontfamily="monospace", va="top")
            y -= 0.031

    # Footer
    fig.text(
        0.5, 0.005,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} WIB  |  "
        f"Strategy: RSI({RSI_PERIOD})+BB({BB_PERIOD},{BB_STD_DEV}s) 4H  |  Leverage: {LEVERAGE}x  |  "
        f"SL: {STOP_LOSS_PCT*100:.0f}%  |  CB: {CIRCUIT_BREAKER_DD*100:.0f}%  |  "
        f"Data: Bybit CRV/USDT Perpetual",
        ha="center", fontsize=8, color="#6E7681"
    )

    outfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backtest_result.png")
    plt.savefig(outfile, dpi=150, bbox_inches="tight", facecolor=DARK_BG, edgecolor="none")
    print(f"  [OK] Chart saved: {outfile}")
    plt.close(fig)


# =================================================================
# STEP 6: PRINT SUMMARY
# =================================================================

def print_summary(stats, trades):
    print("\n" + "="*65)
    print("  RINGKASAN BACKTESTING - CRV/USDT Mean Reversion Bot")
    print("="*65)

    if not stats:
        print("  Tidak ada trade yang dieksekusi.")
        return

    sign = "+" if stats["total_return_pct"] >= 0 else ""
    print(f"  Modal Awal          : ${INITIAL_CAPITAL:>12,.2f}")
    print(f"  Equity Akhir        : ${stats['final_equity']:>12,.2f}")
    print(f"  Total Return        : {sign}{stats['total_return_pct']:.2f}%")
    print(f"  Total P&L           : ${stats['total_pnl_usdt']:>+12.2f}")
    print()
    print(f"  Total Trades        : {stats['total_trades']}")
    print(f"    - Long            : {stats.get('long_trades',0)}")
    print(f"    - Short           : {stats.get('short_trades',0)}")
    print(f"  Win Rate            : {stats['win_rate']:.1f}%")
    print(f"  Profit Factor       : {stats['profit_factor']:.2f}x")
    print(f"  Avg Trade Duration  : {stats['avg_duration_h']:.1f} jam")
    print()
    print(f"  Max Drawdown        : {stats['max_drawdown_pct']:.2f}%")
    print(f"  Sharpe Ratio        : {stats['sharpe_ratio']:.2f}")
    print(f"  Calmar Ratio        : {stats['calmar_ratio']:.2f}")
    print()
    print(f"  Stop Loss Hits      : {stats['sl_count']}")
    print(f"  Flip Trades         : {stats['flip_count']}")
    print(f"  Circuit Breaker     : {stats['cb_count']}")
    print("="*65)

    if trades:
        print(f"\n  Trade Log (last {min(15, len(trades))}):")
        print(f"  {'#':>3} {'Dir':6} {'Entry':>8} {'Exit':>8} {'P&L ($)':>10} {'P&L %':>8} {'Reason':14} {'Duration'}")
        print(f"  {'---':>3} {'------':6} {'--------':>8} {'--------':>8} {'----------':>10} {'--------':>8} {'--------------':14} {'--------'}")
        for idx, t in enumerate(trades[-15:], start=max(1, len(trades)-14)):
            dur = (pd.to_datetime(t["exit_time"]) - pd.to_datetime(t["entry_time"]))
            dur_h = dur.total_seconds() / 3600
            pnl_str = f"${t['pnl_usdt']:>+9.2f}"
            pct_str = f"{t['pnl_pct']:>+7.2f}%"
            print(f"  {idx:>3} {t['direction']:6} {t['entry_price']:>8.4f} "
                  f"{t['exit_price']:>8.4f} {pnl_str:>10} {pct_str:>8} "
                  f"{t['exit_reason']:14} {dur_h:.0f}h")
    print()


# =================================================================
# MAIN
# =================================================================

if __name__ == "__main__":
    print("+" + "-"*60 + "+")
    print("|  CRV-USDT Mean Reversion Bot - Backtest 1 Tahun         |")
    print("|  Modal: $10,000  |  Leverage: 2x  |  TF: 4H            |")
    print("+" + "-"*60 + "+")
    print()

    try:
        # 1. Fetch data
        df = fetch_ohlcv_1y()

        # 2. Compute indicators
        df = compute_indicators(df)

        # 3. Run backtest
        df, trades, sig_l, sig_s, sig_sl, sig_cb = run_backtest(df)

        # 4. Compute stats
        eq_series = pd.Series(df["equity"].values).dropna()
        stats     = compute_stats(trades, INITIAL_CAPITAL, eq_series)

        # 5. Print summary
        print_summary(stats, trades)

        # 6. Visualize
        plot_backtest(df, trades, stats, sig_l, sig_s, sig_sl, sig_cb)

        print("[6/6] Done! Open backtest_result.png to see the chart.")

    except KeyboardInterrupt:
        print("\n[INFO] Cancelled by user.")
    except Exception as e:
        import traceback
        print(f"\n[ERROR] {e}")
        traceback.print_exc()
