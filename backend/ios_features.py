from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from strategy_core import TradingEngine
import pandas as pd
import os
import json
from typing import List, Optional
from datetime import datetime

# --- PENTING: DEFINISI ROUTER ---
# Ini adalah variabel yang dicari oleh main.py
router = APIRouter()

# --- KONFIGURASI LOKAL ---
TRADES_LOG_FILE = "trades_log.csv"
WATCHLIST_FILE = "watchlist.json"

SECTORS = {
    "BIG_CAP": ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "ADA-USD"],
    "AI_COINS": ["FET-USD", "RENDER-USD", "NEAR-USD", "ICP-USD", "GRT-USD", "TAO-USD"],
    "MEME_COINS": ["DOGE-USD", "SHIB-USD", "PEPE-USD", "WIF-USD", "BONK-USD", "FLOKI-USD"],
    "EXCHANGE_TOKENS": ["BNB-USD", "OKB-USD", "KCS-USD", "CRO-USD", "LEO-USD"],
    "DEX_DEFI": ["UNI-USD", "CAKE-USD", "AAVE-USD", "MKR-USD", "LDO-USD", "CRV-USD"],
    "LAYER_2": ["MATIC-USD", "ARB-USD", "OP-USD", "IMX-USD", "MNT-USD"],
    "US_TECH": ["NVDA", "TSLA", "AAPL", "MSFT", "AMD", "META", "GOOG"]
}

# --- MODEL DATA ---
class ScanRequest(BaseModel):
    sector: str
    timeframe: str = "1d"
    period: str = "1y" 
    capital: float = 10000

# --- LOGIKA SCANNER ---
def find_best_strategy(engine, symbol):
    strategies = ["MOMENTUM", "GRID"]
    best_res = None
    best_score = -99999
    
    # Ambil data sekali
    df = engine.fetch_data(symbol, requested_period="max", interval="1d")
    if df is None or len(df) < 50: return None
    
    for strat in strategies:
        # Gunakan try-except agar tidak crash jika data kurang
        try:
            _, _, metrics, _ = engine.run_backtest(df, strat, requested_period="1y")
            if metrics['total_trades'] < 2: continue
            
            score = metrics['win_rate'] * metrics['net_profit']
            if score > best_score:
                best_score = score
                best_res = {
                    "strategy": strat,
                    "win_rate": metrics['win_rate'],
                    "profit": metrics['net_profit']
                }
        except:
            continue
            
    return best_res

# --- ENDPOINT 1: SCANNER ---
@router.post("/api/scan-market")
def scan_market(req: ScanRequest):
    print(f"🚀 IOS SCANNER TRIGGERED: {req.sector}")
    
    if req.sector == "ALL":
        symbols = []
        for s in SECTORS.values(): symbols.extend(s)
        symbols = list(set(symbols))[:15] # Limit
    else:
        symbols = SECTORS.get(req.sector, [])
    
    if not symbols: raise HTTPException(status_code=404, detail="Sektor kosong")
    
    engine = TradingEngine(initial_capital=req.capital)
    results = []
    
    for sym in symbols:
        res = find_best_strategy(engine, sym)
        if res:
            results.append({
                "symbol": sym,
                "sector": req.sector,
                "recommended_strategy": res['strategy'],
                "win_rate_est": res['win_rate'],
                "score": int(res['profit'])
            })
            
    return sorted(results, key=lambda x: x['win_rate_est'], reverse=True)

# --- ENDPOINT 2: LOGS ---
@router.get("/api/logs")
def get_logs():
    print("🚀 IOS LOGS TRIGGERED")
    if not os.path.exists(TRADES_LOG_FILE): return []
    try:
        df = pd.read_csv(TRADES_LOG_FILE)
        logs = []
        for _, row in df.iterrows():
            try:
                if pd.api.types.is_numeric_dtype(row['time']): ts = int(row['time'])
                else: ts = int(pd.to_datetime(row['time']).timestamp())
            except: ts = int(datetime.now().timestamp())

            logs.append({
                "id": int(row.get('id', ts)),
                "time": ts,
                "symbol": str(row.get('pair', 'UNKNOWN')),
                "action": str(row.get('type', 'BUY')).upper(),
                "price": float(row.get('price', 0)),
                "qty": float(row.get('qty', 0)),
                "pnl": float(row.get('pnl', 0)),
                "status": str(row.get('status', 'CLOSED'))
            })
        return sorted(logs, key=lambda x: x['time'], reverse=True)
    except Exception as e:
        print(f"Log Error: {e}")
        return []