# backend/portfolio_engine.py
"""
PortfolioTracker — Tracks portfolio equity over time for the hedge fund dashboard.

Features:
- Takes periodic balance snapshots from Binance Testnet
- Stores snapshots in portfolio_snapshots table (SQLite)
- Computes equity curve, daily PnL, allocation breakdown
"""
import sqlite3
import json
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

DB_FILE = "market_data.db"


def _get_db_conn():
    try:
        return sqlite3.connect(DB_FILE, check_same_thread=False)
    except Exception as e:
        print(f"[ERROR] Portfolio DB Error: {e}")
        return None


def init_portfolio_tables():
    """Create portfolio_snapshots table if not exists."""
    conn = _get_db_conn()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                total_equity REAL NOT NULL,
                free_usdt REAL DEFAULT 0,
                used_usdt REAL DEFAULT 0,
                positions_json TEXT,
                snapshot_type TEXT DEFAULT 'auto',
                created_at TEXT NOT NULL
            );
        """)
        conn.commit()
        conn.close()
        print("[INFO] Portfolio tables initialized")
    except Exception as e:
        print(f"[ERROR] Portfolio table init error: {e}")


def take_snapshot(engine):
    """
    Pull balance from exchange and save a snapshot.
    Called by APScheduler every 5 minutes.
    """
    if engine.auth_mode not in ["TESTNET", "REAL"]:
        return

    try:
        bal = engine.exchange.fetch_balance()

        # Calculate total equity in USDT
        total_usdt = bal.get('USDT', {}).get('total', 0) or 0
        free_usdt = bal.get('USDT', {}).get('free', 0) or 0
        used_usdt = bal.get('USDT', {}).get('used', 0) or 0

        # Collect non-USDT positions with their balances
        positions = {}
        for currency, data in bal.items():
            if isinstance(data, dict) and currency not in [
                'info', 'timestamp', 'datetime', 'free', 'used', 'total', 'USDT'
            ]:
                amount = data.get('total', 0) or 0
                if amount > 0:
                    positions[currency] = {
                        "total": float(amount),
                        "free": float(data.get('free', 0) or 0),
                        "used": float(data.get('used', 0) or 0),
                    }

        # Estimate USD value of non-USDT holdings
        non_usdt_value = 0
        for currency, pos_data in positions.items():
            try:
                ticker = engine.exchange.fetch_ticker(f"{currency}/USDT")
                price = ticker.get('last', 0) or 0
                pos_data['price_usdt'] = float(price)
                pos_data['value_usdt'] = round(float(pos_data['total']) * float(price), 2)
                non_usdt_value += pos_data['value_usdt']
            except Exception:
                pos_data['price_usdt'] = 0
                pos_data['value_usdt'] = 0

        total_equity = float(total_usdt) + non_usdt_value

        # Save to DB
        conn = _get_db_conn()
        if not conn:
            return
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO portfolio_snapshots (total_equity, free_usdt, used_usdt, positions_json, snapshot_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            round(total_equity, 2),
            round(float(free_usdt), 2),
            round(float(used_usdt), 2),
            json.dumps(positions),
            'auto',
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()
        print(f"[SNAPSHOT] Portfolio: ${total_equity:,.2f} ({len(positions)} positions)")

    except Exception as e:
        print(f"[WARN] Snapshot error: {e}")


def get_portfolio_summary(engine):
    """
    Return current portfolio state: equity, positions, allocation %
    """
    if engine.auth_mode not in ["TESTNET", "REAL"]:
        return {"mode": "PUBLIC", "error": "No API keys configured"}

    try:
        bal = engine.exchange.fetch_balance()

        total_usdt = float(bal.get('USDT', {}).get('total', 0) or 0)
        free_usdt = float(bal.get('USDT', {}).get('free', 0) or 0)

        positions = []
        total_non_usdt = 0

        for currency, data in bal.items():
            if isinstance(data, dict) and currency not in [
                'info', 'timestamp', 'datetime', 'free', 'used', 'total', 'USDT'
            ]:
                amount = float(data.get('total', 0) or 0)
                if amount > 0:
                    price = 0
                    value = 0
                    try:
                        ticker = engine.exchange.fetch_ticker(f"{currency}/USDT")
                        price = float(ticker.get('last', 0) or 0)
                        value = round(amount * price, 2)
                        total_non_usdt += value
                    except Exception:
                        pass

                    positions.append({
                        "currency": currency,
                        "amount": round(amount, 8),
                        "price_usdt": round(price, 4),
                        "value_usdt": value,
                        "free": round(float(data.get('free', 0) or 0), 8),
                        "used": round(float(data.get('used', 0) or 0), 8),
                    })

        total_equity = total_usdt + total_non_usdt

        # Add allocation %
        for pos in positions:
            pos["allocation_pct"] = round((pos["value_usdt"] / total_equity * 100) if total_equity > 0 else 0, 1)

        # Sort by value
        positions.sort(key=lambda x: x['value_usdt'], reverse=True)

        # Get last snapshot for comparison
        conn = _get_db_conn()
        today_pnl = 0
        if conn:
            try:
                cursor = conn.cursor()
                today_start = datetime.now().replace(hour=0, minute=0, second=0).isoformat()
                cursor.execute(
                    "SELECT total_equity FROM portfolio_snapshots WHERE created_at < ? ORDER BY id DESC LIMIT 1",
                    (today_start,)
                )
                row = cursor.fetchone()
                if row:
                    today_pnl = round(total_equity - row[0], 2)
                conn.close()
            except Exception:
                pass

        return {
            "mode": engine.auth_mode,
            "total_equity": round(total_equity, 2),
            "usdt_balance": round(total_usdt, 2),
            "usdt_free": round(free_usdt, 2),
            "non_usdt_value": round(total_non_usdt, 2),
            "positions": positions[:20],
            "cash_pct": round((total_usdt / total_equity * 100) if total_equity > 0 else 100, 1),
            "invested_pct": round((total_non_usdt / total_equity * 100) if total_equity > 0 else 0, 1),
            "today_pnl": today_pnl,
        }
    except Exception as e:
        print(f"[WARN] Portfolio summary error: {e}")
        return {"error": str(e)}


def get_equity_curve(days=30):
    """
    Return equity snapshots for charting (line chart for equity curve).
    """
    conn = _get_db_conn()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        since = (datetime.now() - timedelta(days=days)).isoformat()
        cursor.execute(
            "SELECT total_equity, free_usdt, created_at FROM portfolio_snapshots WHERE created_at >= ? ORDER BY id ASC",
            (since,)
        )
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "equity": row[0],
                "cash": row[1],
                "timestamp": row[2],
            }
            for row in rows
        ]
    except Exception as e:
        print(f"[WARN] Equity curve error: {e}")
        return []


def get_daily_pnl(days=30):
    """
    Calculate daily PnL from snapshots (first and last snapshot of each day).
    """
    conn = _get_db_conn()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        since = (datetime.now() - timedelta(days=days)).isoformat()

        # Get all snapshots in the period
        cursor.execute(
            "SELECT total_equity, created_at FROM portfolio_snapshots WHERE created_at >= ? ORDER BY id ASC",
            (since,)
        )
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return []

        # Group by date
        daily = {}
        for equity, ts in rows:
            day = ts[:10]  # "YYYY-MM-DD"
            if day not in daily:
                daily[day] = {"open": equity, "close": equity}
            daily[day]["close"] = equity

        # Calculate PnL per day
        result = []
        prev_close = None
        for day in sorted(daily.keys()):
            day_open = daily[day]["open"]
            day_close = daily[day]["close"]

            # PnL = change from previous day's close to today's close
            if prev_close is not None:
                pnl = round(day_close - prev_close, 2)
                pnl_pct = round((pnl / prev_close * 100) if prev_close > 0 else 0, 2)
            else:
                pnl = round(day_close - day_open, 2)
                pnl_pct = round((pnl / day_open * 100) if day_open > 0 else 0, 2)

            result.append({
                "date": day,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "equity": day_close,
            })
            prev_close = day_close

        return result

    except Exception as e:
        print(f"[WARN] Daily PnL error: {e}")
        return []
