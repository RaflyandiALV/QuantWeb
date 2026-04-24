# =============================================================
# notifier.py — Telegram Alert System
# Sends rich-format messages on trade events, errors, heartbeat
# =============================================================

import logging
import requests
from datetime import datetime
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)


def _send(message: str, parse_mode: str = "HTML") -> bool:
    """
    Core Telegram send function.
    Returns True on success, False on failure (non-blocking).
    """
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.warning("Telegram not configured — skipping notification.")
        return False
    if not TELEGRAM_CHAT_ID or TELEGRAM_CHAT_ID == "YOUR_TELEGRAM_CHAT_ID_HERE":
        logger.warning("Telegram chat_id not configured — skipping notification.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id"    : TELEGRAM_CHAT_ID,
        "text"       : message,
        "parse_mode" : parse_mode,
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.debug("Telegram: message sent.")
            return True
        else:
            logger.warning(f"Telegram API error: {resp.status_code} — {resp.text}")
            return False
    except requests.RequestException as e:
        logger.error(f"Telegram send failed: {e}")
        return False


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")


# ── Notification Types ────────────────────────────────────────

def notify_bot_started(paper_trading: bool) -> None:
    mode = "📄 PAPER TRADING" if paper_trading else "💸 LIVE TRADING"
    _send(
        f"🤖 <b>CRV-USDT Bot Started</b>\n"
        f"Mode: {mode}\n"
        f"Time: {_now()}"
    )


def notify_bot_stopped(reason: str) -> None:
    _send(
        f"🔴 <b>CRV-USDT Bot Stopped</b>\n"
        f"Reason: {reason}\n"
        f"Time: {_now()}"
    )


def notify_signal(signal: str, reason: str, indicators: dict) -> None:
    _send(
        f"📡 <b>Signal: {signal}</b>\n"
        f"{reason}\n\n"
        f"<b>Indicators</b>\n"
        f"Close:    <code>{indicators.get('close', 0):.4f}</code>\n"
        f"RSI:      <code>{indicators.get('rsi', 0):.1f}</code>\n"
        f"BB Upper: <code>{indicators.get('bb_upper', 0):.4f}</code>\n"
        f"BB Lower: <code>{indicators.get('bb_lower', 0):.4f}</code>\n"
        f"ATR:      <code>{indicators.get('atr', 0):.4f}</code>\n"
        f"Time: {_now()}"
    )


def notify_order_opened(side: str, price: float, size_usdt: float, paper: bool) -> None:
    mode = "[PAPER]" if paper else "[LIVE]"
    emoji = "📈" if side.upper() == "LONG" else "📉"
    _send(
        f"{emoji} <b>{mode} Position Opened: {side.upper()}</b>\n"
        f"Entry Price: <code>{price:.4f}</code>\n"
        f"Size:        <code>{size_usdt:.2f} USDT</code>\n"
        f"Stop Loss:   <code>-20% from entry</code>\n"
        f"Exchange SL: <code>Server-side on Bybit</code>\n"
        f"Leverage:    <code>2×</code>\n"
        f"Time: {_now()}"
    )


def notify_order_closed(side: str, entry: float, exit_price: float,
                        pnl_pct: float, pnl_usdt: float, reason: str, paper: bool) -> None:
    mode = "[PAPER]" if paper else "[LIVE]"
    pnl_emoji = "✅" if pnl_usdt >= 0 else "❌"
    _send(
        f"{pnl_emoji} <b>{mode} Position Closed: {side.upper()}</b>\n"
        f"Reason: {reason}\n\n"
        f"Entry:    <code>{entry:.4f}</code>\n"
        f"Exit:     <code>{exit_price:.4f}</code>\n"
        f"P&amp;L:  <code>{pnl_pct:+.2f}% | {pnl_usdt:+.4f} USDT</code>\n"
        f"Time: {_now()}"
    )


def notify_stop_loss(side: str, entry: float, price: float, pnl_usdt: float, paper: bool) -> None:
    mode = "[PAPER]" if paper else "[LIVE]"
    _send(
        f"🛑 <b>{mode} STOP LOSS HIT: {side.upper()}</b>\n"
        f"Entry:   <code>{entry:.4f}</code>\n"
        f"Current: <code>{price:.4f}</code>\n"
        f"Loss:    <code>{pnl_usdt:.4f} USDT</code>\n"
        f"Time: {_now()}"
    )


def notify_circuit_breaker(peak_equity: float, current_equity: float, drawdown_pct: float) -> None:
    from config import COOLDOWN_CANDLES
    cooldown_h = COOLDOWN_CANDLES * 4
    _send(
        f"⛔ <b>CIRCUIT BREAKER TRIGGERED</b>\n\n"
        f"Portfolio dropped <code>{drawdown_pct:.1f}%</code> from peak.\n"
        f"Peak:    <code>{peak_equity:.2f} USDT</code>\n"
        f"Current: <code>{current_equity:.2f} USDT</code>\n\n"
        f"⏳ Bot entering cooldown for {cooldown_h} hours.\n"
        f"Bot will auto-resume after cooldown expires.\n"
        f"Time: {_now()}"
    )


def notify_error(error_msg: str) -> None:
    _send(
        f"🔥 <b>Bot Error</b>\n"
        f"<code>{error_msg[:500]}</code>\n"
        f"Time: {_now()}"
    )


def notify_heartbeat(equity: float, position: str, pnl: dict) -> None:
    """Daily heartbeat to confirm VPS and bot are alive."""
    pnl_str = (
        f"Unrealized P&amp;L: <code>{pnl.get('pnl_pct', 0):+.2f}% ({pnl.get('pnl_usdt', 0):+.4f} USDT)</code>"
        if position != "NONE"
        else "No open position"
    )
    _send(
        f"💓 <b>VPS &amp; Bot Heartbeat (DAILY CHECK-IN)</b>\n"
        f"<i>✔️ RDP / VPS ini terpantau nyala &amp; online!</i>\n\n"
        f"Balance:  <code>{equity:.2f} USDT</code>\n"
        f"Position: <code>{position}</code>\n"
        f"{pnl_str}\n"
        f"Time: {_now()}"
    )
