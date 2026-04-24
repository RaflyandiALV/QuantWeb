# =============================================================
# order_executor.py — Bybit Futures Order Execution via CCXT
# Handles: connect, fetch OHLCV, get equity, place/close orders
# Supports PAPER TRADING mode (no real orders placed)
# =============================================================

import logging
import ccxt
from config import (
    BYBIT_API_KEY, BYBIT_API_SECRET, EXCHANGE_ID, SYMBOL,
    TIMEFRAME, LEVERAGE, OHLCV_LIMIT, PAPER_TRADING,
    POSITION_SIZE_PCT, MIN_ORDER_USD, USE_TESTNET, BYBIT_TESTNET_URLS
)
import pandas as pd

logger = logging.getLogger(__name__)


def create_exchange() -> ccxt.bybit:
    """
    Initialize and return an authenticated Bybit CCXT exchange instance.
    Sets leverage and configures unified account margin mode.
    """
    options = {
        "defaultType"    : "swap",      # Perpetual futures
        "adjustForTimeDifference": True,
    }
    if USE_TESTNET:
        options["urls"] = BYBIT_TESTNET_URLS

    exchange = ccxt.bybit({
        "apiKey"   : BYBIT_API_KEY,
        "secret"   : BYBIT_API_SECRET,
        "options"  : options,
        "enableRateLimit": True,
    })

    if USE_TESTNET:
        exchange.set_sandbox_mode(True)
        logger.info("🧪 Using Bybit TESTNET")

    return exchange


def set_leverage(exchange: ccxt.bybit) -> None:
    """Set leverage for the trading symbol (call once on startup)."""
    try:
        exchange.set_leverage(LEVERAGE, SYMBOL)
        logger.info(f"✅ Leverage set to {LEVERAGE}× for {SYMBOL}")
    except ccxt.BaseError as e:
        # Bybit sometimes returns an error if leverage is already set — safe to ignore
        logger.warning(f"set_leverage warning (may already be set): {e}")


def fetch_ohlcv(exchange: ccxt.bybit) -> pd.DataFrame:
    """
    Fetch the latest N candles and return as a DataFrame.
    Columns: timestamp, open, high, low, close, volume
    """
    raw = exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=OHLCV_LIMIT)
    df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    # Drop the last (potentially incomplete) candle
    df = df.iloc[:-1].reset_index(drop=True)
    logger.debug(f"Fetched {len(df)} candles. Latest: {df.iloc[-1]['timestamp']}")
    return df


def get_equity(exchange: ccxt.bybit) -> float:
    """
    Returns the USDT balance available in the Unified Trading Account.
    """
    try:
        balance = exchange.fetch_balance({"type": "unified"})
        equity  = balance.get("USDT", {}).get("total", 0.0)
        logger.info(f"💰 Equity: {equity:.4f} USDT")
        return float(equity)
    except ccxt.BaseError as e:
        logger.error(f"Failed to fetch balance: {e}")
        raise


def get_open_position(exchange: ccxt.bybit) -> dict | None:
    """
    Returns the current open position dict for CRV/USDT, or None if flat.
    Fields: side ('long'|'short'), contracts, entryPrice, unrealizedPnl, etc.
    """
    try:
        positions = exchange.fetch_positions([SYMBOL])
        for pos in positions:
            if pos.get("contracts", 0) and pos["contracts"] > 0:
                return pos
        return None
    except ccxt.BaseError as e:
        logger.error(f"Failed to fetch positions: {e}")
        raise


def calculate_order_size(exchange: ccxt.bybit, equity: float, price: float) -> float:
    """
    Calculate position size in base currency (CRV amount).
    Uses POSITION_SIZE_PCT of equity with leverage applied.

    notional_usdt = equity * POSITION_SIZE_PCT * LEVERAGE
    qty_crv       = notional_usdt / price
    """
    notional_usdt = equity * POSITION_SIZE_PCT * LEVERAGE
    notional_usdt = max(notional_usdt, MIN_ORDER_USD)
    qty_crv       = notional_usdt / price

    # Round to exchange precision
    try:
        market    = exchange.market(SYMBOL)
        precision = market.get("precision", {}).get("amount", None)
        if precision:
            qty_crv = float(exchange.amount_to_precision(SYMBOL, qty_crv))
    except Exception:
        qty_crv = round(qty_crv, 2)

    logger.info(
        f"📐 Order size: {qty_crv} CRV | "
        f"Notional: {qty_crv * price:.2f} USDT | "
        f"Equity: {equity:.2f} USDT"
    )
    return qty_crv


# ── Order Placement ───────────────────────────────────────────

def open_long(exchange: ccxt.bybit, equity: float, price: float) -> dict | None:
    """Open a LONG (buy) position."""
    qty = calculate_order_size(exchange, equity, price)
    logger.info(f"📈 Opening LONG | {qty} CRV @ ~{price:.4f}")

    if PAPER_TRADING:
        logger.info("[PAPER] LONG order simulated — no real order placed.")
        return {"paper": True, "side": "buy", "amount": qty, "price": price}

    try:
        order = exchange.create_market_buy_order(
            symbol=SYMBOL,
            amount=qty,
            params={"reduceOnly": False, "positionIdx": 0}  # One-way mode
        )
        logger.info(f"✅ LONG order placed: {order}")
        return order
    except ccxt.BaseError as e:
        logger.error(f"Failed to open LONG: {e}")
        raise


def open_short(exchange: ccxt.bybit, equity: float, price: float) -> dict | None:
    """Open a SHORT (sell) position."""
    qty = calculate_order_size(exchange, equity, price)
    logger.info(f"📉 Opening SHORT | {qty} CRV @ ~{price:.4f}")

    if PAPER_TRADING:
        logger.info("[PAPER] SHORT order simulated — no real order placed.")
        return {"paper": True, "side": "sell", "amount": qty, "price": price}

    try:
        order = exchange.create_market_sell_order(
            symbol=SYMBOL,
            amount=qty,
            params={"reduceOnly": False, "positionIdx": 0}
        )
        logger.info(f"✅ SHORT order placed: {order}")
        return order
    except ccxt.BaseError as e:
        logger.error(f"Failed to open SHORT: {e}")
        raise


def close_long(exchange: ccxt.bybit, qty: float, price: float) -> dict | None:
    """Close an existing LONG position (market sell with reduceOnly)."""
    logger.info(f"🔒 Closing LONG | {qty} CRV @ ~{price:.4f}")

    if PAPER_TRADING:
        logger.info("[PAPER] CLOSE LONG simulated.")
        return {"paper": True, "side": "sell", "amount": qty, "price": price, "reduce": True}

    try:
        order = exchange.create_market_sell_order(
            symbol=SYMBOL,
            amount=qty,
            params={"reduceOnly": True, "positionIdx": 0}
        )
        logger.info(f"✅ LONG closed: {order}")
        return order
    except ccxt.BaseError as e:
        logger.error(f"Failed to close LONG: {e}")
        raise


def close_short(exchange: ccxt.bybit, qty: float, price: float) -> dict | None:
    """Close an existing SHORT position (market buy with reduceOnly)."""
    logger.info(f"🔒 Closing SHORT | {qty} CRV @ ~{price:.4f}")

    if PAPER_TRADING:
        logger.info("[PAPER] CLOSE SHORT simulated.")
        return {"paper": True, "side": "buy", "amount": qty, "price": price, "reduce": True}

    try:
        order = exchange.create_market_buy_order(
            symbol=SYMBOL,
            amount=qty,
            params={"reduceOnly": True, "positionIdx": 0}
        )
        logger.info(f"✅ SHORT closed: {order}")
        return order
    except ccxt.BaseError as e:
        logger.error(f"Failed to close SHORT: {e}")
        raise


def get_current_price(exchange: ccxt.bybit) -> float:
    """Fetch latest mid price from the ticker."""
    ticker = exchange.fetch_ticker(SYMBOL)
    return float(ticker["last"])
