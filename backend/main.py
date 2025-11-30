# File: backend/main.py (Kembali ke mode dummy untuk Dashboard)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import random
from typing import List, Dict
# import pandas as pd # DIHAPUS
# import json # DIHAPUS

app = FastAPI()

# --- CORS Configuration ---
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models ---
class StatCardData(BaseModel):
    title: str
    value: str
    change: str
    isPositive: bool

class EquityPoint(BaseModel):
    day: str
    value: float

# Tambahan: Model untuk Active Bots dan Trade Logs
class BotStatusUpdate(BaseModel):
    """Model untuk menerima perintah perubahan status."""
    new_status: str

class ActiveBot(BaseModel):
    """Model untuk menampilkan data bot aktif."""
    id: int
    strategy: str
    pair: str
    status: str
    pnl: str
    trades: int

class TradeLog(BaseModel):
    id: int
    time: str
    pair: str
    type: str
    price: float
    qty: float
    pnl: float
    status: str

# 💥 Model untuk Market Data 💥
class MarketDataPoint(BaseModel):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int

# --- PENTING: DUMMY DATA GLOBAL (untuk Active Bots) ---
ACTIVE_BOTS_DATA: Dict[int, Dict] = {
    1: {
        "id": 1,
        "strategy": "Grid Trading BTC/USDT",
        "pair": "BTC/USDT",
        "status": "Running",
        "pnl": "+1.2%",
        "trades": 55
    },
    2: {
        "id": 2,
        "strategy": "Mean Reversion ETH/USDT",
        "pair": "ETH/USDT",
        "status": "Running",
        "pnl": "+0.5%",
        "trades": 12
    },
    3: {
        "id": 3,
        "strategy": "Arbitrage BNB/USDC",
        "pair": "BNB/USDC",
        "status": "Paused",
        "pnl": "+3.1%",
        "trades": 80
    },
}

# ---------------------------------------------
# 1. ENDPOINTS DASHBOARD (KEMBALI KE DUMMY ACAR)
# ---------------------------------------------

@app.get("/api/dashboard/summary", response_model=List[StatCardData])
def get_dashboard_summary():
    """Mengembalikan data ringkasan dummy acak."""
    return [
        {
            "title": "Total Equity",
            "value": f"${random.randint(15000, 25000):,}",
            "change": f"{random.uniform(-5, 5):+.2f}%",
            "isPositive": random.choice([True, False])
        },
        {
            "title": "Strategy Win Rate (Grid)",
            "value": f"{random.randint(60, 95)}%",
            "change": f"{random.uniform(-0.5, 0.5):+.2f}%",
            "isPositive": random.choice([True, False])
        },
        {
            "title": "Open Positions",
            "value": str(random.randint(5, 20)),
            "change": "N/A",
            "isPositive": True
        },
    ]

@app.get("/api/dashboard/equity_curve", response_model=List[EquityPoint])
def get_equity_curve():
    """Mengembalikan data dummy acak untuk grafik kurva ekuitas."""
    return [
        {"day": "Sen", "value": 10000 + random.randint(-500, 1000)},
        {"day": "Sel", "value": 10500 + random.randint(-500, 1000)},
        {"day": "Rab", "value": 11000 + random.randint(-500, 1000)},
        {"day": "Kam", "value": 11500 + random.randint(-500, 1000)},
        {"day": "Jum", "value": 12000 + random.randint(-500, 1000)},
    ]

# ---------------------------------------------
# 2. ENDPOINTS ACTIVE BOTS (INTERAKTIF)
# ---------------------------------------------

@app.get("/api/bots/active", response_model=List[ActiveBot])
def get_active_bots():
    """Mengembalikan daftar bot aktif (menggunakan data dummy global)."""
    return list(ACTIVE_BOTS_DATA.values())

@app.post("/api/bots/{bot_id}/control")
def control_bot_status(bot_id: int, update: BotStatusUpdate):
    """Mengubah status bot aktif."""
    if bot_id not in ACTIVE_BOTS_DATA:
        return {"message": f"Bot ID {bot_id} not found."}

    current_bot = ACTIVE_BOTS_DATA[bot_id]
    current_bot['status'] = update.new_status

    print(f"Bot {bot_id} ({current_bot['strategy']}) status changed to {update.new_status}")

    return {"message": f"Bot {bot_id} updated successfully to status: {update.new_status}", "bot": current_bot}

# ---------------------------------------------
# 3. ENDPOINTS TRADE LOGS (MASIH DUMMY)
# ---------------------------------------------

@app.get("/api/trades/logs", response_model=List[TradeLog])
def get_trade_logs(limit: int = 20):
    """Mengembalikan daftar transaksi historis dummy."""
    return [
        {"id": 105, "time": "2025-05-01 10:00", "pair": "BTC/USDT", "type": "BUY", "price": 45100.00, "qty": 0.01, "pnl": 5.25, "status": "CLOSED"},
        {"id": 106, "time": "2025-05-01 10:05", "pair": "BTC/USDT", "type": "SELL", "price": 45520.00, "qty": 0.01, "pnl": 4.10, "status": "CLOSED"},
        {"id": 107, "time": "2025-05-01 11:30", "pair": "ETH/USDT", "type": "BUY", "price": 3100.50, "qty": 0.5, "pnl": -2.30, "status": "CLOSED"},
        {"id": 108, "time": "2025-05-01 11:45", "pair": "ETH/USDT", "type": "SELL", "price": 3105.00, "qty": 0.5, "pnl": 1.95, "status": "CLOSED"},
        {"id": 109, "time": "2025-05-01 12:10", "pair": "SOL/USDT", "type": "BUY", "price": 150.20, "qty": 10.0, "pnl": 10.50, "status": "CLOSED"},
    ]

# ---------------------------------------------
# 4. ENDPOINTS MARKET DATA
# ---------------------------------------------

@app.get("/api/market/history", response_model=List[MarketDataPoint])
def get_market_history(ticker: str = "BTC/USDT", limit: int = 10):
    """
    Mengembalikan data harga historis (OHLCV) dummy.
    """
    # Dummy data untuk 5 baris data OHLCV
    return [
        {"timestamp": "2023-01-01 00:00", "open": 16500.00, "high": 16550.00, "low": 16480.00, "close": 16520.00, "volume": 12000},
        {"timestamp": "2023-01-01 05:00", "open": 16520.00, "high": 16600.00, "low": 16510.00, "close": 16590.00, "volume": 15000},
        {"timestamp": "2023-01-01 10:00", "open": 16590.00, "high": 16650.00, "low": 16580.00, "close": 16620.00, "volume": 11000},
        {"timestamp": "2023-01-01 15:00", "open": 16620.00, "high": 16680.00, "low": 16600.00, "close": 16650.00, "volume": 13000},
        {"timestamp": "2023-01-01 20:00", "open": 16650.00, "high": 16720.00, "low": 16640.00, "close": 16690.00, "volume": 14500},
    ]