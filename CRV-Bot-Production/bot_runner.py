# =============================================================
# bot_runner.py — Main Trading Loop
#
# Flow every 4H candle close:
#   1. Fetch OHLCV → compute indicators
#   2. Check circuit breaker (halt if triggered)
#   3. Check stop loss on any open position
#   4. Evaluate signal (signal_engine)
#   5. Execute order (order_executor)
#   6. Update state (risk_manager)
#   7. Send Telegram notification (notifier)
#
# Position Flip in 1 cycle:
#   SELL signal + LONG position  → close LONG → open SHORT
#   BUY  signal + SHORT position → close SHORT → open LONG
#
# Run: python bot_runner.py
# Paper trading: set PAPER_TRADING=true in .env
# Reset CB:      python bot_runner.py --reset-cb
# =============================================================

import sys
import time
import logging
import traceback
from datetime import datetime, timezone

import ccxt

import config
from indicators     import compute_all, get_latest_indicators
from signal_engine  import evaluate_signal, Signal, Position
from risk_manager   import (
    load_state, save_state, reset_position_state, record_entry,
    check_stop_loss, check_circuit_breaker, calculate_unrealized_pnl,
    manual_reset_circuit_breaker
)
from order_executor import (
    create_exchange, set_leverage, fetch_ohlcv, get_equity,
    get_current_price, calculate_order_size,
    open_long, open_short, close_long, close_short
)
import notifier


# ── Logging Setup ─────────────────────────────────────────────

def setup_logging() -> None:
    fmt = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
    ]
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format=fmt,
        handlers=handlers,
    )

logger = logging.getLogger("bot_runner")


# ── Candle Timing ─────────────────────────────────────────────

def seconds_until_next_4h_close() -> float:
    """
    Returns seconds remaining until the next 4H candle closes.
    4H candles close at: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC
    """
    now   = datetime.now(timezone.utc)
    h     = now.hour
    m     = now.minute
    s     = now.second
    us    = now.microsecond

    # Next 4H boundary
    next_boundary_hour = ((h // 4) + 1) * 4
    if next_boundary_hour >= 24:
        next_boundary_hour = 0
        # Handle day rollover — just compute delta in seconds
    total_current_seconds  = (h % 4) * 3600 + m * 60 + s + us / 1e6
    seconds_in_4h_block    = 4 * 3600
    remaining              = seconds_in_4h_block - total_current_seconds
    return remaining


# ── Core Trade Logic ──────────────────────────────────────────

def run_trade_cycle(exchange, state: dict) -> dict:
    """
    Execute one full trading evaluation cycle.
    Returns updated state.
    """
    # 1. Fetch data & indicators
    df         = fetch_ohlcv(exchange)
    df         = compute_all(df)
    ind        = get_latest_indicators(df)
    close      = ind["close"]

    logger.info(
        f"📊 RSI={ind['rsi']:.1f} | Close={close:.4f} | "
        f"BB[{ind['bb_lower']:.4f} — {ind['bb_upper']:.4f}] | "
        f"ATR={ind['atr']:.4f}"
    )

    # 2. Get account equity
    equity = get_equity(exchange)

    # 3. Circuit breaker check
    cb_hit, cb_reason = check_circuit_breaker(state, equity)
    if cb_hit:
        logger.critical(cb_reason)
        notifier.notify_circuit_breaker(
            state.get("peak_equity", equity),
            equity,
            (state.get("peak_equity", equity) - equity) / max(state.get("peak_equity", equity), 1) * 100
        )
        # Close any open position
        current_pos = Position(state.get("position", "NONE"))
        if current_pos == Position.LONG:
            _execute_close_long(exchange, state, close, "circuit_breaker")
        elif current_pos == Position.SHORT:
            _execute_close_short(exchange, state, close, "circuit_breaker")
        return state

    # 4. Stop loss check
    sl_hit, sl_reason = check_stop_loss(state, close)

    # 5. Signal evaluation
    current_pos = Position(state.get("position", "NONE"))
    signal, sig_reason = evaluate_signal(
        close      = close,
        rsi        = ind["rsi"],
        bb_upper   = ind["bb_upper"],
        bb_lower   = ind["bb_lower"],
        current_position  = current_pos,
        stop_loss_hit     = sl_hit,
        circuit_breaker_hit = False,
    )

    reason = sl_reason if sl_hit else sig_reason
    logger.info(f"🚦 Signal: {signal} | {reason}")

    # Log unrealized PnL for open positions
    if current_pos != Position.NONE:
        pnl = calculate_unrealized_pnl(state, close)
        logger.info(f"📈 Unrealized P&L: {pnl['pnl_pct']:+.2f}% ({pnl['pnl_usdt']:+.4f} USDT)")

    # 6. Send signal notification (skip HOLD to avoid spam)
    if signal != Signal.HOLD:
        notifier.notify_signal(signal.value, reason, ind)

    # 7. Execute based on signal + position flip logic
    if signal == Signal.HOLD:
        return state

    # ── Close LONG ────────────────────────────────────────
    if current_pos == Position.LONG and signal in (Signal.SHORT, Signal.CLOSE_LONG):
        state = _execute_close_long(exchange, state, close,
                                    "sl" if sl_hit else "signal")
        # If flipping to SHORT — open immediately
        if signal == Signal.SHORT and not sl_hit:
            state = _execute_open_short(exchange, state, equity, close)

    # ── Close SHORT ───────────────────────────────────────
    elif current_pos == Position.SHORT and signal in (Signal.LONG, Signal.CLOSE_SHORT):
        state = _execute_close_short(exchange, state, close,
                                     "sl" if sl_hit else "signal")
        # If flipping to LONG — open immediately
        if signal == Signal.LONG and not sl_hit:
            state = _execute_open_long(exchange, state, equity, close)

    # ── Fresh entries (no existing position) ─────────────
    elif current_pos == Position.NONE:
        if signal == Signal.LONG:
            state = _execute_open_long(exchange, state, equity, close)
        elif signal == Signal.SHORT:
            state = _execute_open_short(exchange, state, equity, close)

    return state


# ── Execution Helpers ─────────────────────────────────────────

def _execute_open_long(exchange, state, equity, price) -> dict:
    try:
        open_long(exchange, equity, price)
        notional = equity * config.POSITION_SIZE_PCT * config.LEVERAGE
        state    = record_entry(state, price, "LONG", notional)
        save_state(state)
        notifier.notify_order_opened("LONG", price, notional, config.PAPER_TRADING)
    except Exception as e:
        logger.error(f"Error opening LONG: {e}")
        notifier.notify_error(f"Error opening LONG: {e}")
    return state


def _execute_open_short(exchange, state, equity, price) -> dict:
    try:
        open_short(exchange, equity, price)
        notional = equity * config.POSITION_SIZE_PCT * config.LEVERAGE
        state    = record_entry(state, price, "SHORT", notional)
        save_state(state)
        notifier.notify_order_opened("SHORT", price, notional, config.PAPER_TRADING)
    except Exception as e:
        logger.error(f"Error opening SHORT: {e}")
        notifier.notify_error(f"Error opening SHORT: {e}")
    return state


def _execute_close_long(exchange, state, price, reason_tag) -> dict:
    try:
        pnl = calculate_unrealized_pnl(state, price)
        # Get qty from exchange position (live) or estimate from state (paper)
        qty = (state.get("position_size", 0) or 0) * config.LEVERAGE / price
        if not config.PAPER_TRADING:
            # Get actual qty from exchange
            import order_executor as oe
            pos = oe.get_open_position(exchange)
            if pos:
                qty = abs(pos.get("contracts", qty))
        close_long(exchange, qty, price)
        notifier.notify_order_closed(
            "LONG", state.get("entry_price", price), price,
            pnl["pnl_pct"], pnl["pnl_usdt"], reason_tag, config.PAPER_TRADING
        )
        state = reset_position_state(state)
        save_state(state)
    except Exception as e:
        logger.error(f"Error closing LONG: {e}")
        notifier.notify_error(f"Error closing LONG: {e}")
    return state


def _execute_close_short(exchange, state, price, reason_tag) -> dict:
    try:
        pnl = calculate_unrealized_pnl(state, price)
        qty = (state.get("position_size", 0) or 0) * config.LEVERAGE / price
        if not config.PAPER_TRADING:
            import order_executor as oe
            pos = oe.get_open_position(exchange)
            if pos:
                qty = abs(pos.get("contracts", qty))
        close_short(exchange, qty, price)
        notifier.notify_order_closed(
            "SHORT", state.get("entry_price", price), price,
            pnl["pnl_pct"], pnl["pnl_usdt"], reason_tag, config.PAPER_TRADING
        )
        state = reset_position_state(state)
        save_state(state)
    except Exception as e:
        logger.error(f"Error closing SHORT: {e}")
        notifier.notify_error(f"Error closing SHORT: {e}")
    return state


# ── Main Loop ─────────────────────────────────────────────────

def main() -> None:
    setup_logging()

    # Handle CLI flag
    if "--reset-cb" in sys.argv:
        manual_reset_circuit_breaker()
        sys.exit(0)

    logger.info("=" * 60)
    logger.info("🤖 CRV-USDT Mean Reversion Bot Starting...")
    logger.info(f"   Symbol     : {config.SYMBOL}")
    logger.info(f"   Timeframe  : {config.TIMEFRAME}")
    logger.info(f"   Leverage   : {config.LEVERAGE}×")
    logger.info(f"   Paper Mode : {config.PAPER_TRADING}")
    logger.info(f"   Stop Loss  : {config.STOP_LOSS_PCT*100:.0f}%")
    logger.info(f"   Circuit CB : {config.CIRCUIT_BREAKER_DRAWDOWN*100:.0f}% drawdown")
    logger.info("=" * 60)

    # Init exchange
    try:
        exchange = create_exchange()
        exchange.load_markets()
        set_leverage(exchange)
    except Exception as e:
        logger.critical(f"Failed to connect to exchange: {e}")
        notifier.notify_error(f"Bot startup failed: {e}")
        sys.exit(1)

    state = load_state()
    notifier.notify_bot_started(config.PAPER_TRADING)

    heartbeat_counter = 0

    while True:
        try:
            # ── Circuit Breaker Guard ──────────────────────
            if state.get("circuit_breaker_hit", False):
                logger.critical("⛔ Circuit breaker active — bot halted. Run with --reset-cb to resume.")
                time.sleep(3600)
                continue

            # ── Wait for next 4H candle close ──────────────
            wait = seconds_until_next_4h_close() + config.CANDLE_CLOSE_BUFFER_SECONDS
            logger.info(f"⏱️  Next candle in {wait/3600:.2f}h ({wait:.0f}s). Sleeping...")
            time.sleep(max(wait, 1))

            # ── Run trade cycle ────────────────────────────
            logger.info("🔔 Candle closed — evaluating signals...")
            state = run_trade_cycle(exchange, state)

            # ── Heartbeat every 6 cycles (~24h) ───────────
            heartbeat_counter += 1
            if heartbeat_counter >= 6:
                equity = get_equity(exchange)
                pnl    = calculate_unrealized_pnl(state, get_current_price(exchange))
                notifier.notify_heartbeat(equity, state.get("position", "NONE"), pnl)
                heartbeat_counter = 0

        except ccxt.NetworkError as e:
            logger.error(f"Network error: {e} — retrying in 60s")
            notifier.notify_error(f"Network error: {e}")
            time.sleep(60)

        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error: {e} — retrying in 120s")
            notifier.notify_error(f"Exchange error: {e}")
            time.sleep(120)

        except KeyboardInterrupt:
            logger.info("🛑 Bot stopped by user (Ctrl+C).")
            notifier.notify_bot_stopped("Manual stop (Ctrl+C)")
            sys.exit(0)

        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"Unexpected error: {e}\n{tb}")
            notifier.notify_error(f"Unexpected error: {e}\n{tb[:300]}")
            time.sleep(60)


if __name__ == "__main__":
    main()
