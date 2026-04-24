# =============================================================
# risk_manager.py — Stop Loss & Portfolio Circuit Breaker
#
# Rules:
#   1. Per-Trade Stop Loss    : -15% from entry price
#      (With 2× leverage = -30% collateral, buffer = 35% before liq.)
#   2. Portfolio Circuit Breaker: equity drops -35% from ALL-TIME peak
#      → Bot halts, requires manual restart
#   3. State is persisted in bot_state.json
# =============================================================

import json
import os
import logging
from datetime import datetime
from config import STOP_LOSS_PCT, CIRCUIT_BREAKER_DRAWDOWN, STATE_FILE

logger = logging.getLogger(__name__)


DEFAULT_STATE = {
    "peak_equity"         : None,   # Highest equity ever seen (USD)
    "circuit_breaker_hit" : False,  # True = bot is halted
    "entry_price"         : None,   # Price at which current position was opened
    "position"            : "NONE", # "NONE" | "LONG" | "SHORT"
    "position_size"       : None,   # Size in USDT (notional)
    "entry_time"          : None,   # ISO timestamp of entry
    "last_updated"        : None,
}


# ── State Persistence ─────────────────────────────────────────

def load_state() -> dict:
    """Load persisted bot state from JSON file."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
            logger.debug(f"State loaded: {state}")
            return state
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load state file ({e}), using default.")
    return dict(DEFAULT_STATE)


def save_state(state: dict) -> None:
    """Persist bot state to JSON file."""
    state["last_updated"] = datetime.utcnow().isoformat()
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except IOError as e:
        logger.error(f"Failed to save state: {e}")


def reset_position_state(state: dict) -> dict:
    """Clear entry data after a position is closed."""
    state["entry_price"]   = None
    state["position"]      = "NONE"
    state["position_size"] = None
    state["entry_time"]    = None
    return state


def record_entry(state: dict, entry_price: float, position: str, size_usdt: float) -> dict:
    """Record a new position entry."""
    state["entry_price"]   = entry_price
    state["position"]      = position
    state["position_size"] = size_usdt
    state["entry_time"]    = datetime.utcnow().isoformat()
    save_state(state)
    logger.info(f"Position recorded: {position} @ {entry_price:.4f} | Size: {size_usdt:.2f} USDT")
    return state


# ── Stop Loss Check ───────────────────────────────────────────

def check_stop_loss(state: dict, current_price: float) -> tuple[bool, str]:
    """
    Returns (stop_loss_triggered, reason)

    Stop Loss: -15% from entry price
      LONG  → triggered when price drops >= 15% below entry
      SHORT → triggered when price rises >= 15% above entry
    """
    entry_price = state.get("entry_price")
    position    = state.get("position", "NONE")

    if entry_price is None or position == "NONE":
        return False, ""

    if position == "LONG":
        drawdown = (entry_price - current_price) / entry_price
        if drawdown >= STOP_LOSS_PCT:
            reason = (
                f"🛑 STOP LOSS | LONG | Entry={entry_price:.4f} "
                f"Current={current_price:.4f} | Drawdown={drawdown*100:.2f}% ≥ {STOP_LOSS_PCT*100:.0f}%"
            )
            return True, reason

    elif position == "SHORT":
        adverse_move = (current_price - entry_price) / entry_price
        if adverse_move >= STOP_LOSS_PCT:
            reason = (
                f"🛑 STOP LOSS | SHORT | Entry={entry_price:.4f} "
                f"Current={current_price:.4f} | Adverse={adverse_move*100:.2f}% ≥ {STOP_LOSS_PCT*100:.0f}%"
            )
            return True, reason

    return False, ""


# ── Circuit Breaker ───────────────────────────────────────────

def check_circuit_breaker(state: dict, current_equity: float) -> tuple[bool, str]:
    """
    Returns (circuit_breaker_hit, reason)

    Circuit Breaker: if equity drops >= 35% from all-time peak → halt bot.
    Also updates peak equity if current equity is a new high.
    """
    # If already triggered, stay triggered (requires manual reset)
    if state.get("circuit_breaker_hit", False):
        return True, "⛔ Circuit breaker already active — manual restart required"

    # Update peak equity
    peak = state.get("peak_equity")
    if peak is None or current_equity > peak:
        state["peak_equity"] = current_equity
        save_state(state)
        logger.info(f"📈 New equity peak: {current_equity:.2f} USDT")
        return False, ""

    # Check drawdown from peak
    drawdown_from_peak = (peak - current_equity) / peak
    if drawdown_from_peak >= CIRCUIT_BREAKER_DRAWDOWN:
        state["circuit_breaker_hit"] = True
        save_state(state)
        reason = (
            f"⛔ CIRCUIT BREAKER TRIGGERED | "
            f"Peak={peak:.2f} | Current={current_equity:.2f} | "
            f"Drawdown={drawdown_from_peak*100:.2f}% ≥ {CIRCUIT_BREAKER_DRAWDOWN*100:.0f}%"
        )
        logger.critical(reason)
        return True, reason

    return False, ""


def manual_reset_circuit_breaker() -> None:
    """
    Manually reset the circuit breaker after reviewing the situation.
    Call this from command line: python -c "from risk_manager import manual_reset_circuit_breaker; manual_reset_circuit_breaker()"
    """
    state = load_state()
    state["circuit_breaker_hit"] = False
    save_state(state)
    print("✅ Circuit breaker reset. Bot will resume on next run.")


# ── Position P&L Helper ───────────────────────────────────────

def calculate_unrealized_pnl(state: dict, current_price: float) -> dict:
    """
    Returns dict with unrealized PnL info for logging/notification.
    """
    entry_price = state.get("entry_price")
    position    = state.get("position", "NONE")
    size_usdt   = state.get("position_size", 0) or 0

    if entry_price is None or position == "NONE":
        return {"pnl_pct": 0.0, "pnl_usdt": 0.0}

    if position == "LONG":
        pnl_pct  = (current_price - entry_price) / entry_price
    else:  # SHORT
        pnl_pct  = (entry_price - current_price) / entry_price

    # Notional size / 2 = collateral at 2× leverage
    collateral = size_usdt / 2
    pnl_usdt   = collateral * pnl_pct

    return {
        "pnl_pct"    : round(pnl_pct * 100, 2),
        "pnl_usdt"   : round(pnl_usdt, 4),
        "entry_price": entry_price,
        "current_price": current_price,
        "position"   : position,
    }
