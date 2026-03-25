# backend/strategy_core.py
import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sqlite3 # Menggunakan SQLite sesuai request untuk kecepatan lokal
from dotenv import load_dotenv

# ============================================================
# ANNUALIZATION CONSTANTS (bars per year per timeframe)
# ============================================================
BARS_PER_YEAR = {
    "15m": 252 * 96,   # 24192 bars/year
    "1h":  252 * 24,   # 6048 bars/year
    "4h":  252 * 6,    # 1512 bars/year
    "1d":  252,        # 252 bars/year (standard)
    "1w":  52,         # 52 bars/year
}

# Trading Cost Model (Binance Taker + Market Slippage)
TAKER_FEE      = 0.001    # 0.1% per side
SLIPPAGE       = 0.0005   # 0.05% estimated market slippage
ROUND_TRIP_COST = TAKER_FEE + SLIPPAGE  # applied per transaction side

# Load environment variables
load_dotenv()

class TradingEngine:
    def __init__(self, api_key=None, api_secret=None, initial_capital=1000, leverage=1):
        """
        Inisialisasi Trading Engine.
        Menangani koneksi ke Exchange dan Database Lokal.
        """
        self.initial_capital = float(initial_capital)
        self.leverage = leverage
        
        # Menggunakan File Database Lokal agar cepat dan tidak perlu upload ke Cloud
        self.db_file = "market_data.db" 
        
        # Konfigurasi Exchange CCXT
        exchange_config = {
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'},
        }

        # Cek apakah API Key tersedia untuk Execution
        if api_key and api_secret:
            exchange_config['apiKey'] = api_key
            exchange_config['secret'] = api_secret
            self.auth_mode = "TESTNET"  # Default: Testnet (demo money)
        else:
            self.auth_mode = "PUBLIC"

        try:
            # Inisialisasi CCXT
            self.exchange = ccxt.binance(exchange_config)
            
            # Enable Testnet Sandbox Mode
            if self.auth_mode == "TESTNET":
                self.exchange.set_sandbox_mode(True)
                self.exchange.load_markets()
                print(f"[CORE] TradingEngine Active (Mode: TESTNET -- Demo Money)")
            else:
                print(f"[CORE] TradingEngine Active (Mode: PUBLIC DATA ONLY)")
            
            # Inisialisasi Database (Buat Tabel jika belum ada)
            self._init_db()

        except Exception as e:
            print(f"[ERROR] [CORE] Init Error: {e}")

    # ============================================================
    # 1. DATABASE MANAGER (SQLITE LOCAL IMPLEMENTATION)
    # Bagian ini menggantikan logika PostgreSQL/Supabase sebelumnya
    # ============================================================
    
    def _get_db_conn(self):
        """
        Membuat koneksi ke file database lokal.
        WAL mode + busy_timeout untuk mendukung parallel scanning.
        """
        try:
            conn = sqlite3.connect(self.db_file, check_same_thread=False, timeout=30)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
            return conn
        except Exception as e:
            print(f"[ERROR] DB Connection Error: {e}")
            return None

    def _init_db(self):
        """
        Membuat struktur tabel 'market_data' jika file database baru dibuat.
        """
        conn = self._get_db_conn()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            
            # Membuat Tabel dengan Composite Primary Key untuk mencegah duplikasi data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    symbol TEXT,
                    timeframe TEXT,
                    timestamp INTEGER,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume REAL,
                    PRIMARY KEY (symbol, timeframe, timestamp)
                );
            """)
            
            # Tabel Cache untuk Strategy Results (Optimasi Scan)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategy_cache (
                    symbol TEXT,
                    timeframe TEXT,
                    period TEXT,
                    strategy TEXT,
                    net_profit REAL,
                    win_rate REAL,
                    total_trades INTEGER,
                    max_drawdown REAL,
                    sharpe_ratio REAL,
                    final_balance REAL,
                    signal_data TEXT,
                    rr_ratio TEXT,
                    cached_data_ts INTEGER,
                    updated_at TEXT,
                    PRIMARY KEY (symbol, timeframe, period, strategy)
                );
            """)
            
            # Tabel Trade Log — Mencatat setiap order yang dieksekusi bot
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trade_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    qty REAL NOT NULL,
                    price REAL NOT NULL,
                    strategy TEXT,
                    timeframe TEXT,
                    order_id TEXT,
                    status TEXT DEFAULT 'FILLED',
                    pnl REAL DEFAULT 0,
                    notes TEXT,
                    created_at TEXT NOT NULL
                );
            """)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"DB Init Error: {e}")

    def _get_last_timestamp(self, symbol, timeframe):
        """
        Fetch timestamp of the latest candle stored in DB.
        Used to determine the starting point for download (Incremental Fetch).
        """
        conn = self._get_db_conn()
        if not conn: return None
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(timestamp) FROM market_data WHERE symbol=? AND timeframe=?", (symbol, timeframe))
            res = cursor.fetchone()
            conn.close()
            
            # Mengembalikan timestamp jika ada, atau None jika belum ada data
            return res[0] if res else None
            
        except: return None

    def _save_to_db(self, symbol, timeframe, ohlcv_data):
        """
        Save new candle data to local database.
        Uses 'INSERT OR IGNORE' to handle duplicates.
        """
        conn = self._get_db_conn()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            
            # Format data according to table structure
            # ccxt ohlcv: [timestamp, open, high, low, close, volume]
            records = [(symbol, timeframe, row[0], row[1], row[2], row[3], row[4], row[5]) for row in ohlcv_data]
            
            # Execute Batch Insert (Very fast in SQLite)
            cursor.executemany("""
                INSERT OR IGNORE INTO market_data (symbol, timeframe, timestamp, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, records)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"DB Save Error: {e}")

    def _load_from_db(self, symbol, timeframe, requested_period):
        """
        Fetch historical data from local database for analysis/backtest.
        """
        conn = self._get_db_conn()
        if not conn: return None
        
        try:
            # Hitung batas waktu (Cutoff) berdasarkan requested_period
            now_ts = int(datetime.now().timestamp() * 1000)
            cutoff_ts = 0
            
            ms_day = 86400000 # 24 jam dalam milidetik
            
            if requested_period == "1mo": 
                cutoff_ts = now_ts - (30 * ms_day)
            elif requested_period == "3mo": 
                cutoff_ts = now_ts - (90 * ms_day)
            elif requested_period == "6mo": 
                cutoff_ts = now_ts - (180 * ms_day)
            elif requested_period == "1y": 
                cutoff_ts = now_ts - (365 * ms_day)
            elif requested_period == "2y": 
                cutoff_ts = now_ts - (730 * ms_day)
            elif requested_period == "max": 
                cutoff_ts = 0 # Ambil semua data dari awal
            else:
                cutoff_ts = 0 # Fallback: ambil semua data
            
            # Query Select Data
            query = "SELECT timestamp, open, high, low, close, volume FROM market_data WHERE symbol=? AND timeframe=? AND timestamp >= ? ORDER BY timestamp ASC"
            
            # Use Pandas read_sql for direct DataFrame conversion
            df = pd.read_sql_query(query, conn, params=(symbol, timeframe, cutoff_ts))
            return df
            
        except Exception as e:
            print(f"DB Load Error: {e}")
            return None

    def _clear_db_data(self, symbol, timeframe):
        """
        Delete specific data from database (Used for Force Reload / Reset).
        """
        conn = self._get_db_conn()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM market_data WHERE symbol=? AND timeframe=?", (symbol, timeframe))
            # Juga hapus cache strategi yang terkait
            cursor.execute("DELETE FROM strategy_cache WHERE symbol=? AND timeframe=?", (symbol, timeframe))
            conn.commit()
            conn.close()
        except: pass

    def _get_cached_result(self, symbol, timeframe, period, strategy):
        """
        Mengambil hasil backtest dari cache.
        Mengembalikan dict jika cache masih valid, atau None jika stale/tidak ada.
        Cache dianggap stale jika ada candle baru sejak cache terakhir disimpan.
        """
        conn = self._get_db_conn()
        if not conn: return None
        
        try:
            cursor = conn.cursor()
            
            # 1. Ambil timestamp candle terakhir dari market_data
            cursor.execute(
                "SELECT MAX(timestamp) FROM market_data WHERE symbol=? AND timeframe=?",
                (symbol, timeframe)
            )
            row = cursor.fetchone()
            latest_candle_ts = row[0] if row and row[0] else None
            
            if latest_candle_ts is None:
                conn.close()
                return None  # Tidak ada data candle sama sekali
            
            # 2. Ambil cache entry
            cursor.execute(
                "SELECT * FROM strategy_cache WHERE symbol=? AND timeframe=? AND period=? AND strategy=?",
                (symbol, timeframe, period, strategy)
            )
            cache_row = cursor.fetchone()
            conn.close()
            
            if cache_row is None:
                return None  # Cache miss — belum pernah dihitung
            
            # 3. Bandingkan timestamp: cache masih valid?
            # cache_row index: 0=symbol, 1=tf, 2=period, 3=strat, 4=net_profit,
            # 5=win_rate, 6=total_trades, 7=max_dd, 8=sharpe, 9=final_bal,
            # 10=signal_data, 11=rr_ratio, 12=cached_data_ts, 13=updated_at
            cached_data_ts = cache_row[12]
            
            if latest_candle_ts > cached_data_ts:
                return None  # Cache stale — ada candle baru
            
            # 4. Cache hit! Return hasil
            import json
            signal_data = json.loads(cache_row[10]) if cache_row[10] else {}
            
            return {
                "net_profit": cache_row[4],
                "win_rate": cache_row[5],
                "total_trades": cache_row[6],
                "max_drawdown": cache_row[7],
                "sharpe_ratio": cache_row[8],
                "final_balance": cache_row[9],
                "signal_data": signal_data,
                "rr_ratio": cache_row[11],
            }
            
        except Exception as e:
            print(f"[WARN] Cache Read Error: {e}")
            return None

    def _save_cache_result(self, symbol, timeframe, period, strategy, metrics, signal_data=None, rr_ratio="N/A"):
        """
        Menyimpan hasil backtest ke cache.
        Menggunakan INSERT OR REPLACE agar otomatis update jika sudah ada.
        """
        conn = self._get_db_conn()
        if not conn: return
        
        try:
            import json
            cursor = conn.cursor()
            
            # Ambil timestamp candle terakhir sebagai 'snapshot'
            cursor.execute(
                "SELECT MAX(timestamp) FROM market_data WHERE symbol=? AND timeframe=?",
                (symbol, timeframe)
            )
            row = cursor.fetchone()
            latest_candle_ts = row[0] if row and row[0] else 0
            
            signal_json = json.dumps(signal_data) if signal_data else "{}"
            now_str = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR REPLACE INTO strategy_cache 
                (symbol, timeframe, period, strategy, net_profit, win_rate, total_trades,
                 max_drawdown, sharpe_ratio, final_balance, signal_data, rr_ratio,
                 cached_data_ts, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol, timeframe, period, strategy,
                metrics.get('net_profit', 0),
                metrics.get('win_rate', 0),
                metrics.get('total_trades', 0),
                metrics.get('max_drawdown', 0),
                metrics.get('sharpe_ratio', 0),
                metrics.get('final_balance', 0),
                signal_json, rr_ratio,
                latest_candle_ts, now_str
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"[WARN] Cache Write Error: {e}")

    # ============================================================
    # HELPER: TIME INTERVAL CONVERSION
    # ============================================================
    def _get_interval_ms(self, interval):
        """
        Mengkonversi string interval (misal '1h') menjadi milidetik.
        Digunakan untuk Smart Fetching Logic.
        """
        if interval == '1m': return 60000
        if interval == '15m': return 900000
        if interval == '1h': return 3600000
        if interval == '4h': return 14400000
        if interval == '1d': return 86400000
        if interval in ('1w', '1wk'): return 604800000
        return 3600000 # Default 1 jam

    # ============================================================
    # 2. DATA FETCHING (SMART INCREMENTAL LOGIC)
    # Inti dari percepatan data loading
    # ============================================================
    def fetch_data(self, symbol, requested_period="1y", interval="1d", start_date=None, end_date=None, force_reload=False):
        """
        Mengambil data OHLCV dengan logika:
        1. Cek Database Lokal.
        2. Jika data lokal 'fresh' (belum lewat durasi candle), return langsung (INSTANT).
        3. Jika data lokal 'stale' (usang), download HANYA selisih data dari API.
        4. Simpan selisih ke DB, lalu load full data.
        """
        try:
            # Standardisasi interval untuk CCXT (1wk -> 1w)
            if interval == '1wk':
                interval = '1w'
            
            # Standardisasi Simbol untuk CCXT (BTC-USD -> BTC/USDT)
            symbol_ccxt = symbol.upper().replace("-", "/")
            if symbol_ccxt.endswith("/USD"):
                symbol_ccxt = symbol_ccxt.replace("/USD", "/USDT")
            
            # --- FORCE RELOAD CHECK ---
            if force_reload:
                print(f"[DATA] Force Reloading {symbol}...")
                self._clear_db_data(symbol, interval)

            # Cek Timestamp Terakhir di DB
            last_ts = self._get_last_timestamp(symbol, interval)
            now = self.exchange.milliseconds()
            since = None
            
            if last_ts:
                # Jika ada data, set titik mulai download dari (Last TS + 1 ms)
                since = last_ts + 1
            else:
                # Jika DB kosong, set titik mulai dari 3 tahun lalu (Seed Data)
                # 3 tahun = cukup untuk 2y backtest + 200+ candle warmup indikator
                since = now - (1095 * 24 * 60 * 60 * 1000) 
                print(f"[DATA] Initial Download {symbol}...")

            # --- SMART LOGIC: DYNAMIC FETCH INTERVAL ---
            # Tentukan apakah perlu fetch ke API atau tidak
            interval_ms = self._get_interval_ms(interval)
            should_fetch = False
            
            if last_ts is None:
                # Kondisi 1: Belum ada data sama sekali -> Harus Fetch
                should_fetch = True
            else:
                # Kondisi 2: Cek selisih waktu sekarang dengan data terakhir
                time_gap = now - last_ts
                # Hanya fetch jika gap waktu > durasi candle (artinya candle baru sudah close)
                # Ini mencegah spam request setiap detik
                if time_gap >= interval_ms:
                    should_fetch = True
            
            # Proses Fetch API (Hanya dijalankan jika should_fetch = True)
            new_ohlcv = []
            limit = 1000
            
            if should_fetch:
                print(f"[DATA] Fetching {symbol} {interval} from API (since={since})...")
                retry_count = 0
                max_retries = 3
                while True:
                    try:
                        ohlcv = self.exchange.fetch_ohlcv(symbol_ccxt, timeframe=interval, since=since, limit=limit)
                        
                        if not ohlcv: break
                        
                        new_ohlcv.extend(ohlcv)
                        retry_count = 0  # Reset retry on success
                        
                        # Update pointer 'since'
                        last_fetched = ohlcv[-1][0]
                        since = last_fetched + 1
                        
                        # Break condition
                        if len(ohlcv) < limit: break 
                        if len(new_ohlcv) > 50000: break # Safety limit
                        
                    except Exception as e:
                        retry_count += 1
                        if retry_count >= max_retries:
                            print(f"[DATA] Max retries reached for {symbol}: {e}")
                            break
                        print(f"[DATA] API Retry {retry_count}/{max_retries} for {symbol}: {e}")
                        import time as _time
                        _time.sleep(1)  # Wait 1s before retry
                print(f"[DATA] Downloaded {len(new_ohlcv)} new candles for {symbol} {interval}")
            else:
                pass

            # Simpan Data Baru ke Database
            if new_ohlcv:
                self._save_to_db(symbol, interval, new_ohlcv)
            
            # Load Data Lengkap dari Database untuk dikembalikan ke pemanggil
            df = self._load_from_db(symbol, interval, requested_period)
            
            if df is None or df.empty:
                # print(f"[ERROR] No data found for {symbol}")
                return None

            # Formatting DataFrame
            df['time'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Pastikan format angka float
            cols = ['open', 'high', 'low', 'close', 'volume']
            df[cols] = df[cols].apply(pd.to_numeric)
            
            # Sort dan Reset Index
            df = df.sort_values('time').reset_index(drop=True)
            
            print(f"[DATA] {symbol} {interval}: Returning {len(df)} candles (period={requested_period}, range={df.iloc[0]['time']} to {df.iloc[-1]['time']})")

            return df

        except Exception as e:
            print(f"[ERROR] Critical Data Error {symbol}: {e}")
            return None

    # ============================================================
    # 3. INDICATOR CALCULATION (LOGIC LAMA - TETAP DIPERTAHANKAN)
    # ============================================================
    def prepare_indicators(self, df):
        """
        Menghitung indikator teknikal: SMA, EMA, Bollinger, RSI, Grid, ATR.
        Logika ini tidak diubah sama sekali dari versi sebelumnya.
        """
        if df is None or len(df) < 50: return df

        # Trend Indicators
        df['sma_fast'] = df['close'].rolling(20).mean() # SMA 20
        df['sma_slow'] = df['close'].rolling(50).mean() # SMA 50
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean() # EMA 200

        # Volatility Indicators (Bollinger Bands)
        df['bb_mid'] = df['close'].rolling(20).mean()
        std = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_mid'] + (2 * std)
        df['bb_lower'] = df['bb_mid'] - (2 * std)
        
        # Momentum Indicator (RSI)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # Grid Trading Levels
        df['grid_top'] = df['high'].rolling(50).max()
        df['grid_bottom'] = df['low'].rolling(50).min()
        df['grid_mid'] = (df['grid_top'] + df['grid_bottom']) / 2

        # Risk Management Indicator (ATR)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(14).mean()

        # TIDAK menggunakan fillna(0) — biarkan NaN tetap NaN.
        # Indikator membutuhkan warmup period alami (SMA-50: 50 candle, EMA-200: 200 candle).
        # Candle yang belum valid akan di-skip oleh NaN guard di run_backtest().
        return df

    def get_market_condition(self, df, detailed=False):
        """
        Determine market condition: UPTREND, DOWNTREND, or RANGING.
        Enhanced version: EMA200 + RSI + trend strength.
        
        Args:
            df: DataFrame with OHLCV data (needs prepare_indicators() first)
            detailed: If True, return full dict. If False, return string (backward compatible)
        
        Returns:
            str or dict depending on `detailed` flag
        """
        result = {
            "condition": "UNKNOWN",
            "strength": "WEAK",
            "details": {}
        }
        
        # Check data availability
        if df is None or len(df) < 50:
            return result if detailed else "UNKNOWN"
        
        # Ensure indicators are calculated
        required_cols = ['sma_fast', 'sma_slow', 'close']
        if not all(col in df.columns for col in required_cols):
            return result if detailed else "UNKNOWN"
        
        last = df.iloc[-1]
        
        # Cek nilai NaN
        if pd.isna(last['sma_fast']) or pd.isna(last['sma_slow']):
            return result if detailed else "UNKNOWN"
        
        price = float(last['close'])
        sma20 = float(last['sma_fast'])
        sma50 = float(last['sma_slow'])
        
        # EMA200 (optional, might not exist for short data)
        ema200 = float(last['ema_200']) if 'ema_200' in df.columns and not pd.isna(last.get('ema_200', float('nan'))) else None
        
        # RSI (optional)
        rsi = float(last['rsi']) if 'rsi' in df.columns and not pd.isna(last.get('rsi', float('nan'))) else 50.0
        
        # === TREND DETECTION (Multi-Layer) ===
        condition = "RANGING"
        strength = "WEAK"
        
        # Layer 1: SMA Cross (Primary)
        sma_bullish = price > sma50 and sma20 > sma50
        sma_bearish = price < sma50 and sma20 < sma50
        
        # Layer 2: EMA200 Confirmation (Secondary)
        ema_bullish = price > ema200 if ema200 else False
        ema_bearish = price < ema200 if ema200 else False
        
        # Layer 3: RSI Confirmation
        rsi_bullish = rsi > 50
        rsi_bearish = rsi < 50
        rsi_extreme_bull = rsi > 70
        rsi_extreme_bear = rsi < 30
        
        # === SCORING ===
        bull_score = sum([sma_bullish, ema_bullish, rsi_bullish])
        bear_score = sum([sma_bearish, ema_bearish, rsi_bearish])
        
        if bull_score >= 2:
            condition = "UPTREND"
            strength = "STRONG" if bull_score == 3 else "MODERATE"
            if rsi_extreme_bull:
                strength = "STRONG (OVERBOUGHT)"
        elif bear_score >= 2:
            condition = "DOWNTREND"
            strength = "STRONG" if bear_score == 3 else "MODERATE"
            if rsi_extreme_bear:
                strength = "STRONG (OVERSOLD)"
        else:
            condition = "RANGING"
            strength = "MODERATE" if abs(rsi - 50) < 10 else "WEAK"
        
        result = {
            "condition": condition,
            "strength": strength,
            "details": {
                "price": round(price, 2),
                "sma20": round(sma20, 2),
                "sma50": round(sma50, 2),
                "ema200": round(ema200, 2) if ema200 else None,
                "rsi": round(rsi, 2),
                "bull_score": bull_score,
                "bear_score": bear_score
            }
        }
        
        if detailed:
            return result
        else:
            return condition  # Backward compatible

    # ============================================================
    # 4. UTILITIES & SIGNAL ADVICE (LOGIC LAMA)
    # ============================================================
    def slice_data_by_period(self, df, period, start_date=None, end_date=None):
        """Memotong data sesuai periode request user"""
        if df is None or df.empty: return df
        cutoff_date = None
        now = datetime.now()

        # Handle Custom Date
        if start_date and end_date:
            try:
                s_date = pd.to_datetime(start_date).replace(tzinfo=None)
                e_date = pd.to_datetime(end_date).replace(tzinfo=None)
                return df[(df['time'] >= s_date) & (df['time'] <= e_date)].copy()
            except: pass

        # Handle Preset Period
        if period == "1mo": cutoff_date = now - timedelta(days=30)
        elif period == "3mo": cutoff_date = now - timedelta(days=90)
        elif period == "6mo": cutoff_date = now - timedelta(days=180)
        elif period == "1y": cutoff_date = now - timedelta(days=365)
        elif period == "2y": cutoff_date = now - timedelta(days=730)
        elif period == "max": return df # Ambil semua

        if cutoff_date:
            return df[df['time'] >= cutoff_date].copy()
        return df

    def get_signal_advice(self, df, strategy_type):
        """
        Menghasilkan saran Entry/Exit/TP/SL berdasarkan harga terakhir.
        """
        if df is None or df.empty: return None
        last = df.iloc[-1]
        atr = last.get('atr', last['close']*0.02) # Fallback 2%
        price = last['close']
        
        return {
            "price": price,
            "atr": atr,
            "setup_long": {
                "entry": price, 
                "tp": price + (2*atr), 
                "sl": price - (1*atr)
            },
            "setup_short": {
                "entry": price, 
                "tp": price - (2*atr), 
                "sl": price + (1*atr)
            }
        }

    # ============================================================
    # 5. BACKTESTING ENGINE (UPDATED: PORTO & RISK MM IMPLEMENTATION)
    # ============================================================
    def run_backtest(self, raw_df, strategy_type, requested_period="1y", start_date=None, end_date=None, direction="LONG", interval="1d"):
        """
        Menjalankan simulasi trading dengan opsi Risk Management (Kelompok B).
        Args:
            direction: "LONG" (Buy Low, Sell High) or "SHORT" (Sell High, Buy Low)
        """
        # 1. Siapkan Indikator pada data mentah
        full_df = self.prepare_indicators(raw_df.copy())
        
        # 2. Potong Data sesuai periode yang diminta
        df = self.slice_data_by_period(full_df, requested_period, start_date, end_date)
        
        print(f"[BACKTEST] {strategy_type} | raw={len(raw_df)} candles | indicators={len(full_df)} | sliced({requested_period})={len(df)} candles | capital={self.initial_capital}")
        
        # --- ACCOUNT INITIALIZATION ---
        capital = self.initial_capital        # Cash
        initial_capital = self.initial_capital # Starting Capital (for reference)
        peak_capital = capital                 # Peak Portfolio Value (for High Watermark)
        
        position_size = 0  # Number of Coins held
        entry_price = 0    # Average buy price
        
        markers = []       # Chart Markers (Buy/Sell arrows)
        trades = []        # Trade History
        equity_curve = []  # Balance Growth Chart
        
        # --- RISK MANAGEMENT CONFIGURATION (PORTO & RISK MM) ---
        # Default: Disable Risk Module (For Basic Strategies / Group A)
        use_risk_mm = False
        max_porto_dd = 1.0  # 100% (Unlimited / Immune to Margin Call)
        risk_per_trade = 1.0 # 100% (All In - High Risk)

        # Detect Group B Strategies (_PRO)
        base_strategy = strategy_type
        if "_PRO" in strategy_type:
            use_risk_mm = True
            base_strategy = strategy_type.replace("_PRO", "") # Get base strategy name
            
            # 1. RISK PER TRADE (Kelly Criterion Simplification)
            # We risk 2% of capital per trade (Conservative Standard)
            risk_per_trade = 0.02 
            
            # 2. MAX PORTFOLIO DRAWDOWN (Specific per Strategy - As Requested)
            if base_strategy == "MEAN_REVERSAL":
                max_porto_dd = 0.30  # Max Drawdown 30% (Stop Total if lost 30%)
            elif base_strategy == "GRID":
                max_porto_dd = 0.50  # Grid needs 50% breathing room
            elif base_strategy == "MOMENTUM":
                max_porto_dd = 0.20  # Momentum must be strict 20%
            elif base_strategy == "MULTITIMEFRAME":
                max_porto_dd = 0.25  # MultiTF moderate 25%
            elif base_strategy == "MIX_STRATEGY":
                max_porto_dd = 0.25  # MIX_STRATEGY PRO moderate 25%

        # Data Validation
        if df.empty or len(df) < 5:
            return df, [], self.calculate_metrics([], capital, 0, capital, []), []

        start_price = df.iloc[0]['close']
        df = df.reset_index(drop=True)
        is_blown_up = False  # Status if account is "Blown Up" (Hit Drawdown Limit)

        # --- PRE-COMPUTE MIX_STRATEGY MARKET CONDITIONS (O(n) not O(n²)) ---
        # get_market_condition(df.iloc[:i+1]) is O(n) — calling it per bar = O(n²).
        # Pre-compute once here, then use market_conditions[i] inside the loop.
        base_strat_check = strategy_type.replace("_PRO", "")
        if base_strat_check == "MIX_STRATEGY":
            market_conditions = [
                self.get_market_condition(df.iloc[:idx+1])
                for idx in range(len(df))
            ]
        else:
            market_conditions = None

        # --- BAR-BY-BAR SIMULATION LOOP ---
        for i in range(1, len(df)):
            curr = df.iloc[i]
            prev = df.iloc[i-1]
            ts = int(curr['time'].timestamp())
            
            # Hitung Nilai Aset Saat Ini (Mark to Market)
            # Jika punya posisi, nilai = (Jumlah Koin * Harga Sekarang) + Sisa Cash
            current_equity = capital if position_size == 0 else (position_size * curr['close']) + 0
            # Catatan: Variabel 'capital' saat punya posisi dianggap 0 di logic All-In, 
            # tapi di Logic RiskMM, 'capital' adalah sisa cash yang tidak dibelikan koin.
            if use_risk_mm and position_size > 0:
                current_equity = (position_size * curr['close']) + capital

            # --- LOGIC 1: MAX DRAWDOWN GUARD (CIRCUIT BREAKER) ---
            if current_equity > peak_capital: 
                peak_capital = current_equity # Update High Watermark
            
            # Hitung Drawdown saat ini (%)
            current_dd = 0
            if peak_capital > 0:
                current_dd = (peak_capital - current_equity) / peak_capital
            
            # Cek apakah melanggar batas Max Drawdown?
            if use_risk_mm and current_dd >= max_porto_dd:
                # CUT LOSS GLOBAL: Tutup semua posisi & Berhenti Trading Selamanya
                if position_size > 0:
                    liquidated_value = position_size * curr['close']
                    capital += liquidated_value # Uang kembali ke cash
                    
                    pnl = (curr['close'] - entry_price) / entry_price
                    trades.append({'pnl_pct': pnl, 'reason': 'MAX_DD_HIT'})
                    
                    position_size = 0
                    markers.append({'time': ts, 'position': 'aboveBar', 'color': '#000000', 'shape': 'arrowDown', 'text': 'STOP (Risk)'})
                
                is_blown_up = True # Tandai akun mati
            
            # Jika akun sudah mati, catat equity flat dan skip logic trading
            if is_blown_up:
                equity_curve.append({'time': ts, 'value': capital})
                continue

            # GUARD: Skip candle jika indikator utama belum valid (warmup period)
            # SMA-50 butuh 50 candle, RSI butuh 14+1, ATR butuh 14+1 candle.
            if pd.isna(curr.get('sma_fast')) or pd.isna(curr.get('sma_slow')) or \
               pd.isna(curr.get('rsi')) or pd.isna(curr.get('bb_upper')) or \
               pd.isna(curr.get('atr')):
                equity_val = capital + (position_size * curr['close']) if position_size != 0 else capital
                equity_curve.append({'time': ts, 'value': equity_val})
                continue

            # --- STRATEGY SIGNAL GENERATOR ---
            signal = "HOLD"
            base_strategy = strategy_type.replace("_PRO", "")

            # --- LONG LOGIC ---
            if direction == "LONG":
                if base_strategy == "MOMENTUM":
                    if prev['sma_fast'] < prev['sma_slow'] and curr['sma_fast'] > curr['sma_slow']: signal = "BUY"
                    elif prev['sma_fast'] > prev['sma_slow'] and curr['sma_fast'] < curr['sma_slow']: signal = "SELL"
                
                elif base_strategy == "MEAN_REVERSAL":
                    if curr['rsi'] < 30 and curr['close'] < curr['bb_lower']: signal = "BUY"
                    elif curr['rsi'] > 70 and curr['close'] > curr['bb_upper']: signal = "SELL"
                
                elif base_strategy == "GRID":
                    buy_zone = curr['grid_bottom'] + (curr['grid_top'] - curr['grid_bottom']) * 0.2
                    sell_zone = curr['grid_top'] - (curr['grid_top'] - curr['grid_bottom']) * 0.2
                    if curr['close'] <= buy_zone: signal = "BUY"
                    elif curr['close'] >= sell_zone: signal = "SELL"
                
                elif base_strategy == "MULTITIMEFRAME":
                    is_uptrend = curr['close'] > curr['ema_200']
                    if is_uptrend and curr['rsi'] < 40: signal = "BUY"
                    elif curr['rsi'] > 75: signal = "SELL"
                
                elif base_strategy == "MIX_STRATEGY":
                    cond = market_conditions[i] if market_conditions else "RANGING"
                    if cond == "UPTREND": # Momentum Logic
                        if prev['sma_fast'] < prev['sma_slow'] and curr['sma_fast'] > curr['sma_slow']: signal = "BUY"
                        elif prev['sma_fast'] > prev['sma_slow'] and curr['sma_fast'] < curr['sma_slow']: signal = "SELL"
                    elif cond == "RANGING": # Reversal Logic
                        if curr['rsi'] < 30: signal = "BUY"
                        elif curr['rsi'] > 70: signal = "SELL"
                    else: signal = "SELL"

            # --- SHORT LOGIC ---
            elif direction == "SHORT":
                if base_strategy == "MOMENTUM":
                    # Short Signal: Fast Cross Below Slow
                    if prev['sma_fast'] > prev['sma_slow'] and curr['sma_fast'] < curr['sma_slow']: signal = "ENTRY_SHORT"
                    elif prev['sma_fast'] < prev['sma_slow'] and curr['sma_fast'] > curr['sma_slow']: signal = "EXIT_SHORT"
                
                elif base_strategy == "MEAN_REVERSAL":
                    # Short Signal: RSI > 70 (Overbought)
                    if curr['rsi'] > 70 and curr['close'] > curr['bb_upper']: signal = "ENTRY_SHORT"
                    elif curr['rsi'] < 30 and curr['close'] < curr['bb_lower']: signal = "EXIT_SHORT"
                
                elif base_strategy == "GRID":
                    # Short Signal: Sell at Top
                    buy_zone = curr['grid_bottom'] + (curr['grid_top'] - curr['grid_bottom']) * 0.2
                    sell_zone = curr['grid_top'] - (curr['grid_top'] - curr['grid_bottom']) * 0.2
                    if curr['close'] >= sell_zone: signal = "ENTRY_SHORT"
                    elif curr['close'] <= buy_zone: signal = "EXIT_SHORT"
                
                elif base_strategy == "MULTITIMEFRAME":
                    # Short Signal: Downtrend + RSI > 60
                    is_downtrend = curr['close'] < curr['ema_200']
                    if is_downtrend and curr['rsi'] > 60: signal = "ENTRY_SHORT"
                    elif curr['rsi'] < 25: signal = "EXIT_SHORT"
                
                elif base_strategy == "MIX_STRATEGY":
                    cond = market_conditions[i] if market_conditions else "RANGING"
                    if cond == "DOWNTREND":
                         # Momentum Short inside Downtrend
                         if prev['sma_fast'] > prev['sma_slow'] and curr['sma_fast'] < curr['sma_slow']: signal = "ENTRY_SHORT"
                         elif prev['sma_fast'] < prev['sma_slow'] and curr['sma_fast'] > curr['sma_slow']: signal = "EXIT_SHORT"
                    elif cond == "RANGING":
                         # Reversal Short inside Range/Sideways
                         if curr['rsi'] > 70: signal = "ENTRY_SHORT"
                         elif curr['rsi'] < 30: signal = "EXIT_SHORT"
                    else: signal = "EXIT_SHORT"

            # --- EXECUTION LOGIC ---
            
            # LONG EXECUTION (BUY / SELL)
            if direction == "LONG":
                # BUY logic
                if signal == "BUY" and position_size == 0:
                    if use_risk_mm:
                        atr = curr.get('atr', curr['close']*0.02)
                        sl_dist = atr * 1.5
                        risk_amount = capital * risk_per_trade
                        if sl_dist > 0:
                            position_value = risk_amount / (sl_dist / curr['close'])
                            position_value = min(position_value, capital)
                        else: position_value = capital
                    else:
                        position_value = capital

                    # Kurangi biaya entry (taker fee + slippage)
                    entry_cost = position_value * ROUND_TRIP_COST
                    actual_invest = position_value - entry_cost
                    position_size = actual_invest / curr['close']
                    capital -= position_value  # Deduct full amount including cost

                    entry_price = curr['close']
                    markers.append({'time': ts, 'position': 'belowBar', 'color': '#00ff41', 'shape': 'arrowUp', 'text': 'BUY'})

                # SELL logic
                elif signal == "SELL" and position_size > 0:
                    sell_gross = position_size * curr['close']
                    # Kurangi biaya exit (taker fee + slippage)
                    exit_cost = sell_gross * ROUND_TRIP_COST
                    sell_value = sell_gross - exit_cost
                    capital += sell_value
                    pnl = (curr['close'] - entry_price) / entry_price
                    trades.append({'pnl_pct': pnl, 'reason': 'SIGNAL'})
                    position_size = 0
                    markers.append({'time': ts, 'position': 'aboveBar', 'color': '#ff0055', 'shape': 'arrowDown', 'text': 'SELL'})

            # SHORT EXECUTION (ENTRY_SHORT / EXIT_SHORT)
            elif direction == "SHORT":
                # ENTRY SHORT (Sell to Open)
                if signal == "ENTRY_SHORT" and position_size == 0:
                    # Logic: We treat capital as collateral.
                    if use_risk_mm:
                         atr = curr.get('atr', curr['close']*0.02)
                         sl_dist = atr * 1.5
                         risk_amount = capital * risk_per_trade
                         if sl_dist > 0:
                            position_value = risk_amount / (sl_dist / curr['close'])
                            position_value = min(position_value, capital)
                         else: position_value = capital
                         size_to_short = position_value / curr['close']
                    else:
                         size_to_short = capital / curr['close']

                    position_size = -size_to_short
                    # Proceed dari short sale dikurangi entry cost
                    short_proceed = size_to_short * curr['close']
                    entry_cost = short_proceed * ROUND_TRIP_COST
                    capital += (short_proceed - entry_cost)
                    entry_price = curr['close']
                    markers.append({'time': ts, 'position': 'aboveBar', 'color': '#ff0055', 'shape': 'arrowDown', 'text': 'SHORT'})

                # EXIT SHORT (Buy to Cover)
                elif signal == "EXIT_SHORT" and position_size < 0:
                     size_to_cover = abs(position_size)
                     cost_to_cover = size_to_cover * curr['close']
                     # Tambahkan exit cost (taker fee + slippage)
                     exit_cost = cost_to_cover * ROUND_TRIP_COST
                     capital -= (cost_to_cover + exit_cost)

                     pnl = (entry_price - curr['close']) / entry_price
                     trades.append({'pnl_pct': pnl, 'reason': 'SIGNAL'})

                     position_size = 0
                     markers.append({'time': ts, 'position': 'belowBar', 'color': '#00ff41', 'shape': 'arrowUp', 'text': 'COVER'})
            
            # Record Equity Harian
            final_daily_equity = capital + (position_size * curr['close'])
            equity_curve.append({'time': ts, 'value': final_daily_equity})

        # Hitung Final Result setelah Loop Selesai
        final_equity = capital + (position_size * df.iloc[-1]['close'])
        
        bh_return = 0
        bh_final = self.initial_capital
        if start_price > 0:
            bh_return = ((df.iloc[-1]['close'] - start_price) / start_price) * 100
            bh_final = self.initial_capital * (1 + (bh_return / 100))

        metrics = self.calculate_metrics(trades, final_equity, bh_return, bh_final, equity_curve, timeframe=interval)
        
        # Tambahkan Info Drawdown Limit ke Metrics agar Frontend Tahu
        metrics['max_porto_limit'] = f"{max_porto_dd*100}%" if use_risk_mm else "Unlimited"
        metrics['strategy_mode'] = "PRO (Risk Managed)" if use_risk_mm else "BASIC (Aggressive)"
        metrics['trades_list'] = trades
        
        return df, markers, metrics, equity_curve

    # ============================================================
    # 5B. DUAL BACKTEST (LONG + SHORT SIMULTANEOUS) — PnL Segmentation
    # ============================================================
    def run_dual_backtest(self, raw_df, strategy_type, requested_period="1y", start_date=None, end_date=None):
        """
        Run LONG and SHORT backtests on the same data, return segmented PnL.
        Used for Objective 3: PnL Segmentation & Filtering.
        
        Returns:
            dict with pnl_long, pnl_short, pnl_combined, curve_long, curve_short
        """
        # Run LONG backtest
        df_long, markers_long, metrics_long, curve_long = self.run_backtest(
            raw_df.copy(), strategy_type, requested_period=requested_period,
            start_date=start_date, end_date=end_date, direction="LONG"
        )
        
        # Run SHORT backtest
        df_short, markers_short, metrics_short, curve_short = self.run_backtest(
            raw_df.copy(), strategy_type, requested_period=requested_period,
            start_date=start_date, end_date=end_date, direction="SHORT"
        )
        
        # Combine metrics
        combined_metrics = self._combine_metrics(metrics_long, metrics_short)
        
        # Merge equity curves (average of both)
        curve_combined = []
        min_len = min(len(curve_long), len(curve_short))
        for i in range(min_len):
            curve_combined.append({
                'time': curve_long[i]['time'],
                'value': (curve_long[i]['value'] + curve_short[i]['value']) / 2
            })
        
        return {
            "pnl_long": metrics_long,
            "pnl_short": metrics_short,
            "pnl_combined": combined_metrics,
            "curve_long": curve_long,
            "curve_short": curve_short,
            "curve_combined": curve_combined,
            "markers_long": markers_long,
            "markers_short": markers_short
        }

    def _combine_metrics(self, long_metrics, short_metrics):
        """
        Combine LONG and SHORT metrics into a single combined view.
        """
        combined_profit = long_metrics.get('net_profit', 0) + short_metrics.get('net_profit', 0)
        combined_trades = long_metrics.get('total_trades', 0) + short_metrics.get('total_trades', 0)
        
        # Weighted average win rate
        long_trades = long_metrics.get('total_trades', 0)
        short_trades = short_metrics.get('total_trades', 0)
        if combined_trades > 0:
            combined_wr = (
                (long_metrics.get('win_rate', 0) * long_trades +
                 short_metrics.get('win_rate', 0) * short_trades) / combined_trades
            )
        else:
            combined_wr = 0
        
        # Take the worse drawdown
        combined_dd = max(long_metrics.get('max_drawdown', 0), short_metrics.get('max_drawdown', 0))
        
        # Average Sharpe
        combined_sharpe = (long_metrics.get('sharpe_ratio', 0) + short_metrics.get('sharpe_ratio', 0)) / 2
        
        return {
            "initial_balance": long_metrics.get('initial_balance', self.initial_capital),
            "final_balance": round(long_metrics.get('final_balance', 0) + short_metrics.get('final_balance', 0) - self.initial_capital, 2),
            "net_profit": round(combined_profit, 2),
            "win_rate": round(combined_wr, 2),
            "total_trades": combined_trades,
            "total_trades_long": long_trades,
            "total_trades_short": short_trades,
            "buy_hold_return": long_metrics.get('buy_hold_return', 0),
            "max_drawdown": round(combined_dd, 2),
            "sharpe_ratio": round(combined_sharpe, 2),
            "pnl_long": round(long_metrics.get('net_profit', 0), 2),
            "pnl_short": round(short_metrics.get('net_profit', 0), 2)
        }

    def calculate_metrics(self, trades, final, bh_ret, bh_fin, curve, timeframe="1d"):
        """Menghitung performa trading (Win Rate, Drawdown, Sharpe, dll)"""
        total_trades = len(trades)
        wins = [t for t in trades if t['pnl_pct'] > 0]
        losses = [t for t in trades if t['pnl_pct'] <= 0]
        win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
        net_profit = final - self.initial_capital

        # Profit Factor
        gross_profit = sum(t['pnl_pct'] for t in wins)
        gross_loss   = abs(sum(t['pnl_pct'] for t in losses))
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0.0

        # Max Drawdown
        vals = [e['value'] for e in curve]
        dd = 0
        if vals:
            peak = vals[0]
            for v in vals:
                if v > peak: peak = v
                if peak > 0:
                    d = (peak - v)/peak
                    if d > dd: dd = d

        # Sharpe Ratio — timeframe-aware annualization
        sharpe = 0
        if len(vals) > 1:
            series = pd.Series(vals)
            returns = series.pct_change().dropna()
            if returns.std() != 0:
                annualization = BARS_PER_YEAR.get(timeframe, 252)
                sharpe = (returns.mean() / returns.std()) * np.sqrt(annualization)

        # Calmar Ratio — also timeframe-aware
        calmar = 0
        if len(vals) > 1 and dd > 0:
            total_return = (final / self.initial_capital) - 1
            trading_bars = len(vals)
            annualization = BARS_PER_YEAR.get(timeframe, 252)
            annual_return = total_return * (annualization / max(trading_bars, 1))
            calmar = annual_return / dd if dd > 0 else 0

        return {
            "initial_balance": self.initial_capital,
            "final_balance": round(final, 2),
            "net_profit": round(net_profit, 2),
            "win_rate": round(win_rate, 2),
            "total_trades": total_trades,
            "buy_hold_return": round(bh_ret, 2),
            "max_drawdown": round(dd*100, 2),
            "sharpe_ratio": round(sharpe, 2),
            "calmar_ratio": round(calmar, 2),
            "profit_factor": profit_factor,
        }

    # ============================================================
    # 6. REAL EXECUTION (CCXT BRIDGE)
    # ============================================================
    def calculate_position_size(self, symbol, entry, sl, risk_per_trade_pct=0.01):
        """Menghitung ukuran posisi berdasarkan resiko (Risk Management)"""
        if self.auth_mode not in ["TESTNET", "REAL"]:
            print("[WARN] Cannot calc size: Auth Mode is PUBLIC")
            return 0

        try:
            bal = self.exchange.fetch_balance()
            equity = bal['USDT']['total']
            risk = equity * risk_per_trade_pct
            dist = abs(entry - sl) / entry
            if dist == 0: return 0
            size_usd = min(risk / dist, bal['USDT']['free'])
            return size_usd / entry
        except: return 0

    def execute_order(self, symbol, side, amount):
        """Eksekusi Order ke Exchange (Testnet atau Real)"""
        if self.auth_mode not in ["TESTNET", "REAL"]: return None
        try:
            sym = symbol.replace("-", "/")
            if sym.endswith("USD"): sym += "T"
            order = self.exchange.create_order(sym, 'market', side, amount)
            print(f"[OK] [{'🧪 TESTNET' if self.auth_mode == 'TESTNET' else '💰 REAL'}] Order {side.upper()} {amount:.6f} {sym} — ID: {order.get('id', 'N/A')}")
            return order
        except Exception as e: 
            print(f"[ERROR] Exec Error: {e}")
            return None

    def _log_trade(self, symbol, side, qty, price, strategy='', timeframe='', order_id='', status='FILLED', pnl=0, notes=''):
        """
        Mencatat trade ke database lokal untuk tracking & portfolio.
        """
        conn = self._get_db_conn()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO trade_log (timestamp, symbol, side, quantity, price, strategy, timeframe, order_id, status, pnl, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (datetime.now(), symbol, side, qty, price, strategy, timeframe, order_id, status, pnl, notes))
            conn.commit()
        except Exception as e:
            print(f"[ERROR] [DB ERROR] Log Trade Failed: {e}")
        finally:
            conn.close()

    # ============================================================
    # 6. STRATEGY OPTIMIZER (FOR SCANNER)
    # ============================================================
    def calculate_consistency_score(self, equity_curve):
        """
        Calculate R-Squared (R^2) of the equity curve vs a perfect straight line.
        100 = Perfect straight line (consistent growth).
        0 = Random noise.
        """
        if len(equity_curve) < 2: return 0.0

        # Use float64 to avoid overflow during sum_xx calculations
        y = np.array([p['value'] for p in equity_curve], dtype=np.float64)
        x = np.arange(len(y), dtype=np.float64)
        
        # Fit Linear Regression (y = mx + c)
        n = len(x)
        sum_x = np.sum(x)
        sum_y = np.sum(y)
        sum_xy = np.sum(x * y)
        sum_xx = np.sum(x * x)
        
        denominator = (n * sum_xx - sum_x * sum_x)
        if denominator == 0: return 0.0
        
        m = (n * sum_xy - sum_x * sum_y) / denominator
        c = (sum_y - m * sum_x) / n
        
        # Proper R^2 Calculation
        y_mean = np.mean(y)
        ss_tot = np.sum((y - y_mean) ** 2)
        
        y_pred = m * x + c
        ss_res = np.sum((y - y_pred) ** 2)
        
        if ss_tot == 0: return 0.0
        
        r_squared = 1 - (ss_res / ss_tot)
        
        return max(0, min(100, r_squared * 100))

    def find_best_strategy_for_symbol(self, symbol, timeframe="1h", period="1y", allowed_modes=["LONG"]):
        """
        Mencari strategi terbaik untuk satu simbol dengan mencoba SEMUA kombinasi strategi.
        Ranking berdasarkan Consistency Score (R^2) > Profit > Win Rate.
        Returns: Dict or None
        """
        # Fetch Data Sekali Saja (Smart Fetch)
        df_raw = self.fetch_data(symbol, requested_period="max", interval=timeframe)
        
        # Validate Data
        if df_raw is None or len(df_raw) < 50:
             # Try simple fetch if "max" failed (fallback)
             return None

        strategies = [
            "MOMENTUM", "MEAN_REVERSAL", "GRID", "MULTITIMEFRAME",
            "MOMENTUM_PRO", "MEAN_REVERSAL_PRO", "GRID_PRO", "MULTITIMEFRAME_PRO",
            "MIX_STRATEGY", "MIX_STRATEGY_PRO"
        ]
        
        best_result = None
        best_score = -100 # Allow negative score logic if needed, but we prefer positive
        
        # Loop semua mode dan strategi
        for mode in allowed_modes:
            for strat in strategies:
                # Run Backtest
                # Optimization: We could skip heavy logic if not needed, 
                # but run_backtest is reasonably fast for 1 symbol.
                _, _, metrics, equity_data = self.run_backtest(df_raw, strat, requested_period=period, direction=mode)
                
                if not metrics or metrics.get('total_trades', 0) < 3: continue # Skip very few trades
                
                net_profit = metrics.get('net_profit', 0)
                if net_profit <= 0: continue # Focus on profitable strategies
                
                # Hitung Consistency Score
                consistency = self.calculate_consistency_score(equity_data)
                
                # Scoring Function: 
                # Priority 1: Consistency (ensure smooth growth)
                # Priority 2: Profitability
                # Score = (Consistency * 0.6) + (Profit% * 0.4) 
                # (Assuming Profit% is comparable to 0-100 scale. If profit is 500%, it dominates. We cap it.)
                
                capped_profit = min(200, net_profit)
                final_score = (consistency * 0.6) + (capped_profit * 0.4)
                
                if final_score > best_score:
                    best_score = final_score
                    best_result = {
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "period": period,
                        "strategy": strat,
                        "direction": mode,
                        "consistency_score": round(consistency, 2),
                        "net_profit": round(net_profit, 2),
                        "win_rate": metrics.get('win_rate', 0),
                        "total_trades": metrics.get('total_trades', 0),
                        "equity_curve": equity_data, 
                        "score": round(final_score, 2)
                    }
        
        return best_result

    def _get_trade_history(self, limit=50):
        """Ambil riwayat trade dari database."""
        conn = self._get_db_conn()
        if not conn: return []
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trade_log ORDER BY id DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            conn.close()
            columns = ['id', 'symbol', 'side', 'qty', 'price', 'strategy', 'timeframe', 'order_id', 'status', 'pnl', 'notes', 'created_at']
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            print(f"[WARN] Trade History Error: {e}")
            return []

    def _get_bot_status(self):
        """Hitung statistik bot dari trade_log."""
        conn = self._get_db_conn()
        if not conn: return {}
        try:
            cursor = conn.cursor()
            
            # Total trades
            cursor.execute("SELECT COUNT(*) FROM trade_log")
            total_trades = cursor.fetchone()[0]
            
            # Total PnL
            cursor.execute("SELECT COALESCE(SUM(pnl), 0) FROM trade_log")
            total_pnl = cursor.fetchone()[0]
            
            # Win rate
            cursor.execute("SELECT COUNT(*) FROM trade_log WHERE pnl > 0")
            wins = cursor.fetchone()[0]
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            
            # Active positions (BUY tanpa SELL berikutnya)
            cursor.execute("""
                SELECT symbol, side, qty, price, strategy, timeframe, created_at 
                FROM trade_log 
                ORDER BY id DESC LIMIT 20
            """)
            recent = cursor.fetchall()
            columns = ['symbol', 'side', 'qty', 'price', 'strategy', 'timeframe', 'created_at']
            recent_trades = [dict(zip(columns, row)) for row in recent]
            
            # Total volume
            cursor.execute("SELECT COALESCE(SUM(qty * price), 0) FROM trade_log")
            total_volume = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "total_trades": total_trades,
                "total_pnl": round(total_pnl, 2),
                "win_rate": round(win_rate, 1),
                "total_volume": round(total_volume, 2),
                "recent_trades": recent_trades,
                "mode": self.auth_mode
            }
        except Exception as e:
            print(f"[WARN] Bot Status Error: {e}")
            return {}