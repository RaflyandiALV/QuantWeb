# =============================================================
# signal_engine.py — Entry/Exit Signal Logic
# Persis dari backtest QuantWeb:
#   LONG  entry : RSI < 30 AND close < BB_lower
#   LONG  exit  : RSI > 70 AND close > BB_upper
#   SHORT entry : RSI > 70 AND close > BB_upper
#   SHORT exit  : RSI < 30 AND close < BB_lower
#
# Position Flip Logic:
#   SELL signal while LONG  → close LONG → immediately open SHORT
#   BUY  signal while SHORT → close SHORT → immediately open LONG
# =============================================================

from enum import Enum
from config import RSI_OVERSOLD, RSI_OVERBOUGHT


class Signal(str, Enum):
    LONG       = "LONG"      # Open long / stay long
    SHORT      = "SHORT"     # Open short / stay short
    CLOSE_LONG = "CLOSE_LONG"
    CLOSE_SHORT= "CLOSE_SHORT"
    HOLD       = "HOLD"      # No action


class Position(str, Enum):
    NONE  = "NONE"
    LONG  = "LONG"
    SHORT = "SHORT"


def evaluate_signal(
    close: float,
    rsi: float,
    bb_upper: float,
    bb_lower: float,
    current_position: Position,
    stop_loss_hit: bool = False,
    circuit_breaker_hit: bool = False
) -> tuple[Signal, str]:
    """
    Core signal engine.

    Returns:
        (Signal, reason_string) — what action to take and why

    Position Flip:
        When a SELL/BUY signal fires while an opposite position is open,
        the bot closes the old position AND opens the new one in one cycle.
    """

    # ── Emergency overrides ─────────────────────────────────────
    if circuit_breaker_hit:
        if current_position == Position.LONG:
            return Signal.CLOSE_LONG, "⛔ Circuit breaker triggered — closing LONG"
        if current_position == Position.SHORT:
            return Signal.CLOSE_SHORT, "⛔ Circuit breaker triggered — closing SHORT"
        return Signal.HOLD, "⛔ Circuit breaker — bot halted, no new positions"

    if stop_loss_hit:
        if current_position == Position.LONG:
            return Signal.CLOSE_LONG, "🛑 Stop loss hit — closing LONG"
        if current_position == Position.SHORT:
            return Signal.CLOSE_SHORT, "🛑 Stop loss hit — closing SHORT"

    # ── Bollinger Band + RSI conditions ─────────────────────────
    oversold_entry   = (rsi < RSI_OVERSOLD)  and (close < bb_lower)   # → LONG
    overbought_entry = (rsi > RSI_OVERBOUGHT) and (close > bb_upper)   # → SHORT

    # ── No current position → check for fresh entry ─────────────
    if current_position == Position.NONE:
        if oversold_entry:
            reason = f"📈 LONG ENTRY | RSI={rsi:.1f}<{RSI_OVERSOLD} & Close={close:.4f}<BB_lower={bb_lower:.4f}"
            return Signal.LONG, reason
        if overbought_entry:
            reason = f"📉 SHORT ENTRY | RSI={rsi:.1f}>{RSI_OVERBOUGHT} & Close={close:.4f}>BB_upper={bb_upper:.4f}"
            return Signal.SHORT, reason
        return Signal.HOLD, f"⏳ HOLD | No signal | RSI={rsi:.1f} | Close={close:.4f}"

    # ── Currently LONG ──────────────────────────────────────────
    if current_position == Position.LONG:
        if overbought_entry:
            # Flip: close LONG, will open SHORT in same cycle
            reason = f"🔄 FLIP: LONG→SHORT | RSI={rsi:.1f}>{RSI_OVERBOUGHT} & Close={close:.4f}>BB_upper={bb_upper:.4f}"
            return Signal.SHORT, reason   # bot_runner handles close+open
        return Signal.HOLD, f"⏳ HOLD LONG | RSI={rsi:.1f} | Close={close:.4f}"

    # ── Currently SHORT ─────────────────────────────────────────
    if current_position == Position.SHORT:
        if oversold_entry:
            # Flip: close SHORT, will open LONG in same cycle
            reason = f"🔄 FLIP: SHORT→LONG | RSI={rsi:.1f}<{RSI_OVERSOLD} & Close={close:.4f}<BB_lower={bb_lower:.4f}"
            return Signal.LONG, reason    # bot_runner handles close+open
        return Signal.HOLD, f"⏳ HOLD SHORT | RSI={rsi:.1f} | Close={close:.4f}"

    return Signal.HOLD, "HOLD (default)"
