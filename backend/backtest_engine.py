import asyncio
from strategy_core import TradingEngine

class BacktestEngine:
    def __init__(self):
        # We don't need persistent connection here, but TradingEngine init handles it.
        pass

    async def scan_market(self, symbols, allowed_modes=["LONG"]):
        """
        Scan multiple symbols and rank by consistency score using Best Strategy Finder.
        Args:
            symbols: List of symbols (e.g. ['BTC-USDT', ...])
            allowed_modes: List of directions to check (['LONG'], ['SHORT'], or ['LONG', 'SHORT'])
        """
        results = []
        
        print(f"[SCANNER] Starting Deep Scan for {len(symbols)} coins with modes: {allowed_modes}")
        
        # Instantiate engine per thread to avoid shared state issues
        def _process_symbol(symbol):
            ccxt_symbol = symbol.replace("-", "/")
            if ccxt_symbol.endswith("USD"): ccxt_symbol += "T"
            
            try:
                engine = TradingEngine()
                best_strat = engine.find_best_strategy_for_symbol(
                    ccxt_symbol, 
                    timeframe="1h", 
                    period="1y", 
                    allowed_modes=allowed_modes
                )
                
                if best_strat:
                    return {
                        "symbol": symbol, 
                        "score": best_strat['score'], 
                        "consistency": best_strat['consistency_score'],
                        "profit": best_strat['net_profit'],
                        "win_rate": best_strat['win_rate'],
                        "trades_count": best_strat['total_trades'],
                        "best_strategy": f"{best_strat['strategy']} ({best_strat['direction']})",
                        "curve": [p['value'] for p in best_strat['equity_curve']]
                    }
            except Exception as e:
                print(f"[SCANNER] Error processing {symbol}: {e}")
            return None

        # Execute all tasks concurrently using a dedicated pool to prevent
        # starving FastAPI default threads.
        import concurrent.futures
        loop = asyncio.get_running_loop()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            tasks = [loop.run_in_executor(pool, _process_symbol, symbol) for symbol in symbols]
            gathered_results = await asyncio.gather(*tasks)
            
        # Filter valid results
        results = [r for r in gathered_results if r is not None]
        
        # Sort by Score descending
        results.sort(key=lambda x: x['score'], reverse=True)
        return results
