import React, { useState, useEffect, useCallback } from 'react';
import { TrendingUp, Activity, Play, StopCircle, MoreHorizontal, RefreshCw, Clock, DollarSign, BarChart3, Wallet, ArrowUpCircle, ArrowDownCircle, Zap } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';


const BotTracker = () => {
    const [botStatus, setBotStatus] = useState(null);
    const [tradeHistory, setTradeHistory] = useState([]);
    const [portfolio, setPortfolio] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [activeTab, setActiveTab] = useState('overview'); // overview | history | portfolio

    const fetchData = useCallback(async () => {
        try {
            setLoading(true);
            const [statusRes, historyRes, portfolioRes] = await Promise.allSettled([
                fetch(`${API_BASE}/api/bot-status`),
                fetch(`${API_BASE}/api/trade-history?limit=20`),
                fetch(`${API_BASE}/api/portfolio`)
            ]);

            if (statusRes.status === 'fulfilled' && statusRes.value.ok) {
                setBotStatus(await statusRes.value.json());
            }
            if (historyRes.status === 'fulfilled' && historyRes.value.ok) {
                const data = await historyRes.value.json();
                setTradeHistory(data.trades || []);
            }
            if (portfolioRes.status === 'fulfilled' && portfolioRes.value.ok) {
                setPortfolio(await portfolioRes.value.json());
            }
            setError(null);
        } catch (err) {
            setError("Failed to connect to backend");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 30000); // Auto-refresh every 30s
        return () => clearInterval(interval);
    }, [fetchData]);

    // Stats cards data
    const totalPnl = botStatus?.total_pnl || 0;
    const totalTrades = botStatus?.total_trades || 0;
    const winRate = botStatus?.win_rate || 0;
    const totalVolume = botStatus?.total_volume || 0;
    const balance = botStatus?.balance || {};
    const mode = botStatus?.mode || 'PUBLIC';

    return (
        <div className="animate-in slide-in-from-right-4 fade-in duration-300">
            {/* Mode Badge + Refresh */}
            <div className="flex justify-between items-center mb-6">
                <div className="flex items-center gap-3">
                    <div className={`px-3 py-1 rounded-full text-xs font-bold border ${mode === 'TESTNET' ? 'bg-yellow-500/10 border-yellow-500/30 text-yellow-400' : 'bg-gray-800 border-gray-700 text-gray-400'}`}>
                        {mode === 'TESTNET' ? ' TESTNET MODE' : ' PUBLIC MODE (No Trading)'}
                    </div>
                    {mode === 'TESTNET' && (
                        <span className="text-xs text-gray-500">Demo money — testnet.binance.vision</span>
                    )}
                </div>
                <button onClick={fetchData} disabled={loading} className="flex items-center gap-1 text-xs text-gray-400 hover:text-cyan-400 transition px-3 py-1.5 rounded-lg border border-gray-700 hover:border-cyan-500/30">
                    <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
                    {loading ? 'Loading...' : 'Refresh'}
                </button>
            </div>

            {/* Tab Navigation */}
            <div className="flex gap-1 mb-6 bg-gray-900/50 p-1 rounded-xl border border-gray-800 w-fit">
                {[
                    { id: 'overview', label: 'Overview', icon: Activity },
                    { id: 'history', label: 'Trade Log', icon: Clock },
                    { id: 'portfolio', label: 'Portfolio', icon: Wallet },
                ].map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold transition ${activeTab === tab.id
                                ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                                : 'text-gray-500 hover:text-white'
                            }`}
                    >
                        <tab.icon size={14} />
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Header Stats */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
                <div className="bg-gray-900/50 border border-gray-800 p-4 rounded-xl flex flex-col">
                    <span className="text-gray-500 text-[10px] uppercase font-bold tracking-wider flex items-center gap-1"><DollarSign size={10} />Total PnL</span>
                    <span className={`text-2xl font-black ${totalPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {totalPnl >= 0 ? '+' : ''}${totalPnl.toLocaleString()}
                    </span>
                </div>
                <div className="bg-gray-900/50 border border-gray-800 p-4 rounded-xl flex flex-col">
                    <span className="text-gray-500 text-[10px] uppercase font-bold tracking-wider flex items-center gap-1"><BarChart3 size={10} />Total Trades</span>
                    <span className="text-2xl font-black text-cyan-400">{totalTrades}</span>
                </div>
                <div className="bg-gray-900/50 border border-gray-800 p-4 rounded-xl flex flex-col">
                    <span className="text-gray-500 text-[10px] uppercase font-bold tracking-wider flex items-center gap-1"><TrendingUp size={10} />Win Rate</span>
                    <span className="text-2xl font-black text-yellow-400">{winRate}%</span>
                </div>
                <div className="bg-gray-900/50 border border-gray-800 p-4 rounded-xl flex flex-col">
                    <span className="text-gray-500 text-[10px] uppercase font-bold tracking-wider flex items-center gap-1"><Zap size={10} />Volume</span>
                    <span className="text-2xl font-black text-white">${totalVolume.toLocaleString()}</span>
                </div>
                <div className="bg-gray-900/50 border border-gray-800 p-4 rounded-xl flex flex-col">
                    <span className="text-gray-500 text-[10px] uppercase font-bold tracking-wider flex items-center gap-1"><Wallet size={10} />USDT Balance</span>
                    <span className="text-2xl font-black text-green-400">${balance.total_usdt?.toLocaleString() || '0'}</span>
                    <span className="text-[10px] text-gray-500 mt-0.5">Free: ${balance.free_usdt?.toLocaleString() || '0'}</span>
                </div>
            </div>

            {/* Error State */}
            {error && (
                <div className="bg-red-900/20 border border-red-500/30 text-red-400 p-4 rounded-xl text-sm mb-6">
                     {error}
                </div>
            )}

            {/* TAB: Overview */}
            {activeTab === 'overview' && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    <div className="lg:col-span-2">
                        <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2"><Activity size={18} className="text-cyan-500" /> RECENT TRADES</h3>
                        <div className="space-y-3">
                            {(botStatus?.recent_trades || []).length === 0 ? (
                                <div className="text-center py-12 border-2 border-dashed border-gray-800 rounded-xl">
                                    <p className="text-gray-500 text-sm">No trades yet. Add coins to your Watchlist and the bot will start trading automatically every 15 minutes.</p>
                                </div>
                            ) : (
                                (botStatus?.recent_trades || []).map((trade, i) => (
                                    <div key={i} className="bg-gray-900/40 border border-gray-800 p-4 rounded-xl flex justify-between items-center hover:border-cyan-500/30 transition group">
                                        <div className="flex items-center gap-4">
                                            <div className={`w-2 h-10 rounded-full ${trade.side === 'buy' ? 'bg-green-500 shadow-[0_0_10px_lime]' : 'bg-red-500 shadow-[0_0_10px_red]'}`}></div>
                                            <div>
                                                <div className="font-bold text-white flex items-center gap-2">
                                                    {trade.side === 'buy' ? <ArrowUpCircle size={14} className="text-green-400" /> : <ArrowDownCircle size={14} className="text-red-400" />}
                                                    {trade.symbol}
                                                    <span className="text-[9px] bg-gray-800 text-gray-400 px-1.5 py-0.5 rounded border border-gray-700">{trade.strategy}</span>
                                                </div>
                                                <div className="text-xs text-gray-500 font-mono mt-1">
                                                    {trade.side?.toUpperCase()} {trade.qty?.toFixed(6)} @ ${trade.price?.toFixed(2)} | {trade.timeframe}
                                                </div>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <div className="text-xs text-gray-500">{new Date(trade.created_at).toLocaleDateString()}</div>
                                            <div className="text-[10px] text-gray-600">{new Date(trade.created_at).toLocaleTimeString()}</div>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>

                    {/* Sidebar */}
                    <div className="lg:col-span-1">
                        <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2"><TrendingUp size={18} className="text-purple-500" /> BOT INFO</h3>
                        <div className="bg-gray-900/40 border border-gray-800 p-6 rounded-xl space-y-4">
                            <div className="flex justify-between text-sm">
                                <span className="text-gray-500">Mode</span>
                                <span className="text-yellow-400 font-bold">{mode}</span>
                            </div>
                            <div className="flex justify-between text-sm">
                                <span className="text-gray-500">Scan Interval</span>
                                <span className="text-white">Every 15 min</span>
                            </div>
                            <div className="flex justify-between text-sm">
                                <span className="text-gray-500">Risk per Trade</span>
                                <span className="text-white">1% of Equity</span>
                            </div>
                            <div className="flex justify-between text-sm">
                                <span className="text-gray-500">Order Type</span>
                                <span className="text-white">Market</span>
                            </div>
                        </div>

                        <div className="mt-6 bg-blue-900/10 border border-blue-500/20 p-4 rounded-xl">
                            <h4 className="font-bold text-blue-400 text-sm mb-2"> How it Works</h4>
                            <p className="text-xs text-blue-200/80 leading-relaxed">
                                The bot scans your Watchlist every 15 minutes. When a strategy generates a signal on the latest candle, it calculates position size (1% risk) and executes on Binance Testnet.
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {/* TAB: Trade History */}
            {activeTab === 'history' && (
                <div>
                    <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2"><Clock size={18} className="text-cyan-500" /> FULL TRADE LOG</h3>
                    {tradeHistory.length === 0 ? (
                        <div className="text-center py-12 border-2 border-dashed border-gray-800 rounded-xl">
                            <p className="text-gray-500 text-sm">No trades recorded yet.</p>
                        </div>
                    ) : (
                        <div className="overflow-x-auto rounded-xl border border-gray-800">
                            <table className="w-full text-xs">
                                <thead>
                                    <tr className="bg-gray-900/80 text-gray-400 uppercase tracking-wider">
                                        <th className="px-4 py-3 text-left">#</th>
                                        <th className="px-4 py-3 text-left">Symbol</th>
                                        <th className="px-4 py-3 text-left">Side</th>
                                        <th className="px-4 py-3 text-right">Qty</th>
                                        <th className="px-4 py-3 text-right">Price</th>
                                        <th className="px-4 py-3 text-left">Strategy</th>
                                        <th className="px-4 py-3 text-left">TF</th>
                                        <th className="px-4 py-3 text-left">Status</th>
                                        <th className="px-4 py-3 text-left">Notes</th>
                                        <th className="px-4 py-3 text-left">Time</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {tradeHistory.map((t, i) => (
                                        <tr key={t.id || i} className="border-t border-gray-800 hover:bg-gray-900/40 transition">
                                            <td className="px-4 py-3 text-gray-500">{t.id}</td>
                                            <td className="px-4 py-3 font-bold text-white">{t.symbol}</td>
                                            <td className={`px-4 py-3 font-bold ${t.side === 'buy' ? 'text-green-400' : 'text-red-400'}`}>
                                                {t.side?.toUpperCase()}
                                            </td>
                                            <td className="px-4 py-3 text-right text-gray-300 font-mono">{t.qty?.toFixed(6)}</td>
                                            <td className="px-4 py-3 text-right text-gray-300 font-mono">${t.price?.toFixed(2)}</td>
                                            <td className="px-4 py-3 text-gray-400">{t.strategy}</td>
                                            <td className="px-4 py-3 text-gray-400">{t.timeframe}</td>
                                            <td className="px-4 py-3">
                                                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${t.status === 'FILLED' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
                                                    {t.status}
                                                </span>
                                            </td>
                                            <td className="px-4 py-3 text-gray-500 max-w-[180px] truncate">{t.notes}</td>
                                            <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{new Date(t.created_at).toLocaleString()}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            )}

            {/* TAB: Portfolio */}
            {activeTab === 'portfolio' && (
                <div>
                    <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2"><Wallet size={18} className="text-green-500" /> TESTNET PORTFOLIO</h3>

                    {/* USDT Balance Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                        <div className="bg-gradient-to-br from-green-900/20 to-green-900/5 border border-green-500/20 p-5 rounded-xl">
                            <div className="text-green-400/60 text-[10px] uppercase font-bold mb-1">Total USDT</div>
                            <div className="text-3xl font-black text-green-400">${portfolio?.usdt_balance?.toLocaleString() || '0'}</div>
                        </div>
                        <div className="bg-gray-900/50 border border-gray-800 p-5 rounded-xl">
                            <div className="text-gray-500 text-[10px] uppercase font-bold mb-1">Available</div>
                            <div className="text-3xl font-black text-white">${portfolio?.usdt_free?.toLocaleString() || '0'}</div>
                        </div>
                        <div className="bg-gray-900/50 border border-gray-800 p-5 rounded-xl">
                            <div className="text-gray-500 text-[10px] uppercase font-bold mb-1">In Positions</div>
                            <div className="text-3xl font-black text-yellow-400">
                                ${((portfolio?.usdt_balance || 0) - (portfolio?.usdt_free || 0)).toLocaleString()}
                            </div>
                        </div>
                    </div>

                    {/* Positions Table */}
                    {(portfolio?.positions || []).length === 0 ? (
                        <div className="text-center py-12 border-2 border-dashed border-gray-800 rounded-xl">
                            <p className="text-gray-500 text-sm">No positions found on Testnet.</p>
                        </div>
                    ) : (
                        <div className="overflow-x-auto rounded-xl border border-gray-800">
                            <table className="w-full text-xs">
                                <thead>
                                    <tr className="bg-gray-900/80 text-gray-400 uppercase tracking-wider">
                                        <th className="px-4 py-3 text-left">Asset</th>
                                        <th className="px-4 py-3 text-right">Total</th>
                                        <th className="px-4 py-3 text-right">Free</th>
                                        <th className="px-4 py-3 text-right">In Use</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {(portfolio?.positions || []).map((pos, i) => (
                                        <tr key={i} className="border-t border-gray-800 hover:bg-gray-900/40 transition">
                                            <td className="px-4 py-3 font-bold text-white">{pos.currency}</td>
                                            <td className="px-4 py-3 text-right text-gray-300 font-mono">{pos.total}</td>
                                            <td className="px-4 py-3 text-right text-green-400 font-mono">{pos.free}</td>
                                            <td className="px-4 py-3 text-right text-yellow-400 font-mono">{pos.used}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default BotTracker;
