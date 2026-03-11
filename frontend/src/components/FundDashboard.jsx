import React, { useState, useEffect, useCallback } from 'react';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    BarChart, Bar, Cell, ReferenceLine
} from 'recharts';
import {
    Trophy, TrendingUp, TrendingDown, Activity, Calendar, Percent,
    ArrowUpRight, ArrowDownRight, RefreshCw, Scale
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const KPI_COLOR_MAP = {
    cyan: { border: 'border-cyan-500/20', hoverBorder: 'hover:border-cyan-500/40', text: 'text-cyan-400' },
    purple: { border: 'border-purple-500/20', hoverBorder: 'hover:border-purple-500/40', text: 'text-purple-400' },
    blue: { border: 'border-blue-500/20', hoverBorder: 'hover:border-blue-500/40', text: 'text-blue-400' },
    red: { border: 'border-red-500/20', hoverBorder: 'hover:border-red-500/40', text: 'text-red-400' },
    green: { border: 'border-green-500/20', hoverBorder: 'hover:border-green-500/40', text: 'text-green-400' },
    orange: { border: 'border-orange-500/20', hoverBorder: 'hover:border-orange-500/40', text: 'text-orange-400' },
    yellow: { border: 'border-yellow-500/20', hoverBorder: 'hover:border-yellow-500/40', text: 'text-yellow-400' },
};

const KPICard = ({ label, value, subtext, icon: Icon, color = "cyan", format = "number" }) => {
    const c = KPI_COLOR_MAP[color] || KPI_COLOR_MAP.cyan;
    return (
        <div className={`bg-gray-900/40 border ${c.border} p-5 rounded-xl relative overflow-hidden group ${c.hoverBorder} transition-all`}>
            <div className={`absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-20 transition-opacity ${c.text}`}>
                {Icon && <Icon size={40} />}
            </div>
            <div className="text-gray-500 text-[10px] uppercase font-bold mb-1 flex items-center gap-1">
                {Icon && <Icon size={12} className={c.text} />} {label}
            </div>
            <div className="text-2xl font-black text-white">
                {format === "pct" ? `${value}%` : value}
            </div>
            {subtext && <div className="text-[10px] text-gray-500 mt-1">{subtext}</div>}
        </div>
    );
};

const MonthlyHeatmap = ({ data }) => {
    const years = Object.keys(data).sort().reverse();
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

    return (
        <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse">
                <thead>
                    <tr>
                        <th className="text-left text-gray-500 p-2">Year</th>
                        {months.map(m => <th key={m} className="text-gray-500 p-2">{m}</th>)}
                        <th className="text-right text-gray-500 p-2">YTD</th>
                    </tr>
                </thead>
                <tbody>
                    {years.map(year => {
                        const yData = data[year] || {};
                        const ytd = Object.values(yData).reduce((acc, val) => (1 + acc / 100) * (1 + val / 100), 1) - 1;

                        return (
                            <tr key={year} className="border-t border-gray-800 hover:bg-gray-900/30">
                                <td className="font-bold text-gray-400 p-2">{year}</td>
                                {months.map(m => {
                                    const val = yData[m];
                                    let bgClass = "bg-gray-900/20";
                                    let textClass = "text-gray-600";

                                    if (val !== undefined) {
                                        if (val >= 5) bgClass = "bg-green-500/40";
                                        else if (val > 0) bgClass = "bg-green-500/20";
                                        else if (val <= -5) bgClass = "bg-red-500/40";
                                        else if (val < 0) bgClass = "bg-red-500/20";

                                        textClass = val >= 0 ? "text-green-400" : "text-red-400";
                                    }

                                    return (
                                        <td key={m} className="p-1">
                                            {val !== undefined && (
                                                <div className={`${bgClass} ${textClass} rounded p-1 text-center font-mono font-bold`}>
                                                    {val > 0 ? '+' : ''}{val}%
                                                </div>
                                            )}
                                        </td>
                                    );
                                })}
                                <td className={`text-right p-2 font-black ${ytd >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                    {ytd > 0 ? '+' : ''}{(ytd * 100).toFixed(1)}%
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
};

const FundDashboard = () => {
    const [metrics, setMetrics] = useState(null);
    const [loading, setLoading] = useState(true);

    const fetchMetrics = useCallback(async () => {
        setLoading(true);
        try {
            const res = await fetch(`${API_URL}/api/fund/performance`);
            if (res.ok) {
                setMetrics(await res.json());
            }
        } catch (err) {
            console.error("Fund metrics error:", err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchMetrics();
    }, [fetchMetrics]);

    if (!metrics && loading) return <div className="text-center py-20 text-blue-400 animate-pulse">Loading Fund Analytics...</div>;

    const m = metrics || {};

    return (
        <div className="animate-in slide-in-from-right-4 fade-in duration-300">

            {/* Header */}
            <div className="flex justify-between items-center mb-6">
                <div className="flex items-center gap-3">
                    <h2 className="text-xl font-black text-white flex items-center gap-2">
                        <Trophy size={20} className="text-yellow-500" /> Fund Performance
                    </h2>
                    <div className="px-3 py-1 rounded-full text-xs font-bold border bg-gray-800 border-gray-700 text-gray-400">
                        MONTHLY TEARSHEET
                    </div>
                </div>
                <button onClick={fetchMetrics} disabled={loading} className="flex items-center gap-1 text-xs text-gray-400 hover:text-cyan-400 transition px-3 py-1.5 rounded-lg border border-gray-700 hover:border-cyan-500/30">
                    <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
                    {loading ? 'Loading...' : 'Refresh'}
                </button>
            </div>

            {/* KPI Grid */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                <KPICard
                    label="Sharpe Ratio"
                    value={m.sharpe_ratio}
                    icon={Activity}
                    color="purple"
                    subtext="Risk-adjusted return (Annualized)"
                />
                <KPICard
                    label="Sortino Ratio"
                    value={m.sortino_ratio}
                    icon={Scale}
                    color="blue"
                    subtext="Downside risk-adjusted return"
                />
                <KPICard
                    label="Max Drawdown"
                    value={m.max_drawdown_pct}
                    icon={TrendingDown}
                    color="red"
                    format="pct"
                    subtext="Worst peak-to-valley drop"
                />
                <KPICard
                    label="Calmar Ratio"
                    value={m.calmar_ratio}
                    icon={TrendingUp}
                    color="green"
                    subtext="Annual Return / Max Drawdown"
                />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
                {/* Monthly Returns Heatmap - Wide */}
                <div className="lg:col-span-2 bg-gray-900/40 border border-gray-800 rounded-xl p-6">
                    <h3 className="text-sm font-bold text-gray-400 mb-4 flex items-center gap-2">
                        <Calendar size={14} className="text-cyan-500" /> MONTHLY RETURNS
                    </h3>
                    {Object.keys(m.monthly_returns || {}).length === 0 ? (
                        <div className="text-center py-12 text-gray-600 text-sm">No monthly data available yet.</div>
                    ) : (
                        <MonthlyHeatmap data={m.monthly_returns} />
                    )}
                </div>

                {/* Trade Statistics - Narrow */}
                <div className="bg-gray-900/40 border border-gray-800 rounded-xl p-6">
                    <h3 className="text-sm font-bold text-gray-400 mb-4 flex items-center gap-2">
                        <Percent size={14} className="text-orange-500" /> TRADE STATISTICS
                    </h3>

                    <div className="space-y-4">
                        <div className="flex justify-between items-center p-3 bg-gray-800/50 rounded-lg">
                            <span className="text-xs text-gray-400">Win Rate</span>
                            <span className={`font-black ${m.win_rate >= 50 ? 'text-green-400' : 'text-red-400'}`}>
                                {m.win_rate}%
                            </span>
                        </div>
                        <div className="flex justify-between items-center p-3 bg-gray-800/50 rounded-lg">
                            <span className="text-xs text-gray-400">Profit Factor</span>
                            <span className="font-mono text-white">{m.profit_factor}</span>
                        </div>
                        <div className="flex justify-between items-center p-3 bg-gray-800/50 rounded-lg">
                            <span className="text-xs text-gray-400">Total Trades</span>
                            <span className="font-mono text-white">{m.trades_count}</span>
                        </div>
                        <div className="border-t border-gray-800 pt-3">
                            <div className="flex justify-between text-xs mb-1">
                                <span className="text-gray-500">Avg Win</span>
                                <span className="text-green-400 font-mono">+${m.avg_win?.toLocaleString()}</span>
                            </div>
                            <div className="flex justify-between text-xs">
                                <span className="text-gray-500">Avg Loss</span>
                                <span className="text-red-400 font-mono">-${Math.abs(m.avg_loss || 0)?.toLocaleString()}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Footer */}
            <div className="bg-gradient-to-r from-gray-900 to-gray-800 border border-gray-700 p-4 rounded-xl flex justify-between items-center">
                <div>
                    <h4 className="font-bold text-white text-sm">QuantFund Tearsheet</h4>
                    <p className="text-xs text-gray-400">Generated on {new Date().toLocaleDateString()}</p>
                </div>
                <div className="text-right">
                    <div className="text-[10px] text-gray-500 uppercase font-bold">Total Return</div>
                    <div className={`text-xl font-black ${m.total_return_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {m.total_return_pct >= 0 ? '+' : ''}{m.total_return_pct}%
                    </div>
                </div>
            </div>

        </div>
    );
};

export default FundDashboard;
