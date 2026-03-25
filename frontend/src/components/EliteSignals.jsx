import React, { useState } from 'react';
import {
    Trophy, Play, TrendingUp, Activity, Search,
    ArrowUpRight, ArrowDownRight, Gem, Loader2, CheckCircle2, Circle
} from 'lucide-react';
import {
    LineChart, Line, ResponsiveContainer, YAxis
} from 'recharts';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const GemRow = ({ gem, rank, onSelect }) => {
    // Format equity curve for Recharts { value: x }
    const chartData = gem.curve.map((val, i) => ({ i, value: val }));
    const isProfitable = gem.profit >= 0;
    const isShort = gem.best_strategy?.includes("SHORT");

    return (
        <tr
            onClick={() => onSelect(gem)}
            className="border-b border-gray-800 hover:bg-gray-800/50 transition-colors group cursor-pointer"
        >
            <td className="p-4 text-center text-gray-500 font-mono text-xs">#{rank}</td>
            <td className="p-4">
                <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center border font-bold text-xs text-white ${isShort ? 'bg-red-900/20 border-red-700' : 'bg-green-900/20 border-green-700'}`}>
                        {gem.symbol.split('/')[0].substring(0, 1)}
                    </div>
                    <div>
                        <div className="font-bold text-white text-sm flex items-center gap-1">
                            {gem.symbol}
                            {gem.score >= 80 && <Gem size={12} className="text-purple-400" />}
                        </div>
                        <div className="text-[10px] text-gray-500 flex items-center gap-1">
                            {isShort ? <ArrowDownRight size={10} className="text-red-500" /> : <ArrowUpRight size={10} className="text-green-500" />}
                            {isShort ? "SHORT" : "LONG"}
                        </div>
                    </div>
                </div>
            </td>
            <td className="p-4">
                <div className="text-xs font-mono text-gray-300">
                    {gem.best_strategy?.replace(" (LONG)", "").replace(" (SHORT)", "") || "Unknown"}
                </div>
            </td>
            <td className="p-4 text-center">
                <div className={`text-sm font-bold ${gem.score >= 80 ? 'text-purple-400' : gem.score >= 50 ? 'text-green-400' : 'text-yellow-600'}`}>
                    {gem.score}/100
                </div>
                <div className="w-16 h-1 bg-gray-800 rounded-full mx-auto mt-1 overflow-hidden">
                    <div
                        className={`h-full rounded-full ${gem.score >= 80 ? 'bg-purple-500' : gem.score >= 50 ? 'bg-green-500' : 'bg-yellow-600'}`}
                        style={{ width: `${gem.score}%` }}
                    />
                </div>
            </td>
            <td className="p-4 text-center">
                <div className={`text-sm font-bold ${isProfitable ? 'text-green-400' : 'text-red-400'}`}>
                    {isProfitable ? '+' : ''}{gem.profit}%
                </div>
            </td>
            <td className="p-4 text-center font-mono text-sm text-gray-300">
                {gem.win_rate}%
            </td>
            <td className="p-4 w-32 h-16">
                <div className="w-28 h-10">
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={chartData}>
                            <Line
                                type="monotone"
                                dataKey="value"
                                stroke={isProfitable ? '#4ade80' : '#f87171'}
                                strokeWidth={2}
                                dot={false}
                            />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </td>
            <td className="p-4 text-right">
                <button className="px-3 py-1.5 bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 rounded-lg text-xs font-bold transition flex items-center gap-1 ml-auto">
                    <Play size={12} /> Load
                </button>
            </td>
        </tr>
    );
};

const EliteSignals = ({ onGemSelect }) => {
    const [gems, setGems] = useState([]);
    const [loading, setLoading] = useState(false);
    const [scanned, setScanned] = useState(false);

    // Checkbox States
    const [useLong, setUseLong] = useState(true);
    const [useShort, setUseShort] = useState(false);

    const scanMarket = async () => {
        if (!useLong && !useShort) return; // Must select at least one

        setLoading(true);
        try {
            const modes = [];
            if (useLong) modes.push("LONG");
            if (useShort) modes.push("SHORT");

            const modeStr = modes.join(",");
            const res = await fetch(`${API_BASE}/api/scanner/elite?modes=${modeStr}`);

            if (res.ok) {
                const data = await res.json();
                setGems(data.gems || []);
                setScanned(true);
            }
        } catch (err) {
            console.error("Scanner error:", err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="animate-in slide-in-from-right-4 fade-in duration-300">
            {/* Header */}
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h2 className="text-xl font-black text-white flex items-center gap-2">
                        <Gem size={20} className="text-purple-500" /> Elite Gems Scanner
                    </h2>
                    <p className="text-xs text-gray-500 mt-1">
                        Deep Scan 30 top assets using <strong>Multi-Strategy Logic</strong> to find consistent growth.
                    </p>
                </div>

                <div className="flex items-center gap-4">
                    {/* Mode Toggles */}
                    <div className="flex items-center gap-2 bg-gray-900/50 p-1 rounded-lg border border-gray-800">
                        <button
                            onClick={() => setUseLong(!useLong)}
                            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-bold transition-all ${useLong ? 'bg-green-500/20 text-green-400 border border-green-500/30' : 'text-gray-500 hover:text-gray-300'}`}
                        >
                            {useLong ? <CheckCircle2 size={12} /> : <Circle size={12} />} Long
                        </button>
                        <button
                            onClick={() => setUseShort(!useShort)}
                            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-bold transition-all ${useShort ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'text-gray-500 hover:text-gray-300'}`}
                        >
                            {useShort ? <CheckCircle2 size={12} /> : <Circle size={12} />} Short
                        </button>
                    </div>

                    <button
                        onClick={scanMarket}
                        disabled={loading || (!useLong && !useShort)}
                        className={`flex items-center gap-2 px-6 py-2 rounded-xl font-bold transition-all shadow-lg ${loading || (!useLong && !useShort)
                            ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
                            : 'bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 text-white shadow-purple-900/20'
                            }`}
                    >
                        {loading ? <Loader2 size={18} className="animate-spin" /> : <Search size={18} />}
                        {loading ? 'Scanning...' : 'Find Gems '}
                    </button>
                </div>
            </div>

            {/* Empty State */}
            {!scanned && !loading && (
                <div className="text-center py-20 bg-gray-900/20 border border-dashed border-gray-800 rounded-xl">
                    <div className="w-16 h-16 bg-gray-800/50 rounded-full flex items-center justify-center mx-auto mb-4">
                        <Search size={32} className="text-gray-600" />
                    </div>
                    <h3 className="text-lg font-bold text-gray-300">Ready to Scan</h3>
                    <p className="text-sm text-gray-500 max-w-md mx-auto mt-2">
                        Select Long/Short modes and click "Find Gems".
                        The engine will backtest <strong>All 8 Strategies</strong> on top coins to find the best performers.
                    </p>
                </div>
            )}

            {/* Loading State */}
            {loading && (
                <div className="text-center py-20">
                    <Loader2 size={40} className="animate-spin text-purple-500 mx-auto mb-4" />
                    <h3 className="text-lg font-bold text-white">Analyzing Market Structure...</h3>
                    <p className="text-sm text-gray-500">Running Multi-Strategy Backtests on Top 30 Assets...</p>
                </div>
            )}

            {/* Results Table */}
            {scanned && !loading && (
                <div className="bg-gray-900/40 border border-gray-800 rounded-xl overflow-hidden">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="bg-gray-800/50 text-gray-400 text-xs uppercase">
                                <th className="p-4 text-center font-bold w-16">Rank</th>
                                <th className="p-4 font-bold">Asset / Side</th>
                                <th className="p-4 font-bold">Best Strategy</th>
                                <th className="p-4 text-center font-bold">Consistency ($R^2$)</th>
                                <th className="p-4 text-center font-bold">Proj. 30d Profit</th>
                                <th className="p-4 text-center font-bold">Win Rate</th>
                                <th className="p-4 text-center font-bold">Equity Curve</th>
                                <th className="p-4 text-right font-bold">Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {gems.map((gem, index) => (
                                <GemRow
                                    key={`${gem.symbol}-${index}`}
                                    gem={gem}
                                    rank={index + 1}
                                    onSelect={onGemSelect}
                                />
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
};

export default EliteSignals;
