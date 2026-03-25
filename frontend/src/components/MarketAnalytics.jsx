import React, { useState, useEffect, useMemo } from 'react';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
    ResponsiveContainer, BarChart, Bar, Cell
} from 'recharts';
import { TrendingUp, TrendingDown, Activity, Minus } from 'lucide-react';

const MarketAnalytics = ({ data }) => {
    // 2. Color Palette untuk Spaghetti Chart
    const colors = [
        "#8884d8", "#82ca9d", "#ffc658", "#ff7300",
        "#0088fe", "#00C49F", "#FFBB28", "#FF8042"
    ];

    // 3. Data Transformation untuk Spaghetti Chart
    const spaghettiData = [];
    const coinSymbols = useMemo(() => (data?.spaghetti || []).map(c => c.symbol), [data]);
    if (data?.spaghetti?.length > 0) {
        const baseTimestamps = data.spaghetti[0].data.map(d => d.time);
        baseTimestamps.forEach((ts, idx) => {
            let point = { time: new Date(ts * 1000).toLocaleDateString() };
            data.spaghetti.forEach(coin => {
                if (coin.data[idx]) {
                    point[coin.symbol] = coin.data[idx].value;
                }
            });
            spaghettiData.push(point);
        });
    }

    // 3B. Interactive Legend State — Toggle coin visibility (HOOKS MUST be called before early returns)
    const [visibleCoins, setVisibleCoins] = useState(new Set(coinSymbols));

    // Reset visibility when new analytics data arrives with different coins
    useEffect(() => {
        setVisibleCoins(new Set(coinSymbols));
    }, [coinSymbols]);

    // 1. Loading State & Validation (MOVED below hooks to fix Rules of Hooks violation)
    if (!data || !data.spaghetti || data.spaghetti.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center py-20 text-gray-500 animate-pulse bg-gray-900/20 rounded-3xl border border-gray-800">
                <Activity size={48} className="mb-4 opacity-50" />
                <div className="text-xl font-bold">Waiting for Analytics Data...</div>
                <div className="text-sm">Please run a scan or select a sector above.</div>
            </div>
        );
    }

    const toggleCoin = (symbol) => {
        setVisibleCoins(prev => {
            const next = new Set(prev);
            if (next.has(symbol)) {
                next.delete(symbol);
            } else {
                next.add(symbol);
            }
            return next;
        });
    };
    const showAllCoins = () => setVisibleCoins(new Set(coinSymbols));
    const hideAllCoins = () => setVisibleCoins(new Set());

    // Helper untuk Icon Market Condition
    const getConditionIcon = (condition) => {
        if (condition === 'UPTREND') return <TrendingUp size={16} className="text-green-400" />;
        if (condition === 'DOWNTREND') return <TrendingDown size={16} className="text-red-400" />;
        return <Minus size={16} className="text-gray-400" />;
    };

    return (
        <div className="space-y-8 animate-fade-in-up">

            {/* ================================================================================== */}
            {/* SECTION 1: MARKET CONDITION RADAR (NEW FEATURE) */}
            {/* ================================================================================== */}
            <div className="bg-gray-800/50 backdrop-blur-md p-6 rounded-3xl border border-gray-700 shadow-xl">
                <div className="mb-6 border-b border-gray-700 pb-4">
                    <h3 className="text-xl font-bold text-white flex items-center gap-2">
                         Market Condition Radar
                        <span className="text-xs text-cyan-400 font-mono py-1 px-2 bg-cyan-900/30 rounded border border-cyan-500/30">
                            ALGORITHM: SMA Crossover
                        </span>
                    </h3>
                    <p className="text-gray-400 text-sm mt-1">
                        Deteksi cepat status tren pasar (Uptrend/Downtrend) berdasarkan posisi harga terhadap SMA20 & SMA50.
                    </p>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
                    {data.market_conditions && data.market_conditions.map((mc, idx) => (
                        <div key={idx} className={`p-3 rounded-xl border flex flex-col items-center justify-center transition-all hover:scale-105 hover:shadow-lg ${mc.condition === 'UPTREND' ? 'bg-green-900/10 border-green-500/50 shadow-[0_0_10px_rgba(34,197,94,0.1)]' :
                            mc.condition === 'DOWNTREND' ? 'bg-red-900/10 border-red-500/50 shadow-[0_0_10px_rgba(239,68,68,0.1)]' :
                                'bg-gray-700/30 border-gray-600'
                            }`}>
                            <div className="font-bold text-white mb-2 text-sm">{mc.symbol}</div>
                            <div className={`flex items-center gap-1 text-[10px] font-black tracking-widest px-2 py-1 rounded-full ${mc.condition === 'UPTREND' ? 'bg-green-500/20 text-green-400' :
                                mc.condition === 'DOWNTREND' ? 'bg-red-500/20 text-red-400' :
                                    'bg-gray-600 text-gray-300'
                                }`}>
                                {getConditionIcon(mc.condition)}
                                {mc.condition}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* ================================================================================== */}
            {/* SECTION 2: SPAGHETTI CHART (NORMALIZED PERFORMANCE) */}
            {/* ================================================================================== */}
            <div className="bg-gray-800/50 backdrop-blur-md p-6 rounded-3xl border border-gray-700 shadow-xl">
                <div className="mb-6 flex flex-col md:flex-row justify-between items-start md:items-center">
                    <div>
                        <h3 className="text-xl font-bold text-white flex items-center gap-2">
                             Spaghetti Chart: Relative Performance
                        </h3>
                        <p className="text-gray-400 text-sm mt-1">
                            Membandingkan kekuatan tren semua koin dimulai dari titik yang sama (0%).
                        </p>
                    </div>
                    <div className="text-right hidden md:block">
                        <div className="text-xs text-gray-500">Benchmark Period</div>
                        <div className="text-sm font-bold text-cyan-400">Past 1 Year (Normalized)</div>
                    </div>
                </div>

                <div className="h-[450px] w-full bg-gray-900/30 rounded-xl p-2 border border-gray-700/50">
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={spaghettiData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                            <XAxis
                                dataKey="time"
                                stroke="#94a3b8"
                                fontSize={12}
                                minTickGap={50}
                                tick={{ fill: '#94a3b8' }}
                            />
                            <YAxis
                                stroke="#94a3b8"
                                unit="%"
                                fontSize={12}
                                tick={{ fill: '#94a3b8' }}
                            />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#f8fafc', borderRadius: '8px' }}
                                itemStyle={{ color: '#fff' }}
                                labelStyle={{ color: '#94a3b8', marginBottom: '0.5rem' }}
                            />

                            {/* Lines — only render visible coins */}
                            {data.spaghetti.map((coin, index) => (
                                visibleCoins.has(coin.symbol) ? (
                                    <Line
                                        key={coin.symbol}
                                        type="monotone"
                                        dataKey={coin.symbol}
                                        stroke={colors[index % colors.length]}
                                        dot={false}
                                        strokeWidth={2}
                                        activeDot={{ r: 6, strokeWidth: 0 }}
                                    />
                                ) : null
                            ))}
                        </LineChart>
                    </ResponsiveContainer>
                </div>

                {/* INTERACTIVE LEGEND — Click to toggle coins */}
                <div className="mt-4 flex flex-wrap items-center gap-2">
                    <button
                        onClick={showAllCoins}
                        className="text-[10px] font-bold px-2 py-1 rounded border border-cyan-500/40 bg-cyan-900/20 text-cyan-400 hover:bg-cyan-900/40 transition"
                    >
                        Show All
                    </button>
                    <button
                        onClick={hideAllCoins}
                        className="text-[10px] font-bold px-2 py-1 rounded border border-gray-600 bg-gray-800/50 text-gray-400 hover:bg-gray-700/50 transition"
                    >
                        Hide All
                    </button>
                    <span className="text-gray-600 text-[10px]">|</span>
                    {data.spaghetti.map((coin, index) => {
                        const isVisible = visibleCoins.has(coin.symbol);
                        const color = colors[index % colors.length];
                        return (
                            <button
                                key={coin.symbol}
                                onClick={() => toggleCoin(coin.symbol)}
                                className="flex items-center gap-1 px-2 py-1 rounded-full transition-all text-[11px] font-bold cursor-pointer"
                                style={{
                                    background: isVisible ? `${color}22` : 'rgba(255,255,255,0.03)',
                                    border: `1px solid ${isVisible ? color : 'rgba(255,255,255,0.1)'}`,
                                    color: isVisible ? color : '#6b7280',
                                    opacity: isVisible ? 1 : 0.5
                                }}
                            >
                                <span style={{
                                    width: '8px', height: '8px', borderRadius: '50%',
                                    background: isVisible ? color : '#4b5563', display: 'inline-block'
                                }} />
                                {coin.symbol}
                            </button>
                        );
                    })}
                </div>

                {/* PERFORMANCE SUMMARY CARDS */}
                <div className="mt-6">
                    <h4 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-3">Performance Summary</h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
                        {data.performance.map((p, idx) => (
                            <div key={idx} className={`p-3 rounded-lg border text-center transition hover:-translate-y-1 ${p.return_pct >= 0 ? 'bg-green-900/10 border-green-800/50' : 'bg-red-900/10 border-red-800/50'}`}>
                                <div className="text-[10px] text-gray-400 font-bold mb-1">{p.symbol}</div>
                                <div className={`text-base font-black font-mono ${p.return_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                    {p.return_pct > 0 ? '+' : ''}{p.return_pct}%
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* ================================================================================== */}
            {/* SECTION 3: RISK & DISTRIBUTION METRICS */}
            {/* ================================================================================== */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

                {/* VOLATILITY COMPARISON */}
                <div className="bg-gray-800/50 backdrop-blur-md p-6 rounded-3xl border border-gray-700 shadow-xl">
                    <div className="mb-4">
                        <h3 className="text-lg font-bold text-white flex items-center gap-2"> Annualized Volatility</h3>
                        <p className="text-gray-400 text-xs mt-1 leading-relaxed">
                            Mengukur fluktuasi harga tahunan.
                            <br /><span className="text-green-400 font-bold">Rendah</span> = Stabil/Safe Haven.
                            <span className="text-red-400 font-bold ml-2">Tinggi</span> = High Risk/Reward.
                        </p>
                    </div>
                    <div className="h-[300px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={data.volatility} layout="vertical" margin={{ left: 10, right: 30 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
                                <XAxis type="number" stroke="#94a3b8" unit="%" fontSize={10} />
                                <YAxis dataKey="symbol" type="category" stroke="#94a3b8" width={60} tick={{ fontSize: 11, fontWeight: 'bold' }} />
                                <Tooltip cursor={{ fill: 'rgba(255,255,255,0.05)' }} contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }} />
                                <Bar dataKey="volatility" radius={[0, 4, 4, 0]} barSize={20}>
                                    {data.volatility.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.volatility > 100 ? '#ef4444' : (entry.volatility > 60 ? '#f59e0b' : '#3b82f6')} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* RETURN DISTRIBUTION */}
                <div className="bg-gray-800/50 backdrop-blur-md p-6 rounded-3xl border border-gray-700 shadow-xl">
                    <div className="mb-4">
                        <h3 className="text-lg font-bold text-white flex items-center gap-2"> Daily Return Histogram</h3>
                        <p className="text-gray-400 text-xs mt-1 leading-relaxed">
                            Frekuensi kenaikan/penurunan harga harian.
                            <br /><span className="text-gray-300">Analisa:</span> Grafik condong ke kanan (Hijau) menandakan tren Bullish yang sehat.
                        </p>
                    </div>
                    <div className="h-[300px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={data.distribution} margin={{ top: 10 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                                <XAxis dataKey="range" stroke="#94a3b8" fontSize={10} tickLine={false} axisLine={false} />
                                <YAxis stroke="#94a3b8" fontSize={10} tickLine={false} axisLine={false} />
                                <Tooltip cursor={{ fill: 'rgba(255,255,255,0.05)' }} contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }} />
                                <Bar dataKey="count" radius={[4, 4, 0, 0]} barSize={40}>
                                    {data.distribution.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={index < 3 ? '#ef4444' : '#10b981'} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

            </div>
        </div>
    );
};

export default MarketAnalytics;