import React, { useState } from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip as RechartsTooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { Activity, Play, ShieldAlert, BarChart3, Info } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const MonteCarloChart = ({ symbol, capital, strategy, period, timeframe }) => {
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);

    const runSimulation = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(`${API_URL}/api/monte-carlo`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symbol, capital, strategy, period, timeframe })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || data.error || 'Server error');
            if (data.error) throw new Error(data.error);
            setResult(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    if (!result && !loading && !error) {
        return (
            <div className="bg-gray-900/40 border border-gray-800 rounded-xl p-5 mt-4 text-center">
                <ShieldAlert className="w-10 h-10 text-purple-500 mx-auto mb-3 opacity-50" />
                <h3 className="text-white font-bold mb-2">Institutional Monte Carlo Analysis</h3>
                <p className="text-xs text-gray-400 max-w-md mx-auto mb-4">
                    Run 5,000 bootstrap resampled realities to calculate Tail Risk, Expected Shortfall (CVaR), and Probability of Ruin based on this strategy's historical trades.
                </p>
                <button
                    onClick={runSimulation}
                    className="bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold py-2 px-6 rounded-lg transition-colors flex items-center gap-2 mx-auto"
                >
                    <Play size={14} /> Run 5,000 Simulations
                </button>
            </div>
        );
    }

    if (loading) {
        return (
            <div className="bg-gray-900/40 border border-gray-800 rounded-xl p-10 mt-4 flex flex-col items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500 mb-4"></div>
                <div className="text-sm font-bold text-gray-300">Resampling histories...</div>
                <div className="text-xs text-gray-500 mt-1">Generating 5,000 possible equity paths</div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-red-900/20 border border-red-500/30 rounded-xl p-5 mt-4 text-center">
                <div className="text-red-400 font-bold mb-2">Simulation Failed</div>
                <div className="text-xs text-gray-400">{error}</div>
                <button onClick={runSimulation} className="mt-4 text-xs text-red-400 underline hover:text-red-300">Try Again</button>
            </div>
        );
    }

    const { metrics, chart_data } = result;

    return (
        <div className="bg-gray-900/40 border border-gray-800 rounded-xl p-5 mt-4">
            <div className="flex justify-between items-center mb-5">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <Activity size={16} className="text-purple-500" />
                    Monte Carlo Trajectory (5,000 Paths)
                </h3>
                <div className="text-[10px] text-gray-500 bg-gray-800/50 px-2 py-1 rounded">
                    Bootstrap Resampling
                </div>
            </div>

            {/* Main Risk Metrics Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
                <div className="bg-gray-800/40 border border-gray-700 p-3 rounded-lg relative group">
                    <div className="text-[9px] uppercase font-bold text-gray-500 mb-1 flex justify-between">
                        VaR 95% <Info size={10} className="cursor-help" />
                    </div>
                    <div className="text-lg font-black text-red-400">{metrics.var_95_pct}%</div>
                    <div className="absolute hidden group-hover:block bg-gray-700 text-[10px] text-white p-2 rounded -top-8 left-0 w-48 z-10 shadow-xl border border-gray-600">
                        Value at Risk: Expected max loss in 95% of trades.
                    </div>
                </div>

                <div className="bg-gray-800/40 border border-gray-700 p-3 rounded-lg relative group">
                    <div className="text-[9px] uppercase font-bold text-gray-500 mb-1 flex justify-between">
                        CVaR / Expected Shortfall <Info size={10} className="cursor-help" />
                    </div>
                    <div className="text-lg font-black text-red-500">{metrics.cvar_95_pct}%</div>
                    <div className="absolute hidden group-hover:block bg-gray-700 text-[10px] text-white p-2 rounded -top-8 left-0 w-48 z-10 shadow-xl border border-gray-600">
                        Average loss when loss exceeds the 95% VaR threshold (Tail Risk).
                    </div>
                </div>

                <div className="bg-gray-800/40 border border-gray-700 p-3 rounded-lg relative group">
                    <div className="text-[9px] uppercase font-bold text-gray-500 mb-1 flex justify-between">
                        Probability of Ruin <Info size={10} className="cursor-help" />
                    </div>
                    <div className="text-lg font-black text-orange-400">{metrics.probability_of_ruin_pct}%</div>
                    <div className="absolute hidden group-hover:block bg-gray-700 text-[10px] text-white p-2 rounded -top-8 left-0 w-48 z-10 shadow-xl border border-gray-600">
                        Chance of losing &gt;20% of initial capital.
                    </div>
                </div>

                <div className="bg-gray-800/40 border border-gray-700 p-3 rounded-lg relative group">
                    <div className="text-[9px] uppercase font-bold text-gray-500 mb-1 flex justify-between">
                        Kelly Criterion <Info size={10} className="cursor-help" />
                    </div>
                    <div className="text-lg font-black text-cyan-400">{metrics.kelly_criterion_pct}%</div>
                    <div className="absolute hidden group-hover:block bg-gray-700 text-[10px] text-white p-2 rounded -top-8 left-0 w-48 z-10 shadow-xl border border-gray-600">
                        Theoretical optimal bet size. (Use Half-Kelly: {metrics.half_kelly_pct}% for safety)
                    </div>
                </div>
            </div>

            {/* Fan Chart Visualization */}
            <div className="h-64 mb-4">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chart_data} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                        <defs>
                            <linearGradient id="colorP95" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#4ade80" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#4ade80" stopOpacity={0} />
                            </linearGradient>
                            <linearGradient id="colorP5" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#f87171" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#f87171" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <XAxis dataKey="trade" stroke="#374151" tick={{ fontSize: 10, fill: '#6b7280' }} />
                        <YAxis stroke="#374151" tick={{ fontSize: 10, fill: '#6b7280' }} tickFormatter={(vals) => '$' + vals.toLocaleString()} />
                        <RechartsTooltip
                            contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', fontSize: '12px' }}
                            itemStyle={{ color: '#e5e7eb' }}
                            formatter={(value) => ['$' + Math.round(value).toLocaleString()]}
                            labelFormatter={(label) => `Trade #${label}`}
                        />
                        <ReferenceLine y={capital} stroke="#4b5563" strokeDasharray="3 3" />

                        <Area type="monotone" dataKey="p95" name="P95 (Optimistic)" stroke="#4ade80" fillOpacity={1} fill="url(#colorP95)" strokeWidth={1} />
                        <Area type="monotone" dataKey="p5" name="P5 (Conservative)" stroke="#f87171" fillOpacity={1} fill="url(#colorP5)" strokeWidth={1} />
                        <Area type="monotone" dataKey="median" name="Median Path" stroke="#22d3ee" fill="none" strokeWidth={2} />
                    </AreaChart>
                </ResponsiveContainer>
            </div>

            <div className="flex items-center justify-between text-[10px] text-gray-500 px-2 mt-2">
                <div className="flex items-center gap-4">
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-400"></span> 95th Percentile</span>
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-cyan-400"></span> Median</span>
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-400"></span> 5th Percentile</span>
                </div>
                <div>Based on {metrics.simulations_run} stochastic paths</div>
            </div>

            <button onClick={() => setResult(null)} className="w-full mt-4 bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs py-2 rounded-lg transition-colors">
                Reset Analysis
            </button>
        </div>
    );
};

export default MonteCarloChart;
