import React, { useState, useEffect, useCallback } from 'react';
import { 
  Play, Square, RefreshCw, Activity, DollarSign, 
  TrendingUp, TrendingDown, Clock, CheckCircle, XCircle, AlertTriangle, Crosshair,
  Brain, Search, Target, Zap, Pause, ChevronDown, ChevronUp, Terminal
} from 'lucide-react';
import axios from 'axios';
import PaperTradingChart from './PaperTradingChart';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const PaperTradingDashboard = () => {
  const [status, setStatus] = useState(null);
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedSymbol, setSelectedSymbol] = useState(null);
  const [expandedEvent, setExpandedEvent] = useState(null);

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
      const res = await axios.get(`${API_BASE}/api/paper-trader/status`);
      setStatus(res.data);
      setError(null);
    } catch (err) {
      setError("Failed to fetch paper trader status");
      console.error(err);
    }
  };

  const fetchTrades = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/paper-trader/trades?limit=50`);
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
      await axios.post(`${API_BASE}/api/paper-trader/configure`, {
        ...config,
        watchlist: watchlistArr
      });
      
      // Then start
      await axios.post(`${API_BASE}/api/paper-trader/start`);
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
      await axios.post(`${API_BASE}/api/paper-trader/stop`);
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
      await axios.post(`${API_BASE}/api/paper-trader/cycle`);
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
    <div className="animate-in slide-in-from-right-4 fade-in duration-300">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* Header Section — matched to BotTracker/Operations style */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center" style={{
          background: 'rgba(30, 41, 59, 0.6)', border: '1px solid rgba(100, 116, 139, 0.2)',
          borderRadius: 16, padding: '20px 24px'
        }}>
          <div className="flex items-center gap-3">
            <div style={{
              width: 42, height: 42, borderRadius: 12,
              background: 'linear-gradient(135deg, #f97316, #ef4444)',
              display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}>
              <Activity className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 style={{ fontSize: 20, fontWeight: 800, margin: 0, color: '#f3f4f6' }}>
                Paper Trading Engine
              </h2>
              <p style={{ fontSize: 12, color: '#6b7280', margin: 0 }}>
                Autonomous AI-driven paper trading (simulated balance)
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-4 mt-4 md:mt-0">
            <div className={`flex items-center px-4 py-2 rounded-lg font-medium content-center ${isRunning ? 'bg-green-500/20 text-green-400 border border-green-500/30' : 'bg-red-500/20 text-red-400 border border-red-500/30'}`}>
              <div className={`w-2.5 h-2.5 rounded-full mr-2 ${isRunning ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
              {isRunning ? 'ACTIVE - RUNNING' : 'STOPPED'}
            </div>
            
            <button
              onClick={loadAllData}
              disabled={actionLoading}
              style={{
                background: 'rgba(249, 115, 22, 0.15)', border: '1px solid rgba(249, 115, 22, 0.3)',
                borderRadius: 10, padding: '8px 16px', color: '#f97316',
                cursor: actionLoading ? 'wait' : 'pointer', display: 'flex', alignItems: 'center', gap: 6,
                fontSize: 13, fontWeight: 600, transition: 'all 0.2s'
              }}
            >
              <RefreshCw className={`w-4 h-4 ${actionLoading ? 'animate-spin' : ''}`} />
              {actionLoading ? 'Loading...' : 'Refresh'}
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
            <div style={{ background: 'rgba(30, 41, 59, 0.6)', border: '1px solid rgba(100, 116, 139, 0.2)', borderRadius: 12, padding: '20px' }}>
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
                  <span className="text-sm font-medium text-gray-300">Mode</span>
                  <div className="flex bg-gray-800 rounded-lg p-1 border border-gray-700">
                    <button 
                      onClick={() => setConfig({...config, use_testnet: true})}
                      disabled={isRunning}
                      className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${config.use_testnet ? 'bg-blue-600 text-white shadow-sm' : 'text-gray-400 hover:text-gray-200 disabled:opacity-50'}`}
                    >
                      Simulated
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

            {/* ══════ LIVE FEED / AI EVENT LOG ══════ */}
            <div className="bg-gray-800 rounded-xl border border-gray-700/50 shadow-lg overflow-hidden flex flex-col h-[360px]">
              <div className="p-4 border-b border-gray-700/50 bg-gray-800/80 shrink-0 flex justify-between items-center">
                <h2 className="text-lg font-bold flex items-center">
                  <Terminal className="w-5 h-5 mr-2 text-purple-400" />
                  Live Feed — AI Reasoning
                </h2>
                {actionLoading && (
                  <span className="flex items-center text-xs text-purple-400 animate-pulse">
                    <RefreshCw className="w-3 h-3 mr-1 animate-spin" /> Processing...
                  </span>
                )}
              </div>
              <div className="overflow-y-auto flex-1 p-3 space-y-1 font-mono text-xs bg-gray-950/50" style={{scrollbarWidth:'thin'}}>
                {status?.recent_events && status.recent_events.length > 0 ? (
                  [...status.recent_events].reverse().map((evt, idx) => {
                    const typeConfig = {
                      scan: { icon: Search, color: 'text-blue-400', bg: 'bg-blue-500/10' },
                      strategy: { icon: Target, color: 'text-yellow-400', bg: 'bg-yellow-500/10' },
                      decision: { icon: Brain, color: 'text-purple-400', bg: 'bg-purple-500/10' },
                      execute: { icon: Zap, color: 'text-green-400', bg: 'bg-green-500/10' },
                      hold: { icon: Pause, color: 'text-gray-400', bg: 'bg-gray-500/10' },
                      error: { icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-500/10' },
                    };
                    const cfg = typeConfig[evt.type] || typeConfig.scan;
                    const Icon = cfg.icon;
                    const hasDetail = evt.detail && (evt.detail.reasoning || evt.detail.strategy || evt.detail.side);
                    const isExpanded = expandedEvent === idx;

                    return (
                      <div key={idx}>
                        <div 
                          className={`flex items-start gap-2 px-2 py-1.5 rounded ${cfg.bg} cursor-pointer hover:brightness-125 transition-all`}
                          onClick={() => hasDetail && setExpandedEvent(isExpanded ? null : idx)}
                        >
                          <Icon className={`w-3.5 h-3.5 mt-0.5 shrink-0 ${cfg.color}`} />
                          <span className="text-gray-500 shrink-0">
                            {evt.time ? new Date(evt.time).toLocaleTimeString() : ''}
                          </span>
                          <span className={`${cfg.color} font-semibold uppercase shrink-0`}>
                            [{evt.type}]
                          </span>
                          <span className="text-gray-300 flex-1">
                            {evt.message}
                          </span>
                          {hasDetail && (
                            isExpanded 
                              ? <ChevronUp className="w-3 h-3 text-gray-500 shrink-0 mt-0.5" />
                              : <ChevronDown className="w-3 h-3 text-gray-500 shrink-0 mt-0.5" />
                          )}
                        </div>

                        {/* Expanded Detail */}
                        {isExpanded && evt.detail && (
                          <div className="ml-8 mt-1 mb-2 p-3 rounded-lg bg-gray-900/80 border border-gray-700/50 text-xs space-y-1">
                            {evt.detail.reasoning && (
                              <div>
                                <span className="text-purple-400 font-bold"> AI Reasoning:</span>
                                <p className="text-gray-300 mt-1 leading-relaxed whitespace-pre-wrap">{evt.detail.reasoning}</p>
                              </div>
                            )}
                            <div className="flex gap-4 flex-wrap mt-2">
                              {evt.detail.strategy && (
                                <span className="text-yellow-400">Strategy: <strong>{evt.detail.strategy}</strong></span>
                              )}
                              {evt.detail.confidence !== undefined && (
                                <span className={evt.detail.confidence >= 60 ? 'text-green-400' : 'text-orange-400'}>
                                  Confidence: <strong>{evt.detail.confidence}%</strong>
                                </span>
                              )}
                              {evt.detail.price && (
                                <span className="text-gray-400">Price: <strong>${Number(evt.detail.price).toLocaleString()}</strong></span>
                              )}
                              {evt.detail.side && (
                                <span className={evt.detail.side === 'LONG' ? 'text-green-400' : 'text-red-400'}>
                                  Side: <strong>{evt.detail.side}</strong>
                                </span>
                              )}
                              {evt.detail.sl && (
                                <span className="text-red-400">SL: <strong>${Number(evt.detail.sl).toLocaleString()}</strong></span>
                              )}
                              {evt.detail.tp && (
                                <span className="text-green-400">TP: <strong>${Number(evt.detail.tp).toLocaleString()}</strong></span>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-gray-600 p-8">
                    <Terminal className="w-8 h-8 mb-2 opacity-30" />
                    <p>No events yet. Start the bot or run a cycle to see AI reasoning here.</p>
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
