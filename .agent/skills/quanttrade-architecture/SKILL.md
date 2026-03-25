---
description: QuantTrade Web App architecture reference — data pipeline, common bugs, and fix patterns
---

# QuantTrade Web App — Architecture & Fix Patterns

## Project Structure

```
QuantTrade-Web-App/
├── backend/
│   ├── main.py              # FastAPI app, all API endpoints, bot scheduler
│   ├── strategy_core.py     # TradingEngine class: data fetch, indicators, backtest
│   ├── paper_trader.py      # PaperTrader class: simulated trading with events
│   ├── execution_engine.py  # Real/Testnet order execution via CCXT
│   ├── db_utils.py          # Centralized SQLite connection (WAL mode)
│   └── market_data.db       # SQLite database (auto-created)
├── frontend/
│   └── src/
│       ├── pages/Dashboard/DashboardPage.jsx  # BacktestLab + Scanner UI
│       └── components/
│           ├── PaperTradingDashboard.jsx
│           ├── EliteSignals.jsx
│           ├── Watchlist.jsx
│           ├── Sidebar.jsx
│           └── ...
```

## Data Pipeline Flow

```
User Request → API Endpoint → TradingEngine → fetch_data() → _load_from_db / API → _save_to_db
                                             → prepare_indicators() → slice_data_by_period()
                                             → run_backtest() → metrics
```

### Key TradingEngine Methods (strategy_core.py)

| Method | Purpose |
|--------|---------|
| `fetch_data(symbol, period, interval)` | Smart incremental data fetch: DB-first, then API delta |
| `_load_from_db(symbol, timeframe, period)` | Load candles from SQLite with period cutoff |
| `_save_to_db(symbol, timeframe, ohlcv)` | Batch INSERT OR IGNORE candles |
| `_get_cached_result(symbol, tf, period, strat)` | Check strategy_cache for valid cached backtest |
| `prepare_indicators(df)` | Compute SMA20/50, EMA200, BB, RSI, ATR, Grid levels |
| `slice_data_by_period(df, period)` | Slice DataFrame by period string |
| `run_backtest(raw_df, strategy, period)` | Full bar-by-bar simulation, returns metrics |

### Frontend Period/Timeframe Options (DashboardPage.jsx line 460-461)

- **Timeframes**: `1h`, `4h`, `1d`, `1wk`
- **Periods**: `1mo`, `6mo`, `1y`, `2y`, `max`
- **Directions**: `LONG`, `SHORT`

### CCXT Symbol Mapping

Frontend sends `CAKE-USDT` → `fetch_data` converts to `CAKE/USDT` for CCXT API.
Frontend sends `1wk` → `fetch_data` converts to `1w` for CCXT API.

## Database Schema (market_data.db)

### market_data
```sql
(symbol TEXT, timeframe TEXT, timestamp INTEGER,
 open REAL, high REAL, low REAL, close REAL, volume REAL,
 PRIMARY KEY (symbol, timeframe, timestamp))
```

### strategy_cache
```sql
(symbol TEXT, timeframe TEXT, period TEXT, strategy TEXT,
 net_profit REAL, win_rate REAL, total_trades INTEGER,
 max_drawdown REAL, sharpe_ratio REAL, final_balance REAL,
 signal_data TEXT, rr_ratio TEXT, cached_data_ts INTEGER, updated_at TEXT,
 PRIMARY KEY (symbol, timeframe, period, strategy))
```

### Other tables
- `trade_log` — Bot execution history
- `scan_cache` — Scanner results cache by sector
- `watchlist` — User watchlist items (created in main.py)
- `paper_trades` / `paper_events` — Paper trading data (created in paper_trader.py)

## Common Bugs & Fix Patterns

### 1. Windows Terminal Emoji Crash
**Symptom**: `surrogates not allowed` error, functions silently return None
**Cause**: Emoji chars (📥, ⚡, etc.) in print() crash on Windows uvicorn terminal encoding
**Fix**: NEVER use emoji in Python print statements. Use ASCII like `[DATA]`, `[ERROR]`, `[OK]`
**Scope**: ALL backend .py files

### 2. Database Locking / Infinite Loading
**Symptom**: UI shows infinite loading on Paper Trading or Watchlist pages
**Cause**: Multiple threads hold sqlite3 connections without WAL mode
**Fix**: Use `db_utils.get_db_connection("market_data.db")` which enables WAL + busy_timeout
**Scope**: main.py, paper_trader.py (all direct sqlite3.connect calls)

### 3. Data Consistency Between Scanner and Manual Backtest
**Symptom**: Same config gives different results depending on whether scanner ran first
**Cause**: `fetch_data` seeds only 2 years (730 days) — insufficient for 2y + indicator warmup
**Fix**: Extended seed to 3 years (1095 days). Both scanner and manual backtest use identical
code paths through `find_best_strategy_for_symbol` → `fetch_data(period="max")` → `run_backtest`
**Key**: Scanner tests 60 combos (10 strats × 3 TF × 2 periods) and picks the BEST one

### 4. Binance Futures Testnet Deprecated
**Symptom**: `binance testnet/sandbox mode is not supported for futures anymore`
**Cause**: CCXT Binance futures sandbox was deprecated
**Fix**: In execution_engine.py, force `paper_mode=True` when `use_testnet=True` (bypass CCXT)

### 5. Period/Timeframe Support Gaps
**Must handle these periods**: `1mo`, `3mo`, `6mo`, `1y`, `2y`, `max`
**Must handle these timeframes**: `1h`, `4h`, `1d`, `1wk` (→ `1w` for CCXT)
**Check 3 functions**: `_load_from_db`, `slice_data_by_period`, `_get_interval_ms`

## API Endpoints Reference

### BacktestLab
- `POST /api/run-backtest` — Single strategy backtest
- `POST /api/run-dual-backtest` — LONG + SHORT comparison
- `POST /api/compare-strategies` — All strategies matrix

### Scanner
- `POST /api/scan-market` — Single sector scan
- `POST /api/scan-all` — All sectors parallel scan
- `GET /api/scanner/results` — Cached scan results

### Paper Trading
- `GET /api/paper-trader/status` — Current status
- `POST /api/paper-trader/configure` — Set config (use_testnet → paper_mode=True)
- `POST /api/paper-trader/start` — Start auto-trading
- `POST /api/paper-trader/stop` — Stop
- `POST /api/paper-trader/cycle` — Run single cycle
- `GET /api/paper-trader/trades` — Returns `{trades: [...]}`
- `GET /api/paper-trader/events` — SSE stream for live feed

### Watchlist
- `GET /api/watchlist` — List watchlist
- `POST /api/watchlist` — Add item
- `DELETE /api/watchlist/{symbol}` — Remove item

## Fix Approach Rules

1. **Fix in 1 package**: When fixing a bug, trace ALL related code paths and fix everything at once
2. **No emojis in Python**: Use ASCII-only in print statements to prevent Windows crashes
3. **Always check 3 period functions**: `_load_from_db`, `slice_data_by_period`, `_get_interval_ms`
4. **DB connections**: Always use `db_utils.get_db_connection` or engine's `_get_db_conn` (WAL mode)
5. **Test with fresh DB**: Delete `market_data.db` to test cold-start scenarios
