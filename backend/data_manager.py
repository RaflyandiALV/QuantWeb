import ccxt.async_support as ccxt
import pandas as pd
import asyncio

class DataManager:
    def __init__(self, exchange_id='binance'):
        self.exchange_id = exchange_id
        # Initialize exchange (using Binance as default, but scalable to others)
        self.exchange = getattr(ccxt, exchange_id)({
            'enableRateLimit': True,  # Prevent getting banned by API
        })

    async def fetch_data(self, symbol: str, timeframe: str = '1h', limit: int = 100):
        """
        Fetch OHLCV data from crypto exchange via CCXT.
        
        Args:
            symbol (str): Trading pair, e.g., 'BTC/USDT' (Note: CCXT uses '/', not '-')
            timeframe (str): Candle timeframe, e.g., '1m', '1h', '4h', '1d'
            limit (int): Number of candles to fetch
        """
        try:
            # Standardization: CCXT usually requires uppercase symbols
            symbol = symbol.upper().replace('-', '/') 

            # Fetch data (Timestamp, Open, High, Low, Close, Volume)
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            if not ohlcv:
                print(f"No data returned for {symbol}")
                return None

            # Convert to Pandas DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Convert timestamp from milliseconds to datetime objects
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Ensure numeric types for calculations
            cols = ['open', 'high', 'low', 'close', 'volume']
            df[cols] = df[cols].apply(pd.to_numeric)

            return df

        except Exception as e:
            print(f"Error fetching data via CCXT for {symbol}: {e}")
            return None
        
    async def close_connection(self):
        """Close the async session"""
        await self.exchange.close()

# --- FOR TESTING PURPOSES ONLY ---
if __name__ == "__main__":
    async def main():
        dm = DataManager()
        print("Fetching BTC/USDT data via CCXT...")
        data = await dm.fetch_data('BTC/USDT', '1h', 50)
        
        if data is not None:
            print(data.head())
            print(f"\nSuccessfully fetched {len(data)} rows.")
        else:
            print("Failed to fetch data.")
            
        await dm.close_connection()

    # Run the async test loop
    asyncio.run(main())