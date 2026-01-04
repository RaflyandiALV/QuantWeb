
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from strategy_core import TradingEngine
import pandas as pd
import json
import os
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from typing import Optional, List, Literal
from datetime import datetime
import contextlib
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()


# --- CONFIGURATION ---
# --- CONFIGURATION (Ganti agar mengambil dari .env) ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DATABASE_URL = os.getenv("DATABASE_URL")
WATCHLIST_FILE = "watchlist.json" # Tetap ada untuk cadangan jika perlu

# --- HELPER: TELEGRAM SENDER ---
def send_telegram_alert(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload)
    except Exception as e: print(f"Telegram Error: {e}")

# --- CENTRALIZED SCANNING LOGIC (HEAVY DATA VERSION) ---
def find_best_strategy_for_symbol(engine, symbol, mode="AUTO", manual_strat=None, manual_tf=None, manual_per=None):
    """
    Fungsi Utama:
    1. Mengambil data 'max' (seluruh history) agar indikator 100% akurat (memaksimalkan profit).
    2. Melakukan backtest sesuai periode yang diminta (1y/6mo).
    """
    
    if mode == 'MANUAL':
        # --- LOGIKA MANUAL ---
        # Fetch MAX data agar indikator EMA/RSI matang sempurna sebelum periode analisa dimulai
        df_raw = engine.fetch_data(symbol, requested_period="max", interval=manual_tf)
        
        if df_raw is not None and len(df_raw) > 30:
            # Slicing data dilakukan di dalam run_backtest sesuai manual_per
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
        strategies = ["MOMENTUM", "MEAN_REVERSAL", "GRID", "MULTITIMEFRAME"]
        timeframes = ["1h", "4h", "1d"]
        
        # Sesuai request: Tetap gunakan 6mo dan 1y agar scanner rapi
        periods = ["6mo", "1y"] 
        
        best_config = None
        best_score = -999999999
        
        for tf in timeframes:
            # OPTIMASI PENTING: Fetch "max" data sekali per timeframe.
            # Ini kuncinya: Walaupun kita scan '1y', data mentahnya 'max' biar indikator akurat.
            df_raw = engine.fetch_data(symbol, requested_period="max", interval=tf) 
            if df_raw is None or len(df_raw) < 50: continue

            for per in periods:
                for strat in strategies:
                    # Run logic (Slicing handled by engine based on per)
                    _, _, metrics, _ = engine.run_backtest(df_raw, strat, requested_period=per)
                    
                    # Filter minimal trade agar statistik valid
                    if metrics['total_trades'] < 3: continue 
                    
                    # Score Logic: WinRate * Profit
                    score = metrics['win_rate'] * metrics['net_profit']
                    
                    if score > best_score:
                        best_score = score
                        signal_info = engine.get_signal_advice(df_raw, strat)
                        rr_long = calculate_rr_string(signal_info['price'], signal_info['setup_long']['tp'], signal_info['setup_long']['sl'])
                        
                        best_config = {
                            "symbol": symbol, "strategy": strat, "timeframe": tf, "period": per,
                            "win_rate": metrics['win_rate'], "profit": metrics['net_profit'],
                            "trades": metrics['total_trades'], "signal_data": signal_info,
                            "rr_ratio": rr_long, "mode": "AUTO"
                        }
        return best_config

# --- BOT BACKGROUND TASK ---
def check_market_signals():
    """
    Bot Loop yang menggunakan logika find_best_strategy_for_symbol
    """
    # Ganti load_watchlist_data() menjadi load_watchlist_from_db()
    watchlist = load_watchlist_from_db() 
    
    if not watchlist: return
    
    print(f"[{datetime.now().strftime('%H:%M')}] 🧠 AI Bot: Running Heavy Logic on Watchlist...")
    engine = TradingEngine(initial_capital=1000)
    
    for item in watchlist:
        try:
            # 1. CARI KONFIGURASI TERBAIK (Centralized Logic)
            config = find_best_strategy_for_symbol(
                engine, 
                item['symbol'], 
                mode=item.get('mode', 'AUTO'),
                manual_strat=item.get('strategy'),
                manual_tf=item.get('timeframe'),
                manual_per=item.get('period')
            )
            
            if config:
                # 2. VALIDASI SIGNAL (REAL-TIME CHECK)
                # Fetch max data lagi untuk akurasi indikator saat cek signal terakhir
                df_raw = engine.fetch_data(config['symbol'], requested_period="max", interval=config['timeframe'])
                if df_raw is None: continue

                # Backtest pendek (1mo) cukup untuk mengambil marker terakhir, 
                # karena indikator sudah dihitung dari data 'max'
                df_res, markers, _, _ = engine.run_backtest(df_raw, config['strategy'], requested_period="1mo")
                
                if markers:
                    last_marker = markers[-1]
                    last_candle_time = int(df_res.iloc[-1]['time'].timestamp())
                    
                    # Trigger hanya jika signal ada di candle terakhir
                    if last_marker['time'] >= last_candle_time:
                        signal_type = last_marker['text'] 
                        price = df_res.iloc[-1]['close']
                        
                        tp = 0; sl = 0
                        if signal_type == "BUY":
                            tp = config['signal_data']['setup_long']['tp']
                            sl = config['signal_data']['setup_long']['sl']
                        else:
                            tp = config['signal_data']['setup_short']['tp']
                            sl = config['signal_data']['setup_short']['sl']
                        
                        rr_str = calculate_rr_string(price, tp, sl)
                        mode_icon = "🛠️" if config.get('mode') == 'MANUAL' else "🤖"

                        msg = (
                            f"🚨 **SIGNAL ALERT: {config['symbol']}**\n\n"
                            f"📈 **Action:** {signal_type}\n"
                            f"💰 **Price:** ${price:,.2f}\n\n"
                            f"{mode_icon} **Mode:** {config.get('mode', 'AUTO')}\n"
                            f"⚙️ **Strategy:** {config['strategy']}\n"
                            f"⏳ **Timeframe:** {config['timeframe']} ({config['period']})\n"
                            f"📊 **Stats:** WR {config['win_rate']}% | {config['trades']} Trades\n\n"
                            f"🎯 **TP:** ${tp:,.2f}\n"
                            f"🛑 **SL:** ${sl:,.2f}\n"
                            f"⚖️ **R:R:** {rr_str}\n\n"
                            f"_QuantBot System_"
                        )
                        send_telegram_alert(msg)
                        print(f"✅ Alert sent for {config['symbol']}")

        except Exception as e:
            print(f"Error checking {item['symbol']}: {e}")

# --- LIFESPAN MANAGER ---
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    print("✅ System Startup: Sending Telegram Notification...")
    send_telegram_alert("🟢 **SYSTEM ACTIVE**\n\nBot QuantTrade is running with Heavy Data Accuracy Mode.")
    
    scheduler = BackgroundScheduler()
    # Interval check setiap 60 menit
    scheduler.add_job(check_market_signals, 'interval', minutes=10)
    scheduler.start()
    
    yield
    
    print("🛑 System Shutdown: Sending Telegram Notification...")
    send_telegram_alert("🔴 **SYSTEM INACTIVE**\n\nBot QuantTrade has been stopped.")
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "https://quantweb-frontend.vercel.app",           # Domain Production (Utama)
    "http://localhost:5173",                          # Localhost Vite (Default)
    "http://127.0.0.1:5173",                        # Localhost IP
    "https://quantweb-frontend-rafliyandiandis-projects.vercel.app" # Domain General Vercel
    ], # URL Vercel Anda
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATA MODELS ---
class StrategyRequest(BaseModel):
    symbol: str
    strategy: str
    capital: float
    timeframe: str = "1d"
    period: str = "1y"
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class ScanRequest(BaseModel):
    sector: str
    timeframe: str = "1d"
    period: str = "1y" 
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    capital: float = 10000

class WatchlistItem(BaseModel):
    symbol: str
    mode: Literal["AUTO", "MANUAL"] = "AUTO"
    strategy: Optional[str] = "MOMENTUM"
    timeframe: Optional[str] = "1d"
    period: Optional[str] = "1y"

# --- SECTORS CONFIG ---
SECTORS = {
    "BIG_CAP": ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "ADA-USD", "AVAX-USD"],
    "AI_COINS": ["FET-USD", "RENDER-USD", "NEAR-USD", "ICP-USD", "GRT-USD", "TAO-USD"],
    "MEME_COINS": ["DOGE-USD", "SHIB-USD", "PEPE-USD", "WIF-USD", "BONK-USD", "FLOKI-USD"],
    "EXCHANGE_TOKENS": ["BNB-USD", "OKB-USD", "KCS-USD", "CRO-USD", "LEO-USD"],
    "DEX_DEFI": ["UNI-USD", "CAKE-USD", "AAVE-USD", "MKR-USD", "LDO-USD", "CRV-USD"],
    "LAYER_2": ["MATIC-USD", "ARB-USD", "OP-USD", "IMX-USD", "MNT-USD"],
    "US_TECH": ["NVDA", "TSLA", "AAPL", "MSFT", "AMD", "META", "GOOG"]
}

# --- HELPER FUNCTIONS ---
def get_db_connection():
    # Optimasi: Tambahkan pengecekan agar tidak error localhost lagi
    url = os.getenv("DATABASE_URL")
    if not url:
        print("❌ ERROR: DATABASE_URL tidak terbaca dari .env!")
        return None
    return psycopg2.connect(url, cursor_factory=RealDictCursor)

def load_watchlist_from_db():
    conn = get_db_connection() # Pastikan ini memanggil fungsi get_db_connection()
    if not conn: 
        return []
    cur = conn.cursor()
    cur.execute("SELECT symbol, mode, strategy, timeframe, period FROM watchlist")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def calculate_rr_string(entry, tp, sl):
    try:
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        if risk == 0: return "1 : N/A"
        ratio = reward / risk
        return f"1 : {ratio:.1f}"
    except:
        return "N/A"

def analyze_market_reason(best_strat, win_rate):
    if best_strat == "HOLD ONLY": return "🚀 Parabolic Run"
    elif best_strat == "MOMENTUM": return "📈 Strong Uptrend"
    elif best_strat == "MULTITIMEFRAME": return "✅ Trend Confirmation"
    elif best_strat == "GRID": return "〰️ Ranging Area"
    elif best_strat == "MEAN_REVERSAL": return "🔄 Reversal Zone"
    else: return "❓ Unclear"

# --- API ENDPOINTS ---

@app.get("/")
def read_root():
    return {"status": "Backend Active", "bot_status": "Monitoring"}

@app.get("/api/watchlist")
def get_watchlist():
    # 1. Hubungkan ke Database
    conn = get_db_connection()
    if not conn: 
        raise HTTPException(status_code=500, detail="Gagal terhubung ke database")
    
    cur = conn.cursor()
    # 2. Ambil data dari tabel watchlist
    cur.execute("SELECT symbol, mode, strategy, timeframe, period FROM watchlist ORDER BY created_at DESC")
    items = cur.fetchall()
    cur.close()
    conn.close()
    
    results = []
    engine = TradingEngine(initial_capital=1000)
    
    # 3. Lakukan kalkulasi strategi untuk setiap koin
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
    if not conn:
        raise HTTPException(status_code=500, detail="Database error")
    
    cur = conn.cursor()
    try:
        # Perintah SQL untuk memasukkan data
        cur.execute(
            """
            INSERT INTO watchlist (symbol, mode, strategy, timeframe, period) 
            VALUES (%s, %s, %s, %s, %s)
            """,
            (item.symbol.upper(), item.mode, item.strategy, item.timeframe, item.period)
        )
        conn.commit()
    except psycopg2.IntegrityError:
        # Jika koin sudah ada (karena kita pakai constraint UNIQUE pada kolom symbol)
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
    # Perintah SQL untuk menghapus berdasarkan simbol
    cur.execute("DELETE FROM watchlist WHERE symbol = %s", (symbol.upper(),))
    conn.commit()
    cur.close()
    conn.close()
    return {"status": "deleted"}

@app.post("/api/run-backtest")
def run_backtest(req: StrategyRequest):
    engine = TradingEngine(initial_capital=req.capital)
    
    # PERUBAHAN PENTING: Force Fetch 'max' untuk data awal
    # Ini memastikan hasil backtest MANUAL sama persis dengan SCANNER (Heavy Load)
    fetch_period = "max"
    
    df_raw = engine.fetch_data(req.symbol, requested_period=fetch_period, interval=req.timeframe, start_date=req.start_date, end_date=req.end_date)
    
    if df_raw is None or len(df_raw) < 30: raise HTTPException(status_code=404, detail=f"Data kosong {req.symbol}.")

    # Run backtest akan melakukan slicing sesuai req.period yang diminta user (misal 1y)
    # Tapi perhitungan indikator didasarkan pada data max yang di-fetch di atas
    df_res, markers, metrics, equity_data = engine.run_backtest(df_raw, req.strategy, requested_period=req.period, start_date=req.start_date, end_date=req.end_date)
    
    chart_data = []
    line1, line2, line3 = [], [], []
    for index, row in df_res.iterrows():
        if pd.isna(row['close']): continue
        t = int(row['time'].timestamp())
        chart_data.append({ "time": t, "open": row['open'], "high": row['high'], "low": row['low'], "close": row['close'] })
        
        if req.strategy == "MOMENTUM":
            line1.append({"time": t, "value": row['sma_fast']})
            line2.append({"time": t, "value": row['sma_slow']})
        elif req.strategy in ["MEAN_REVERSAL", "GRID"]:
            line1.append({"time": t, "value": row['bb_upper'] if req.strategy == "MEAN_REVERSAL" else row['grid_top']})
            line2.append({"time": t, "value": row['bb_lower'] if req.strategy == "MEAN_REVERSAL" else row['grid_bottom']})
            if req.strategy == "GRID": line3.append({"time": t, "value": row['grid_mid']})
        elif req.strategy == "MULTITIMEFRAME":
            line3.append({"time": t, "value": row['ema_trend']})

    return { "status": "success", "chart_data": chart_data, "equity_curve": equity_data, "indicators": {"line1": line1, "line2": line2, "line3": line3}, "markers": markers, "metrics": metrics }

@app.post("/api/compare-strategies")
def compare_strategies(req: StrategyRequest):
    engine = TradingEngine(initial_capital=req.capital)
    # Force max fetch for comparison too
    df_raw = engine.fetch_data(req.symbol, requested_period="max", interval=req.timeframe, start_date=req.start_date, end_date=req.end_date)
    
    if df_raw is None or len(df_raw) < 30: raise HTTPException(status_code=404, detail="Data Error")

    results = []
    strategies = ["MOMENTUM", "MEAN_REVERSAL", "GRID", "MULTITIMEFRAME"]
    for strat in strategies:
        _, _, metrics, _ = engine.run_backtest(df_raw, strat, requested_period=req.period)
        results.append({ "strategy": strat, "net_profit": metrics['net_profit'], "win_rate": metrics['win_rate'], "trades": metrics['total_trades'], "sharpe": metrics.get('sharpe_ratio', 0), "is_hold": False })
    
    hold_val = req.capital * (metrics['buy_hold_return'] / 100)
    results.append({ "strategy": "HOLD ONLY", "net_profit": round(hold_val, 2), "win_rate": 100, "trades": 1, "sharpe": 0, "is_hold": True })
    results.sort(key=lambda x: x['net_profit'], reverse=True)
    return {"symbol": req.symbol, "comparison": results}

@app.post("/api/scan-market")
def scan_market(req: ScanRequest):
    if req.sector == "ALL":
        symbols = []
        for s in SECTORS.values(): symbols.extend(s)
        symbols = list(set(symbols))[:20] 
    else:
        symbols = SECTORS.get(req.sector, [])
    
    if not symbols: raise HTTPException(status_code=404, detail="Sektor tidak ditemukan")
    
    engine = TradingEngine(initial_capital=req.capital)
    scan_results = []
    elite_signals = []

    for sym in symbols:
        # Panggil fungsi Centralized Logic
        best_config = find_best_strategy_for_symbol(engine, sym, mode="AUTO")
        
        if best_config:
            best_config['reason'] = analyze_market_reason(best_config['strategy'], best_config['win_rate'])
            scan_results.append(best_config)
            
            # --- LOGIKA SORTIR ELITE SIGNAL (UPDATED) ---
            # Trades harus >= 15
            if best_config['win_rate'] >= 60 and best_config['trades'] >= 15:
                elite_signals.append(best_config)

    elite_signals.sort(key=lambda x: (x['win_rate'], x['trades']), reverse=True)
    return { "sector": req.sector, "results": scan_results, "elite_signals": elite_signals[:10] }

@app.post("/api/send-alert")
def trigger_alert(item: dict):
    msg = (f"🚨 **MANUAL TEST ALERT**\n_QuantBot Test_")
    send_telegram_alert(msg)
    return {"status": "ok"}
