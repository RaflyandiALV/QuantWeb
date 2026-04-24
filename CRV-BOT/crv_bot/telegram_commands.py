# =============================================================
# telegram_commands.py — Telegram Bot Command Center
#
# Commands:
#   /status  → Posisi aktif, equity, PnL, RSI, harga saat ini
#   /log     → 20 baris terakhir bot.log
#   /battery → Level baterai & status charging S20+
#   /chart   → Price chart CRV + BB + Entry/Exit + RSI panel
#              (menggunakan QuickChart.io API, tanpa matplotlib)
#
# Berjalan sebagai background thread di dalam bot_runner.py
# Polling Telegram setiap 2 detik untuk cek perintah masuk
# =============================================================

import io
import os
import json
import logging
import subprocess
import threading
import requests
import math
import pandas as pd
from datetime import datetime, timezone

import config

logger = logging.getLogger(__name__)

# ── Shared state (diupdate oleh bot_runner) ──────────────────
_state_ref    : dict  = {}
_exchange_ref        = None
_last_df_ref  : dict = {"df": None}
_state_lock          = threading.Lock()

_offset = 0


def set_shared_refs(state: dict, exchange, df_ref: dict):
    global _state_ref, _exchange_ref, _last_df_ref
    # ⚠️ CRITICAL: Use dict(state) to make a COPY, NOT a shared reference.
    # If _state_ref IS the same object as state, then update_state(state) will:
    #   1. _state_ref.clear()          → empties the SAME dict that state points to
    #   2. _state_ref.update(new_state) → new_state is now also empty → state is wiped!
    # This caused every candle to reset position/peak_equity to defaults.
    _state_ref    = dict(state)
    _exchange_ref = exchange
    _last_df_ref  = df_ref


def update_state(new_state: dict):
    with _state_lock:
        _state_ref.clear()
        _state_ref.update(new_state)


# ── Telegram Helpers ──────────────────────────────────────────

def _send_text(text: str) -> bool:
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, json={
            "chat_id"   : config.TELEGRAM_CHAT_ID,
            "text"      : text,
            "parse_mode": "HTML",
        }, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"[CMD] Send text failed: {e}")
        return False


def _send_photo(image_bytes: bytes, caption: str = "") -> bool:
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        resp = requests.post(url, data={
            "chat_id" : config.TELEGRAM_CHAT_ID,
            "caption" : caption[:1024],
        }, files={
            "photo": ("chart.png", image_bytes, "image/png"),
        }, timeout=30)
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"[CMD] Send photo failed: {e}")
        return False


def _get_updates() -> list:
    global _offset
    if not config.TELEGRAM_BOT_TOKEN:
        return []
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getUpdates"
    try:
        resp = requests.get(url, params={
            "offset"         : _offset,
            "timeout"        : 2,
            "allowed_updates": ["message"],
        }, timeout=8)
        if resp.status_code != 200:
            return []
        updates = resp.json().get("result", [])
        if updates:
            _offset = updates[-1]["update_id"] + 1
        return updates
    except Exception:
        return []


# ── Command Handlers ──────────────────────────────────────────

def _handle_status():
    from risk_manager import calculate_unrealized_pnl

    with _state_lock:
        state = dict(_state_ref)

    position   = state.get("position", "NONE")
    entry_px   = state.get("entry_price")
    size_usdt  = state.get("position_size", 0) or 0
    peak_eq    = state.get("peak_equity", 0) or 0
    cooldown   = state.get("cooldown_until")
    entry_time = state.get("entry_time", "-")

    try:
        from order_executor import get_current_price, get_equity
        current_px = get_current_price(_exchange_ref)
        equity     = get_equity(_exchange_ref)
    except Exception as e:
        current_px = 0.0
        equity     = 0.0
        logger.warning(f"[CMD] Cannot fetch exchange data: {e}")

    rsi_str = "-"
    bb_str  = "-"
    df = _last_df_ref.get("df")
    if df is not None and not df.empty:
        try:
            last    = df.iloc[-1]
            rsi_str = f"{last['rsi']:.1f}"
            bb_str  = f"{last['bb_lower']:.4f} — {last['bb_upper']:.4f}"
        except Exception:
            pass

    pnl = calculate_unrealized_pnl(state, current_px) if current_px else {"pnl_pct": 0, "pnl_usdt": 0}

    now     = datetime.now(timezone.utc)
    elapsed = (now.hour % 4) * 3600 + now.minute * 60 + now.second
    remain  = 4 * 3600 - elapsed
    next_h  = remain // 3600
    next_m  = (remain % 3600) // 60

    sl_str = "-"
    if entry_px and position != "NONE":
        sl_str = f"{entry_px * (1 - config.STOP_LOSS_PCT):.4f}" if position == "LONG" \
            else f"{entry_px * (1 + config.STOP_LOSS_PCT):.4f}"

    pos_emoji = {"LONG": "📈", "SHORT": "📉", "NONE": "💤"}.get(position, "💤")
    pnl_emoji = "✅" if pnl["pnl_usdt"] >= 0 else "🔴"

    msg = (
        f"📊 <b>CRV Bot Status</b>\n"
        f"{'─' * 28}\n"
        f"⏰ <code>{now.strftime('%Y-%m-%d %H:%M UTC')}</code>\n\n"
        f"<b>💰 Account</b>\n"
        f"Equity:     <code>{equity:.2f} USDT</code>\n"
        f"Peak Eq:    <code>{peak_eq:.2f} USDT</code>\n\n"
        f"<b>{pos_emoji} Position</b>\n"
        f"Direction:  <code>{position}</code>\n"
        f"Entry Px:   <code>{f'{entry_px:.4f}' if entry_px else '-'}</code>\n"
        f"Current Px: <code>{current_px:.4f}</code>\n"
        f"Stop Loss:  <code>{sl_str}</code>\n"
        f"Size:       <code>{size_usdt:.2f} USDT</code>\n"
        f"Entry Time: <code>{str(entry_time)[:16] if entry_time else '-'}</code>\n"
        f"{pnl_emoji} PnL:      <code>{pnl['pnl_pct']:+.2f}% | {pnl['pnl_usdt']:+.4f} USDT</code>\n\n"
        f"<b>📡 Indicators</b>\n"
        f"RSI(14):    <code>{rsi_str}</code>\n"
        f"BB Bands:   <code>{bb_str}</code>\n\n"
        f"<b>⏱️ Next Candle</b>\n"
        f"<code>{next_h}h {next_m}m remaining</code>\n"
    )
    if cooldown:
        msg += f"\n⏳ <b>Cooldown until:</b> <code>{str(cooldown)[:16]}</code>"

    _send_text(msg)


def _handle_log():
    log_file = config.LOG_FILE
    try:
        if not os.path.exists(log_file):
            _send_text("⚠️ <b>bot.log</b> belum ada.")
            return
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        log_text = "".join(lines[-20:]).strip()
        _send_text(f"📋 <b>bot.log (20 baris terakhir)</b>\n\n<code>{log_text[-3500:]}</code>")
    except Exception as e:
        _send_text(f"❌ Gagal membaca log: <code>{e}</code>")


def _handle_battery():
    try:
        result = subprocess.run(
            ["termux-battery-status"],
            capture_output=True, text=True, timeout=5
        )
        data        = json.loads(result.stdout)
        level       = data.get("percentage", "?")
        status      = data.get("status", "?")
        health      = data.get("health", "?")
        temperature = data.get("temperature", "?")
        plugged     = data.get("plugged", "?")

        bat_emoji = "⚡" if status == "CHARGING" else "🔋"
        if isinstance(level, (int, float)):
            bar = "█████" if level >= 80 else "████░" if level >= 60 else "███░░" if level >= 40 else "██░░░" if level >= 20 else "█░░░░"
        else:
            bar = "░░░░░"

        msg = (
            f"{bat_emoji} <b>Battery — Samsung S20+</b>\n"
            f"{'─' * 28}\n"
            f"Level:       <code>{level}% [{bar}]</code>\n"
            f"Status:      <code>{status}</code>\n"
            f"Plugged:     <code>{plugged}</code>\n"
            f"Health:      <code>{health}</code>\n"
            f"Temperature: <code>{temperature}°C</code>\n"
        )
    except FileNotFoundError:
        msg = (
            "⚠️ <b>termux-api</b> belum terinstall.\n\n"
            "Jalankan:\n<code>pkg install termux-api -y</code>\n"
            "Lalu install <b>Termux:API</b> dari Play Store/F-Droid."
        )
    except Exception as e:
        msg = f"❌ Gagal cek baterai: <code>{e}</code>"

    _send_text(msg)


def _handle_chart():
    """Generate chart via QuickChart.io — tanpa matplotlib, 100% kompatibel Android."""
    _send_text("📊 <i>Generating chart via QuickChart.io... tunggu ~5 detik</i>")

    df = _last_df_ref.get("df")
    if df is None or df.empty:
        _send_text("⚠️ Data candle belum tersedia. Coba lagi setelah candle pertama selesai.")
        return

    with _state_lock:
        state = dict(_state_ref)

    plot_df  = df.tail(100).copy()
    position = state.get("position", "NONE")
    entry_px = state.get("entry_price")

    # Labels — hanya tampilkan setiap 10 candle
    labels = []
    for i, ts in enumerate(plot_df["timestamp"]):
        labels.append(str(ts)[:13].replace("T", " ") if i % 10 == 0 else "")

    # Helper untuk bersihkan NaN agar JSON valid (None -> null)
    def clean(v, round_digit=4):
        try:
            val = float(v)
            return round(val, round_digit) if not math.isnan(val) else None
        except Exception:
            return None

    closes    = [clean(v, 4) for v in plot_df["close"]]
    bb_upper  = [clean(v, 4) for v in plot_df["bb_upper"]]
    bb_middle = [clean(v, 4) for v in plot_df["bb_mid"]]
    bb_lower  = [clean(v, 4) for v in plot_df["bb_lower"]]
    rsi_vals  = [clean(v, 2) for v in plot_df["rsi"]]

    # Scale RSI ke range harga agar bisa overlay (0-100 → price range bawah)
    valid_bb = [x for x in bb_lower + bb_upper if x is not None]
    if valid_bb:
        p_min = min(valid_bb)
        p_max = max(valid_bb)
    else:
        p_min = min(closes)
        p_max = max(closes)

    p_rng = (p_max - p_min) * 0.35  # RSI menempati 35% bawah chart
    rsi_scaled = [round(p_min + (v / 100) * p_rng, 4) if v is not None else None for v in rsi_vals]

    # Entry & SL lines
    sl_px = None
    datasets = [
        {
            "label": "BB Upper",
            "data": bb_upper,
            "borderColor": "rgba(88,166,255,0.5)",
            "backgroundColor": "rgba(88,166,255,0.06)",
            "borderWidth": 1,
            "pointRadius": 0,
            "fill": False,
        },
        {
            "label": "BB Middle",
            "data": bb_middle,
            "borderColor": "rgba(139,148,158,0.4)",
            "borderWidth": 1,
            "borderDash": [4, 4],
            "pointRadius": 0,
            "fill": False,
        },
        {
            "label": "BB Lower",
            "data": bb_lower,
            "borderColor": "rgba(88,166,255,0.5)",
            "borderWidth": 1,
            "pointRadius": 0,
            "fill": False,
        },
        {
            "label": "CRV/USDT",
            "data": closes,
            "borderColor": "#e6edf3",
            "borderWidth": 1.8,
            "pointRadius": 0,
            "fill": False,
        },
        {
            "label": "RSI(14) overlay",
            "data": rsi_scaled,
            "borderColor": "rgba(163,113,247,0.7)",
            "borderWidth": 1,
            "borderDash": [2, 3],
            "pointRadius": 0,
            "fill": False,
        },
    ]

    if entry_px and position != "NONE":
        if position == "LONG":
            sl_px = round(entry_px * (1 - config.STOP_LOSS_PCT), 4)
        else:
            sl_px = round(entry_px * (1 + config.STOP_LOSS_PCT), 4)

        datasets.append({
            "label": f"Entry {round(entry_px, 4)}",
            "data": [round(entry_px, 4)] * len(closes),
            "borderColor": "#3fb950",
            "borderWidth": 1.5,
            "borderDash": [6, 4],
            "pointRadius": 0,
            "fill": False,
        })
        datasets.append({
            "label": f"SL {sl_px}",
            "data": [sl_px] * len(closes),
            "borderColor": "#f85149",
            "borderWidth": 1.2,
            "borderDash": [3, 5],
            "pointRadius": 0,
            "fill": False,
        })

    title = (
        f"CRV/USDT 4H | BB(17,1.8) + RSI(14) | "
        f"Pos: {position}" + (f" @ {round(entry_px,4)}" if entry_px else "")
    )

    chart_config = {
        "type": "line",
        "data": {"labels": labels, "datasets": datasets},
        "options": {
            "animation": False,
            "plugins": {
                "legend": {"labels": {"color": "#8b949e", "font": {"size": 9}}},
                "title": {
                    "display": True,
                    "text": title,
                    "color": "#e6edf3",
                    "font": {"size": 11},
                },
            },
            "scales": {
                "x": {
                    "ticks": {"color": "#8b949e", "maxRotation": 30, "font": {"size": 8}},
                    "grid": {"color": "rgba(48,54,61,0.6)"},
                },
                "y": {
                    "ticks": {"color": "#8b949e", "font": {"size": 8}},
                    "grid": {"color": "rgba(48,54,61,0.6)"},
                },
            },
        },
    }

    try:
        resp = requests.post(
            "https://quickchart.io/chart",
            json={
                "chart"          : chart_config,
                "width"          : 960,
                "height"         : 520,
                "backgroundColor": "#0d1117",
                "format"         : "png",
            },
            timeout=30,
        )
        if resp.status_code != 200:
            _send_text(f"❌ QuickChart error {resp.status_code}: {resp.text[:200]}")
            return

        caption = (
            f"📊 CRV/USDT 4H — 100 candles\n"
            f"Price: {closes[-1]:.4f} | RSI: {rsi_vals[-1]:.1f}\n"
            f"Position: {position}"
            + (f" @ {entry_px:.4f}" if entry_px else "")
            + f"\n{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
        )
        _send_photo(resp.content, caption)
        logger.info("[CMD] Chart sent via QuickChart.io")

    except Exception as e:
        logger.error(f"[CMD] Chart failed: {e}")
        _send_text(f"❌ Chart gagal: <code>{e}</code>")


# ── Command Dispatcher ────────────────────────────────────────

def _dispatch(text: str):
    cmd = text.strip().lower().split()[0] if text.strip() else ""
    logger.info(f"[CMD] Received: {cmd}")

    if cmd == "/status":
        _handle_status()
    elif cmd == "/log":
        _handle_log()
    elif cmd == "/battery":
        _handle_battery()
    elif cmd == "/chart":
        _handle_chart()
    elif cmd == "/help":
        _send_text(
            "🤖 <b>CRV Bot — Commands</b>\n\n"
            "/status  — Status bot, posisi, equity, PnL, RSI\n"
            "/chart   — Price chart CRV + BB + RSI (gambar)\n"
            "/log     — 20 baris terakhir bot.log\n"
            "/battery — Level baterai Samsung S20+\n"
            "/help    — Daftar perintah ini"
        )
    else:
        if cmd.startswith("/"):
            _send_text(f"❓ Perintah <code>{cmd}</code> tidak dikenal. Ketik /help")


# ── Main Polling Loop ─────────────────────────────────────────

def run_command_listener():
    """Loop utama — berjalan sebagai background thread."""
    logger.info("[CMD] Telegram command listener started.")
    if not config.TELEGRAM_BOT_TOKEN:
        logger.warning("[CMD] Telegram not configured — command listener disabled.")
        return

    _send_text(
        "🎮 <b>Command Center Aktif!</b>\n\n"
        "Ketik salah satu perintah:\n"
        "/status  — Status bot lengkap\n"
        "/chart   — Kirim chart CRV (100 candles)\n"
        "/log     — Log terakhir\n"
        "/battery — Baterai S20+\n"
        "/help    — Lihat semua perintah"
    )

    while True:
        try:
            updates = _get_updates()
            for update in updates:
                msg  = update.get("message", {})
                text = msg.get("text", "")
                if text:
                    threading.Thread(
                        target=_dispatch, args=(text,), daemon=True
                    ).start()
        except Exception as e:
            logger.error(f"[CMD] Polling error: {e}")

        import time
        time.sleep(2)
