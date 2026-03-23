import React, { useState, useEffect, useCallback } from 'react';
import { 
  Play, Square, RefreshCw, Activity, DollarSign, 
  TrendingUp, TrendingDown, Clock, CheckCircle, XCircle, AlertTriangle, Crosshair
} from 'lucide-react';
import axios from 'axios';
import PaperTradingChart from './PaperTradingChart';

const PaperTradingDashboard = () => {
  const [status, setStatus] = useState(null);
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedSymbol, setSelectedSymbol] = useState(null);

  // Configuration state
  const [config, setConfig] = useState({
    watchlist: "CRV-USDT, LDO-USDT, CAKE-USDT",
    interval: 3600, // 1 hour default
    trade_amount: 100,
    leverage: 1,
    use_testnet: true
  });

  const fetchStatus = async () => {
    try {
      const res = await axios.get('http://127.0.0.1:8000/api/paper-trader/status');
      setStatus(res.data);
      setError(null);
    } catch (err) {
      setError("Failed to fetch paper trader status");
      console.error(err);
    }
  };

  const fetchTrades = async () => {
    try {
      const res = await axios.get('http://127.0.0.1:8000/api/paper-trader/trades?limit=50');
      setTrades(res.data.trades || []);
    } catch (err) {
      console.error("Failed to fetch trades", err);
    }
  };

  const loadAllData = useCallback(async () => {
    setLoading(true);
    await Promise.all([fetchStatus(), fetchTrades()]);
    setLoading(false);
  }, []);

  useEffect(() => {
    const initTimeout = setTimeout(() => {
      loadAllData();
    }, 0);
    
    const intervalId = setInterval(() => {
      fetchStatus();
      fetchTrades();
    }, 15000); // Auto refresh every 15s

    return () => {
      clearTimeout(initTimeout);
      clearInterval(intervalId);
    };
  }, [loadAllData]);

  useEffect(() => {
    // Need to avoid synchronous setState inside useEffect to satisfy ESLint
    const timeoutId = setTimeout(() => {
      if (status?.positions?.length > 0) {
        if (!selectedSymbol || !status.positions.find(p => p.symbol === selectedSymbol)) {
          setSelectedSymbol(status.positions[0].symbol);
        }
      } else if (!selectedSymbol && config.watchlist) {
        const first = config.watchlist.split(',')[0].trim();
        if (first) setSelectedSymbol(first);
      }
    }, 0);
    
    return () => clearTimeout(timeoutId);
  }, [status?.positions, config.watchlist, selectedSymbol]);

  const handleStart = async () => {
    setActionLoading(true);
    try {
      // First configure
      const watchlistArr = config.watchlist.split(',').map(s => s.trim()).filter(s => s);
      await axios.post('http://127.0.0.1:8000/api/paper-trader/configure', {
        ...config,
        watchlist: watchlistArr
      });
      
      // Then start
      await axios.post('http://127.0.0.1:8000/api/paper-trader/start');
      await loadAllData();
    } catch (err) {
      setError("Failed to start paper trader");
      console.error(err);
    }
    setActionLoading(false);
  };

  const handleStop = async () => {
    setActionLoading(true);
    try {
      await axios.post('http://127.0.0.1:8000/api/paper-trader/stop');
      await loadAllData();
    } catch (err) {
      setError("Failed to stop paper trader");
      console.error(err);
    }
    setActionLoading(false);
  };

  const handleRunCycle = async () => {
    setActionLoading(true);
    try {
      await axios.post('http://127.0.0.1:8000/api/paper-trader/cycle');
      await loadAllData();
    } catch (err) {
      setError("Failed to run cycle manually");
      console.error(err);
    }
    setActionLoading(false);
  };

  if (loading && !status) {
    return (
      <div className="flex items-center justify-center p-12 w-full h-full">
        <RefreshCw className="w-8 h-8 text-blue-500 animate-spin mr-3" />
        <span className="text-gray-400 font-medium">Loading Paper Trading Status...</span>
      </div>
    );
  }

  const isRunning = status?.running || false;

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-8 bg-gray-900 text-white min-h-screen">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* Header Section */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center bg-gray-800 p-6 rounded-xl border border-gray-700/50 shadow-lg">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center">
              <Activity className="w-6 h-6 mr-3 text-orange-500" />
              Paper Trading Engine
            </h1>
            <p className="text-gray-400 mt-1 text-sm">
              Autonomous AI-driven trading on Binance Futures Testnet
            </p>
          </div>
          
          <div className="flex items-center space-x-4 mt-4 md:mt-0">
            <div className={`flex items-center px-4 py-2 rounded-lg font-medium content-center ${isRunning ? 'bg-green-500/20 text-green-400 border border-green-500/30' : 'bg-red-500/20 text-red-400 border border-red-500/30'}`}>
              <div className={`w-2.5 h-2.5 rounded-full mr-2 ${isRunning ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
              {isRunning ? 'ACTIVE - RUNNING' : 'STOPPED'}
            </div>
            
            <button
              onClick={loadAllData}
              disabled={actionLoading}
              className="p-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors border border-gray-600 text-gray-300"
              title="Refresh Data"
            >
              <RefreshCw className={`w-5 h-5 ${actionLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/50 text-red-400 px-4 py-3 rounded-xl flex items-center">
            <AlertTriangle className="w-5 h-5 mr-3 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Controls & Config Column */}
          <div className="lg:col-span-1 space-y-6">
            
            {/* Control Panel */}
            <div className="bg-gray-800 rounded-xl p-6 border border-gray-700/50 shadow-lg">
              <h2 className="text-lg font-bold mb-4 flex items-center">
                <Crosshair className="w-5 h-5 mr-2 text-blue-400" />
                Controls
              </h2>
              
              <div className="grid grid-cols-2 gap-3 mb-4">
                <button
                  onClick={handleStart}
                  disabled={isRunning || actionLoading}
                  className={`flex items-center justify-center p-3 rounded-lg font-medium transition-all ${
                    isRunning 
                      ? 'bg-gray-700 text-gray-500 cursor-not-allowed border border-gray-600' 
                      : 'bg-gradient-to-r from-green-600 to-green-500 hover:from-green-500 hover:to-green-400 text-white shadow-lg shadow-green-900/20 shadow-green-500/30 border border-green-400'
                  }`}
                >
                  <Play className="w-4 h-4 mr-2" /> Start Bot
                </button>
                <button
                  onClick={handleStop}
                  disabled={!isRunning || actionLoading}
                  className={`flex items-center justify-center p-3 rounded-lg font-medium transition-all ${
                    !isRunning 
                      ? 'bg-gray-700 text-gray-500 cursor-not-allowed border border-gray-600' 
                      : 'bg-gradient-to-r from-red-600 to-red-500 hover:from-red-500 hover:to-red-400 text-white shadow-lg shadow-red-500/30 border border-red-400'
                  }`}
                >
                  <Square className="w-4 h-4 mr-2" /> Stop Bot
                </button>
              </div>
              
              <button
                onClick={handleRunCycle}
                disabled={actionLoading}
                className="w-full flex items-center justify-center p-3 bg-gray-700 hover:bg-gray-600 rounded-lg text-white transition-colors border border-gray-600 font-medium"
              >
                <RefreshCw className="w-4 h-4 mr-2" /> Run Single Cycle Now
              </button>

              <div className="mt-6 pt-5 border-t border-gray-700/50">
                <div className="flex justify-between items-center text-sm mb-2">
                  <span className="text-gray-400">Total Cycles Executed:</span>
                  <span className="font-mono text-gray-200 bg-gray-900 px-2 py-1 rounded">{status?.cycle_count || 0}</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-gray-400">Last Cycle:</span>
                  <span className="font-mono text-gray-400 text-xs">
                    {status?.last_cycle ? new Date(status.last_cycle).toLocaleTimeString() : 'Never'}
                  </span>
                </div>
              </div>
            </div>

            {/* Config Panel */}
            <div className="bg-gray-800 rounded-xl p-6 border border-gray-700/50 shadow-lg">
              <h2 className="text-lg font-bold mb-4">Configuration</h2>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">Watchlist (comma separated)</label>
                  <textarea 
                    value={config.watchlist}
                    onChange={(e) => setConfig({...config, watchlist: e.target.value})}
                    disabled={isRunning}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg p-2.5 text-sm text-gray-200 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
                    rows="2"
                  />
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-400 mb-1">Interval (Secs)</label>
                    <input 
                      type="number" 
                      value={config.interval}
                      onChange={(e) => setConfig({...config, interval: parseInt(e.target.value) || 0})}
                      disabled={isRunning}
                      className="w-full bg-gray-900 border border-gray-700 rounded-lg p-2.5 text-sm text-gray-200 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-400 mb-1">Trade Size ($)</label>
                    <input 
                      type="number" 
                      value={config.trade_amount}
                      onChange={(e) => setConfig({...config, trade_amount: parseFloat(e.target.value) || 0})}
                      disabled={isRunning}
                      className="w-full bg-gray-900 border border-gray-700 rounded-lg p-2.5 text-sm text-gray-200 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
                    />
                  </div>
                </div>
                
                <div className="flex items-center justify-between p-3 bg-gray-900/50 rounded-lg border border-gray-700/50">
                  <span className="text-sm font-medium text-gray-300">Target Environment</span>
                  <div className="flex bg-gray-800 rounded-lg p-1 border border-gray-700">
                    <button 
                      onClick={() => setConfig({...config, use_testnet: true})}
                      disabled={isRunning}
                      className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${config.use_testnet ? 'bg-blue-600 text-white shadow-sm' : 'text-gray-400 hover:text-gray-200 disabled:opacity-50'}`}
                    >
                      Testnet
                    </button>
                    <button 
                      onClick={() => setConfig({...config, use_testnet: false})}
                      disabled={isRunning}
                      className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${!config.use_testnet ? 'bg-red-600 text-white shadow-sm' : 'text-gray-400 hover:text-gray-200 disabled:opacity-50'}`}
                    >
                      Live
                    </button>
                  </div>
                </div>
                <p className="text-xs text-orange-400/80 italic mt-2">
                  * Note: Changing config requires stopping the bot first.
                </p>
              </div>
            </div>
            
          </div>

          {/* Stats & Tables Column */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Stats Overview */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-gray-800 rounded-xl p-4 border border-gray-700/50 shadow-sm">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm font-medium text-gray-400">Total Balance</p>
                    <h3 className="text-2xl font-bold mt-1 text-white">
                      ${status?.balance?.total?.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) || "0.00"}
                    </h3>
                  </div>
                  <div className="p-2 bg-blue-500/10 rounded-lg border border-blue-500/20">
                    <DollarSign className="w-5 h-5 text-blue-400" />
                  </div>
                </div>
                <p className="text-xs mt-3 flex items-center text-gray-400">
                  <span className="text-gray-300 mr-1">Free:</span>
                  ${status?.balance?.free?.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) || "0.00"}
                </p>
              </div>

              <div className="bg-gray-800 rounded-xl p-4 border border-gray-700/50 shadow-sm">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm font-medium text-gray-400">Total PnL</p>
                    <h3 className={`text-2xl font-bold mt-1 ${status?.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {status?.total_pnl >= 0 ? '+' : ''}{status?.total_pnl?.toFixed(2) || "0.00"}
                    </h3>
                  </div>
                  <div className={`p-2 rounded-lg border ${status?.total_pnl >= 0 ? 'bg-green-500/10 border-green-500/20' : 'bg-red-500/10 border-red-500/20'}`}>
                    {status?.total_pnl >= 0 ? <TrendingUp className="w-5 h-5 text-green-400" /> : <TrendingDown className="w-5 h-5 text-red-400" />}
                  </div>
                </div>
              </div>

              <div className="bg-gray-800 rounded-xl p-4 border border-gray-700/50 shadow-sm">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm font-medium text-gray-400">Win Rate</p>
                    <h3 className="text-2xl font-bold mt-1 text-white">
                      {status?.win_rate || "0"}%
                    </h3>
                  </div>
                  <div className="p-2 bg-purple-500/10 rounded-lg border border-purple-500/20">
                    <Activity className="w-5 h-5 text-purple-400" />
                  </div>
                </div>
                <div className="flex items-center space-x-2 mt-3 text-xs font-medium">
                  <span className="text-green-400 bg-green-400/10 px-1.5 py-0.5 rounded">{status?.wins || 0} W</span>
                  <span className="text-red-400 bg-red-400/10 px-1.5 py-0.5 rounded">{status?.losses || 0} L</span>
                </div>
              </div>

              <div className="bg-gray-800 rounded-xl p-4 border border-gray-700/50 shadow-sm">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm font-medium text-gray-400">Open Positions</p>
                    <h3 className="text-2xl font-bold mt-1 text-white">
                      {status?.open_positions || 0}
                    </h3>
                  </div>
                  <div className="p-2 bg-orange-500/10 rounded-lg border border-orange-500/20">
                    <Clock className="w-5 h-5 text-orange-400" />
                  </div>
                </div>
              </div>
            </div>

            {/* Trading Chart */}
            <div className="bg-gray-800 rounded-xl border border-gray-700/50 shadow-lg overflow-hidden flex flex-col h-[400px]">
              <div className="p-4 border-b border-gray-700/50 bg-gray-800/80 shrink-0 flex justify-between items-center">
                <h2 className="text-lg font-bold flex items-center">
                  <Activity className="w-5 h-5 mr-2 text-blue-400" />
                  Live Trading Chart
                </h2>
                {selectedSymbol && (
                  <span className="bg-gray-700 px-3 py-1 rounded text-sm text-gray-300 font-bold border border-gray-600">
                    {selectedSymbol}
                  </span>
                )}
              </div>
              <div className="flex-1 p-0 relative">
                <PaperTradingChart symbol={selectedSymbol} positions={status?.positions} />
              </div>
            </div>

            {/* Active Positions Table */}
            <div className="bg-gray-800 rounded-xl border border-gray-700/50 shadow-lg overflow-hidden flex flex-col h-[280px]">
              <div className="p-4 border-b border-gray-700/50 bg-gray-800/80 shrink-0">
                <h2 className="text-lg font-bold flex items-center">
                  <Activity className="w-5 h-5 mr-2 text-indigo-400" />
                  Active Positions
                </h2>
              </div>
              <div className="overflow-auto flex-1 p-0">
                {status?.positions && status.positions.length > 0 ? (
                  <table className="w-full text-left text-sm whitespace-nowrap">
                    <thead className="bg-gray-900/50 text-gray-400 sticky top-0 z-10">
                      <tr>
                        <th className="p-3 font-medium">Symbol</th>
                        <th className="p-3 font-medium">Side</th>
                        <th className="p-3 font-medium text-right">Size</th>
                        <th className="p-3 font-medium text-right">Entry Price</th>
                        <th className="p-3 font-medium text-right">Current Price</th>
                        <th className="p-3 font-medium text-right">PnL</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700/50">
                      {status.positions.map((pos, idx) => {
                        const isLong = pos.side.toUpperCase() === 'LONG';
                        const pnlColor = pos.pnl >= 0 ? 'text-green-400' : 'text-red-400';
                        return (
                          <tr key={idx} 
                              onClick={() => setSelectedSymbol(pos.symbol)}
                              className={`cursor-pointer transition-colors ${selectedSymbol === pos.symbol ? 'bg-blue-500/10 border-l-2 border-blue-500' : 'hover:bg-gray-700/20'}`}>
                            <td className="p-3 font-bold text-gray-200">{pos.symbol}</td>
                            <td className="p-3">
                              <span className={`px-2 py-1 rounded text-xs font-bold ${isLong ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
                                {pos.side}
                              </span>
                            </td>
                            <td className="p-3 text-right font-mono text-gray-300">{(pos.amount || 0).toFixed(4)}</td>
                            <td className="p-3 text-right font-mono text-gray-300">${pos.entry_price?.toLocaleString() || '-'}</td>
                            <td className="p-3 text-right font-mono text-gray-300">${pos.current_price?.toLocaleString() || '-'}</td>
                            <td className={`p-3 text-right font-bold font-mono ${pnlColor}`}>
                              {pos.pnl >= 0 ? '+' : ''}{pos.pnl?.toFixed(2)} ({pos.pnl_pct?.toFixed(2)}%)
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-gray-500 p-8">
                    <p>No active positions found.</p>
                  </div>
                )}
              </div>
            </div>

            {/* Trade History Table */}
            <div className="bg-gray-800 rounded-xl border border-gray-700/50 shadow-lg overflow-hidden flex flex-col h-[320px]">
              <div className="p-4 border-b border-gray-700/50 bg-gray-800/80 shrink-0">
                <h2 className="text-lg font-bold flex items-center">
                  <CheckCircle className="w-5 h-5 mr-2 text-green-400" />
                  Recent Trade History
                </h2>
              </div>
              <div className="overflow-auto flex-1 p-0">
                {trades && trades.length > 0 ? (
                  <table className="w-full text-left text-sm whitespace-nowrap">
                    <thead className="bg-gray-900/50 text-gray-400 sticky top-0 z-10">
                      <tr>
                        <th className="p-3 font-medium">Time (Close)</th>
                        <th className="p-3 font-medium">Symbol</th>
                        <th className="p-3 font-medium">Side</th>
                        <th className="p-3 font-medium text-right">Entry</th>
                        <th className="p-3 font-medium text-right">Exit</th>
                        <th className="p-3 font-medium text-right">Return</th>
                        <th className="p-3 font-medium text-right">Net PnL</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700/50">
                      {trades.map((trade, idx) => {
                        const isLong = trade.side.toUpperCase() === 'LONG';
                        const pnlColor = trade.pnl >= 0 ? 'text-green-400' : 'text-red-400';
                        const timeClosed = trade.closed_at ? new Date(trade.closed_at).toLocaleString() 
                                          : trade.timestamp ? new Date(trade.timestamp).toLocaleString() : '-';
                        return (
                          <tr key={idx} className="hover:bg-gray-700/20 transition-colors">
                            <td className="p-3 text-gray-400 text-xs">{timeClosed}</td>
                            <td className="p-3 font-bold text-gray-200">{trade.symbol}</td>
                            <td className="p-3">
                              <span className={`px-2 py-1 rounded text-xs font-bold ${isLong ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
                                {trade.side}
                              </span>
                            </td>
                            <td className="p-3 text-right font-mono text-gray-400">${trade.entry_price?.toLocaleString() || '-'}</td>
                            <td className="p-3 text-right font-mono text-gray-300">${trade.exit_price?.toLocaleString() || '-'}</td>
                            <td className={`p-3 text-right font-medium ${pnlColor}`}>
                              {trade.pnl_pct >= 0 ? '+' : ''}{trade.pnl_pct?.toFixed(2)}%
                            </td>
                            <td className={`p-3 text-right font-bold font-mono ${pnlColor}`}>
                              ${trade.pnl?.toFixed(2)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-gray-500 p-8">
                    <p>No trade history available yet.</p>
                  </div>
                )}
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
};

export default PaperTradingDashboard;
