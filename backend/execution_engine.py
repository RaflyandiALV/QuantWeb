import ccxt
import os
import math
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ExecutionManager:
    """
    EXECUTION ENGINE (Diadaptasi dari bot_testing.ipynb)
    Tugas: Mengirim order eksekusi (Jual/Beli) ke Binance.
    """
    
    def __init__(self, use_testnet=True):
        self.api_key = os.getenv("BINANCE_API_KEY")
        self.api_secret = os.getenv("BINANCE_SECRET_KEY")
        self.use_testnet = use_testnet
        
        # Inisialisasi Exchange (Binance)
        self.exchange = ccxt.binance({
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'},
            'timeout': 30000  # Timeout 30 detik (untuk koneksi lambat/VPN)
        })
        
        # Mode Testnet (Uang Virtual)
        if self.use_testnet:
            self.exchange.set_sandbox_mode(True)
            print("[INFO] EXECUTION ENGINE: Running in TESTNET Mode (Sandbox)")
        else:
            print("[WARN] EXECUTION ENGINE: Running in REAL MONEY Mode")

    def get_balance(self, asset="USDT"):
        """
        Mengecek saldo aset tertentu di dompet Spot.
        """
        try:
            balance = self.exchange.fetch_balance()
            total = balance['total'].get(asset, 0.0)
            free = balance['free'].get(asset, 0.0)
            return {"total": total, "free": free}
        except Exception as e:
            print(f"[ERROR] Error Get Balance: {e}")
            return {"total": 0.0, "free": 0.0}

    def get_current_price(self, symbol):
        """
        Mengambil harga market terakhir untuk perhitungan jumlah koin.
        """
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            print(f"[ERROR] Error Fetch Price {symbol}: {e}")
            return None

    def execute_order(self, symbol, side, amount_usd_size):
        """
        Eksekusi Market Order berdasarkan jumlah Dollar.
        
        Parameters:
        - symbol: 'BTC/USDT' (Format CCXT)
        - side: 'buy' atau 'sell'
        - amount_usd_size: Jumlah uang yang dipakai (misal $50)
        """
        try:
            # 1. Pastikan simbol formatnya benar (BTC/USDT)
            symbol = symbol.replace("-", "/")
            if symbol.endswith("/USD"): symbol = symbol.replace("/USD", "/USDT")

            # 2. Ambil harga terakhir
            price = self.get_current_price(symbol)
            if not price:
                return {"status": "error", "message": "Gagal mengambil harga pasar"}

            # 3. Hitung jumlah koin yang didapat
            # amount_coin = Uang / Harga
            amount_coin = amount_usd_size / price
            
            # (Opsional) Normalisasi presisi agar tidak ditolak Binance
            # Binance biasanya minta presisi tertentu, tapi ccxt sering handle otomatis.
            # Kita bulatkan 5 desimal untuk aman.
            amount_coin = float(self.exchange.amount_to_precision(symbol, amount_coin))

            print(f"[ORDER] SENDING ORDER: {side.upper()} {symbol}")
            print(f"   Value: ${amount_usd_size} | Amount: {amount_coin} @ ${price}")

            # 4. Kirim Order ke Binance
            order = self.exchange.create_order(symbol, 'market', side, amount_coin)
            
            print(f"[SUCCESS] ORDER SUCCESS! ID: {order['id']}")
            return {
                "status": "success",
                "order_id": order['id'],
                "filled": order['filled'],
                "average_price": order['average'],
                "cost": order['cost']
            }

        except Exception as e:
            print(f"[FAILED] ORDER FAILED: {e}")
            return {"status": "error", "message": str(e)}


class FuturesExecutionManager:
    """
    FUTURES EXECUTION ENGINE (Gap 4)
    Supports LONG/SHORT with configurable leverage, SL/TP orders, and paper mode.
    """

    def __init__(self, use_testnet=True, paper_mode=True, leverage=1):
        self.api_key = os.getenv("BINANCE_API_KEY")
        self.api_secret = os.getenv("BINANCE_SECRET_KEY")
        self.use_testnet = use_testnet
        self.paper_mode = paper_mode
        self.leverage = leverage

        # Paper mode tracking
        self._paper_positions = {}  # {symbol: {side, qty, entry_price, sl, tp, pnl}}
        self._paper_balance = 10000.0  # Starting paper balance
        self._paper_trades = []

        if not paper_mode:
            try:
                self.exchange = ccxt.binance({
                    'apiKey': self.api_key,
                    'secret': self.api_secret,
                    'enableRateLimit': True,
                    'options': {'defaultType': 'future'},
                    'timeout': 30000,
                })
                if self.use_testnet:
                    self.exchange.set_sandbox_mode(True)
                    print("[FUTURES] Running in TESTNET Futures Mode (Sandbox)")
                else:
                    print("[FUTURES] ⚠️ Running in REAL MONEY Futures Mode")

                # Set leverage
                self._exchange_ready = True
            except Exception as e:
                print(f"[FUTURES] Exchange init failed: {e}")
                self._exchange_ready = False
                self.paper_mode = True
        else:
            self._exchange_ready = False
            print(f"[FUTURES] Running in PAPER MODE (Simulated) | Balance: ${self._paper_balance:,.2f} | Leverage: {self.leverage}x")

    def set_leverage(self, symbol: str, leverage: int):
        """Set leverage for a symbol."""
        self.leverage = leverage
        if self._exchange_ready and not self.paper_mode:
            try:
                sym = symbol.replace("-", "/").replace("/", "")
                self.exchange.fapiPrivate_post_leverage({
                    'symbol': sym,
                    'leverage': leverage
                })
                print(f"[FUTURES] Leverage set to {leverage}x for {symbol}")
            except Exception as e:
                print(f"[FUTURES] Leverage set error: {e}")

    def get_balance(self) -> dict:
        """Get account balance."""
        if self.paper_mode:
            unrealized_pnl = sum(p.get('pnl', 0) for p in self._paper_positions.values())
            return {
                "total": round(self._paper_balance + unrealized_pnl, 2),
                "free": round(self._paper_balance, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
                "mode": "PAPER"
            }

        try:
            bal = self.exchange.fetch_balance()
            return {
                "total": round(bal.get('USDT', {}).get('total', 0), 2),
                "free": round(bal.get('USDT', {}).get('free', 0), 2),
                "unrealized_pnl": 0,
                "mode": "TESTNET" if self.use_testnet else "LIVE"
            }
        except Exception as e:
            print(f"[FUTURES] Balance error: {e}")
            return {"total": 0, "free": 0, "unrealized_pnl": 0, "mode": "ERROR"}

    def get_current_price(self, symbol: str) -> float:
        """Get current futures price."""
        if self.paper_mode or not self._exchange_ready:
            # Use spot ccxt as price reference
            try:
                temp_ex = ccxt.binance({'enableRateLimit': True, 'timeout': 15000})
                sym = symbol.replace("-", "/")
                ticker = temp_ex.fetch_ticker(sym)
                return ticker['last']
            except Exception as e:
                print(f"[FUTURES] Price fetch error: {e}")
                return 0

        try:
            sym = symbol.replace("-", "/") + ":USDT"
            ticker = self.exchange.fetch_ticker(sym)
            return ticker['last']
        except Exception as e:
            print(f"[FUTURES] Price error: {e}")
            return 0

    def open_position(self, symbol: str, side: str, amount_usd: float,
                      stop_loss: float = None, take_profit: float = None) -> dict:
        """
        Open a futures position.

        Args:
            symbol: 'BTC-USDT'
            side: 'LONG' or 'SHORT'
            amount_usd: Dollar amount to trade
            stop_loss: SL price
            take_profit: TP price

        Returns:
            {status, order_id, entry_price, qty, side, sl, tp}
        """
        price = self.get_current_price(symbol)
        if not price:
            return {"status": "error", "message": "Failed to fetch price"}

        qty = (amount_usd * self.leverage) / price

        if self.paper_mode:
            return self._paper_open(symbol, side, price, qty, amount_usd, stop_loss, take_profit)

        # Live/Testnet execution
        try:
            sym = symbol.replace("-", "/") + ":USDT"
            ccxt_side = 'buy' if side.upper() == 'LONG' else 'sell'

            qty = float(self.exchange.amount_to_precision(sym, qty))

            # Main order
            order = self.exchange.create_order(sym, 'market', ccxt_side, qty)
            order_id = order.get('id', 'unknown')

            print(f"[FUTURES] OPENED: {side} {symbol} | Qty: {qty} @ ${price:,.2f}")

            # Place SL/TP as separate orders
            if stop_loss:
                try:
                    sl_side = 'sell' if side.upper() == 'LONG' else 'buy'
                    self.exchange.create_order(sym, 'stop_market', sl_side, qty,
                                               params={'stopPrice': stop_loss, 'closePosition': True})
                except Exception as e:
                    print(f"[FUTURES] SL order error: {e}")

            if take_profit:
                try:
                    tp_side = 'sell' if side.upper() == 'LONG' else 'buy'
                    self.exchange.create_order(sym, 'take_profit_market', tp_side, qty,
                                               params={'stopPrice': take_profit, 'closePosition': True})
                except Exception as e:
                    print(f"[FUTURES] TP order error: {e}")

            return {
                "status": "success",
                "order_id": order_id,
                "entry_price": price,
                "qty": qty,
                "side": side.upper(),
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "leverage": self.leverage
            }

        except Exception as e:
            print(f"[FUTURES] Order failed: {e}")
            return {"status": "error", "message": str(e)}

    def close_position(self, symbol: str) -> dict:
        """Close an open position."""
        if self.paper_mode:
            return self._paper_close(symbol)

        try:
            sym = symbol.replace("-", "/") + ":USDT"
            positions = self.exchange.fetch_positions([sym])
            for pos in positions:
                if float(pos.get('contracts', 0)) > 0:
                    side = 'sell' if pos['side'] == 'long' else 'buy'
                    qty = float(pos['contracts'])
                    order = self.exchange.create_order(sym, 'market', side, qty,
                                                       params={'reduceOnly': True})
                    return {"status": "closed", "order_id": order['id']}
            return {"status": "no_position", "message": "No open position found"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # =========================================================================
    # PAPER MODE SIMULATION
    # =========================================================================

    def _paper_open(self, symbol, side, price, qty, amount_usd, sl, tp) -> dict:
        """Simulate opening a futures position."""
        import uuid
        order_id = f"PAPER-{uuid.uuid4().hex[:8]}"

        self._paper_positions[symbol] = {
            "order_id": order_id,
            "side": side.upper(),
            "qty": qty,
            "entry_price": price,
            "amount_usd": amount_usd,
            "stop_loss": sl,
            "take_profit": tp,
            "leverage": self.leverage,
            "opened_at": datetime.now().isoformat()
        }

        # Deduct margin from balance
        margin = amount_usd
        self._paper_balance -= margin

        print(f"[PAPER] OPENED: {side} {symbol} | Qty: {qty:.6f} @ ${price:,.2f} | "
              f"Margin: ${margin:,.2f} | Leverage: {self.leverage}x")

        return {
            "status": "success",
            "order_id": order_id,
            "entry_price": price,
            "qty": round(qty, 6),
            "side": side.upper(),
            "stop_loss": sl,
            "take_profit": tp,
            "leverage": self.leverage,
            "mode": "PAPER"
        }

    def _paper_close(self, symbol: str) -> dict:
        """Simulate closing a futures position."""
        if symbol not in self._paper_positions:
            return {"status": "no_position", "message": "No paper position found"}

        pos = self._paper_positions[symbol]
        current_price = self.get_current_price(symbol)

        if not current_price:
            return {"status": "error", "message": "Cannot fetch current price"}

        # Calculate PnL
        entry = pos["entry_price"]
        qty = pos["qty"]
        side = pos["side"]

        if side == "LONG":
            pnl = (current_price - entry) * qty
        else:
            pnl = (entry - current_price) * qty

        # Add margin back + PnL
        self._paper_balance += pos["amount_usd"] + pnl

        trade_record = {
            "symbol": symbol,
            "side": side,
            "entry_price": entry,
            "exit_price": current_price,
            "qty": qty,
            "pnl": round(pnl, 2),
            "pnl_pct": round((pnl / pos["amount_usd"]) * 100, 2),
            "leverage": pos["leverage"],
            "opened_at": pos["opened_at"],
            "closed_at": datetime.now().isoformat(),
            "order_id": pos["order_id"]
        }

        self._paper_trades.append(trade_record)
        del self._paper_positions[symbol]

        print(f"[PAPER] CLOSED: {side} {symbol} | PnL: ${pnl:,.2f} ({trade_record['pnl_pct']:+.1f}%)")

        return {
            "status": "closed",
            "trade": trade_record,
            "balance": round(self._paper_balance, 2),
            "mode": "PAPER"
        }

    def check_sl_tp(self, symbol: str) -> dict:
        """
        Check if any paper position has hit SL or TP.
        Should be called periodically.
        """
        if symbol not in self._paper_positions:
            return {"triggered": False}

        pos = self._paper_positions[symbol]
        current_price = self.get_current_price(symbol)
        if not current_price:
            return {"triggered": False}

        sl = pos.get("stop_loss")
        tp = pos.get("take_profit")
        side = pos["side"]

        triggered = False
        trigger_type = None

        if side == "LONG":
            if sl and current_price <= sl:
                triggered = True
                trigger_type = "STOP_LOSS"
            elif tp and current_price >= tp:
                triggered = True
                trigger_type = "TAKE_PROFIT"
        elif side == "SHORT":
            if sl and current_price >= sl:
                triggered = True
                trigger_type = "STOP_LOSS"
            elif tp and current_price <= tp:
                triggered = True
                trigger_type = "TAKE_PROFIT"

        if triggered:
            result = self._paper_close(symbol)
            result["trigger"] = trigger_type
            return {"triggered": True, **result}

        # Update unrealized PnL
        entry = pos["entry_price"]
        qty = pos["qty"]
        if side == "LONG":
            unrealized = (current_price - entry) * qty
        else:
            unrealized = (entry - current_price) * qty

        pos["pnl"] = round(unrealized, 2)

        return {
            "triggered": False,
            "unrealized_pnl": round(unrealized, 2),
            "current_price": current_price
        }

    def get_open_positions(self) -> list:
        """Get all open paper positions."""
        if self.paper_mode:
            positions = []
            for sym, pos in self._paper_positions.items():
                current_price = self.get_current_price(sym)
                entry = pos["entry_price"]
                qty = pos["qty"]
                if pos["side"] == "LONG":
                    pnl = (current_price - entry) * qty if current_price else 0
                else:
                    pnl = (entry - current_price) * qty if current_price else 0

                positions.append({
                    "symbol": sym,
                    **pos,
                    "current_price": current_price,
                    "pnl": round(pnl, 2),
                    "pnl_pct": round((pnl / pos["amount_usd"]) * 100, 2) if pos["amount_usd"] else 0
                })
            return positions
        return []

    def get_trade_history(self) -> list:
        """Get paper trade history."""
        return self._paper_trades


from datetime import datetime  # Ensure import for FuturesExecutionManager

# --- BLOK TESTING MANUAL ---
if __name__ == "__main__":
    print("=" * 60)
    print("EXECUTION ENGINE — Standalone Test")
    print("=" * 60)

    # Test Spot Engine
    try:
        print("\n--- Spot ExecutionManager ---")
        engine = ExecutionManager(use_testnet=True)
        saldo = engine.get_balance("USDT")
        print(f"   Saldo USDT: {saldo['free']}")
        btc_price = engine.get_current_price("BTC/USDT")
        print(f"   Harga BTC: ${btc_price}")
    except Exception as e:
        print(f"   Spot test skipped: {e}")

    # Test Futures Paper Engine
    print("\n--- Futures Paper Mode ---")
    futures = FuturesExecutionManager(paper_mode=True, leverage=3)
    bal = futures.get_balance()
    print(f"   Balance: ${bal['total']:,.2f}")

    price = futures.get_current_price("BTC-USDT")
    if price:
        print(f"   BTC Price: ${price:,.2f}")

        # Open a paper LONG
        result = futures.open_position("BTC-USDT", "LONG", 100, 
                                        stop_loss=price * 0.98,
                                        take_profit=price * 1.06)
        print(f"   Open result: {result['status']}")

        # Check positions
        positions = futures.get_open_positions()
        print(f"   Open positions: {len(positions)}")

        # Close it
        close = futures.close_position("BTC-USDT")
        print(f"   Close result: {close['status']}, PnL: ${close.get('trade', {}).get('pnl', 0)}")

        bal_after = futures.get_balance()
        print(f"   Balance after: ${bal_after['total']:,.2f}")
    else:
        print("   Skipped (no price data)")

    print("\n✅ Execution engine test completed!")