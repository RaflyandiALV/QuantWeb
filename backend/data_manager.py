# File: backend/data_manager.py
# (Pastikan file ini berada di folder yang sama dengan main.py)

import yfinance as yf
import pandas as pd
from typing import Dict, List
import random # Diperlukan untuk dummy/random data di placeholder

# --- Logika Inti: Mengambil Data ---

def fetch_historical_data(ticker: str = "BTC-USD", period: str = "1mo") -> pd.DataFrame:
    """Mengambil data harga historis dari Yahoo Finance."""
    try:
        # Menambahkan timeout untuk mencegah hang
        data = yf.download(ticker, period=period, interval="1d", timeout=10)
        if data.empty:
            # Perhatikan: yfinance.download akan mengembalikan DF kosong jika gagal
            return pd.DataFrame() 
        
        data.columns = [col.lower().replace(' ', '_') for col in data.columns]
        return data
    except Exception as e:
        # Menangkap error koneksi
        print(f"Error fetching data from yfinance: {e}")
        return pd.DataFrame()

# --- Fungsi Analisis Strategi (Placeholder) ---

def analyze_strategy_performance(df: pd.DataFrame) -> Dict:
    """Mengembalikan metrik performa (ROE, Win Rate, dll.)"""
    # 💥 Ini adalah nilai yang akan muncul di dashboard sekarang 💥
    return {
        "roe": 0.05,  # 5% (positif)
        "win_rate": 0.65, # 65% 
    }

def generate_equity_curve(df: pd.DataFrame) -> List[Dict]:
    """Mengembalikan data yang siap diplot untuk kurva ekuitas."""
    # Karena kita belum memasukkan logika backtest, kita gunakan data harga asli
    # sebagai kurva ekuitas sementara (sekadar untuk memastikan grafik terisi)
    
    # Ambil 5 baris terakhir (5 hari)
    last_5_days = df.tail(5).reset_index()
    
    equity_data = []
    
    # Menggunakan 'close' sebagai nilai ekuitas sementara
    for index, row in last_5_days.iterrows():
        equity_data.append({
            "day": row['date'].strftime('%b %d'), # Format tanggal
            "value": 10000 + (row['close'] * 10) # Base 10000 + nilai close
        })
        
    # Jika data kosong, gunakan dummy statis
    if not equity_data:
        return [
            {"day": "Sen", "value": 10000},
            {"day": "Sel", "value": 10000},
            {"day": "Rab", "value": 10000},
            {"day": "Kam", "value": 10000},
            {"day": "Jum", "value": 10000},
        ]
        
    return equity_data

# Jika kamu menjalankan file ini langsung, ia akan menguji fungsinya
if __name__ == '__main__':
    data = fetch_historical_data()
    print(f"Data shape: {data.shape}")
    print(data.tail())
    metrics = analyze_strategy_performance(data)
    print(f"Metrics: {metrics}")
    curve = generate_equity_curve(data)
    print(f"Equity Curve Points: {len(curve)}")