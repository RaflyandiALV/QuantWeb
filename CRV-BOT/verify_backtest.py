"""Quick verification script - CRV-BOT backtest with fixed indicators."""
import sys, os, warnings, time
warnings.filterwarnings("ignore")
import matplotlib; matplotlib.use("Agg")
import ccxt, pandas as pd, numpy as np
from datetime import datetime, timezone, timedelta

INITIAL_CAPITAL=10000; LEVERAGE=2; POSITION_SIZE_PCT=0.90; STOP_LOSS_PCT=0.15
CIRCUIT_BREAKER_DD=0.35; RSI_PERIOD=14; RSI_OVERSOLD=30; RSI_OVERBOUGHT=70
BB_PERIOD=20; BB_STD_DEV=2.0; TRADING_FEE=0.00055

print("=== CRV-BOT Backtest Verification (SMA RSI + ddof=1 BB) ===\n")
print("[1/3] Fetching 1Y data from Bybit...")
since_dt = datetime.now(timezone.utc) - timedelta(days=365)
since_ms = int(since_dt.timestamp() * 1000)
now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
exchange = ccxt.bybit({"enableRateLimit": True, "options": {"defaultType": "swap"}})
all_ohlcv = []
cursor = since_ms
while cursor < now_ms:
    batch = exchange.fetch_ohlcv("CRV/USDT:USDT", "4h", since=cursor, limit=200)
    if not batch: break
    all_ohlcv.extend(batch)
    last_ts = batch[-1][0]
    if last_ts <= cursor: break
    cursor = last_ts + 1
    time.sleep(0.15)

df = pd.DataFrame(all_ohlcv, columns=["timestamp","open","high","low","close","volume"])
df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
df = df.drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)
df = df[df["timestamp"] >= since_dt].reset_index(drop=True)
print(f"  Candles: {len(df)} ({df['timestamp'].iloc[0].strftime('%Y-%m-%d')} to {df['timestamp'].iloc[-1].strftime('%Y-%m-%d')})")

print("[2/3] Computing indicators (SMA RSI + ddof=1 BB)...")
df["bb_mid"] = df["close"].rolling(BB_PERIOD).mean()
bb_std = df["close"].rolling(BB_PERIOD).std()  # ddof=1 default = QuantWeb
df["bb_upper"] = df["bb_mid"] + BB_STD_DEV * bb_std
df["bb_lower"] = df["bb_mid"] - BB_STD_DEV * bb_std
delta = df["close"].diff()
gain = (delta.where(delta > 0, 0)).rolling(RSI_PERIOD).mean()
loss = (-delta.where(delta < 0, 0)).rolling(RSI_PERIOD).mean()
rs = gain / loss
df["rsi"] = 100 - (100 / (1 + rs))

print("[3/3] Running backtest...")

# Use a class to hold mutable state (avoids nonlocal issues)
class State:
    equity = INITIAL_CAPITAL
    peak_equity = INITIAL_CAPITAL
    circuit_breaker = False
    position = "NONE"
    entry_price = None
    entry_idx = None
    position_notional = 0.0

s = State()
trades = []
WARMUP = BB_PERIOD + RSI_PERIOD + 5

for i in range(len(df)):
    row = df.iloc[i]
    close = row["close"]
    
    if s.position == "LONG":
        pnl_pct = (close - s.entry_price) / s.entry_price
        current_equity = s.equity + s.position_notional * pnl_pct
    elif s.position == "SHORT":
        pnl_pct = (s.entry_price - close) / s.entry_price
        current_equity = s.equity + s.position_notional * pnl_pct
    else:
        current_equity = s.equity

    if i < WARMUP:
        continue

    rsi = row["rsi"]
    bb_upper = row["bb_upper"]
    bb_lower = row["bb_lower"]

    if pd.isna(rsi) or pd.isna(bb_upper):
        continue
    if s.circuit_breaker:
        continue

    if current_equity > s.peak_equity:
        s.peak_equity = current_equity

    dd_from_peak = (s.peak_equity - current_equity) / s.peak_equity
    if dd_from_peak >= CIRCUIT_BREAKER_DD:
        s.circuit_breaker = True
        if s.position != "NONE":
            fee = s.position_notional * TRADING_FEE
            if s.position == "LONG":
                pnl_pct_r = (close - s.entry_price) / s.entry_price
            else:
                pnl_pct_r = (s.entry_price - close) / s.entry_price
            realized = s.position_notional * pnl_pct_r - fee
            s.equity += realized
            trades.append({"dir": s.position, "pnl_pct": pnl_pct_r * 100, "pnl_usdt": realized, "reason": "circuit_breaker"})
            s.position = "NONE"
            s.entry_price = None
        print(f"  [CB] Circuit Breaker! Equity=${s.equity:.2f}")
        continue

    sl_hit = False
    if s.position == "LONG" and s.entry_price:
        if (s.entry_price - close) / s.entry_price >= STOP_LOSS_PCT:
            sl_hit = True
    elif s.position == "SHORT" and s.entry_price:
        if (close - s.entry_price) / s.entry_price >= STOP_LOSS_PCT:
            sl_hit = True

    if sl_hit:
        fee = s.position_notional * TRADING_FEE
        if s.position == "LONG":
            pnl_pct_r = (close - s.entry_price) / s.entry_price
        else:
            pnl_pct_r = (s.entry_price - close) / s.entry_price
        realized = s.position_notional * pnl_pct_r - fee
        s.equity += realized
        trades.append({"dir": s.position, "pnl_pct": pnl_pct_r * 100, "pnl_usdt": realized, "reason": "stop_loss"})
        s.position = "NONE"
        s.entry_price = None
        continue

    oversold_entry = (rsi < RSI_OVERSOLD) and (close < bb_lower)
    overbought_entry = (rsi > RSI_OVERBOUGHT) and (close > bb_upper)

    def close_pos(reason_tag):
        fee = s.position_notional * TRADING_FEE
        if s.position == "LONG":
            pnl_r = (close - s.entry_price) / s.entry_price
        else:
            pnl_r = (s.entry_price - close) / s.entry_price
        realized = s.position_notional * pnl_r - fee
        s.equity += realized
        trades.append({"dir": s.position, "pnl_pct": pnl_r * 100, "pnl_usdt": realized, "reason": reason_tag})
        s.position = "NONE"
        s.entry_price = None
        s.entry_idx = None

    def open_pos(direction):
        notional = s.equity * POSITION_SIZE_PCT * LEVERAGE
        fee_open = notional * TRADING_FEE
        s.equity -= fee_open
        s.position = direction
        s.entry_price = close
        s.entry_idx = i
        s.position_notional = notional

    if s.position == "NONE":
        if oversold_entry:
            open_pos("LONG")
        elif overbought_entry:
            open_pos("SHORT")
    elif s.position == "LONG":
        if overbought_entry:
            close_pos("flip")
            open_pos("SHORT")
    elif s.position == "SHORT":
        if oversold_entry:
            close_pos("flip")
            open_pos("LONG")

# ── Print Results ──
lt = [t for t in trades if t["dir"] == "LONG"]
st = [t for t in trades if t["dir"] == "SHORT"]
wins = [t for t in trades if t["pnl_usdt"] > 0]

print("")
print("=" * 60)
print("  BACKTEST RESULTS - CRV/USDT 4H Mean Reversion")
print("  (SMA RSI + Sample StdDev BB = QuantWeb-aligned)")
print("  Leverage: 2x | Position: 90% equity")
print("=" * 60)
print(f"  Modal Awal       : ${INITIAL_CAPITAL:>12,.2f}")
print(f"  Final Equity     : ${s.equity:>12,.2f}")
print(f"  Total Return     : {(s.equity - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100:>+10.2f}%")
print(f"  Total PnL        : ${s.equity - INITIAL_CAPITAL:>+12,.2f}")
print("")
print(f"  Total Trades     : {len(trades)}")
print(f"    Long           : {len(lt)}")
print(f"    Short          : {len(st)}")
wr = len(wins) / len(trades) * 100 if trades else 0
print(f"  Win Rate         : {wr:.1f}%")

sl_cnt = len([t for t in trades if t["reason"] == "stop_loss"])
flip_cnt = len([t for t in trades if t["reason"] == "flip"])
cb_cnt = len([t for t in trades if t["reason"] == "circuit_breaker"])
print(f"  Stop Loss Hits   : {sl_cnt}")
print(f"  Flip Trades      : {flip_cnt}")
print(f"  Circuit Breaker  : {cb_cnt}")
print("")
print("  --- Trade Log ---")
print(f"  {'#':>3} {'Dir':5s} {'PnL%':>9s} {'PnL USD':>12s}  Reason")
print(f"  {'---':>3} {'-----':5s} {'---------':>9s} {'------------':>12s}  ------")
for idx, t in enumerate(trades, 1):
    d = t["dir"]
    pct = t["pnl_pct"]
    usd = t["pnl_usdt"]
    r = t["reason"]
    print(f"  {idx:3d} {d:5s} {pct:+9.2f}% ${usd:+11.2f}  {r}")
print("=" * 60)
