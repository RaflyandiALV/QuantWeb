import React, { useState, useEffect, useCallback } from 'react';
import {
    LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, Area, AreaChart, Cell, ReferenceLine
} from 'recharts';
import {
    TrendingUp, Wallet, DollarSign, ArrowUpCircle, ArrowDownCircle,
    RefreshCw, PieChart, BarChart3, Clock
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const PortfolioPage = () => {
    const [summary, setSummary] = useState(null);
    const [equityCurve, setEquityCurve] = useState([]);
    const [dailyPnl, setDailyPnl] = useState([]);
    const [loading, setLoading] = useState(true);
    const [activeChart, setActiveChart] = useState('equity'); // equity | pnl

    const fetchAll = useCallback(async () => {
        setLoading(true);
        try {
            const [sumRes, eqRes, pnlRes] = await Promise.allSettled([
                fetch(`${API_URL}/api/portfolio/summary`),
                fetch(`${API_URL}/api/portfolio/equity-curve?days=30`),
                fetch(`${API_URL}/api/portfolio/daily-pnl?days=30`)
            ]);

            if (sumRes.status === 'fulfilled' && sumRes.value.ok) setSummary(await sumRes.value.json());
            if (eqRes.status === 'fulfilled' && eqRes.value.ok) {
                const d = await eqRes.value.json();
                setEquityCurve((d.curve || []).map(p => ({
                    ...p,
                    time: new Date(p.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
                    fullTime: new Date(p.timestamp).toLocaleString(),
                })));
            }
            if (pnlRes.status === 'fulfilled' && pnlRes.value.ok) {
                const d = await pnlRes.value.json();
                setDailyPnl((d.daily_pnl || []).map(p => ({ ...p, label: p.date.slice(5) })));
            }
        } catch (err) {
            console.error("Portfolio fetch error:", err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchAll();
        const interval = setInterval(fetchAll, 60000); // refresh every 60s
        return () => clearInterval(interval);
    }, [fetchAll]);

    const totalEquity = summary?.total_equity || 0;
    const todayPnl = summary?.today_pnl || 0;
    const cashPct = summary?.cash_pct || 100;
    const investedPct = summary?.invested_pct || 0;
    const mode = summary?.mode || 'PUBLIC';

    // Custom tooltip for equity curve
    const EquityTooltip = ({ active, payload }) => {
        if (!active || !payload?.length) return null;
        return (
            <div className="bg-gray-900 border border-cyan-500/30 rounded-lg px-4 py-2 shadow-xl text-xs">
                <div className="text-gray-400">{payload[0]?.payload?.fullTime}</div>
                <div className="text-cyan-400 font-bold text-lg">${payload[0]?.value?.toLocaleString()}</div>
                <div className="text-gray-500">Cash: ${payload[0]?.payload?.cash?.toLocaleString()}</div>
            </div>
        );
    };

    // Custom tooltip for PnL
    const PnlTooltip = ({ active, payload }) => {
        if (!active || !payload?.length) return null;
        const pnl = payload[0]?.value || 0;
        return (
            <div className="bg-gray-900 border border-cyan-500/30 rounded-lg px-4 py-2 shadow-xl text-xs">
                <div className="text-gray-400">{payload[0]?.payload?.date}</div>
                <div className={`font-bold text-lg ${pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {pnl >= 0 ? '+' : ''}${pnl.toLocaleString()}
                </div>
                <div className="text-gray-500">{payload[0]?.payload?.pnl_pct}%</div>
            </div>
        );
    };

    return (
        <div className="animate-in slide-in-from-right-4 fade-in duration-300">

            {/* Mode Badge + Refresh */}
            <div className="flex justify-between items-center mb-6">
                <div className="flex items-center gap-3">
                    <h2 className="text-xl font-black text-white flex items-center gap-2">
                        <PieChart size={20} className="text-green-400" /> Portfolio Dashboard
                    </h2>
                    <div className={`px-3 py-1 rounded-full text-xs font-bold border ${mode === 'TESTNET' ? 'bg-yellow-500/10 border-yellow-500/30 text-yellow-400' : 'bg-gray-800 border-gray-700 text-gray-400'}`}>
                        {mode === 'TESTNET' ? '🧪 TESTNET' : '⚠️ PUBLIC'}
                    </div>
                </div>
                <button onClick={fetchAll} disabled={loading} className="flex items-center gap-1 text-xs text-gray-400 hover:text-cyan-400 transition px-3 py-1.5 rounded-lg border border-gray-700 hover:border-cyan-500/30">
                    <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
                    {loading ? 'Loading...' : 'Refresh'}
                </button>
            </div>

            {/* ============= STAT CARDS ============= */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                {/* Total Equity */}
                <div className="bg-gradient-to-br from-cyan-900/20 to-cyan-900/5 border border-cyan-500/20 p-5 rounded-xl">
                    <div className="text-cyan-400/60 text-[10px] uppercase font-bold mb-1 flex items-center gap-1"><DollarSign size={10} />Total Equity</div>
                    <div className="text-3xl font-black text-cyan-400">${totalEquity.toLocaleString()}</div>
                    <div className="text-[10px] text-gray-500 mt-1">
                        Cash: ${summary?.usdt_balance?.toLocaleString() || '0'} | Invested: ${summary?.non_usdt_value?.toLocaleString() || '0'}
                    </div>
                </div>

                {/* Today's PnL */}
                <div className={`border p-5 rounded-xl ${todayPnl >= 0 ? 'bg-green-900/10 border-green-500/20' : 'bg-red-900/10 border-red-500/20'}`}>
                    <div className="text-gray-500 text-[10px] uppercase font-bold mb-1 flex items-center gap-1">
                        {todayPnl >= 0 ? <ArrowUpCircle size={10} className="text-green-400" /> : <ArrowDownCircle size={10} className="text-red-400" />}
                        Today's PnL
                    </div>
                    <div className={`text-3xl font-black ${todayPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {todayPnl >= 0 ? '+' : ''}${todayPnl.toLocaleString()}
                    </div>
                </div>

                {/* Cash Allocation */}
                <div className="bg-gray-900/50 border border-gray-800 p-5 rounded-xl">
                    <div className="text-gray-500 text-[10px] uppercase font-bold mb-1 flex items-center gap-1"><Wallet size={10} />Cash %</div>
                    <div className="text-3xl font-black text-white">{cashPct}%</div>
                    <div className="w-full bg-gray-800 rounded-full h-1.5 mt-2">
                        <div className="bg-green-500 h-1.5 rounded-full transition-all" style={{ width: `${cashPct}%` }}></div>
                    </div>
                </div>

                {/* Invested Allocation */}
                <div className="bg-gray-900/50 border border-gray-800 p-5 rounded-xl">
                    <div className="text-gray-500 text-[10px] uppercase font-bold mb-1 flex items-center gap-1"><BarChart3 size={10} />Invested %</div>
                    <div className="text-3xl font-black text-yellow-400">{investedPct}%</div>
                    <div className="w-full bg-gray-800 rounded-full h-1.5 mt-2">
                        <div className="bg-yellow-500 h-1.5 rounded-full transition-all" style={{ width: `${investedPct}%` }}></div>
                    </div>
                </div>
            </div>

            {/* ============= CHART TABS ============= */}
            <div className="flex gap-2 mb-4">
                <button
                    onClick={() => setActiveChart('equity')}
                    className={`flex items-center gap-1.5 px-5 py-2 rounded-lg text-xs font-bold transition border ${activeChart === 'equity'
                            ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30'
                            : 'text-gray-500 border-gray-800 hover:text-white hover:border-gray-600'
                        }`}
                >
                    <TrendingUp size={14} /> Equity Curve
                </button>
                <button
                    onClick={() => setActiveChart('pnl')}
                    className={`flex items-center gap-1.5 px-5 py-2 rounded-lg text-xs font-bold transition border ${activeChart === 'pnl'
                            ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30'
                            : 'text-gray-500 border-gray-800 hover:text-white hover:border-gray-600'
                        }`}
                >
                    <BarChart3 size={14} /> Daily PnL
                </button>
            </div>

            {/* ============= EQUITY CURVE CHART ============= */}
            {activeChart === 'equity' && (
                <div className="bg-gray-900/40 border border-gray-800 rounded-xl p-6 mb-8">
                    <h3 className="text-sm font-bold text-gray-400 mb-4 flex items-center gap-2">
                        <TrendingUp size={14} className="text-cyan-500" /> EQUITY CURVE — 30 DAY
                    </h3>
                    {equityCurve.length === 0 ? (
                        <div className="text-center py-16 text-gray-600">
                            <div className="text-4xl mb-3">📈</div>
                            <p className="text-sm">No equity data yet. Snapshots are taken every 5 minutes.</p>
                            <p className="text-xs text-gray-700 mt-1">The equity curve will appear here once enough data is collected.</p>
                        </div>
                    ) : (
                        <ResponsiveContainer width="100%" height={300}>
                            <AreaChart data={equityCurve}>
                                <defs>
                                    <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="#22d3ee" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                                <XAxis dataKey="time" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={{ stroke: '#334155' }} />
                                <YAxis tick={{ fill: '#64748b', fontSize: 10 }} axisLine={{ stroke: '#334155' }} domain={['auto', 'auto']} tickFormatter={v => `$${v.toLocaleString()}`} />
                                <Tooltip content={<EquityTooltip />} />
                                <Area type="monotone" dataKey="equity" stroke="#22d3ee" fill="url(#eqGrad)" strokeWidth={2} dot={false} />
                            </AreaChart>
                        </ResponsiveContainer>
                    )}
                </div>
            )}

            {/* ============= DAILY PNL BAR CHART ============= */}
            {activeChart === 'pnl' && (
                <div className="bg-gray-900/40 border border-gray-800 rounded-xl p-6 mb-8">
                    <h3 className="text-sm font-bold text-gray-400 mb-4 flex items-center gap-2">
                        <BarChart3 size={14} className="text-purple-500" /> DAILY P&L — 30 DAY
                    </h3>
                    {dailyPnl.length === 0 ? (
                        <div className="text-center py-16 text-gray-600">
                            <div className="text-4xl mb-3">📊</div>
                            <p className="text-sm">No PnL data yet. Daily PnL is calculated from equity snapshots.</p>
                        </div>
                    ) : (
                        <ResponsiveContainer width="100%" height={300}>
                            <BarChart data={dailyPnl}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                                <XAxis dataKey="label" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={{ stroke: '#334155' }} />
                                <YAxis tick={{ fill: '#64748b', fontSize: 10 }} axisLine={{ stroke: '#334155' }} tickFormatter={v => `$${v}`} />
                                <Tooltip content={<PnlTooltip />} />
                                <ReferenceLine y={0} stroke="#475569" strokeDasharray="3 3" />
                                <Bar dataKey="pnl" radius={[4, 4, 0, 0]}>
                                    {dailyPnl.map((entry, i) => (
                                        <Cell key={i} fill={entry.pnl >= 0 ? '#22c55e' : '#ef4444'} fillOpacity={0.8} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    )}
                </div>
            )}

            {/* ============= POSITIONS TABLE ============= */}
            <div className="bg-gray-900/40 border border-gray-800 rounded-xl p-6">
                <h3 className="text-sm font-bold text-gray-400 mb-4 flex items-center gap-2">
                    <Wallet size={14} className="text-green-500" /> CURRENT POSITIONS
                </h3>

                {(summary?.positions || []).length === 0 ? (
                    <div className="text-center py-12 border-2 border-dashed border-gray-800 rounded-xl">
                        <div className="text-4xl mb-3">💼</div>
                        <p className="text-gray-500 text-sm">No positions found on {mode}.</p>
                        <p className="text-xs text-gray-600 mt-1">Positions will appear here after the bot executes trades.</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto rounded-xl border border-gray-800">
                        <table className="w-full text-xs">
                            <thead>
                                <tr className="bg-gray-900/80 text-gray-400 uppercase tracking-wider">
                                    <th className="px-4 py-3 text-left">Asset</th>
                                    <th className="px-4 py-3 text-right">Amount</th>
                                    <th className="px-4 py-3 text-right">Price (USDT)</th>
                                    <th className="px-4 py-3 text-right">Value (USDT)</th>
                                    <th className="px-4 py-3 text-right">Allocation</th>
                                </tr>
                            </thead>
                            <tbody>
                                {(summary?.positions || []).map((pos, i) => (
                                    <tr key={i} className="border-t border-gray-800 hover:bg-gray-900/60 transition">
                                        <td className="px-4 py-3 font-bold text-white">{pos.currency}</td>
                                        <td className="px-4 py-3 text-right text-gray-300 font-mono">{pos.amount}</td>
                                        <td className="px-4 py-3 text-right text-gray-300 font-mono">${pos.price_usdt?.toLocaleString()}</td>
                                        <td className="px-4 py-3 text-right text-cyan-400 font-mono font-bold">${pos.value_usdt?.toLocaleString()}</td>
                                        <td className="px-4 py-3 text-right">
                                            <div className="flex items-center justify-end gap-2">
                                                <div className="w-16 bg-gray-800 rounded-full h-1.5">
                                                    <div className="bg-cyan-500 h-1.5 rounded-full" style={{ width: `${Math.min(pos.allocation_pct, 100)}%` }}></div>
                                                </div>
                                                <span className="text-gray-400 font-mono w-10 text-right">{pos.allocation_pct}%</span>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Footer info */}
            <div className="mt-6 bg-blue-900/10 border border-blue-500/20 p-4 rounded-xl">
                <h4 className="font-bold text-blue-400 text-sm mb-1">📸 Snapshots</h4>
                <p className="text-xs text-blue-200/80 leading-relaxed">
                    Portfolio equity is recorded every 5 minutes. The equity curve and daily PnL charts are built from these snapshots.
                    The more data collected, the more detailed the charts become.
                </p>
            </div>
        </div>
    );
};

export default PortfolioPage;
