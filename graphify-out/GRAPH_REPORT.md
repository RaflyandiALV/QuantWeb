# Graph Report - C:\Project Github\QuantTrade-Web-App  (2026-04-18)

## Corpus Check
- 91 files · ~319,353 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 806 nodes · 2174 edges · 60 communities detected
- Extraction: 51% EXTRACTED · 49% INFERRED · 0% AMBIGUOUS · INFERRED: 1070 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]

## God Nodes (most connected - your core abstractions)
1. `TradingEngine` - 125 edges
2. `AlphaDataProvider` - 112 edges
3. `AIBrain` - 96 edges
4. `AlphaFeatureEngine` - 93 edges
5. `FuturesExecutionManager` - 92 edges
6. `PaperTrader` - 82 edges
7. `ValidationEngine` - 73 edges
8. `MacroIntelligence` - 72 edges
9. `GlobalMarketAnalyzer` - 71 edges
10. `AnomalyScanner` - 69 edges

## Surprising Connections (you probably didn't know these)
- `Cumulative Volume Delta = buy_volume - sell_volume.         Positive → buyers d` --uses--> `AlphaDataProvider`  [INFERRED]
  C:\Project Github\QuantTrade-Web-App\backend\alpha_features.py → C:\Project Github\QuantTrade-Web-App\backend\alpha_data.py
- `Delta Momentum = slope of CVD over recent snapshots.         Uses linear regres` --uses--> `AlphaDataProvider`  [INFERRED]
  C:\Project Github\QuantTrade-Web-App\backend\alpha_features.py → C:\Project Github\QuantTrade-Web-App\backend\alpha_data.py
- `Funding Pressure = funding_rate × open_interest_value.         Represents the d` --uses--> `AlphaDataProvider`  [INFERRED]
  C:\Project Github\QuantTrade-Web-App\backend\alpha_features.py → C:\Project Github\QuantTrade-Web-App\backend\alpha_data.py
- `OI Change Rate = ΔOI / OI as percentage.         Positive → new money entering,` --uses--> `AlphaDataProvider`  [INFERRED]
  C:\Project Github\QuantTrade-Web-App\backend\alpha_features.py → C:\Project Github\QuantTrade-Web-App\backend\alpha_data.py
- `Long/Short Skew = (long_ratio - 0.5) × 2.         Range: -1 to +1.         +1` --uses--> `AlphaDataProvider`  [INFERRED]
  C:\Project Github\QuantTrade-Web-App\backend\alpha_features.py → C:\Project Github\QuantTrade-Web-App\backend\alpha_data.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.12
Nodes (99): AIBrain, Hybrid AI Decision Engine.     Primary: Gemini 2.5 Flash via Google Generative, AlphaDataProvider, Fetches microstructure data from Binance Futures API.     Provides raw data for, AlphaFeatureEngine, Transforms raw microstructure data into normalized trading features.     Output, AnomalyScanner, Market anomaly detector using CCXT exchange connection.     Designed to work wi (+91 more)

### Community 1 - "Community 1"
Cohesion: 0.03
Nodes (69): Retrieve decision history from database., get_db_connection(), Get a new SQLite connection with WAL mode enabled.     WAL mode prevents 'databa, add_watchlist(), analyze_market_reason(), btc_radar(), calculate_rr_string(), _calculate_score() (+61 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (79): _execute_close_long(), _execute_close_short(), _execute_open_long(), _execute_open_short(), main(), _place_exchange_stop_loss(), Place a server-side conditional SL order on Bybit.     This protects against fla, Returns seconds remaining until the next 4H candle closes.     4H candles close (+71 more)

### Community 3 - "Community 3"
Cohesion: 0.03
Nodes (61): Rotate to next API key in the pool., Main entry point: analyze market data and return trading decision.          Ar, Call Gemini 2.5 Flash for trading decision with rolling key rotation., Build concise prompt from market snapshot (~500 tokens)., Parse Claude's JSON response into decision dict., Ensure decision has all required fields and valid values., Rule-based mock decision engine.         Uses the same feature inputs as Claude, Log every decision to SQLite for audit trail. (+53 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (25): compute_indicators(), compute_stats(), fetch_ohlcv_1y(), plot_backtest(), print_summary(), Jalankan backtest persis logika bot live.     Returns: (df, trades, signals_long, Jalankan backtest persis logika bot live.     Returns: (df, trades, signals_long, Fetch 1 tahun penuh data 4H CRV/USDT dari Bybit.     Retry logic + paginate agar (+17 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (14): ExecutionManager, EXECUTION ENGINE (Diadaptasi dari bot_testing.ipynb)     Tugas: Mengirim order, # NOTE: sandbox_mode is NOT used — it's deprecated for futures, Get current futures price., Open a futures position.          Args:             symbol: 'BTC-USDT', Close an open position., Simulate opening a futures position., Simulate closing a futures position. (+6 more)

### Community 6 - "Community 6"
Cohesion: 0.09
Nodes (14): Fetch kline/candlestick data for price chart., Fetch funding rate history.          Returns:             {, Fetch open interest history.          Returns:             {, Fallback: get current OI via ccxt., Fetch global long/short account ratio.          Returns:             {, Fetch taker buy/sell volume ratio.          Returns:             {, Fetch ALL microstructure data for a symbol.         Returns combined dict for A, Fetch order book depth from Binance Futures and calculate         buy/sell pres (+6 more)

### Community 7 - "Community 7"
Cohesion: 0.1
Nodes (23): generate_html(), main(), Generate HTML report from loop output data. If auto_refresh is True, adds a meta, _call_claude(), improve_description(), main(), Run `claude -p` with the prompt on stdin and return the text response.      Prom, Call Claude to improve the description based on eval results. (+15 more)

### Community 8 - "Community 8"
Cohesion: 0.11
Nodes (10): Volatility Regime = percentile rank of current volatility vs history.         U, Compute z-score of value against its rolling history.         z = (x - mean) /, Compute ALL derived features for a symbol.          Args:             symbol:, Combine individual features into an overall trading signal.         Uses a weig, Cumulative Volume Delta = buy_volume - sell_volume.         Positive → buyers d, Delta Momentum = slope of CVD over recent snapshots.         Uses linear regres, Funding Pressure = funding_rate × open_interest_value.         Represents the d, OI Change Rate = ΔOI / OI as percentage.         Positive → new money entering, (+2 more)

### Community 9 - "Community 9"
Cohesion: 0.15
Nodes (10): Return cached value if still valid., Fetch historical price data for a single asset via yfinance.          Args:, Compute % price change over multiple timeframes.          Returns:, Fetch data and compute % changes for ALL tracked assets.          Returns:, Compute a rolling correlation matrix between all assets.          Returns:, Classify current global market regime based on cross-asset % changes., Master method: returns everything for the frontend.          Returns:, Generate human-readable insights about capital rotation. (+2 more)

### Community 10 - "Community 10"
Cohesion: 0.12
Nodes (9): Walk-Forward Validation:         - Split trades: 70% in-sample (training), 30%, Monte Carlo Validation:         - Shuffle trade order 1000x         - Compute, Compute performance metrics for a set of trades., Run complete validation suite.         Combines walk-forward + Monte Carlo + de, Convert AI decisions to mock trades with estimated PnL.         Uses entry pric, Compute statistics about AI decisions., Save validation report to database., Fetch AI decisions from database. (+1 more)

### Community 11 - "Community 11"
Cohesion: 0.2
Nodes (16): update_risk_config(), _get_db_conn(), get_risk_alerts(), get_risk_config(), get_risk_dashboard(), init_risk_tables(), log_risk_alert(), pre_trade_risk_check() (+8 more)

### Community 12 - "Community 12"
Cohesion: 0.34
Nodes (13): _dispatch(), _get_updates(), _handle_battery(), _handle_chart(), _handle_log(), _handle_status(), Generate chart via QuickChart.io — tanpa matplotlib, 100% kompatibel Android., Loop utama — berjalan sebagai background thread. (+5 more)

### Community 13 - "Community 13"
Cohesion: 0.14
Nodes (7): Run LONG and SHORT backtests on the same data, return segmented PnL.         Us, Combine LONG and SHORT metrics into a single combined view., Menghitung performa trading (Win Rate, Drawdown, Sharpe, dll), Calculate R-Squared (R^2) of the equity curve vs a perfect straight line., Mencari strategi terbaik untuk satu simbol dengan mencoba SEMUA kombinasi strate, Memotong data sesuai periode request user, Menjalankan simulasi trading dengan opsi Risk Management (Kelompok B).

### Community 14 - "Community 14"
Cohesion: 0.29
Nodes (10): calculate_atr(), calculate_bollinger_bands(), calculate_rsi(), compute_all(), get_latest_indicators(), Bollinger Bands: Period=20, StdDev=2×     Returns: (upper_band, middle_band, low, RSI: Period=14 (Wilder's smoothing via EWM)     Returns: RSI series (0–100), ATR: Period=14 (Wilder's smoothing)     True Range = max(H-L, |H-Cprev|, |L-Cpre (+2 more)

### Community 15 - "Community 15"
Cohesion: 0.24
Nodes (11): aggregate_results(), calculate_stats(), generate_benchmark(), generate_markdown(), load_run_results(), main(), Aggregate run results into summary statistics.      Returns run_summary with sta, Generate complete benchmark.json from run results. (+3 more)

### Community 16 - "Community 16"
Cohesion: 0.28
Nodes (7): main(), package_skill(), Check if a path should be excluded from packaging., Package a skill folder into a .skill file.      Args:         skill_path: Path t, should_exclude(), Basic validation of a skill, validate_skill()

### Community 17 - "Community 17"
Cohesion: 0.36
Nodes (4): DataManager, main(), Fetch OHLCV data from crypto exchange via CCXT.                  Args:, Close the async session

### Community 18 - "Community 18"
Cohesion: 0.25
Nodes (5): Automatically identify horizontal Support and Resistance levels         using r, Evaluate market regime based on strict conditions:          BULLISH: USDT.D ↓,, Simple helper that returns the recommended trade direction         based on mac, get_macro_direction(), get_macro_intelligence()

### Community 19 - "Community 19"
Cohesion: 0.25
Nodes (0): 

### Community 20 - "Community 20"
Cohesion: 0.29
Nodes (3): Detect mode: live (Gemini API) or mock (rule-based)., Create decision log table., Load comma-separated API keys from GEMINI_API_KEYS env var.

### Community 21 - "Community 21"
Cohesion: 0.33
Nodes (0): 

### Community 22 - "Community 22"
Cohesion: 0.33
Nodes (0): 

### Community 23 - "Community 23"
Cohesion: 0.33
Nodes (0): 

### Community 24 - "Community 24"
Cohesion: 0.4
Nodes (3): get_side_stats(), optimize_rsi_detailed.py Grid Search RSI Oversold (25-35) x Overbought (65-75) +, Extract win rate, avg pnl, count for LONG or SHORT only.

### Community 25 - "Community 25"
Cohesion: 0.67
Nodes (3): _get_db_conn(), get_fund_performance(), Calculate comprehensive fund performance metrics.     returns: dict of metrics

### Community 26 - "Community 26"
Cohesion: 0.5
Nodes (0): 

### Community 27 - "Community 27"
Cohesion: 0.5
Nodes (0): 

### Community 28 - "Community 28"
Cohesion: 0.67
Nodes (1): Create validation reports table.

### Community 29 - "Community 29"
Cohesion: 0.67
Nodes (1): optimize_possize_v2.py - Position Size grid with NEW BB(17,1.8) + RSI(30,71) Tes

### Community 30 - "Community 30"
Cohesion: 0.67
Nodes (1): # IMPORTANT: Always place exchange-level SL orders for flash crash protection

### Community 31 - "Community 31"
Cohesion: 0.67
Nodes (1): optimize_bb.py - Grid Search Bollinger Bands Parameters BB Period (15-25) x BB S

### Community 32 - "Community 32"
Cohesion: 0.67
Nodes (1): Print full trade log from the latest backtest run.

### Community 33 - "Community 33"
Cohesion: 0.67
Nodes (0): 

### Community 34 - "Community 34"
Cohesion: 0.67
Nodes (0): 

### Community 35 - "Community 35"
Cohesion: 0.67
Nodes (0): 

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (1): Return AI service status.

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (1): Args:             exchange: A connected ccxt exchange instance (e.g., from Trad

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (1): Set leverage for a symbol.

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (1): Get paper trade history.

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (0): 

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (0): 

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (0): 

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (0): 

### Community 44 - "Community 44"
Cohesion: 1.0
Nodes (0): 

### Community 45 - "Community 45"
Cohesion: 1.0
Nodes (0): 

### Community 46 - "Community 46"
Cohesion: 1.0
Nodes (0): 

### Community 47 - "Community 47"
Cohesion: 1.0
Nodes (0): 

### Community 48 - "Community 48"
Cohesion: 1.0
Nodes (0): 

### Community 49 - "Community 49"
Cohesion: 1.0
Nodes (0): 

### Community 50 - "Community 50"
Cohesion: 1.0
Nodes (0): 

### Community 51 - "Community 51"
Cohesion: 1.0
Nodes (0): 

### Community 52 - "Community 52"
Cohesion: 1.0
Nodes (0): 

### Community 53 - "Community 53"
Cohesion: 1.0
Nodes (0): 

### Community 54 - "Community 54"
Cohesion: 1.0
Nodes (0): 

### Community 55 - "Community 55"
Cohesion: 1.0
Nodes (0): 

### Community 56 - "Community 56"
Cohesion: 1.0
Nodes (0): 

### Community 57 - "Community 57"
Cohesion: 1.0
Nodes (0): 

### Community 58 - "Community 58"
Cohesion: 1.0
Nodes (0): 

### Community 59 - "Community 59"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **205 isolated node(s):** `Hybrid AI Decision Engine.     Primary: Gemini 2.5 Flash via Google Generative`, `Load comma-separated API keys from GEMINI_API_KEYS env var.`, `Rotate to next API key in the pool.`, `Detect mode: live (Gemini API) or mock (rule-based).`, `Create decision log table.` (+200 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 36`** (2 nodes): `.get_status()`, `Return AI service status.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (2 nodes): `.__init__()`, `Args:             exchange: A connected ccxt exchange instance (e.g., from Trad`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (2 nodes): `.set_leverage()`, `Set leverage for a symbol.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (2 nodes): `.get_trade_history()`, `Get paper trade history.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (2 nodes): `migrate_to_supabase.py`, `migrate()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (2 nodes): `run_tests.py`, `test_endpoint()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (2 nodes): `App()`, `App.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (2 nodes): `BotTracker()`, `BotTracker.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (2 nodes): `MarketAnalytics.jsx`, `MarketAnalytics()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (2 nodes): `MonteCarloChart.jsx`, `MonteCarloChart()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (2 nodes): `PaperTradingChart.jsx`, `PaperTradingChart()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (2 nodes): `PaperTradingDashboard.jsx`, `PaperTradingDashboard()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (2 nodes): `PortfolioPage.jsx`, `PortfolioPage()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (2 nodes): `Watchlist.jsx`, `Watchlist()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (1 nodes): `vite.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (1 nodes): `config.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (1 nodes): `eslint.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 54`** (1 nodes): `postcss.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 55`** (1 nodes): `tailwind.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 56`** (1 nodes): `vite.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 57`** (1 nodes): `api.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 58`** (1 nodes): `main.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 59`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TradingEngine` connect `Community 0` to `Community 1`, `Community 3`, `Community 4`, `Community 13`?**
  _High betweenness centrality (0.124) - this node is a cross-community bridge._
- **Why does `AlphaDataProvider` connect `Community 0` to `Community 8`, `Community 6`?**
  _High betweenness centrality (0.082) - this node is a cross-community bridge._
- **Why does `PaperTrader` connect `Community 0` to `Community 1`, `Community 4`, `Community 5`?**
  _High betweenness centrality (0.078) - this node is a cross-community bridge._
- **Are the 98 inferred relationships involving `TradingEngine` (e.g. with `BacktestEngine` and `Scan multiple symbols and rank by consistency score using Best Strategy Finder.`) actually correct?**
  _`TradingEngine` has 98 INFERRED edges - model-reasoned connections that need verification._
- **Are the 90 inferred relationships involving `AlphaDataProvider` (e.g. with `AlphaFeatureEngine` and `Transforms raw microstructure data into normalized trading features.     Output`) actually correct?**
  _`AlphaDataProvider` has 90 INFERRED edges - model-reasoned connections that need verification._
- **Are the 77 inferred relationships involving `AIBrain` (e.g. with `StrategyRequest` and `ScanRequest`) actually correct?**
  _`AIBrain` has 77 INFERRED edges - model-reasoned connections that need verification._
- **Are the 78 inferred relationships involving `AlphaFeatureEngine` (e.g. with `AlphaDataProvider` and `StrategyRequest`) actually correct?**
  _`AlphaFeatureEngine` has 78 INFERRED edges - model-reasoned connections that need verification._