# backend/risk_manager.py
"""
RiskManager — Hedge fund-grade risk management system.

Features:
- Max Drawdown Cutoff: stop trading if portfolio drops >X% from peak
- Max Position Size: cap at X% of equity per coin
- Max Open Positions: cap simultaneous positions
- Daily Loss Limit: pause bot if daily PnL < -X%
- Per-trade risk checks before execution
- Risk alerts logged to DB
"""
import sqlite3
import json
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

DB_FILE = "market_data.db"

# Default risk parameters
DEFAULT_RISK_CONFIG = {
    "max_drawdown_pct": 15.0,       # Stop bot if portfolio drops >15% from peak
    "max_position_pct": 10.0,       # Max 10% of equity per single coin
    "max_open_positions": 5,        # Max 5 simultaneous positions
    "daily_loss_limit_pct": 3.0,    # Pause if daily PnL < -3%
    "risk_per_trade_pct": 1.0,      # Risk 1% of equity per trade
    "enabled": True,                # Master switch
}


def _get_db_conn():
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn
    except Exception as e:
        print(f"[ERROR] Risk DB Error: {e}")
        return None


def init_risk_tables():
    """Create risk_config and risk_alerts tables."""
    conn = _get_db_conn()
    if not conn:
        return
    try:
        cursor = conn.cursor()

        # Risk configuration (single row, updated in-place)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS risk_config (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                config_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)

        # Risk alerts log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS risk_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,
                severity TEXT DEFAULT 'WARNING',
                message TEXT NOT NULL,
                details_json TEXT,
                created_at TEXT NOT NULL
            );
        """)

        # Insert default config if not exists
        cursor.execute("SELECT COUNT(*) FROM risk_config")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO risk_config (id, config_json, updated_at) VALUES (1, ?, ?)",
                (json.dumps(DEFAULT_RISK_CONFIG), datetime.now().isoformat())
            )

        conn.commit()
        conn.close()
        print("[INFO] Risk tables initialized")
    except Exception as e:
        print(f"[ERROR] Risk table init error: {e}")


def get_risk_config():
    """Get current risk configuration."""
    conn = _get_db_conn()
    if not conn:
        return DEFAULT_RISK_CONFIG.copy()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT config_json FROM risk_config WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
        return DEFAULT_RISK_CONFIG.copy()
    except Exception:
        return DEFAULT_RISK_CONFIG.copy()


def update_risk_config(new_config):
    """Update risk configuration."""
    conn = _get_db_conn()
    if not conn:
        return False
    try:
        # Merge with defaults to ensure all keys exist
        config = DEFAULT_RISK_CONFIG.copy()
        config.update(new_config)

        cursor = conn.cursor()
        cursor.execute(
            "UPDATE risk_config SET config_json = ?, updated_at = ? WHERE id = 1",
            (json.dumps(config), datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        print(f"[INFO] Risk config updated: {config}")
        return True
    except Exception as e:
        print(f"[ERROR] Risk config update error: {e}")
        return False


def log_risk_alert(alert_type, message, severity="WARNING", details=None):
    """Log a risk alert to the database."""
    conn = _get_db_conn()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO risk_alerts (alert_type, severity, message, details_json, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            alert_type, severity, message,
            json.dumps(details) if details else None,
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()
        icon = "[CRITICAL]" if severity == "CRITICAL" else "[WARNING]"
        print(f"{icon} RISK ALERT [{alert_type}]: {message}")
    except Exception as e:
        print(f"[WARN] Risk alert log error: {e}")


def get_risk_alerts(limit=50):
    """Get recent risk alerts."""
    conn = _get_db_conn()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, alert_type, severity, message, details_json, created_at FROM risk_alerts ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        cols = ['id', 'alert_type', 'severity', 'message', 'details', 'created_at']
        result = []
        for row in rows:
            d = dict(zip(cols, row))
            if d['details']:
                try:
                    d['details'] = json.loads(d['details'])
                except Exception:
                    pass
            result.append(d)
        return result
    except Exception:
        return []


def pre_trade_risk_check(engine, symbol, side, qty, price):
    """
    Run all risk checks BEFORE executing a trade.
    Returns (allowed: bool, reason: str)
    """
    config = get_risk_config()

    if not config.get("enabled", True):
        return True, "Risk management disabled"

    try:
        # 1. Fetch current balance
        bal = engine.exchange.fetch_balance()
        total_equity = float(bal.get('USDT', {}).get('total', 0) or 0)
        free_usdt = float(bal.get('USDT', {}).get('free', 0) or 0)

        if total_equity <= 0:
            return False, "Zero equity — cannot trade"

        trade_value = qty * price

        # 2. CHECK: Max Position Size (% of equity)
        max_pos_pct = config.get("max_position_pct", 10.0)
        position_pct = (trade_value / total_equity) * 100
        if position_pct > max_pos_pct:
            msg = f"Position too large: {position_pct:.1f}% > {max_pos_pct}% limit (${trade_value:.2f} / ${total_equity:.2f})"
            log_risk_alert("MAX_POSITION", msg, "WARNING", {"symbol": symbol, "pct": position_pct, "limit": max_pos_pct})
            return False, msg

        # 3. CHECK: Max Open Positions
        max_positions = config.get("max_open_positions", 5)
        conn = _get_db_conn()
        if conn:
            cursor = conn.cursor()
            # Count open positions using net quantity per symbol (buy qty - sell qty)
            # COALESCE(qty, 1) for backward compat with rows that may not have qty set
            cursor.execute("""
                SELECT COUNT(*) FROM (
                    SELECT symbol,
                           SUM(CASE WHEN side = 'buy'  THEN COALESCE(qty, 1) ELSE 0 END) -
                           SUM(CASE WHEN side = 'sell' THEN COALESCE(qty, 1) ELSE 0 END) AS net_qty
                    FROM trade_log
                    GROUP BY symbol
                    HAVING net_qty > 0
                )
            """)
            open_positions = cursor.fetchone()[0]
            conn.close()

            if side == 'buy' and open_positions >= max_positions:
                msg = f"Max positions reached: {open_positions}/{max_positions}"
                log_risk_alert("MAX_POSITIONS", msg, "WARNING", {"current": open_positions, "limit": max_positions})
                return False, msg

        # 4. CHECK: Max Drawdown from Peak
        max_dd_pct = config.get("max_drawdown_pct", 15.0)
        conn = _get_db_conn()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(total_equity) FROM portfolio_snapshots")
            row = cursor.fetchone()
            peak_equity = row[0] if row and row[0] else total_equity
            conn.close()

            if peak_equity > 0:
                current_dd = ((peak_equity - total_equity) / peak_equity) * 100
                if current_dd > max_dd_pct:
                    msg = f"Max drawdown breached: {current_dd:.1f}% > {max_dd_pct}% limit (Peak: ${peak_equity:.2f}, Now: ${total_equity:.2f})"
                    log_risk_alert("MAX_DRAWDOWN", msg, "CRITICAL", {"drawdown_pct": current_dd, "limit": max_dd_pct, "peak": peak_equity, "current": total_equity})
                    return False, msg

        # 5. CHECK: Daily Loss Limit
        daily_limit_pct = config.get("daily_loss_limit_pct", 3.0)
        conn = _get_db_conn()
        if conn:
            cursor = conn.cursor()
            today_start = datetime.now().replace(hour=0, minute=0, second=0).isoformat()

            # Get first snapshot of today or last snapshot from yesterday
            cursor.execute(
                "SELECT total_equity FROM portfolio_snapshots WHERE created_at < ? ORDER BY id DESC LIMIT 1",
                (today_start,)
            )
            row = cursor.fetchone()
            conn.close()

            if row and row[0] and row[0] > 0:
                day_start_equity = row[0]
                daily_pnl_pct = ((total_equity - day_start_equity) / day_start_equity) * 100
                if daily_pnl_pct < -daily_limit_pct:
                    msg = f"Daily loss limit hit: {daily_pnl_pct:.1f}% < -{daily_limit_pct}% limit"
                    log_risk_alert("DAILY_LOSS", msg, "CRITICAL", {"daily_pnl_pct": daily_pnl_pct, "limit": daily_limit_pct})
                    return False, msg

        return True, "All risk checks passed"

    except Exception as e:
        print(f"[WARN] Risk check error: {e}")
        # Fail open — allow trade but log warning
        log_risk_alert("RISK_CHECK_ERROR", f"Risk check failed: {e}", "WARNING")
        return True, f"Risk check error (allowing trade): {e}"


def get_risk_dashboard(engine):
    """
    Compute current risk metrics for the dashboard.
    """
    config = get_risk_config()

    result = {
        "config": config,
        "metrics": {},
        "alerts": get_risk_alerts(20),
    }

    try:
        # Fetch current balance
        bal = engine.exchange.fetch_balance()
        total_equity = float(bal.get('USDT', {}).get('total', 0) or 0)
        free_usdt = float(bal.get('USDT', {}).get('free', 0) or 0)

        # Peak equity (from snapshots)
        conn = _get_db_conn()
        peak_equity = total_equity
        daily_pnl = 0
        daily_pnl_pct = 0
        open_positions = 0

        if conn:
            cursor = conn.cursor()

            # Peak equity
            cursor.execute("SELECT MAX(total_equity) FROM portfolio_snapshots")
            row = cursor.fetchone()
            if row and row[0]:
                peak_equity = row[0]

            # Daily PnL
            today_start = datetime.now().replace(hour=0, minute=0, second=0).isoformat()
            cursor.execute(
                "SELECT total_equity FROM portfolio_snapshots WHERE created_at < ? ORDER BY id DESC LIMIT 1",
                (today_start,)
            )
            row = cursor.fetchone()
            if row and row[0] and row[0] > 0:
                daily_pnl = total_equity - row[0]
                daily_pnl_pct = (daily_pnl / row[0]) * 100

            # Open positions count
            cursor.execute("""
                SELECT COUNT(DISTINCT symbol) FROM trade_log
                WHERE side = 'buy'
                AND symbol NOT IN (
                    SELECT symbol FROM trade_log WHERE side = 'sell'
                    GROUP BY symbol
                    HAVING COUNT(*) >= (SELECT COUNT(*) FROM trade_log t2 WHERE t2.symbol = trade_log.symbol AND t2.side = 'buy')
                )
            """)
            open_positions = cursor.fetchone()[0]

            # Total alerts today
            cursor.execute(
                "SELECT COUNT(*) FROM risk_alerts WHERE created_at >= ?",
                (today_start,)
            )
            alerts_today = cursor.fetchone()[0]

            conn.close()

        # Calculate drawdown
        current_dd = ((peak_equity - total_equity) / peak_equity * 100) if peak_equity > 0 else 0

        # Exposure (non-cash as % of equity)
        exposure_pct = ((total_equity - free_usdt) / total_equity * 100) if total_equity > 0 else 0

        # --- ADVANCED INSTITUTIONAL RISK METRICS (for HSB Investasi Interview) ---
        advanced_metrics = {
            "historical_var_95": 0.0,
            "parametric_var_95": 0.0,
            "cvar_95": 0.0,
            "sortino_ratio": 0.0,
            "stress_tests": {
                "btc_drop_10pct": 0.0,
                "btc_drop_20pct": 0.0,
                "flash_crash_30pct": 0.0
            }
        }

        # Compute advanced metrics from historical portfolio snapshots
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT total_equity FROM portfolio_snapshots ORDER BY id ASC")
            equities = [row[0] for row in cursor.fetchall() if row[0] is not None]
            
            if len(equities) > 1:
                import pandas as pd
                series = pd.Series(equities)
                returns = series.pct_change().dropna()
                
                if not returns.empty:
                    # 1. Historical VaR (95%)
                    advanced_metrics["historical_var_95"] = round(float(np.percentile(returns, 5)) * 100, 2)
                    
                    # 2. Parametric VaR (95%) = Mean - 1.645 * StdDev
                    mean_ret = returns.mean()
                    std_ret = returns.std()
                    advanced_metrics["parametric_var_95"] = round((mean_ret - 1.645 * std_ret) * 100, 2)
                    
                    # 3. CVaR / Expected Shortfall (95%)
                    var_threshold = np.percentile(returns, 5)
                    tail_returns = returns[returns <= var_threshold]
                    cvar = tail_returns.mean() if len(tail_returns) > 0 else var_threshold
                    advanced_metrics["cvar_95"] = round(float(cvar) * 100, 2)
                    
                    # 4. Sortino Ratio (Annualized)
                    # Uses only downside deviation (Standard Deviation of negative returns)
                    downside_returns = returns[returns < 0]
                    downside_std = downside_returns.std()
                    if downside_std > 0 and len(downside_returns) > 0:
                        annualized_return = mean_ret * 365 # Crypto is 365 days
                        annualized_downside_std = downside_std * np.sqrt(365)
                        advanced_metrics["sortino_ratio"] = round(annualized_return / annualized_downside_std, 2)
            
            conn.close()

        # 5. Stress Tests (Estimated portfolio impact based on exposure)
        # Using linear beta approximation (Beta = 1.0 to BTC for simplicity in this demo)
        beta_estimate = 1.0  
        active_exposure_value = (total_equity * exposure_pct / 100)
        
        advanced_metrics["stress_tests"] = {
            "btc_drop_10pct": round(-(active_exposure_value * 0.10 * beta_estimate), 2),
            "btc_drop_20pct": round(-(active_exposure_value * 0.20 * beta_estimate), 2),
            "flash_crash_30pct": round(-(active_exposure_value * 0.30 * beta_estimate), 2)
        }

        result["metrics"] = {
            "total_equity": round(total_equity, 2),
            "peak_equity": round(peak_equity, 2),
            "current_drawdown_pct": round(current_dd, 2),
            "max_drawdown_limit": config.get("max_drawdown_pct", 15.0),
            "daily_pnl": round(daily_pnl, 2),
            "daily_pnl_pct": round(daily_pnl_pct, 2),
            "daily_loss_limit": config.get("daily_loss_limit_pct", 3.0),
            "open_positions": open_positions,
            "max_positions": config.get("max_open_positions", 5),
            "exposure_pct": round(exposure_pct, 1),
            "max_position_pct": config.get("max_position_pct", 10.0),
            "risk_per_trade": config.get("risk_per_trade_pct", 1.0),
            "enabled": config.get("enabled", True),
            "alerts_today": alerts_today if 'alerts_today' in dir() else 0,
            "advanced": advanced_metrics
        }

    except Exception as e:
        print(f"[WARN] Risk dashboard error: {e}")
        import traceback
        traceback.print_exc()
        result["metrics"] = {"error": str(e)}

    return result
