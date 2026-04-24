# =============================================================
# config.py — CRV-USDT Mean Reversion Bot
# All strategy, risk, and operational parameters in one place.
# Edit here first before tweaking anything else.
# =============================================================

from dotenv import load_dotenv
import os

# [SECURITY LAPIS 2]: Menyamarkan file .env menjadi .python_config_cache
# Ini mempersulit script malicious/pemilik VPS untuk menemukan API key Anda
load_dotenv(dotenv_path=".python_config_cache")

# ── Exchange & Symbol ──────────────────────────────────────────
EXCHANGE_ID       = "bybit"
SYMBOL            = "CRV/USDT:USDT"   # Bybit USDT Perpetual Futures (CCXT format)
MARKET_TYPE       = "swap"             # Perpetual futures
TIMEFRAME         = "4h"               # Signal candle timeframe
LEVERAGE          = 2                  # 2× leverage
PAPER_TRADING     = os.getenv("PAPER_TRADING", "true").lower() == "true"

# ── API Credentials (loaded from .env) ─────────────────────────
BYBIT_API_KEY     = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET  = os.getenv("BYBIT_API_SECRET")

# ── Telegram ────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")

# ── Indicator Parameters (persis dari backtest) ─────────────────
BB_PERIOD         = 17      # Bollinger Bands period (optimal from grid search)
BB_STD_DEV        = 1.8     # Bollinger Bands standard deviation multiplier (optimal)
RSI_PERIOD        = 14      # RSI period
ATR_PERIOD        = 14      # ATR period (used for position sizing reference / logging)

# ── Signal Thresholds ───────────────────────────────────────────
RSI_OVERSOLD      = 30      # RSI < 30 → oversold (buy zone)
RSI_OVERBOUGHT    = 71      # RSI > 71 → overbought (sell zone)

# ── Position Sizing ─────────────────────────────────────────────
# Bot uses a fixed % of total equity per trade (ATR-aware but simplified)
POSITION_SIZE_PCT = 0.92    # Use 92% of available equity per trade (optimal from backtest grid search)
MIN_ORDER_USD     = 5.0     # Minimum order size in USDT (Bybit min ~5 USDT)

# ── Risk Management ─────────────────────────────────────────────
# Stop Loss: -20% from entry price on the POSITION (not collateral)
# With 2x leverage, this means -40% of collateral — still 10% buffer before liquidation at -50%
STOP_LOSS_PCT           = 0.20    # 20% adverse price move triggers stop loss

# Portfolio Circuit Breaker: if total equity drops 50% from ALL-TIME peak -> resume after cooldown
CIRCUIT_BREAKER_DRAWDOWN = 0.50   # 50% drawdown from peak -> emergency close + cooldown

# Cooldown: after SL or CB event, wait N candles before re-entering
# 6 candles x 4H = 24 hours of "cooling off" to let market stabilize
COOLDOWN_CANDLES        = 6       # 24-hour cooldown after SL/CB hit

# Liquidation Safety Reference (informational, not enforced by code):
# 2x leverage -> liquidation at -50% from entry
# Our SL at -20% gives a 30% buffer before liquidation
# IMPORTANT: Always place exchange-level SL orders for flash crash protection

# ── Operational ─────────────────────────────────────────────────
CANDLE_CLOSE_BUFFER_SECONDS = 10   # Wait N seconds after expected candle close before fetching
LOOP_INTERVAL_SECONDS       = 30   # How often to poll for new signals within the 4H window
OHLCV_LIMIT                 = 105  # Fetch 105 candles; last 1 dropped (incomplete) = 104 usable, chart uses tail(100)
LOG_LEVEL                   = "INFO"
LOG_FILE                    = "bot.log"

# ── State File ──────────────────────────────────────────────────
STATE_FILE        = "bot_state.json"  # Tracks peak equity, open position, etc.

# ── Bybit Testnet (optional, for initial testing) ───────────────
USE_TESTNET       = False   # Set True to use Bybit testnet sandbox

BYBIT_TESTNET_URLS = {
    "apiUrl":  "https://api-testnet.bybit.com",
    "wsUrl":   "wss://stream-testnet.bybit.com",
}
