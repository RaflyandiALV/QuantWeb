import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType } from 'lightweight-charts';
import { Play, TrendingUp, Activity, Zap, Info, Search, Globe, Coins, Shield, MousePointerClick, AlertTriangle, Settings, Clock, CheckCircle } from 'lucide-react';
import Watchlist from '../../components/Watchlist'; 

const BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const SECTORS_LIST = [
    { id: "BIG_CAP", name: "Big Cap & L1" },
    { id: "AI_COINS", name: "AI Narratives" },
    { id: "MEME_COINS", name: "Meme Coins" },
    { id: "DEX_DEFI", name: "DeFi Bluechips" },
    { id: "US_TECH", name: "US Tech Stocks" }
];

const InfoTooltip = ({ text }) => (
    <div className="group relative flex items-center ml-1">
        <Info size={12} className="text-gray-500 hover:text-cyan-400 cursor-help transition" />
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block w-48 bg-gray-800 text-xs text-gray-200 p-2 rounded shadow-xl border border-gray-700 z-50 text-center pointer-events-none">
            {text}
            <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800"></div>
        </div>
    </div>
);

const DashboardPage = () => {
    // --- REFS ---
    const priceChartContainer = useRef(null);
    const equityChartContainer = useRef(null);
    const priceChartInstance = useRef(null);
    const equityChartInstance = useRef(null);
    
    const priceSeries = useRef(null);
    const equitySeries = useRef(null);
    const lineSeries1 = useRef(null);
    const lineSeries2 = useRef(null);
    const lineSeries3 = useRef(null);

    // --- STATE ---
    const [formData, setFormData] = useState({
        symbol: "BTC-USD", strategy: "MULTITIMEFRAME", capital: 10000, 
        timeframe: "1d", period: "1y", startDate: "", endDate: ""
    });
    const [metrics, setMetrics] = useState(null);
    const [loading, setLoading] = useState(false);
    const [compLoading, setCompLoading] = useState(false);
    const [scanResults, setScanResults] = useState({});
    const [eliteSignals, setEliteSignals] = useState([]);
    const [isScanning, setIsScanning] = useState(false);
    const [comparisonData, setComparisonData] = useState(null);

    // --- SETUP CHART ---
    useEffect(() => {
        if (!priceChartContainer.current || !equityChartContainer.current) return;
        
        // 1. Chart Harga
        const chartPrice = createChart(priceChartContainer.current, {
            layout: { background: { type: ColorType.Solid, color: '#000000' }, textColor: '#22d3ee' },
            grid: { vertLines: { color: '#1e293b' }, horzLines: { color: '#1e293b' } },
            width: priceChartContainer.current.clientWidth, height: 400,
            timeScale: { borderColor: '#334155', timeVisible: true }, 
            rightPriceScale: { borderColor: '#334155', autoScale: true },
        });
        priceChartInstance.current = chartPrice;

        priceSeries.current = chartPrice.addCandlestickSeries({ upColor: '#00ff41', downColor: '#ff0055', borderVisible: false, wickUpColor: '#00ff41', wickDownColor: '#ff0055' });
        lineSeries1.current = chartPrice.addLineSeries({ color: '#facc15', lineWidth: 2, visible: false });
        lineSeries2.current = chartPrice.addLineSeries({ color: '#3b82f6', lineWidth: 2, visible: false });
        lineSeries3.current = chartPrice.addLineSeries({ color: '#ffffff', lineWidth: 2, visible: false });

        // 2. Chart Equity
        const chartEquity = createChart(equityChartContainer.current, {
            layout: { background: { type: ColorType.Solid, color: '#020617' }, textColor: '#64748b' },
            grid: { vertLines: { visible: false }, horzLines: { color: '#1e293b' } },
            width: equityChartContainer.current.clientWidth, height: 150,
            timeScale: { borderColor: '#334155', timeVisible: true },
            rightPriceScale: { autoScale: true },
        });
        equityChartInstance.current = chartEquity;
        equitySeries.current = chartEquity.addAreaSeries({ lineColor: '#3b82f6', topColor: 'rgba(59, 130, 246, 0.4)', bottomColor: 'rgba(59, 130, 246, 0.0)' });

        // --- SYNC LOGIC ---
        const priceTimeScale = chartPrice.timeScale();
        const equityTimeScale = chartEquity.timeScale();

        priceTimeScale.subscribeVisibleLogicalRangeChange(range => { if(range) equityTimeScale.setVisibleLogicalRange(range); });
        equityTimeScale.subscribeVisibleLogicalRangeChange(range => { if(range) priceTimeScale.setVisibleLogicalRange(range); });

        const resizeObserver = new ResizeObserver(entries => {
            for (let entry of entries) {
                if (entry.target === priceChartContainer.current) chartPrice.applyOptions({ width: entry.contentRect.width });
                if (entry.target === equityChartContainer.current) chartEquity.applyOptions({ width: entry.contentRect.width });
            }
        });
        resizeObserver.observe(priceChartContainer.current);
        resizeObserver.observe(equityChartContainer.current);

        handleRunBacktest();

        return () => { resizeObserver.disconnect(); chartPrice.remove(); chartEquity.remove(); };
    }, []);

    const handleRunBacktest = async () => {
        setLoading(true);
        try {
            const payload = { ...formData };
            if (formData.period === 'custom') { payload.start_date = formData.startDate; payload.end_date = formData.endDate; }

            const res = await fetch(`${BASE_URL}/api/run-backtest`, {
                method: 'POST', 
                headers: { 'Content-Type': 'application/json' }, 
                body: JSON.stringify(payload)
            });
            
            if (!res.ok) {
                const err = await res.json();
                if(res.status === 404) { alert(`⚠️ ${err.detail}`); setLoading(false); return; }
                throw new Error(err.detail || "Error");
            }

            const data = await res.json();
            
            priceSeries.current.setData(data.chart_data);
            equitySeries.current.setData(data.equity_curve);
            if (data.markers) priceSeries.current.setMarkers(data.markers.sort((a,b) => a.time - b.time));
            
            priceChartInstance.current.timeScale().fitContent();
            equityChartInstance.current.timeScale().fitContent();

            lineSeries1.current.applyOptions({ visible: false });
            lineSeries2.current.applyOptions({ visible: false });
            lineSeries3.current.applyOptions({ visible: false });

            if (formData.strategy === "MOMENTUM") {
                lineSeries1.current.applyOptions({ visible: true, color: '#facc15' }); lineSeries1.current.setData(data.indicators.line1);
                lineSeries2.current.applyOptions({ visible: true, color: '#3b82f6' }); lineSeries2.current.setData(data.indicators.line2);
            } else if (formData.strategy === "MULTITIMEFRAME") {
                lineSeries3.current.applyOptions({ visible: true }); lineSeries3.current.setData(data.indicators.line3);
            } else if (formData.strategy === "GRID") {
                lineSeries1.current.applyOptions({ visible: true, color: '#ff0055' }); lineSeries1.current.setData(data.indicators.line1);
                lineSeries2.current.applyOptions({ visible: true, color: '#00ff41' }); lineSeries2.current.setData(data.indicators.line2);
                lineSeries3.current.applyOptions({ visible: true, color: '#555', lineWidth: 1, lineStyle: 2 }); lineSeries3.current.setData(data.indicators.line3);
            } else {
                lineSeries1.current.applyOptions({ visible: true, color: '#ff0055' }); lineSeries1.current.setData(data.indicators.line1);
                lineSeries2.current.applyOptions({ visible: true, color: '#00ff41' }); lineSeries2.current.setData(data.indicators.line2);
            }

            setMetrics(data.metrics);
            handleCompareStrategies();

            // --- PERBAIKAN GRAFIK: PAKSA FIT CONTENT SETELAH DATA MASUK ---
            requestAnimationFrame(() => {
                priceChartInstance.current.timeScale().fitContent();
            });

        } catch (err) { alert(`Error: ${err.message}`); } finally { setLoading(false); }
    };

    const handleCompareStrategies = async () => {
        setCompLoading(true);
        setComparisonData(null);
        try {
            const payload = { ...formData };
            if (formData.period === 'custom') { payload.start_date = formData.startDate; payload.end_date = formData.endDate; }
            const res = await fetch(`${BASE_URL}/api/compare-strategies`, {
               method: 'POST', 
               headers: { 'Content-Type': 'application/json' }, 
               body: JSON.stringify(payload)
            });
            if(res.ok) { const data = await res.json(); setComparisonData(data.comparison); }
        } catch (err) { console.error(err); }
        setCompLoading(false);
    };

    const handleScanMarket = async () => {
        setIsScanning(true);
        setScanResults({});
        setEliteSignals([]); 
        let allElites = [];

        for (const sector of SECTORS_LIST) {
            try {
                const payload = { sector: sector.id, timeframe: "1d", period: "1y", capital: formData.capital };
                const res = await fetch(`${BASE_URL}/api/scan-market`, {
                    method: 'POST', 
                    headers: { 'Content-Type': 'application/json' }, 
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    const data = await res.json();
                    setScanResults(prev => ({ ...prev, [sector.name]: data.results }));
                    if(data.elite_signals) allElites = [...allElites, ...data.elite_signals];
                }
            } catch (err) { console.error(`Gagal scan ${sector.name}`, err); }
        }
        allElites.sort((a,b) => b.win_rate - a.win_rate || b.trades - a.trades);
        setEliteSignals(allElites.slice(0, 10)); // LIMIT MAX 10
        setIsScanning(false);
    };

    const handleChange = (e) => setFormData({ ...formData, [e.target.name]: e.target.value });
    
    const handleWatchlistSelect = (symbol) => {
        setFormData(prev => ({ ...prev, symbol: symbol }));
        window.scrollTo({ top: 0, behavior: 'smooth' });
        setTimeout(() => document.getElementById('run-btn').click(), 100);
    };

    return (
        <div className="min-h-screen bg-black text-cyan-50 font-sans p-4 md:p-8 selection:bg-cyan-500 selection:text-black pb-20">
            {/* HEADER */}
            <div className="flex flex-col xl:flex-row justify-between items-center mb-8 border-b border-cyan-900/50 pb-6 gap-6 relative">
                <div className="absolute top-0 left-1/4 w-96 h-96 bg-purple-600/20 rounded-full blur-[100px] -z-10"></div>
                <div>
                    <h1 className="text-3xl md:text-4xl font-black italic tracking-tighter">
                        <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-600 drop-shadow-[0_0_10px_rgba(34,211,238,0.5)]">QUANTITATIVE TRADE</span> 
                        <span className="text-white drop-shadow-[0_0_15px_rgba(255,255,255,0.8)]"> PROTOCOL</span>
                    </h1>
                    <p className="text-[10px] md:text-xs text-gray-400 font-mono tracking-[0.2em] mt-1 uppercase opacity-80">
                        OWNERS: <span className="text-cyan-300">RAFLYANDI ALVIANSYAH</span> - <span className="text-purple-300">BRIAN EVAN KRISTANTO</span> - <span className="text-yellow-300">WELAN ALE ZENI</span>
                    </p>
                </div>
                <div className="flex flex-col gap-2 items-center">
                    <div className="flex flex-wrap gap-3 bg-gray-900/40 backdrop-blur-md p-4 rounded-xl border border-cyan-500/30 shadow-[0_0_20px_rgba(8,145,178,0.2)] justify-center items-end">
                        <InputGroup label="ASSET" icon="💎"><input name="symbol" value={formData.symbol} onChange={handleChange} className="neon-input w-24 text-center" /></InputGroup>
                        <InputGroup label="STRATEGY" icon="⚡"><select name="strategy" value={formData.strategy} onChange={handleChange} className="neon-input w-36 cursor-pointer"><option value="MOMENTUM">Momentum</option><option value="MEAN_REVERSAL">Mean Reversal</option><option value="GRID">Grid Trading</option><option value="MULTITIMEFRAME">Multi TF</option></select></InputGroup>
                        <InputGroup label="TIMEFRAME" icon="⏱️"><select name="timeframe" value={formData.timeframe} onChange={handleChange} className="neon-input w-24 cursor-pointer"><option value="1h">1 H</option><option value="4h">4 H</option><option value="1d">1 D</option><option value="1wk">1 W</option><option value="1mo">1 M</option></select></InputGroup>
                        <InputGroup label="RANGE" icon="📅"><select name="period" value={formData.period} onChange={handleChange} className="neon-input w-24 cursor-pointer"><option value="1mo">1 M</option><option value="6mo">6 M</option><option value="1y">1 Y</option><option value="2y">2 Y</option><option value="5y">5 Y</option><option value="max">Max</option><option value="custom">Custom</option></select></InputGroup>
                        <InputGroup label="CAPITAL" icon="💰"><input type="number" name="capital" value={formData.capital} onChange={handleChange} className="neon-input w-24" /></InputGroup>
                        <button id="run-btn" onClick={handleRunBacktest} disabled={loading} className="mt-auto h-[42px] bg-gradient-to-r from-cyan-600 to-blue-700 hover:from-cyan-500 hover:to-blue-600 text-white px-6 rounded-lg font-bold flex items-center gap-2 transition-all shadow-[0_0_15px_rgba(8,145,178,0.5)] disabled:opacity-50">
                            {loading ? <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div> : <Play size={18} fill="currentColor"/>} RUN
                        </button>
                    </div>
                </div>
            </div>

            {/* CHART & STATS AREA */}
            <div className="flex flex-col lg:flex-row gap-6 mb-12">
                <div className="lg:w-3/4 flex flex-col gap-4 min-h-[600px]">
                    <div className="flex-1 bg-gray-900/30 backdrop-blur-sm border border-cyan-900/50 rounded-2xl p-1 shadow-2xl relative flex flex-col">
                        <div className="absolute top-3 left-4 z-10 flex gap-2 pointer-events-none"><Badge text={`${formData.symbol} • ${formData.timeframe}`} color="bg-cyan-900/80 text-cyan-300" /><Badge text={formData.strategy} color="bg-purple-900/80 text-purple-300" /></div>
                        <div className="flex-1 w-full relative" ref={priceChartContainer}></div>
                    </div>
                    <div className="h-48 bg-gray-900/30 backdrop-blur-sm border border-cyan-900/50 rounded-2xl p-1 relative flex flex-col">
                         <div className="absolute top-2 left-4 z-10 text-[10px] text-blue-400 font-bold tracking-widest uppercase flex items-center gap-2"><TrendingUp size={12}/> Portfolio Growth</div>
                        <div className="flex-1 w-full relative" ref={equityChartContainer}></div>
                    </div>
                </div>
                
                <div className="lg:w-1/4 flex flex-col gap-6">
                    <div className="bg-gray-900/50 backdrop-blur-md border border-cyan-500/30 rounded-2xl p-6 shadow-[0_0_30px_rgba(0,0,0,0.5)]">
                        <h3 className="text-cyan-400 text-xs font-bold uppercase tracking-[0.2em] mb-4 flex items-center gap-2"><Zap size={14}/> Net Performance</h3>
                        <div className={`text-4xl font-black font-mono mb-2 ${metrics?.net_profit >= 0 ? 'text-[#00ff41]' : 'text-[#ff0055]'}`}>
                            ${metrics?.net_profit?.toLocaleString() || "0"}
                        </div>
                        <div className="flex justify-between items-end text-xs text-gray-400 mt-2"><span>Final Equity</span><span className="text-white font-mono font-bold">${metrics?.final_balance?.toLocaleString()}</span></div>
                    </div>
                    
                    <div className="bg-gray-900/30 border border-gray-800 rounded-2xl p-6">
                        <h3 className="text-gray-500 text-xs font-bold uppercase tracking-[0.2em] mb-4 flex items-center gap-2"><Shield size={14}/> Risk Analysis</h3>
                        <div className="space-y-3 font-mono text-sm">
                            <StatRow label="Max Drawdown" value={`${metrics?.max_drawdown || 0}%`} color="text-red-400" />
                            <div className="flex justify-between items-center text-sm border-b border-gray-800 pb-2 hover:bg-white/5 px-2 rounded transition">
                                <span className="text-gray-500 text-xs uppercase flex items-center">Sharpe Ratio <InfoTooltip text="Reward per unit of risk."/></span>
                                <span className="font-bold text-yellow-400">{metrics?.sharpe_ratio || 0}</span>
                            </div>
                            <div className="flex justify-between items-center text-sm border-b border-gray-800 pb-2 hover:bg-white/5 px-2 rounded transition">
                                <span className="text-gray-500 text-xs uppercase flex items-center">Calmar Ratio <InfoTooltip text="Return / Max Drawdown."/></span>
                                <span className="font-bold text-blue-400">{metrics?.calmar_ratio || 0}</span>
                            </div>
                        </div>
                    </div>

                    <div className="bg-gray-900/30 border border-gray-800 rounded-2xl p-6 flex-1">
                        <h3 className="text-gray-500 text-xs font-bold uppercase tracking-[0.2em] mb-4 flex items-center gap-2"><Activity size={14} /> Trade Stats</h3>
                        <div className="space-y-3 font-mono">
                            <StatRow label="Win Rate" value={`${metrics?.win_rate || 0}%`} color="text-yellow-400" />
                            <StatRow label="Trades" value={metrics?.total_trades || 0} />
                            <StatRow label="Starting Capital" value={`$${metrics?.initial_balance?.toLocaleString() || 0}`} />
                        </div>
                    </div>
                </div>
            </div>

            {/* STRATEGY COMPARISON */}
            <div className="mb-12">
                <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">STRATEGY MATRIX <span className="text-sm text-gray-500 font-normal ml-2">Which logic fits {formData.symbol} best?</span></h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                    {compLoading ? (
                        <div className="col-span-5 text-center text-cyan-500 py-10 animate-pulse bg-gray-900/30 rounded-xl">Analyzing Strategies...</div>
                    ) : (comparisonData ? comparisonData.map((s, idx) => (
                        <div key={idx} className={`p-4 rounded-xl border backdrop-blur-sm transition hover:scale-105 ${idx === 0 ? 'border-yellow-500 border-2 bg-yellow-900/20' : (s.net_profit > 0 ? 'border-green-500/30 bg-green-900/10' : 'border-red-500/30 bg-red-900/10')}`}>
                            <div className={`text-xs font-bold uppercase tracking-widest mb-2 ${idx === 0 ? 'text-yellow-400' : 'text-gray-400'}`}>{s.strategy} {idx === 0 && "(BEST)"}</div>
                            <div className={`text-2xl font-black font-mono mb-2 ${s.net_profit > 0 ? 'text-green-400' : 'text-red-400'}`}>${s.net_profit.toLocaleString()}</div>
                            {!s.is_hold && <div className="flex justify-between text-xs text-gray-500"><span>Win: {s.win_rate}%</span><span>Sharpe: {s.sharpe}</span></div>}
                        </div>
                    )) : <div className="col-span-5 text-center text-gray-600">Run backtest to see matrix.</div>)}
                </div>
            </div>

            {/* GLOBAL SCANNER */}
            <div className="bg-gray-900/20 border border-cyan-900/30 rounded-3xl p-8 relative overflow-hidden mb-12">
                <div className="flex flex-col md:flex-row justify-between items-center mb-8 gap-4 z-10 relative">
                    <div>
                        <h2 className="text-2xl font-bold text-white flex items-center gap-2"><Globe className="text-cyan-500"/> GLOBAL MARKET SCANNER</h2>
                        <p className="text-gray-400 text-sm mt-1">Multi-timeframe scanning to find "Golden Setups" (1H {'>'} 4H {'>'} 1D).</p>
                    </div>
                    <button onClick={handleScanMarket} disabled={isScanning} className="bg-cyan-600 hover:bg-cyan-500 text-white px-8 py-3 rounded-lg font-bold flex items-center gap-2 transition shadow-[0_0_20px_cyan]">
                        {isScanning ? <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div> : <Search size={20}/>} SCAN ALL MARKETS
                    </button>
                </div>

                {/* ELITE SIGNALS (REVISED UI) */}
                {eliteSignals.length > 0 && (
                    <div className="mb-8 animate-in slide-in-from-top-4 fade-in duration-500">
                        <h3 className="text-lg font-bold text-yellow-400 mb-4 flex items-center gap-2"><AlertTriangle size={18} /> ELITE SIGNALS (WR {'>'} 60%, Max 10)</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                            {eliteSignals.map((sig, idx) => (
                                <div key={idx} className="bg-yellow-900/10 border border-yellow-500/50 p-4 rounded-xl relative overflow-hidden hover:bg-yellow-900/20 transition cursor-pointer" onClick={() => {
                                     setFormData({ symbol: sig.symbol, strategy: sig.strategy, timeframe: sig.timeframe, period: sig.period, capital: formData.capital, startDate: "", endDate: "" });
                                     window.scrollTo({ top: 0, behavior: 'smooth' });
                                     setTimeout(() => document.getElementById('run-btn').click(), 100);
                                }}>
                                    <div className="absolute top-0 right-0 bg-yellow-500 text-black text-[9px] font-bold px-2 py-0.5 rounded-bl">RANK #{idx+1}</div>
                                    <div className="flex justify-between items-center mb-2">
                                        <div className="font-bold text-white">{sig.symbol}</div>
                                        <Badge text={sig.timeframe} color="bg-gray-700 text-gray-200"/>
                                    </div>
                                    
                                    {/* STRATEGY DISPLAY (RESTORED) */}
                                    <div className="text-[10px] text-cyan-300 font-bold mb-2 flex items-center gap-1">
                                        <Settings size={10}/> {sig.strategy}
                                    </div>

                                    <div className="flex justify-between text-xs text-gray-400 mb-2">
                                        <span>WR: <span className="text-green-400 font-bold">{sig.win_rate}%</span></span>
                                        <span>Trades: <span className="text-white">{sig.trades}</span></span>
                                    </div>

                                    <div className="bg-black/40 p-2 rounded border border-gray-800 text-[10px] space-y-1 font-mono">
                                        <div className="flex justify-between"><span className="text-blue-400">ENTRY</span> <span>${sig.signal_data.price.toFixed(2)}</span></div>
                                        <div className="flex justify-between"><span className="text-green-400">TP</span> <span>${sig.signal_data.setup_long.tp.toFixed(2)}</span></div>
                                        <div className="flex justify-between"><span className="text-red-400">SL</span> <span>${sig.signal_data.setup_long.sl.toFixed(2)}</span></div>
                                        <div className="flex justify-between border-t border-gray-700 pt-1 mt-1"><span className="text-yellow-400">R:R</span> <span>{sig.rr_ratio}</span></div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* SCAN RESULTS */}
                <div className="space-y-8">
                    {SECTORS_LIST.map((sector) => (
                        <div key={sector.id} className="border-t border-gray-800 pt-6">
                            <h3 className="text-lg font-bold text-purple-400 mb-4 flex items-center gap-2"><Coins size={16}/> {sector.name}</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                                {scanResults[sector.name] ? scanResults[sector.name].map((coin, idx) => (
                                    <div key={idx} className="bg-black/40 border border-gray-800 p-4 rounded-xl hover:border-cyan-500/50 transition group cursor-pointer" onClick={() => {
                                        setFormData(prev => ({...prev, symbol: coin.symbol, timeframe: coin.timeframe, strategy: coin.strategy, period: coin.period }));
                                        window.scrollTo({ top: 0, behavior: 'smooth' });
                                        setTimeout(() => document.getElementById('run-btn').click(), 100);
                                    }}>
                                        <div className="flex justify-between items-start mb-2">
                                            <div className="flex items-center gap-2">
                                                <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-[10px] ${coin.profit > 0 ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'}`}>{coin.symbol.substring(0,3)}</div>
                                                <div>
                                                    <div className="font-bold text-sm text-white">{coin.symbol}</div>
                                                    <div className="text-[9px] text-gray-500">{coin.timeframe} • {coin.period}</div>
                                                </div>
                                            </div>
                                            <div className={`text-sm font-mono font-bold ${coin.profit > 0 ? 'text-green-400' : 'text-red-400'}`}>{coin.profit > 0 ? '+' : ''}{coin.profit.toLocaleString()}</div>
                                        </div>
                                        <div className="flex justify-between items-end mt-2">
                                            <div className="text-[10px] text-gray-500 uppercase tracking-wider">{coin.strategy}</div>
                                            {coin.profit > 0 && <Shield size={12} className="text-green-500"/>}
                                        </div>
                                    </div>
                                )) : (isScanning ? <div className="col-span-4 text-xs text-gray-600 animate-pulse">Scanning...</div> : <div className="col-span-4 text-xs text-gray-700">Waiting to scan...</div>)}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* --- PERSONAL WATCHLIST --- */}
            <div className="bg-gray-900/40 backdrop-blur-md border border-cyan-500/30 rounded-3xl p-8 shadow-[0_0_20px_rgba(8,145,178,0.1)]">
                 <Watchlist onSelectAsset={handleWatchlistSelect} />
            </div>

        </div>
    );
};

const InputGroup = ({ label, icon, children }) => (<div className="flex flex-col"><label className="text-[9px] text-cyan-500/80 font-bold uppercase ml-1 mb-1 tracking-wider flex items-center gap-1">{icon} {label}</label>{children}</div>);
const Badge = ({ text, color }) => (<span className={`px-2 py-0.5 rounded text-[10px] font-mono border border-white/10 shadow-lg backdrop-blur-md ${color}`}>{text}</span>);
const StatRow = ({ label, value, color = "text-gray-300" }) => (<div className="flex justify-between items-center text-sm border-b border-gray-800 pb-2 last:border-0 hover:bg-white/5 px-2 rounded transition"><span className="text-gray-500 text-xs uppercase">{label}</span><span className={`font-bold ${color}`}>{value}</span></div>);

export default DashboardPage;