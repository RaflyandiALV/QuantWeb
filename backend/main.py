# backend/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from strategy_core import TradingEngine
import portfolio_engine
import risk_manager
import fund_analytics
from backtest_engine import BacktestEngine
from anomaly_scanner import AnomalyScanner
from macro_intelligence import MacroIntelligence
from global_market import GlobalMarketAnalyzer
from alpha_data import AlphaDataProvider
from alpha_features import AlphaFeatureEngine
from ai_brain import AIBrain
from paper_trader import PaperTrader
from validation_engine import ValidationEngine
from monte_carlo import MonteCarloEngine
import pandas as pd
import json
import os
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from typing import Optional, List, Literal
from datetime import datetime
import numpy as np
import contextlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# =============================================================================
# 1. CONFIGURATION & ENVIRONMENT VARIABLES
# =============================================================================
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DATABASE_URL = os.getenv("DATABASE_URL")
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")

WATCHLIST_FILE = "watchlist.json" # Legacy backup file (Secondary storage)

# Thread pool for parallel scanning — shared across requests
_scan_executor = ThreadPoolExecutor(max_workers=4)
_symbol_executor = ThreadPoolExecutor(max_workers=3)

# =============================================================================
# 2. HELPER FUNCTIONS (UTILITIES)
# =============================================================================

def send_telegram_alert(message):
    """
    Mengirim pesan notifikasi ke Telegram Bot.
    Digunakan untuk alert sinyal trading dan status sistem.
    """
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try: 
        requests.post(url, json=payload)
    except Exception as e: 
        print(f"Telegram Error: {e}")

def get_db_connection():
    """
    Membuat koneksi ke Database PostgreSQL (Supabase).
    Menggunakan library psycopg2.
    """
    url = os.getenv("DATABASE_URL")
    if not url:
        print("[ERROR] DATABASE_URL tidak terbaca dari .env!")
        return None
    return psycopg2.connect(url, cursor_factory=RealDictCursor)

def load_watchlist_from_db():
    """
    Mengambil daftar pantauan (watchlist) dari Database.
    Digunakan oleh Bot Scheduler.
    """
    conn = get_db_connection()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT symbol, mode, strategy, timeframe, period FROM watchlist")
        rows = cur.fetchall()
        cur.close()
        return rows
    except Exception as e:
        print(f"DB Error: {e}")
        return []
    finally:
        conn.close()

def calculate_rr_string(entry, tp, sl):
    """
    Menghitung dan memformat Risk:Reward Ratio untuk display.
    """
    try:
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        if risk == 0: return "1 : N/A"
        ratio = reward / risk
        return f"1 : {ratio:.1f}"
    except Exception:
        return "N/A"

def analyze_market_reason(best_strat, win_rate):
    """
    Memberikan alasan naratif sederhana berdasarkan strategi yang terpilih.
    """
    if best_strat == "HOLD ONLY": return "[UPTREND] Parabolic Run"
    elif best_strat == "MOMENTUM": return "[UPTREND] Strong Uptrend"
    elif best_strat == "MULTITIMEFRAME": return "[INFO] Trend Confirmation"
    elif best_strat == "GRID": return "[SIDEWAYS] Ranging Area"
    elif best_strat == "MEAN_REVERSAL": return "[DIP] Reversal Zone"
    else: return "[INFO] Unclear"

# =============================================================================
# 3. CORE LOGIC (STRATEGY & SCANNING)
# =============================================================================

def find_best_strategy_for_symbol(engine, symbol, mode="AUTO", manual_strat=None, manual_tf=None, manual_per=None):
    """
    Core Logic: Mencari strategi terbaik atau menjalankan strategi manual.
    Digunakan oleh Scanner API dan Bot Scheduler.
    """
    if mode == 'MANUAL':
        # --- LOGIKA MANUAL ---
        # Fetch Data Max agar indikator akurat (engine akan handle cache)
        df_raw = engine.fetch_data(symbol, requested_period="max", interval=manual_tf)
        
        if df_raw is not None and len(df_raw) > 30:
            _, _, metrics, _ = engine.run_backtest(df_raw, manual_strat, requested_period=manual_per)
            signal_info = engine.get_signal_advice(df_raw, manual_strat)
            rr_long = calculate_rr_string(signal_info['price'], signal_info['setup_long']['tp'], signal_info['setup_long']['sl'])
            
            return {
                "symbol": symbol, "strategy": manual_strat, "timeframe": manual_tf, "period": manual_per,
                "win_rate": metrics['win_rate'], "profit": metrics['net_profit'],
                "trades": metrics['total_trades'], "signal_data": signal_info,
                "rr_ratio": rr_long, "mode": "MANUAL"
            }
        return None

    else:
        # --- LOGIKA AUTO (SCANNER) ---
        strategies = [
            # KELOMPOK A: BASIC
            "MOMENTUM", "MEAN_REVERSAL", "GRID", "MULTITIMEFRAME",
            # KELOMPOK B: PRO (Risk Managed)
            "MOMENTUM_PRO", "MEAN_REVERSAL_PRO", "GRID_PRO", "MULTITIMEFRAME_PRO",
            # BONUS
            "MIX_STRATEGY", "MIX_STRATEGY_PRO"
        ]
        
        timeframes = ["1h", "4h", "1d"]
        periods = ["6mo", "1y"] 
        
        best_config = None
        best_score = -999999999
        
        for tf in timeframes:
            # Fetch Max data sekali per timeframe untuk efisiensi
            df_raw = engine.fetch_data(symbol, requested_period="max", interval=tf) 
            if df_raw is None or len(df_raw) < 50: continue

            for per in periods:
                for strat in strategies:
                    # === CACHE-FIRST LOGIC ===
                    cached = engine._get_cached_result(symbol, tf, per, strat)
                    
                    if cached:
                        # Cache HIT — skip backtest entirely
                        print(f"   [CACHE HIT] {symbol} | {tf} | {per} | {strat}")
                        metrics = cached  # cached sudah berisi dict metrics
                        signal_info = cached.get('signal_data', {})
                        rr_long = cached.get('rr_ratio', 'N/A')
                    else:
                        # Cache MISS — harus hitung
                        print(f"   [CACHE MISS] {symbol} | {tf} | {per} | {strat}")
                        _, _, metrics, _ = engine.run_backtest(df_raw, strat, requested_period=per)
                        signal_info = engine.get_signal_advice(df_raw, strat)
                        rr_long = calculate_rr_string(signal_info['price'], signal_info['setup_long']['tp'], signal_info['setup_long']['sl'])
                        
                        # Save ke cache untuk next time
                        engine._save_cache_result(symbol, tf, per, strat, metrics, signal_info, rr_long)
                    
                    if metrics.get('total_trades', 0) < 3: continue 
                    
                    # Score Logic: WinRate * Profit
                    score = metrics.get('win_rate', 0) * metrics.get('net_profit', 0)
                    
                    # Boost Score untuk Strategy PRO (Risk Managed lebih disukai)
                    if "_PRO" in strat:
                        score *= 1.1 

                    if score > best_score:
                        best_score = score
                        best_config = {
                            "symbol": symbol, "strategy": strat, "timeframe": tf, "period": per,
                            "win_rate": metrics.get('win_rate', 0), "profit": metrics.get('net_profit', 0),
                            "trades": metrics.get('total_trades', 0), "signal_data": signal_info,
                            "rr_ratio": rr_long, "mode": "AUTO", "max_dd": metrics.get('max_drawdown', 0)
                        }
        return best_config

# =============================================================================
# 4. BOT BACKGROUND TASK (SCHEDULER & REAL EXECUTION)
# =============================================================================

def check_market_signals():
    """
    Bot Loop Utama:
    1. Load Watchlist
    2. Scan Market (Validasi Sinyal)
    3. Hitung Risk (Position Sizing)
    4. Eksekusi Order (Via CCXT)
    5. Kirim Alert Telegram
    """
    watchlist = load_watchlist_from_db() 
    if not watchlist: return
    
    print(f"[{datetime.now().strftime('%H:%M')}] AI Bot: Running Heavy Logic on Watchlist...")
    
    # Inisialisasi Engine dengan API KEY untuk eksekusi
    engine = TradingEngine(api_key=BINANCE_API_KEY, api_secret=BINANCE_SECRET_KEY, initial_capital=1000)
    
    for item in watchlist:
        try:
            # 1. CARI KONFIGURASI TERBAIK
            config = find_best_strategy_for_symbol(
                engine, 
                item['symbol'], 
                mode=item.get('mode', 'AUTO'),
                manual_strat=item.get('strategy'),
                manual_tf=item.get('timeframe'),
                manual_per=item.get('period')
            )
            
            if config:
                # 2. VALIDASI SIGNAL
                df_raw = engine.fetch_data(config['symbol'], requested_period="max", interval=config['timeframe'])
                if df_raw is None: continue

                # Cek Backtest 1 bulan terakhir
                df_res, markers, _, _ = engine.run_backtest(df_raw, config['strategy'], requested_period="1mo")
                
                if markers:
                    last_marker = markers[-1]
                    last_candle_time = int(df_res.iloc[-1]['time'].timestamp())
                    
                    # Trigger jika signal baru muncul di candle terakhir yang close
                    if last_marker['time'] >= last_candle_time:
                        signal_type = last_marker['text'] # BUY / SELL
                        price = df_res.iloc[-1]['close']
                        
                        setup = config['signal_data']['setup_long'] if signal_type == "BUY" else config['signal_data']['setup_short']
                        tp = setup['tp']
                        sl = setup['sl']
                        
                        rr_str = calculate_rr_string(price, tp, sl)
                        mode_icon = "[MANUAL]" if config.get('mode') == 'MANUAL' else "[AUTO]"

                        # --- LOGIKA EKSEKUSI (TESTNET TRADE) ---
                        exec_msg = ""
                        if config.get('mode') == 'AUTO':
                            # Hitung Lot Size Aman (Risk 1% dari Equity)
                            qty = engine.calculate_position_size(config['symbol'], price, sl, risk_per_trade_pct=0.01)
                            
                            if qty > 0:
                                side = 'buy' if signal_type == "BUY" else 'sell'
                                
                                # --- RISK CHECK (Phase 3) ---
                                risk_ok, risk_reason = risk_manager.pre_trade_risk_check(engine, config['symbol'], side, qty, price)
                                if not risk_ok:
                                    exec_msg = f"\n[BLOCKED BY RISK]: {risk_reason}"
                                    print(f"Risk blocked {config['symbol']}: {risk_reason}")
                                else:
                                    order = engine.execute_order(config['symbol'], side, qty)
                                    if order:
                                        exec_msg = f"\n[EXECUTED TESTNET]: {side.upper()} {qty:.5f}"
                                        engine._log_trade(
                                            symbol=config['symbol'],
                                            side=side,
                                            qty=qty,
                                            price=price,
                                            strategy=config['strategy'],
                                            timeframe=config['timeframe'],
                                            order_id=order.get('id', ''),
                                            status='FILLED',
                                            notes=f"TP={tp:.2f} SL={sl:.2f} RR={rr_str}"
                                        )
                                    else:
                                        exec_msg = "\n[EXEC FAILED]: Check Logs."
                            else:
                                exec_msg = "\n[SKIPPED]: High Risk / Low Balance."

                        # Kirim Telegram Alert
                        msg = (
                            f"SIGNAL ALERT: {config['symbol']}\n"
                            f"Action: {signal_type}\n"
                            f"Price: ${price:,.2f}\n"
                            f"{mode_icon} Mode: {config.get('mode', 'AUTO')}\n"
                            f"Strategy: {config['strategy']}\n"
                            f"Timeframe: {config['timeframe']}\n"
                            f"TP: ${tp:,.2f}\n"
                            f"SL: ${sl:,.2f}\n"
                            f"R:R: {rr_str}\n"
                            f"{exec_msg}\n"
                            f"QuantBot System"
                        )
                        send_telegram_alert(msg)
                        print(f"Alert sent for {config['symbol']}")

        except Exception as e:
            print(f"Error checking {item['symbol']}: {e}")

# =============================================================================
# 5. LIFESPAN & API SETUP (SCHEDULER)
# =============================================================================

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    print("System Startup: Sending Telegram Notification...")
    send_telegram_alert("SYSTEM ACTIVE [TESTNET]\n\nBot QuantTrade is running on Binance Testnet (demo money).")
    
    scheduler = BackgroundScheduler()
    # Interval 15 menit (sesuai timeframe terendah yang umum)
    scheduler.add_job(check_market_signals, 'interval', minutes=15)
    
    # Portfolio Snapshot setiap 5 menit
    portfolio_engine.init_portfolio_tables()
    risk_manager.init_risk_tables()
    init_scan_cache_table()
    def _take_portfolio_snapshot():
        try:
            eng = TradingEngine(api_key=BINANCE_API_KEY, api_secret=BINANCE_SECRET_KEY)
            portfolio_engine.take_snapshot(eng)
        except Exception as e:
            print(f"Snapshot scheduler error: {e}")
    scheduler.add_job(_take_portfolio_snapshot, 'interval', minutes=5)
    # Take initial snapshot on startup
    _take_portfolio_snapshot()
    
    scheduler.start()
    
    yield
    
    print("System Shutdown: Sending Telegram Notification...")
    send_telegram_alert("SYSTEM INACTIVE\n\nBot QuantTrade has been stopped.")
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# 6. DATA MODELS
# =============================================================================

class StrategyRequest(BaseModel):
    symbol: str
    strategy: str
    capital: float
    timeframe: str = "1d"
    period: str = "1y"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    direction: str = "LONG"  # "LONG" or "SHORT"

class ScanRequest(BaseModel):
    sector: str
    timeframe: str = "1d"
    period: str = "1y" 
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    capital: float = 10000
    force_reload: bool = False # Parameter Baru untuk Reset Data di DB

class WatchlistItem(BaseModel):
    symbol: str
    mode: Literal["AUTO", "MANUAL"] = "AUTO"
    strategy: Optional[str] = "MOMENTUM"
    timeframe: Optional[str] = "1d"
    period: Optional[str] = "1y"

class SingleBacktestRequest(BaseModel):
    symbol: str
    strategy: str
    capital: float = 1000.0
    timeframe: str = "1d"
    period: str = "1y"

# =============================================================================
# 7. SECTORS CONFIGURATION
# =============================================================================

# --- BOT STATUS & TRADE HISTORY ENDPOINTS ---

@app.get("/api/bot-status")
def get_bot_status():
    """Return live bot statistics from trade_log."""
    engine = TradingEngine(api_key=BINANCE_API_KEY, api_secret=BINANCE_SECRET_KEY)
    status = engine._get_bot_status()
    
    # Tambah info balance dari Testnet
    try:
        bal = engine.exchange.fetch_balance()
        status["balance"] = {
            "total_usdt": round(bal.get('USDT', {}).get('total', 0), 2),
            "free_usdt": round(bal.get('USDT', {}).get('free', 0), 2),
            "used_usdt": round(bal.get('USDT', {}).get('used', 0), 2),
        }
    except Exception as e:
        print(f"⚠️ Balance fetch error: {e}")
        status["balance"] = {"total_usdt": 0, "free_usdt": 0, "used_usdt": 0}
    
    return status

@app.get("/api/trade-history")
def get_trade_history(limit: int = 50):
    """Return paginated trade history from trade_log."""
    engine = TradingEngine()
    return {"trades": engine._get_trade_history(limit=limit)}

@app.get("/api/portfolio")
def get_portfolio():
    """Return portfolio summary from Testnet."""
    engine = TradingEngine(api_key=BINANCE_API_KEY, api_secret=BINANCE_SECRET_KEY)
    
    try:
        bal = engine.exchange.fetch_balance()
        
        # Filter non-zero balances
        positions = []
        for currency, data in bal.items():
            if isinstance(data, dict) and data.get('total', 0) > 0 and currency not in ['info', 'timestamp', 'datetime', 'free', 'used', 'total']:
                positions.append({
                    "currency": currency,
                    "total": round(data.get('total', 0), 8),
                    "free": round(data.get('free', 0), 8),
                    "used": round(data.get('used', 0), 8),
                })
        
        # Sort by total descending
        positions.sort(key=lambda x: x['total'], reverse=True)
        
        return {
            "mode": "TESTNET",
            "positions": positions[:20],  # Top 20
            "usdt_balance": round(bal.get('USDT', {}).get('total', 0), 2),
            "usdt_free": round(bal.get('USDT', {}).get('free', 0), 2),
        }
    except Exception as e:
        print(f"⚠️ Portfolio Error: {e}")
        raise HTTPException(status_code=500, detail=f"Portfolio fetch failed: {e}")


# --- PORTFOLIO ENGINE ENDPOINTS (Phase 2) ---

@app.get("/api/portfolio/summary")
def get_portfolio_summary():
    """Return comprehensive portfolio summary with allocation breakdown."""
    engine = TradingEngine(api_key=BINANCE_API_KEY, api_secret=BINANCE_SECRET_KEY)
    return portfolio_engine.get_portfolio_summary(engine)

@app.get("/api/portfolio/equity-curve")
def get_equity_curve(days: int = 30):
    """Return equity curve data for charting."""
    return {"curve": portfolio_engine.get_equity_curve(days=days)}

@app.get("/api/portfolio/daily-pnl")
def get_daily_pnl(days: int = 30):
    """Return daily PnL series for bar chart."""
    return {"daily_pnl": portfolio_engine.get_daily_pnl(days=days)}


# --- RISK MANAGEMENT ENDPOINTS (Phase 3) ---

@app.get("/api/risk-dashboard")
def get_risk_dashboard():
    """Return current risk metrics, config, and recent alerts."""
    engine = TradingEngine(api_key=BINANCE_API_KEY, api_secret=BINANCE_SECRET_KEY)
    return risk_manager.get_risk_dashboard(engine)

@app.post("/api/risk-config")
def update_risk_config(config: dict):
    """Update risk management parameters."""
    success = risk_manager.update_risk_config(config)
    if success:
        return {"status": "ok", "config": risk_manager.get_risk_config()}
    return {"status": "error", "message": "Failed to update config"}

@app.get("/api/risk-alerts")
def get_risk_alerts(limit: int = 50):
    """Return recent risk alerts."""
    return {"alerts": risk_manager.get_risk_alerts(limit=limit)}


# --- FUND ANALYTICS ENDPOINTS (Phase 4) ---

@app.get("/api/fund/performance")
def get_fund_performance():
    """Return comprehensive fund performance metrics (Sharpe, Sortino, etc.)."""
    return fund_analytics.get_fund_performance()


# --- ELITE GEMS SCANNER ENDPOINT (Phase 5) ---

@app.get("/api/scanner/elite")
async def get_elite_gems(modes: str = "LONG"):
    """
    Scan top coins for consistent growth (High R^2 Equity Curve).
    modes: Comma separated string, e.g. "LONG,SHORT"
    Returns ranked list of 'Elite Gems'.
    """
    # Parse modes
    allowed_modes = [m.strip().upper() for m in modes.split(',') if m.strip()]
    if not allowed_modes: allowed_modes = ["LONG"]

    # Combine ALL sectors for a comprehensive scan
    target_coins = []
    for sector_list in SECTORS.values():
        target_coins.extend(sector_list)
    
    # Remove duplicates and take top 30 to avoid timeout/rate-limits
    target_coins = list(set(target_coins))[:30] 
    
    scanner = BacktestEngine()
    results = await scanner.scan_market(target_coins, allowed_modes=allowed_modes)
    
    return {"status": "ok", "gems": results}


# --- ANOMALY SCANNER ENDPOINT (Objective 1) ---

class AnomalyScanRequest(BaseModel):
    symbol: str
    include_volume: bool = True  # Needs OHLCV data
    include_orderbook: bool = True  # Live order book
    include_whale: bool = True  # Live trade analysis

@app.post("/api/anomaly-scan")
def anomaly_scan(req: AnomalyScanRequest):
    """
    Scan a symbol for market anomalies:
    1. Volume Spike (2x 20-period SMA)
    2. Order Book Imbalance (Bids > 1.5x Asks)
    3. Whale/Iceberg Activity (Dynamic threshold)
    """
    try:
        engine = TradingEngine()
        scanner = AnomalyScanner(engine.exchange)
        
        # Fetch OHLCV for volume analysis
        df = None
        if req.include_volume:
            df = engine.fetch_data(req.symbol, requested_period="3mo", interval="1h")
            if df is not None:
                df = engine.prepare_indicators(df)
        
        # Run full scan
        result = scanner.full_scan(req.symbol, df=df)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Anomaly scan error: {e}")


@app.get("/api/anomaly-scan")
def anomaly_scan_get(symbol: str):
    """GET version of anomaly scan for quick single-symbol queries."""
    try:
        engine = TradingEngine()
        scanner = AnomalyScanner(engine.exchange)
        df = engine.fetch_data(symbol, requested_period="3mo", interval="1h")
        if df is not None:
            df = engine.prepare_indicators(df)
        result = scanner.full_scan(symbol, df=df)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Anomaly scan error: {e}")


@app.post("/api/batch-anomaly-scan")
def batch_anomaly_scan(req: dict):
    """
    Scan multiple symbols for anomalies at once.
    Body: { "symbols": ["BTC-USDT", "ETH-USDT", ...] }
    Returns aggregated results sorted by severity.
    """
    symbols = req.get("symbols", [])
    if not symbols:
        raise HTTPException(status_code=400, detail="No symbols provided")
    
    engine = TradingEngine()
    scanner = AnomalyScanner(engine.exchange)
    results = []
    
    for sym in symbols[:20]:  # Cap at 20 to prevent timeout
        try:
            df = engine.fetch_data(sym, requested_period="3mo", interval="1h")
            if df is not None:
                df = engine.prepare_indicators(df)
            scan_result = scanner.full_scan(sym, df=df)
            scan_result["symbol"] = sym
            results.append(scan_result)
        except Exception as e:
            print(f"Batch anomaly scan error for {sym}: {e}")
            results.append({"symbol": sym, "error": str(e)})
    
    # Sort by number of detected anomalies (descending)
    def _score(r):
        s = 0
        if r.get("volume_spike", {}).get("detected"): s += 35
        if r.get("order_book", {}).get("detected"): s += 35
        if r.get("whale_activity", {}).get("detected"): s += 30
        return s
    
    results.sort(key=_score, reverse=True)
    return {"results": results}


# --- MACRO INTELLIGENCE ENDPOINT (Objective 5) ---

# Singleton instance — preserves the 5-min internal cache across requests
_macro_instance = MacroIntelligence()

@app.get("/api/macro-intelligence")
def get_macro_intelligence():
    """
    Automated Top-Down Market Analysis.
    Returns market regime (BULLISH/BEARISH/NEUTRAL) with indicator breakdown.
    """
    try:
        return _macro_instance.evaluate_regime()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Macro intelligence error: {e}")

@app.get("/api/macro-intelligence/direction")
def get_macro_direction():
    """
    Quick endpoint: Returns recommended trade direction based on macro regime.
    Used by the strategy engine to filter signal direction.
    """
    try:
        direction = _macro_instance.get_regime_direction()
        return {"direction": direction}
    except Exception as e:
        return {"direction": "BOTH", "error": str(e)}


# --- GLOBAL MARKET ANALYSIS ENDPOINTS ---

_global_market_instance = GlobalMarketAnalyzer()

@app.get("/api/global-market")
def get_global_market():
    """
    Full cross-asset global market analysis.
    Returns: asset price changes, regime classification, correlation matrix, insights.
    """
    try:
        return _global_market_instance.get_full_analysis()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Global market error: {e}")

@app.get("/api/global-market/heatmap")
def get_global_heatmap():
    """
    Simplified heatmap data: just asset names + % changes for quick rendering.
    """
    try:
        assets = _global_market_instance.get_all_assets_data()
        heatmap = []
        for key, data in assets.items():
            heatmap.append({
                "key": key,
                "label": data["label"],
                "category": data["category"],
                "icon": data["icon"],
                "color": data["color"],
                "price": data["current_price"],
                "changes": data["changes"]
            })
        return {"heatmap": heatmap}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Heatmap error: {e}")


# --- DUAL BACKTEST ENDPOINT (Objective 3: PnL Segmentation) ---

@app.post("/api/run-dual-backtest")
def run_dual_backtest(req: StrategyRequest):
    """
    Run LONG + SHORT backtests simultaneously.
    Returns segmented PnL: pnl_long, pnl_short, pnl_combined.
    """
    engine = TradingEngine(initial_capital=req.capital)
    df_raw = engine.fetch_data(
        req.symbol, requested_period="max", interval=req.timeframe,
        start_date=req.start_date, end_date=req.end_date
    )
    
    if df_raw is None or len(df_raw) < 30:
        raise HTTPException(status_code=404, detail=f"Data kosong {req.symbol}.")
    
    result = engine.run_dual_backtest(
        df_raw, req.strategy, requested_period=req.period,
        start_date=req.start_date, end_date=req.end_date
    )
    
    return {
        "status": "success",
        "symbol": req.symbol,
        "strategy": req.strategy,
        **result
    }


SECTORS = {
    # ===================== TIER 1: CORE MARKET =====================
    
    # Big Cap & Layer 1 — Market Leaders, Highest Liquidity
    "BIG_CAP": [
        "BTC-USDT", "ETH-USDT", "SOL-USDT", "BNB-USDT", "XRP-USDT",
        "ADA-USDT", "AVAX-USDT", "DOT-USDT", "TRX-USDT", "LINK-USDT",
        "TON-USDT", "SUI-USDT", "ATOM-USDT", "NEAR-USDT", "APT-USDT"
    ],
    
    # AI & Data Economy — High Narrative Momentum
    "AI_COINS": [
        "FET-USDT", "RENDER-USDT", "ICP-USDT", "GRT-USDT", "TAO-USDT",
        "WLD-USDT", "ARKM-USDT", "THETA-USDT", "AIOZ-USDT", "AI-USDT"
    ],
    
    # Meme Coins — Extreme Volatility, Grid & Momentum Friendly
    "MEME_COINS": [
        "DOGE-USDT", "SHIB-USDT", "PEPE-USDT", "WIF-USDT", "BONK-USDT",
        "FLOKI-USDT", "BOME-USDT", "TRUMP-USDT", "NEIRO-USDT", "1000SATS-USDT"
    ],
    
    # ===================== TIER 2: SECTOR ROTATION =====================
    
    # DeFi Bluechips — Yield, Lending, DEX
    "DEFI": [
        "UNI-USDT", "AAVE-USDT", "MKR-USDT", "LDO-USDT", "CRV-USDT",
        "COMP-USDT", "SNX-USDT", "PENDLE-USDT", "ENA-USDT", "DYDX-USDT"
    ],
    
    # Layer 2 & ZK Scaling — Infrastructure Growth
    "LAYER_2": [
        "POL-USDT", "ARB-USDT", "OP-USDT", "IMX-USDT", "STRK-USDT",
        "MANTA-USDT", "ZK-USDT", "METIS-USDT", "BLAST-USDT", "MODE-USDT"
    ],
    
    # Gaming & Metaverse — Cyclical Pump Potential
    "GAMING": [
        "AXS-USDT", "SAND-USDT", "GALA-USDT", "ENJ-USDT", "PIXEL-USDT",
        "PORTAL-USDT", "RON-USDT", "YGG-USDT", "SUPER-USDT", "ALICE-USDT"
    ],
    
    # Real World Assets (RWA) — Emerging Narrative
    "RWA": [
        "ONDO-USDT", "OM-USDT", "PENDLE-USDT", "MKR-USDT", "RSR-USDT",
        "DUSK-USDT", "CELO-USDT", "POLYX-USDT", "TRU-USDT", "MPL-USDT"
    ],
    
    # ===================== TIER 3: ADVANCED =====================
    
    # Infrastructure & Oracle — Backend of Crypto
    "INFRA": [
        "LINK-USDT", "FIL-USDT", "AR-USDT", "STORJ-USDT", "PYTH-USDT",
        "W-USDT", "JTO-USDT", "TIA-USDT", "SEI-USDT", "INJ-USDT"
    ],
    
    # Privacy & ZK Tech
    "PRIVACY_ZK": [
        "ZEC-USDT", "XMR-USDT", "ROSE-USDT", "SCRT-USDT", "MINA-USDT",
        "ZK-USDT", "STRK-USDT", "DUSK-USDT", "MASK-USDT", "NMR-USDT"
    ],
    
    # Hot & New Listings — High Alpha Potential
    "NEW_LISTINGS": [
        "EIGEN-USDT", "ZRO-USDT", "LISTA-USDT", "REZ-USDT", "BB-USDT",
        "NOT-USDT", "IO-USDT", "W-USDT", "ETHFI-USDT", "AEVO-USDT"
    ],
    
    # Exchange Tokens — Correlated with Exchange Revenue
    "CEX_TOKENS": [
        "BNB-USDT", "OKB-USDT", "GT-USDT", "CRO-USDT", "KCS-USDT",
        "MX-USDT", "CAKE-USDT", "DEXE-USDT", "JOE-USDT", "SUSHI-USDT"
    ],
    
    # Yield & Staking — Passive Income Plays
    "YIELD_STAKING": [
        "PENDLE-USDT", "ENA-USDT", "LDO-USDT", "RPL-USDT", "SSV-USDT",
        "ANKR-USDT", "ETHFI-USDT", "LQTY-USDT", "FXS-USDT", "SD-USDT"
    ],
}


# =============================================================================
# 8. API ENDPOINTS
# =============================================================================

@app.get("/")
def read_root():
    return {"status": "Backend Active", "bot_status": "Monitoring", "db_status": "Connected"}

@app.get("/api/watchlist")
def get_watchlist():
    conn = get_db_connection()
    if not conn: raise HTTPException(status_code=500, detail="Database Error")
    
    cur = conn.cursor()
    cur.execute("SELECT symbol, mode, strategy, timeframe, period FROM watchlist ORDER BY created_at DESC")
    items = cur.fetchall()
    cur.close()
    conn.close()
    
    results = []
    engine = TradingEngine(initial_capital=1000)
    
    for item in items:
        try:
            config = find_best_strategy_for_symbol(
                engine, 
                item['symbol'], 
                mode=item['mode'], 
                manual_strat=item.get('strategy'), 
                manual_tf=item.get('timeframe'), 
                manual_per=item.get('period')
            )
            if config:
                growth_pct = (config['profit'] / 1000) * 100
                results.append({
                    "symbol": item['symbol'],
                    "mode": item['mode'],
                    "strategy": config['strategy'],
                    "timeframe": config['timeframe'],
                    "period": config['period'],
                    "growth_usd": config['profit'],
                    "growth_pct": round(growth_pct, 2),
                    "win_rate": config['win_rate']
                })
        except Exception as e:
            print(f"Error pada {item['symbol']}: {e}")
            
    return results

@app.post("/api/watchlist")
def add_watchlist(item: WatchlistItem):
    conn = get_db_connection()
    if not conn: raise HTTPException(status_code=500, detail="Database error")
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO watchlist (symbol, mode, strategy, timeframe, period) 
               VALUES (%s, %s, %s, %s, %s)""",
            (item.symbol.upper(), item.mode, item.strategy, item.timeframe, item.period)
        )
        conn.commit()
    except psycopg2.IntegrityError:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Simbol sudah ada di watchlist")
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
        conn.close()
    return {"status": "success", "message": f"{item.symbol} berhasil ditambahkan"}

@app.delete("/api/watchlist/{symbol}")
def delete_watchlist(symbol: str):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM watchlist WHERE symbol = %s", (symbol.upper(),))
    conn.commit()
    cur.close()
    conn.close()
    return {"status": "deleted"}

@app.post("/api/run-backtest")
def run_backtest(req: StrategyRequest):
    engine = TradingEngine(initial_capital=req.capital)
    df_raw = engine.fetch_data(req.symbol, requested_period="max", interval=req.timeframe, start_date=req.start_date, end_date=req.end_date)
    
    if df_raw is None or len(df_raw) < 30: raise HTTPException(status_code=404, detail=f"Data kosong {req.symbol}.")

    # Pass direction to run_backtest
    direction = req.direction.upper() if req.direction else "LONG"
    df_res, markers, metrics, equity_data = engine.run_backtest(df_raw, req.strategy, requested_period=req.period, start_date=req.start_date, end_date=req.end_date, direction=direction)
    
    chart_data = []
    line1, line2, line3 = [], [], []
    for index, row in df_res.iterrows():
        if pd.isna(row['close']): continue
        t = int(row['time'].timestamp())
        chart_data.append({ "time": t, "open": row['open'], "high": row['high'], "low": row['low'], "close": row['close'] })
        
        base_strat = req.strategy.replace("_PRO", "")
        
        if base_strat == "MOMENTUM" or (req.strategy == "MIX_STRATEGY"):
            line1.append({"time": t, "value": row['sma_fast']})
            line2.append({"time": t, "value": row['sma_slow']})
        elif base_strat in ["MEAN_REVERSAL", "GRID"]:
            line1.append({"time": t, "value": row['bb_upper'] if base_strat == "MEAN_REVERSAL" else row['grid_top']})
            line2.append({"time": t, "value": row['bb_lower'] if base_strat == "MEAN_REVERSAL" else row['grid_bottom']})
            if base_strat == "GRID": line3.append({"time": t, "value": row['grid_mid']})
        elif base_strat == "MULTITIMEFRAME":
            line3.append({"time": t, "value": row['ema_200']}) 

    return { "status": "success", "chart_data": chart_data, "equity_curve": equity_data, "indicators": {"line1": line1, "line2": line2, "line3": line3}, "markers": markers, "metrics": metrics, "direction": direction }

@app.post("/api/compare-strategies")
def compare_strategies(req: StrategyRequest):
    engine = TradingEngine(initial_capital=req.capital)
    df_raw = engine.fetch_data(req.symbol, requested_period="max", interval=req.timeframe, start_date=req.start_date, end_date=req.end_date)
    
    if df_raw is None or len(df_raw) < 30: raise HTTPException(status_code=404, detail="Data Error")

    direction = req.direction.upper() if req.direction else "LONG"
    strategies = [
        "MOMENTUM", "MEAN_REVERSAL", "GRID", "MULTITIMEFRAME",
        "MOMENTUM_PRO", "MEAN_REVERSAL_PRO", "GRID_PRO", "MULTITIMEFRAME_PRO",
        "MIX_STRATEGY", "MIX_STRATEGY_PRO"
    ]

    # --- PARALLEL EXECUTION for Speed ---
    def _run_single(strat):
        cache_key = f"{strat}_{direction}"
        cached = engine._get_cached_result(req.symbol, req.timeframe, req.period, cache_key)
        if cached:
            return strat, cached
        else:
            _, _, metrics, _ = engine.run_backtest(df_raw.copy(), strat, requested_period=req.period, direction=direction)
            engine._save_cache_result(req.symbol, req.timeframe, req.period, cache_key, metrics)
            return strat, metrics

    results = []
    buy_hold_return = 0

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(_run_single, strat): strat for strat in strategies}
        for future in futures:
            strat, metrics = future.result()
            results.append({
                "strategy": strat,
                "direction": direction,
                "net_profit": metrics.get('net_profit', 0),
                "win_rate": metrics.get('win_rate', 0),
                "trades": metrics.get('total_trades', 0),
                "sharpe": metrics.get('sharpe_ratio', 0),
                "max_dd": metrics.get('max_drawdown', 0),
                "is_hold": False
            })
            buy_hold_return = metrics.get('buy_hold_return', 0)

    hold_val = req.capital * (buy_hold_return / 100)
    results.append({ "strategy": "HOLD ONLY", "direction": direction, "net_profit": round(hold_val, 2), "win_rate": 100, "trades": 1, "sharpe": 0, "max_dd": 0, "is_hold": True })
    results.sort(key=lambda x: x['net_profit'], reverse=True)
    return {"symbol": req.symbol, "direction": direction, "comparison": results}

# =============================================================================
# SCAN CACHE — Persist results to DB for instant startup
# =============================================================================

def init_scan_cache_table():
    """Create scan_cache table if not exists."""
    conn = get_db_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS scan_cache (
                sector TEXT PRIMARY KEY,
                results JSONB DEFAULT '[]',
                elite_signals JSONB DEFAULT '[]',
                scanned_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        conn.commit()
        print("[INFO] Scan cache table initialized")
    except Exception as e:
        print(f"[ERROR] init_scan_cache_table: {e}")
    finally:
        conn.close()

def save_scan_results(sector, results, elite_signals):
    """Save scan results to DB cache for instant reload."""
    conn = get_db_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO scan_cache (sector, results, elite_signals, scanned_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (sector) DO UPDATE SET
                results = EXCLUDED.results,
                elite_signals = EXCLUDED.elite_signals,
                scanned_at = NOW()
        """, (sector, json.dumps(results), json.dumps(elite_signals)))
        conn.commit()
    except Exception as e:
        print(f"[ERROR] save_scan_results: {e}")
    finally:
        conn.close()

def load_last_scan_results():
    """Load all cached scan results from DB."""
    conn = get_db_connection()
    if not conn: return {}
    try:
        cur = conn.cursor()
        cur.execute("SELECT sector, results, elite_signals, scanned_at FROM scan_cache ORDER BY scanned_at DESC")
        rows = cur.fetchall()
        return rows
    except Exception as e:
        print(f"[ERROR] load_last_scan_results: {e}")
        return []
    finally:
        conn.close()

def _scan_single_symbol(sym, capital, force_reload=False):
    """Scan a single symbol — designed for parallel execution."""
    try:
        engine = TradingEngine(initial_capital=capital)
        if force_reload:
            engine.fetch_data(sym, requested_period="1mo", interval="1d", force_reload=True)
        best_config = find_best_strategy_for_symbol(engine, sym, mode="AUTO")
        if best_config:
            best_config['reason'] = analyze_market_reason(best_config['strategy'], best_config['win_rate'])
            return best_config
    except Exception as e:
        print(f"[ERROR] Scanning {sym}: {e}")
    return None

def _scan_sector_parallel(sector_id, capital, force_reload=False):
    """Scan all symbols in a sector using parallel symbol processing."""
    symbols = SECTORS.get(sector_id, [])
    if not symbols:
        return sector_id, [], []
    
    print(f"\n🚀 PARALLEL SCAN: {sector_id} ({len(symbols)} symbols)")
    start = time.time()
    
    scan_results = []
    elite_signals = []
    
    # Process symbols in parallel (max 3 concurrent)
    futures = {}
    for sym in symbols:
        future = _symbol_executor.submit(_scan_single_symbol, sym, capital, force_reload)
        futures[future] = sym
    
    for future in as_completed(futures):
        sym = futures[future]
        try:
            result = future.result(timeout=120)  # 2 min timeout per symbol
            if result:
                scan_results.append(result)
                if result.get('win_rate', 0) >= 60 and result.get('trades', 0) >= 15:
                    elite_signals.append(result)
                print(f"  ✅ {sym} done")
            else:
                print(f"  ⚪ {sym} no viable strategy")
        except Exception as e:
            print(f"  ❌ {sym} error: {e}")
    
    elapsed = time.time() - start
    print(f"✅ {sector_id} completed in {elapsed:.1f}s ({len(scan_results)} results)")
    
    # Save to cache
    save_scan_results(sector_id, scan_results, elite_signals)
    
    return sector_id, scan_results, elite_signals


@app.post("/api/scan-market")
def scan_market(req: ScanRequest):
    """
    Endpoint Scan with PARALLEL symbol processing.
    Supports Incremental Loading & Progress Bar.
    """
    if "-" in req.sector and req.sector not in SECTORS: 
        symbols = [req.sector]
    elif req.sector == "ALL":
        symbols = []
        for s in SECTORS.values(): symbols.extend(s)
        symbols = list(set(symbols))[:20]
    else:
        symbols = SECTORS.get(req.sector, [])
    
    if not symbols: raise HTTPException(status_code=404, detail="Sektor/Simbol tidak ditemukan")
    
    print(f"🚀 STARTING SCAN: {req.sector} ({len(symbols)} symbols)")
    scan_results = []
    elite_signals = []
    
    # Parallel symbol processing
    futures = {}
    for sym in symbols:
        future = _symbol_executor.submit(_scan_single_symbol, sym, req.capital, req.force_reload)
        futures[future] = sym
    
    for future in as_completed(futures):
        sym = futures[future]
        try:
            result = future.result(timeout=120)
            if result:
                scan_results.append(result)
                if result.get('win_rate', 0) >= 60 and result.get('trades', 0) >= 15:
                    elite_signals.append(result)
        except Exception as e:
            print(f"Error scanning {sym}: {e}")
    
    elite_signals.sort(key=lambda x: (x['win_rate'], x['trades']), reverse=True)
    
    # Save to cache for instant reload
    save_scan_results(req.sector, scan_results, elite_signals)
    
    return { "sector": req.sector, "results": scan_results, "elite_signals": elite_signals[:10] }


@app.post("/api/scan-all")
def scan_all_sectors(req: ScanRequest):
    """
    Batch scan ALL sectors in parallel using ThreadPoolExecutor.
    Returns complete results for all sectors in one response.
    ~3-4x faster than sequential scanning.
    """
    start_time = time.time()
    sector_ids = list(SECTORS.keys())
    all_results = {}
    all_elites = []
    
    print(f"\n{'='*60}")
    print(f"🚀🚀🚀 PARALLEL SCAN ALL: {len(sector_ids)} sectors")
    print(f"{'='*60}")
    
    # Process sectors in parallel (max 4 concurrent)
    futures = {}
    for sector_id in sector_ids:
        future = _scan_executor.submit(
            _scan_sector_parallel, sector_id, req.capital, req.force_reload
        )
        futures[future] = sector_id
    
    for future in as_completed(futures):
        sector_id = futures[future]
        try:
            _, results, elites = future.result(timeout=600)  # 10 min timeout per sector
            # Find the sector display name
            sector_name = sector_id
            for s in [{"id": "BIG_CAP", "name": "Big Cap & L1"}, {"id": "AI_COINS", "name": "AI Narratives"},
                      {"id": "MEME_COINS", "name": "Meme Coins"}, {"id": "DEFI", "name": "DeFi Bluechips"},
                      {"id": "LAYER_2", "name": "Layer 2 & ZK"}, {"id": "GAMING", "name": "Gaming & Metaverse"},
                      {"id": "RWA", "name": "Real World Assets"}, {"id": "INFRA", "name": "Infrastructure"},
                      {"id": "PRIVACY_ZK", "name": "Privacy & ZK"}, {"id": "NEW_LISTINGS", "name": "Hot & New"},
                      {"id": "CEX_TOKENS", "name": "Exchange Tokens"}, {"id": "YIELD_STAKING", "name": "Yield & Staking"}]:
                if s["id"] == sector_id:
                    sector_name = s["name"]
                    break
            all_results[sector_name] = results
            all_elites.extend(elites)
        except Exception as e:
            print(f"❌ Sector {sector_id} failed: {e}")
    
    # Sort elites globally
    all_elites.sort(key=lambda x: (x.get('win_rate', 0), x.get('trades', 0)), reverse=True)
    
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"✅ ALL SECTORS COMPLETE in {elapsed:.1f}s")
    print(f"{'='*60}")
    
    return {
        "sectors": all_results,
        "elite_signals": all_elites[:10],
        "scan_time_seconds": round(elapsed, 1),
        "total_results": sum(len(v) for v in all_results.values())
    }


@app.get("/api/last-scan")
def get_last_scan():
    """
    Return cached scan results from DB for instant UI loading.
    No VPN or Binance calls needed — pure DB read.
    """
    rows = load_last_scan_results()
    if not rows:
        return { "sectors": {}, "elite_signals": [], "cached": False }
    
    # Reconstruct the same format as scan-all response
    sectors = {}
    all_elites = []
    latest_time = None
    
    # Map sector IDs to display names
    SECTOR_NAMES = {
        "BIG_CAP": "Big Cap & L1", "AI_COINS": "AI Narratives",
        "MEME_COINS": "Meme Coins", "DEFI": "DeFi Bluechips",
        "LAYER_2": "Layer 2 & ZK", "GAMING": "Gaming & Metaverse",
        "RWA": "Real World Assets", "INFRA": "Infrastructure",
        "PRIVACY_ZK": "Privacy & ZK", "NEW_LISTINGS": "Hot & New",
        "CEX_TOKENS": "Exchange Tokens", "YIELD_STAKING": "Yield & Staking"
    }
    
    for row in rows:
        sector_id = row['sector']
        display_name = SECTOR_NAMES.get(sector_id, sector_id)
        results = row['results'] if isinstance(row['results'], list) else json.loads(row['results']) if row['results'] else []
        elites = row['elite_signals'] if isinstance(row['elite_signals'], list) else json.loads(row['elite_signals']) if row['elite_signals'] else []
        sectors[display_name] = results
        all_elites.extend(elites)
        if row.get('scanned_at'):
            ts = row['scanned_at']
            if latest_time is None or str(ts) > str(latest_time):
                latest_time = ts
    
    all_elites.sort(key=lambda x: (x.get('win_rate', 0), x.get('trades', 0)), reverse=True)
    
    return {
        "sectors": sectors,
        "elite_signals": all_elites[:10],
        "cached": True,
        "last_scan_time": str(latest_time) if latest_time else None,
        "total_results": sum(len(v) for v in sectors.values())
    }

@app.post("/api/monte-carlo")
def run_monte_carlo(req: SingleBacktestRequest):
    """
    Institutional-grade Monte Carlo Simulation endpoint.
    1. Runs backtest to get historical trades.
    2. Passes trades to MonteCarloEngine to run 5000 resampled realities.
    3. Returns VaR, CVaR, Probability of Ruin, and chart data.
    """
    engine = TradingEngine(initial_capital=req.capital)
    
    try:
        raw_df = engine.fetch_data(req.symbol, requested_period=req.period, interval=req.timeframe)
        if raw_df is None or raw_df.empty:
            raise HTTPException(status_code=400, detail="Gagal mengambil data market")
        
        # We need the full trade history, so we use the regular backtest engine
        try:
            df_res, markers, metrics, equity_data = engine.run_backtest(raw_df, req.strategy, req.period)
            trades = metrics.get("trades_list", [])
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
            
        if len(trades) < 5:
            return {"error": "Not enough trades (minimum 5) to run a meaningful Monte Carlo simulation."}
            
        mc = MonteCarloEngine(initial_capital=req.capital, num_simulations=5000)
        mc_results = mc.run_simulation(trades)
        
        return mc_results

    except Exception as e:
        print(f"[ERROR] Monte Carlo: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/send-alert")
def trigger_alert(item: dict):
    """Endpoint untuk testing manual Alert Telegram"""
    msg = (f"🚨 **MANUAL TEST ALERT**\n_QuantBot Test System_")
    send_telegram_alert(msg)
    return {"status": "ok"}

# =============================================================================
# 9. BTC MARKET RADAR — Macro Condition + Altcoin Correlation + Anomaly
# =============================================================================

@app.post("/api/btc-radar")
def btc_radar(req: ScanRequest):
    """
    BTC-focused Market Condition Radar.
    1. Analisis kondisi makro BTC (UPTREND / DOWNTREND / RANGING) dengan strength
    2. Hitung korelasi 30 hari setiap altcoin terhadap BTC
    3. Deteksi anomali: koin yang bergerak berlawanan arah BTC
    """
    engine = TradingEngine(initial_capital=req.capital)
    
    # === 1. BTC MACRO CONDITION ===
    btc_df = engine.fetch_data("BTC-USDT", requested_period="6mo", interval="1d")
    
    if btc_df is None or btc_df.empty:
        raise HTTPException(status_code=404, detail="BTC data not available")
    
    # Prepare indicators untuk BTC
    btc_df = engine.prepare_indicators(btc_df)
    btc_macro = engine.get_market_condition(btc_df, detailed=True)
    
    # BTC 30-day returns untuk korelasi
    btc_returns = btc_df['close'].pct_change().tail(30).dropna().values
    btc_30d_return = float(((btc_df.iloc[-1]['close'] - btc_df.iloc[-30]['close']) / btc_df.iloc[-30]['close']) * 100) if len(btc_df) >= 30 else 0
    
    # === 2. ALTCOIN CORRELATION & ANOMALY SCAN ===
    # Kumpulkan sample koin dari semua sektor (top 5 per sector)
    sample_coins = set()
    for key, coins in SECTORS.items():
        for coin in coins[:5]:
            if coin != "BTC-USDT":
                sample_coins.add(coin)
    
    correlations = []
    anomalies = []
    
    for coin in sample_coins:
        try:
            coin_df = engine.fetch_data(coin, requested_period="6mo", interval="1d")
            if coin_df is None or len(coin_df) < 30:
                continue
            
            # Prepare dan hitung kondisi coin
            coin_df = engine.prepare_indicators(coin_df)
            coin_condition = engine.get_market_condition(coin_df, detailed=True)
            
            # Hitung returns 30 hari
            coin_returns = coin_df['close'].pct_change().tail(30).dropna().values
            coin_30d_return = float(((coin_df.iloc[-1]['close'] - coin_df.iloc[-30]['close']) / coin_df.iloc[-30]['close']) * 100)
            
            # Hitung Pearson Correlation
            if len(coin_returns) == len(btc_returns) and len(coin_returns) > 5:
                corr = float(np.corrcoef(btc_returns, coin_returns)[0, 1])
            else:
                corr = 0.0
            
            coin_data = {
                "symbol": coin,
                "correlation": round(corr, 3),
                "return_30d": round(coin_30d_return, 2),
                "condition": coin_condition.get("condition", "UNKNOWN") if isinstance(coin_condition, dict) else coin_condition,
                "strength": coin_condition.get("strength", "WEAK") if isinstance(coin_condition, dict) else "UNKNOWN"
            }
            
            correlations.append(coin_data)
            
            # === 3. ANOMALY DETECTION ===
            # Anomali = koin yang decouple dari BTC
            btc_cond = btc_macro.get("condition", "UNKNOWN") if isinstance(btc_macro, dict) else btc_macro
            coin_cond = coin_data["condition"]
            
            is_anomaly = False
            anomaly_reason = ""
            
            # Case 1: BTC DOWNTREND tapi koin UPTREND (Bullish Anomaly)
            if btc_cond == "DOWNTREND" and coin_cond == "UPTREND":
                is_anomaly = True
                anomaly_reason = "🟢 Bullish Anomaly — Pumping despite BTC downtrend"
            
            # Case 2: BTC UPTREND tapi koin DOWNTREND (Bearish Anomaly)  
            elif btc_cond == "UPTREND" and coin_cond == "DOWNTREND":
                is_anomaly = True
                anomaly_reason = "🔴 Bearish Anomaly — Dumping despite BTC uptrend"
            
            # Case 3: Low correlation (< 0.3) = decoupled
            elif abs(corr) < 0.3 and abs(coin_30d_return) > 10:
                is_anomaly = True
                anomaly_reason = f"⚡ Decoupled — Low BTC correlation ({corr:.2f}) with {coin_30d_return:+.1f}% move"
            
            if is_anomaly:
                coin_data["anomaly_reason"] = anomaly_reason
                anomalies.append(coin_data)
                
        except Exception as e:
            print(f"⚠️ BTC Radar Error for {coin}: {e}")
            continue
    
    # Sort correlations by absolute return (most interesting first)
    correlations.sort(key=lambda x: abs(x['return_30d']), reverse=True)
    anomalies.sort(key=lambda x: abs(x['return_30d']), reverse=True)
    
    return {
        "btc_macro": {
            "condition": btc_macro.get("condition", "UNKNOWN") if isinstance(btc_macro, dict) else btc_macro,
            "strength": btc_macro.get("strength", "UNKNOWN") if isinstance(btc_macro, dict) else "UNKNOWN",
            "details": btc_macro.get("details", {}) if isinstance(btc_macro, dict) else {},
            "return_30d": round(btc_30d_return, 2)
        },
        "correlations": correlations[:20],  # Top 20 most interesting
        "anomalies": anomalies,
        "total_coins_scanned": len(correlations),
        "total_anomalies": len(anomalies)
    }

@app.post("/api/market-analytics")
def get_market_analytics(req: ScanRequest):
    """
    Endpoint KHUSUS untuk Visualisasi Advanced (Spaghetti, Volatility, Distribution).
    Mendukung 'ALL_SECTORS' untuk melihat gabungan market.
    """
    # HANDLE "ALL_SECTORS" GABUNGAN
    if req.sector == "ALL_SECTORS" or req.sector == "ALL":
        symbols = []
        # Ambil Top 2 dari setiap sektor agar grafik tidak terlalu ramai (Sample)
        for key, coins in SECTORS.items():
            if key in ["US_STOCKS", "STOCKS"]: continue
            symbols.extend(coins[:2])
        symbols = list(set(symbols))
    else:
        symbols = SECTORS.get(req.sector, [])
        symbols = symbols[:7] # Limit 7 koin agar grafik enak dilihat
    
    engine = TradingEngine(initial_capital=req.capital)
    
    analytics_data = {
        "spaghetti": [],
        "performance": [],
        "volatility": [],
        "distribution": [],
        "market_conditions": [] # Fitur Baru: Indikator Kondisi Pasar
    }
    
    daily_returns_all = []

    for sym in symbols:
        # Gunakan Fetch Data Pintar (DB + Cache)
        df = engine.fetch_data(sym, requested_period=req.period, interval="1d")
        
        if df is None or df.empty: continue
        
        # A. Market Condition (Trending/Ranging) - Fitur Baru
        condition = engine.get_market_condition(df)
        analytics_data["market_conditions"].append({
            "symbol": sym,
            "condition": condition
        })
        
        # B. Spaghetti (Normalized)
        start_price = df.iloc[0]['close']
        end_price = df.iloc[-1]['close']
        
        series_data = []
        # Sampling data agar tidak terlalu berat dikirim ke frontend
        step = 5 if len(df) > 300 else 1
        
        for i in range(0, len(df), step):
            row = df.iloc[i]
            norm_val = ((row['close'] - start_price) / start_price) * 100
            series_data.append({
                "time": int(row['time'].timestamp()),
                "value": round(norm_val, 2)
            })
            
        analytics_data["spaghetti"].append({
            "symbol": sym,
            "data": series_data
        })
        
        # C. Performance & Volatility
        total_ret = ((end_price - start_price) / start_price) * 100
        df['pct_change'] = df['close'].pct_change()
        std_dev = df['pct_change'].std()
        ann_vol = std_dev * (365 ** 0.5) * 100 
        
        analytics_data["performance"].append({ "symbol": sym, "return_pct": round(total_ret, 2) })
        analytics_data["volatility"].append({ "symbol": sym, "volatility": round(ann_vol, 2) })
        
        clean_rets = df['pct_change'].dropna().tolist()
        daily_returns_all.extend([r * 100 for r in clean_rets if abs(r) < 1.0])

    # D. Distribution Histogram
    if daily_returns_all:
        bins = [-10, -5, -2, 0, 2, 5, 10]
        labels = ["Crash", "Dump", "Red", "Green", "Pump", "Moon"]
        counts = [0] * 6
        for ret in daily_returns_all:
            if ret < -5: counts[0] += 1
            elif -5 <= ret < -2: counts[1] += 1
            elif -2 <= ret < 0: counts[2] += 1
            elif 0 <= ret < 2: counts[3] += 1
            elif 2 <= ret < 5: counts[4] += 1
            else: counts[5] += 1
            
        for i, label in enumerate(labels):
            analytics_data["distribution"].append({ "range": label, "count": counts[i] })

    # Sort Data untuk Tampilan Rapi
    analytics_data["performance"].sort(key=lambda x: x['return_pct'], reverse=True)
    analytics_data["volatility"].sort(key=lambda x: x['volatility'])

    return analytics_data

@app.get("/health")
def health_check():
    return {"status": "staying_alive", "timestamp": datetime.now().isoformat()}

# =============================================================================
# ALPHA DATA & AI PIPELINE (Gap Resolution)
# =============================================================================

# Singleton instances (preserve internal caching across requests)
alpha_data_provider = AlphaDataProvider()
alpha_feature_engine = AlphaFeatureEngine(alpha_data_provider)
ai_brain_instance = AIBrain()
paper_trader_instance = PaperTrader()
validation_engine_instance = ValidationEngine()

# --- Alpha Data Endpoints ---

@app.get("/api/alpha-data/{symbol}")
def get_alpha_data(symbol: str):
    """Get microstructure data for a symbol (aggTrades, funding, OI, L/S, taker vol)."""
    try:
        data = alpha_data_provider.get_full_snapshot(symbol)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/alpha-features/{symbol}")
def get_alpha_features(symbol: str):
    """Get computed features + z-scores + signal synthesis for a symbol."""
    try:
        raw_data = alpha_data_provider.get_full_snapshot(symbol)
        features = alpha_feature_engine.compute_all_features(symbol, raw_data)
        return features
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- AI Decision Endpoints ---

@app.get("/api/ai/status")
def get_ai_status():
    """Get AI service status (mode, model, key presence)."""
    return ai_brain_instance.get_status()

class AIDecisionRequest(BaseModel):
    context: Optional[str] = None  # market, signal, portfolio, risk
    data: Optional[dict] = None

@app.post("/api/ai-decision/{symbol}")
def make_ai_decision(symbol: str):
    """Get AI trading decision for a symbol."""
    try:
        # Build full pipeline: fetch → compute → decide
        raw_data = alpha_data_provider.get_full_snapshot(symbol)
        features = alpha_feature_engine.compute_all_features(symbol, raw_data)
        
        # Get current price
        from execution_engine import FuturesExecutionManager
        temp_exec = FuturesExecutionManager(paper_mode=True)
        price = temp_exec.get_current_price(symbol)
        
        market_snapshot = {
            **features,
            "price": price or 0,
            "regime": features.get("signals", {}).get("overall_bias", "NEUTRAL")
        }
        
        decision = ai_brain_instance.make_decision(symbol, market_snapshot)
        return decision
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/analyze")
def ai_analyze(request: AIDecisionRequest):
    """General-purpose AI analysis for different contexts."""
    try:
        context = request.context or "market"
        data = request.data or {}
        result = ai_brain_instance.analyze_context(context, data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ai/decisions")
def get_ai_decisions(symbol: Optional[str] = None, limit: int = 50):
    """Get AI decision history."""
    return ai_brain_instance.get_decision_history(symbol, limit)

# --- Paper Trader Endpoints ---

@app.get("/api/paper-trader/status")
def get_paper_trader_status():
    """Get paper trader status."""
    return paper_trader_instance.get_status()

@app.post("/api/paper-trader/start")
def start_paper_trader():
    """Start the paper trading loop."""
    return paper_trader_instance.start()

@app.post("/api/paper-trader/stop")
def stop_paper_trader():
    """Stop the paper trading loop."""
    return paper_trader_instance.stop()

@app.get("/api/paper-trader/trades")
def get_paper_trades(limit: int = 100):
    """Get paper trade history."""
    return paper_trader_instance.get_trades(limit)

@app.post("/api/paper-trader/cycle")
def run_paper_cycle():
    """Run a single paper trading cycle manually."""
    try:
        return paper_trader_instance.run_single_cycle()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Validation Endpoints ---

@app.post("/api/validation/run")
def run_validation(symbol: Optional[str] = None):
    """Run full statistical validation suite."""
    try:
        return validation_engine_instance.run_validation(symbol)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/validation/report")
def get_validation_report():
    """Get latest validation report."""
    return validation_engine_instance.get_latest_report()