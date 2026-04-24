# =============================================================
# config.py — CRV-USDT Mean Reversion Bot
# All strategy, risk, and operational parameters in one place.
# Edit here first before tweaking anything else.
# =============================================================

from dotenv import load_dotenv
import os

load_dotenv()

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
BB_PERIOD         = 20      # Bollinger Bands period
BB_STD_DEV        = 2.0     # Bollinger Bands standard deviation multiplier
RSI_PERIOD        = 14      # RSI period
ATR_PERIOD        = 14      # ATR period (used for position sizing reference / logging)

# ── Signal Thresholds ───────────────────────────────────────────
RSI_OVERSOLD      = 30      # RSI < 30 → oversold (buy zone)
RSI_OVERBOUGHT    = 70      # RSI > 70 → overbought (sell zone)

# ── Position Sizing ─────────────────────────────────────────────
# Bot uses a fixed % of total equity per trade (ATR-aware but simplified)
POSITION_SIZE_PCT = 0.90    # Use 90% of available equity per trade (leave 10% buffer)
MIN_ORDER_USD     = 5.0     # Minimum order size in USDT (Bybit min ~5 USDT)

# ── Risk Management ─────────────────────────────────────────────
# Stop Loss: -15% from entry price on the POSITION (not collateral)
# With 2× leverage, this means -30% of collateral — still far from liquidation at -50%
STOP_LOSS_PCT           = 0.15    # 15% adverse price move triggers stop loss

# Portfolio Circuit Breaker: if total equity drops 35% from ALL-TIME peak → halt bot
CIRCUIT_BREAKER_DRAWDOWN = 0.35   # 35% drawdown from peak → emergency stop

# Liquidation Safety Reference (informational, not enforced by code):
# 2× leverage → liquidation at -50% from entry
# Our SL at -15% gives a 35% buffer before liquidation

# ── Operational ─────────────────────────────────────────────────
CANDLE_CLOSE_BUFFER_SECONDS = 10   # Wait N seconds after expected candle close before fetching
LOOP_INTERVAL_SECONDS       = 30   # How often to poll for new signals within the 4H window
OHLCV_LIMIT                 = 100  # Number of candles to fetch from exchange
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
