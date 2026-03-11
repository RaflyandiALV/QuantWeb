import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType } from 'lightweight-charts';
import {
    Play, TrendingUp, Activity, Zap, Info, Search, Globe, Coins,
    Shield, AlertTriangle, Settings, BarChart2, Layers, RefreshCw, PieChart, Trophy, Gem,
    ArrowUpRight, ArrowDownRight
} from 'lucide-react';

// Import Components
import MarketAnalytics from '../../components/MarketAnalytics';
import Watchlist from '../../components/Watchlist';
import BotTracker from '../../components/BotTracker';
import PortfolioPage from '../../components/PortfolioPage';
import RiskDashboard from '../../components/RiskDashboard';
import MonteCarloChart from '../../components/MonteCarloChart';
import FundDashboard from '../../components/FundDashboard';
import EliteSignals from '../../components/EliteSignals';
import MacroDashboard from '../../components/MacroDashboard';
import Sidebar from '../../components/Sidebar';
import AnomalyDashboard from '../../components/AnomalyDashboard';
import GlobalMarketDashboard from '../../components/GlobalMarketDashboard';
import AIDashboard from '../../components/AIDashboard';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

// Daftar Sektor Lengkap (Sesuai Backend)
const SECTORS_LIST = [
    { id: "BIG_CAP", name: "Big Cap & L1" },
    { id: "AI_COINS", name: "AI Narratives" },
    { id: "MEME_COINS", name: "Meme Coins" },
    { id: "DEFI", name: "DeFi Bluechips" },
    { id: "LAYER_2", name: "Layer 2 & ZK" },
    { id: "GAMING", name: "Gaming & Metaverse" },
    { id: "RWA", name: "Real World Assets" },
    { id: "INFRA", name: "Infrastructure" },
    { id: "PRIVACY_ZK", name: "Privacy & ZK" },
    { id: "NEW_LISTINGS", name: "Hot & New" },
    { id: "CEX_TOKENS", name: "Exchange Tokens" },
    { id: "YIELD_STAKING", name: "Yield & Staking" }
];

// --- TOOLTIP COMPONENT ---
const InfoTooltip = ({ text }) => (
    <div className="group relative flex items-center ml-1">
        <Info size={12} className="text-gray-500 hover:text-cyan-400 cursor-help transition" />
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block w-56 bg-gray-800 text-xs text-gray-200 p-3 rounded shadow-xl border border-gray-700 z-50 text-center pointer-events-none leading-relaxed">
            {text}
            <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800"></div>
        </div>
    </div>
);

const DashboardPage = () => {
    // --- REFS FOR CHARTS ---
    const priceChartContainer = useRef(null);
    const equityChartContainer = useRef(null);
    const priceChartInstance = useRef(null);
    const equityChartInstance = useRef(null);

    // --- REFS FOR SERIES ---
    const priceSeries = useRef(null);
    const equitySeries = useRef(null);
    const lineSeries1 = useRef(null);
    const lineSeries2 = useRef(null);
    const lineSeries3 = useRef(null);

    // --- MAIN STATE ---
    const [formData, setFormData] = useState({
        symbol: "BTC-USD",
        strategy: "MULTITIMEFRAME",
        capital: 10000,
        timeframe: "1d",
        period: "1y",
        startDate: "",
        endDate: "",
        direction: "LONG" // Added direction
    });

    const [metrics, setMetrics] = useState(null);
    const [loading, setLoading] = useState(false);

    // --- SCANNER STATE ---
    const [scanResults, setScanResults] = useState({});
    const [eliteSignals, setEliteSignals] = useState([]);
    const [isScanning, setIsScanning] = useState(false);
    const [scanProgress, setScanProgress] = useState(0); // 0 to 100 Progress Bar

    // --- ANALYTICS STATE (NEW) ---
    const [viewMode, setViewMode] = useState('BACKTEST'); // Driven by sidebar
    const [analyticsData, setAnalyticsData] = useState(null);
    const [isAnalyticsLoading, setIsAnalyticsLoading] = useState(false);
    const [selectedAnalyticsSector, setSelectedAnalyticsSector] = useState("ALL_SECTORS");

    // --- STRATEGY COMPARISON STATE ---
    const [compLoading, setCompLoading] = useState(false);
    const [comparisonData, setComparisonData] = useState(null);

    // --- PnL SEGMENTATION STATE (Objective 3) ---
    const [pnlFilter, setPnlFilter] = useState('COMBINED'); // 'COMBINED' | 'LONG' | 'SHORT'
    const [dualData, setDualData] = useState(null);
    const [dualLoading, setDualLoading] = useState(false);
    const [pnlError, setPnlError] = useState(null);

    // =================================================================================
    // 1. CHART INITIALIZATION (TradingView Lightweight Charts)
    // =================================================================================
    useEffect(() => {
        if (!priceChartContainer.current || !equityChartContainer.current) return;

        // A. Setup Chart Harga
        const chartPrice = createChart(priceChartContainer.current, {
            layout: { background: { type: ColorType.Solid, color: '#000000' }, textColor: '#22d3ee' },
            grid: { vertLines: { color: '#1e293b' }, horzLines: { color: '#1e293b' } },
            width: priceChartContainer.current.clientWidth, height: 400,
            timeScale: { borderColor: '#334155', timeVisible: true },
            rightPriceScale: { borderColor: '#334155', autoScale: true },
        });
        priceChartInstance.current = chartPrice;

        priceSeries.current = chartPrice.addCandlestickSeries({
            upColor: '#00ff41', downColor: '#ff0055', borderVisible: false, wickUpColor: '#00ff41', wickDownColor: '#ff0055'
        });

        // Indikator Lines (MA, Bollinger, etc)
        lineSeries1.current = chartPrice.addLineSeries({ color: '#facc15', lineWidth: 2, visible: false });
        lineSeries2.current = chartPrice.addLineSeries({ color: '#3b82f6', lineWidth: 2, visible: false });
        lineSeries3.current = chartPrice.addLineSeries({ color: '#ffffff', lineWidth: 2, visible: false });

        // B. Setup Chart Equity
        const chartEquity = createChart(equityChartContainer.current, {
            layout: { background: { type: ColorType.Solid, color: '#020617' }, textColor: '#64748b' },
            grid: { vertLines: { visible: false }, horzLines: { color: '#1e293b' } },
            width: equityChartContainer.current.clientWidth, height: 150,
            timeScale: { borderColor: '#334155', timeVisible: true },
            rightPriceScale: { autoScale: true },
        });
        equityChartInstance.current = chartEquity;
        equitySeries.current = chartEquity.addAreaSeries({
            lineColor: '#3b82f6', topColor: 'rgba(59, 130, 246, 0.4)', bottomColor: 'rgba(59, 130, 246, 0.0)'
        });

        // C. Sync Logic (Agar kedua chart bergerak bersamaan)
        const priceTimeScale = chartPrice.timeScale();
        const equityTimeScale = chartEquity.timeScale();

        priceTimeScale.subscribeVisibleLogicalRangeChange(range => { if (range) equityTimeScale.setVisibleLogicalRange(range); });
        equityTimeScale.subscribeVisibleLogicalRangeChange(range => { if (range) priceTimeScale.setVisibleLogicalRange(range); });

        // D. Responsive Resize
        const resizeObserver = new ResizeObserver(entries => {
            for (let entry of entries) {
                if (entry.target === priceChartContainer.current) chartPrice.applyOptions({ width: entry.contentRect.width });
                if (entry.target === equityChartContainer.current) chartEquity.applyOptions({ width: entry.contentRect.width });
            }
        });
        resizeObserver.observe(priceChartContainer.current);
        resizeObserver.observe(equityChartContainer.current);

        // Run Initial Backtest
        handleRunBacktest();

        return () => {
            resizeObserver.disconnect();
            chartPrice.remove();
            chartEquity.remove();
        };
    }, []);

    // Load cached scan data on startup (instant UI)
    useEffect(() => {
        fetch(`${BASE_URL}/api/last-scan`)
            .then(res => res.json())
            .then(data => {
                if (data.cached && data.sectors && Object.keys(data.sectors).length > 0) {
                    setScanResults(data.sectors);
                    if (data.elite_signals?.length > 0) {
                        setEliteSignals(data.elite_signals);
                    }
                    console.log(`[CACHE] Loaded ${data.total_results} results from last scan (${data.last_scan_time})`);
                }
            })
            .catch(() => console.log('[CACHE] No cached scan data available'));
    }, []);

    // =================================================================================
    // 2. BACKEND API CALLS
    // =================================================================================

    // --- RUN SINGLE BACKTEST ---
    // --- AUTO-FETCH DUAL BACKTEST (PnL Segmentation) ---
    const fetchDualBacktest = async (payloadOverride) => {
        setDualLoading(true);
        setPnlError(null);
        try {
            const payload = payloadOverride || { ...formData };
            if (payload.period === 'custom') {
                payload.start_date = payload.startDate || formData.startDate;
                payload.end_date = payload.endDate || formData.endDate;
            }
            const res = await fetch(`${BASE_URL}/api/run-dual-backtest`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                setDualData(await res.json());
            } else {
                setPnlError(`Dual backtest API error: ${res.status}`);
            }
        } catch (error) {
            console.error('Dual backtest error:', error);
            setPnlError(error.message || 'Dual backtest failed');
        } finally {
            setDualLoading(false);
        }
    };

    // --- RUN SINGLE BACKTEST ---
    const handleRunBacktest = async () => {
        setLoading(true);
        setDualData(null); // Reset stale PnL segmentation data
        setPnlError(null);
        try {
            const payload = { ...formData };
            if (formData.period === 'custom') {
                payload.start_date = formData.startDate;
                payload.end_date = formData.endDate;
            }

            const res = await fetch(`${BASE_URL}/api/run-backtest`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) {
                const err = await res.json();
                if (res.status === 404) { alert(`⚠️ ${err.detail}`); setLoading(false); return; }
                throw new Error(err.detail || "Error");
            }

            const data = await res.json();

            // Update Chart Data
            if (priceSeries.current) priceSeries.current.setData(data.chart_data);
            if (equitySeries.current) equitySeries.current.setData(data.equity_curve);
            if (data.markers && priceSeries.current) priceSeries.current.setMarkers(data.markers.sort((a, b) => a.time - b.time));

            // Reset Zoom
            if (priceChartInstance.current) priceChartInstance.current.timeScale().fitContent();
            if (equityChartInstance.current) equityChartInstance.current.timeScale().fitContent();

            // Setup Indicators Visibility (Updated for 8 Strategies)
            const strat = formData.strategy;
            // Reset
            lineSeries1.current.applyOptions({ visible: false });
            lineSeries2.current.applyOptions({ visible: false });
            lineSeries3.current.applyOptions({ visible: false });

            if (strat.includes("MOMENTUM") || strat === "MIX_STRATEGY") {
                lineSeries1.current.applyOptions({ visible: true, color: '#facc15' }); lineSeries1.current.setData(data.indicators.line1);
                lineSeries2.current.applyOptions({ visible: true, color: '#3b82f6' }); lineSeries2.current.setData(data.indicators.line2);
            } else if (strat.includes("MULTITIMEFRAME")) {
                lineSeries3.current.applyOptions({ visible: true }); lineSeries3.current.setData(data.indicators.line3);
            } else {
                // Mean Reversal & Grid
                lineSeries1.current.applyOptions({ visible: true, color: '#ff0055' }); lineSeries1.current.setData(data.indicators.line1);
                lineSeries2.current.applyOptions({ visible: true, color: '#00ff41' }); lineSeries2.current.setData(data.indicators.line2);
                if (strat.includes("GRID")) {
                    lineSeries3.current.applyOptions({ visible: true, color: '#555', lineWidth: 1, lineStyle: 2 }); lineSeries3.current.setData(data.indicators.line3);
                }
            }

            setMetrics(data.metrics);
            handleCompareStrategies(); // Auto compare after run

            // Auto-fetch PnL segmentation data in background
            fetchDualBacktest(payload);

        } catch (err) {
            alert(`Error: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    // --- COMPARE STRATEGIES (MATRIX) ---
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
            if (res.ok) { const data = await res.json(); setComparisonData(data.comparison); }
        } catch (err) { console.error(err); }
        setCompLoading(false);
    };

    // --- GEM SELECTION HANDLER ---
    const handleGemSelect = (gem) => {
        // Parse Strategy and Direction from gem.best_strategy
        // Format: "MOMENTUM (SHORT)" or "GRID (LONG)"
        let strategy = "MULTITIMEFRAME";
        let direction = "LONG";

        if (gem.best_strategy) {
            const parts = gem.best_strategy.split(' ');
            strategy = parts[0];
            if (gem.best_strategy.includes("(SHORT)")) direction = "SHORT";
        }

        setFormData(prev => ({
            ...prev,
            symbol: gem.symbol,
            strategy: strategy,
            direction: direction,
            timeframe: "1h", // Scanner uses 1h usually
            period: "1y"
        }));

        // Optional: Auto run backtest or scroll to top?
        // Let's scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    // --- FETCH MARKET ANALYTICS (NEW) ---
    const fetchAnalytics = async (sectorName) => {
        setIsAnalyticsLoading(true);
        try {
            const response = await fetch(`${BASE_URL}/api/market-analytics`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    sector: sectorName,
                    timeframe: "1d",
                    period: "1y", // Analisis 1 tahun untuk volatility/return
                    capital: 1000
                }),
            });
            const data = await response.json();
            setAnalyticsData(data);
            setSelectedAnalyticsSector(sectorName);
        } catch (error) {
            console.error("Failed fetch analytics", error);
        } finally {
            setIsAnalyticsLoading(false);
        }
    };

    // --- SMART SCANNER — PARALLEL BATCH (UPDATED) ---
    const handleScanMarket = async (isForceReset = false) => {
        setIsScanning(true);
        setScanProgress(0);
        setScanResults({});
        setEliteSignals([]);
        setViewMode('SCANNER');

        try {
            // Use batch scan-all endpoint — processes all sectors in parallel
            setScanProgress(10); // Show initial progress
            const res = await fetch(`${BASE_URL}/api/scan-all`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    sector: 'ALL',
                    timeframe: '1d',
                    period: '1y',
                    capital: formData.capital,
                    force_reload: isForceReset
                })
            });

            if (res.ok) {
                const data = await res.json();
                setScanResults(data.sectors || {});

                // Sort and set elite signals
                const allElites = data.elite_signals || [];
                allElites.sort((a, b) => b.win_rate - a.win_rate || b.trades - a.trades);
                setEliteSignals(allElites.slice(0, 10));

                console.log(`✅ Scan complete: ${data.total_results} results in ${data.scan_time_seconds}s`);
            }
        } catch (err) {
            console.error('Scan error:', err);
        }

        setScanProgress(100);

        // Auto Fetch Analytics
        fetchAnalytics("ALL_SECTORS");

        setIsScanning(false);
    };

    // --- EVENT HANDLERS ---
    const handleChange = (e) => setFormData({ ...formData, [e.target.name]: e.target.value });

    const handleWatchlistSelect = (symbol) => {
        setFormData(prev => ({ ...prev, symbol: symbol }));
        window.scrollTo({ top: 0, behavior: 'smooth' });
        setTimeout(() => document.getElementById('run-btn').click(), 100);
    };

    // --- VIEW CHANGE HANDLER ---
    const handleViewChange = (view) => {
        setViewMode(view);
        if (view === 'ANALYTICS' && !analyticsData) fetchAnalytics("ALL_SECTORS");
    };

    // =================================================================================
    // 3. RENDER UI
    // =================================================================================
    return (
        <>
            <Sidebar activeView={viewMode} onViewChange={handleViewChange} />
            <div className="app-content">
                <div className="min-h-screen bg-black text-cyan-50 font-sans p-4 md:p-8 selection:bg-cyan-500 selection:text-black pb-20">

                    {/* --- BACKTEST / MATRIX / PNL VIEWS --- */}
                    <div className={!['BACKTEST', 'MATRIX', 'PNL'].includes(viewMode) ? 'chart-section--hidden' : ''}>

                        {/* --- HEADER SECTION --- */}
                        <div className="flex flex-col xl:flex-row justify-between items-center mb-8 border-b border-cyan-900/50 pb-6 gap-6 relative">
                            <div className="absolute top-0 left-1/4 w-96 h-96 bg-purple-600/20 rounded-full blur-[100px] -z-10"></div>
                            <div>
                                <h1 className="text-3xl md:text-4xl font-black italic tracking-tighter">
                                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-600 drop-shadow-[0_0_10px_rgba(34,211,238,0.5)]">QUANTITATIVE TRADE</span>
                                    <span className="text-white drop-shadow-[0_0_15px_rgba(255,255,255,0.8)]"> PROTOCOL</span>
                                </h1>
                                <p className="text-[10px] md:text-xs text-gray-400 font-mono tracking-[0.2em] mt-1 uppercase opacity-80">
                                    OWNER: <span className="text-cyan-300">RAFLYANDI ALVIANSYAH</span> • MODE: <span className={formData.period === 'max' ? 'text-red-400' : 'text-green-400'}>{formData.period === 'max' ? 'HEAVY LOAD' : 'SMART INCREMENTAL'}</span>
                                </p>
                            </div>

                            {/* --- INPUT CONTROL PANEL --- */}
                            <div className="flex flex-col gap-2 items-center">
                                <div className="flex flex-wrap gap-3 bg-gray-900/40 backdrop-blur-md p-4 rounded-xl border border-cyan-500/30 shadow-[0_0_20px_rgba(8,145,178,0.2)] justify-center items-end">
                                    <InputGroup label="ASSET" icon="💎"><input name="symbol" value={formData.symbol} onChange={handleChange} className="neon-input w-28 text-center" /></InputGroup>
                                    <InputGroup label="STRATEGY" icon="⚡">
                                        <select name="strategy" value={formData.strategy} onChange={handleChange} className="neon-input w-36 cursor-pointer">
                                            <option value="MOMENTUM">Momentum</option>
                                            <option value="MEAN_REVERSAL">Mean Reversal</option>
                                            <option value="GRID">Grid</option>
                                            <option value="MULTITIMEFRAME">Multi TF</option>
                                            <option value="MOMENTUM_PRO">Momentum PRO</option>
                                            <option value="MEAN_REVERSAL_PRO">Mean Rev PRO</option>
                                            <option value="GRID_PRO">Grid PRO</option>
                                            <option value="MULTITIMEFRAME_PRO">Multi TF PRO</option>
                                            <option value="MIX_STRATEGY">Mix Strategy</option>
                                            <option value="MIX_STRATEGY_PRO">Mix Strategy PRO</option>
                                        </select>
                                    </InputGroup>
                                    <InputGroup label="TIMEFRAME" icon="⏱️"><select name="timeframe" value={formData.timeframe} onChange={handleChange} className="neon-input w-24 cursor-pointer"><option value="1h">1 H</option><option value="4h">4 H</option><option value="1d">1 D</option><option value="1wk">1 W</option></select></InputGroup>
                                    <InputGroup label="RANGE" icon="📅"><select name="period" value={formData.period} onChange={handleChange} className="neon-input w-24 cursor-pointer"><option value="1mo">1 M</option><option value="6mo">6 M</option><option value="1y">1 Y</option><option value="2y">2 Y</option><option value="max">Max</option></select></InputGroup>
                                    <InputGroup label="CAPITAL" icon="💰"><input type="number" name="capital" value={formData.capital} onChange={handleChange} className="neon-input w-24" /></InputGroup>

                                    {/* DIRECTION TOGGLE */}
                                    <InputGroup label="DIRECTION" icon="🎯">
                                        <div className="flex gap-1 h-[42px]">
                                            <button
                                                type="button"
                                                onClick={() => setFormData(prev => ({ ...prev, direction: 'LONG' }))}
                                                className={`px-3 rounded-lg text-xs font-bold transition-all flex items-center gap-1 border ${formData.direction === 'LONG'
                                                    ? 'bg-green-500/20 text-green-400 border-green-500/50 shadow-[0_0_10px_rgba(34,197,94,0.2)]'
                                                    : 'bg-gray-900 text-gray-500 border-gray-700 hover:text-gray-300'
                                                    }`}
                                            >
                                                <ArrowUpRight size={14} /> LONG
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => setFormData(prev => ({ ...prev, direction: 'SHORT' }))}
                                                className={`px-3 rounded-lg text-xs font-bold transition-all flex items-center gap-1 border ${formData.direction === 'SHORT'
                                                    ? 'bg-red-500/20 text-red-400 border-red-500/50 shadow-[0_0_10px_rgba(239,68,68,0.2)]'
                                                    : 'bg-gray-900 text-gray-500 border-gray-700 hover:text-gray-300'
                                                    }`}
                                            >
                                                <ArrowDownRight size={14} /> SHORT
                                            </button>
                                        </div>
                                    </InputGroup>

                                    <button id="run-btn" onClick={handleRunBacktest} disabled={loading} className="mt-auto h-[42px] bg-gradient-to-r from-cyan-600 to-blue-700 hover:from-cyan-500 hover:to-blue-600 text-white px-6 rounded-lg font-bold flex items-center gap-2 transition-all shadow-[0_0_15px_rgba(8,145,178,0.5)] disabled:opacity-50">
                                        {loading ? <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div> : <Play size={18} fill="currentColor" />} RUN
                                    </button>
                                </div>
                            </div>
                        </div>

                        {/* --- MAIN CHART & METRICS SECTION --- */}
                        <div className="flex flex-col lg:flex-row gap-6 mb-12">

                            {/* LEFT COLUMN: CHARTS */}
                            <div className="lg:w-3/4 flex flex-col gap-4 min-h-[600px]">
                                {/* Price Chart */}
                                <div className="flex-1 bg-gray-900/30 backdrop-blur-sm border border-cyan-900/50 rounded-2xl p-1 shadow-2xl relative flex flex-col group">
                                    <div className="absolute top-3 left-4 z-10 flex gap-2 pointer-events-none">
                                        <Badge text={`${formData.symbol} • ${formData.timeframe}`} color="bg-cyan-900/80 text-cyan-300" />
                                        <Badge text={formData.strategy} color="bg-purple-900/80 text-purple-300" />
                                    </div>
                                    <div className="flex-1 w-full relative" ref={priceChartContainer}></div>
                                </div>

                                {/* Equity Chart */}
                                <div className="h-48 bg-gray-900/30 backdrop-blur-sm border border-cyan-900/50 rounded-2xl p-1 relative flex flex-col">
                                    <div className="absolute top-2 left-4 z-10 text-[10px] text-blue-400 font-bold tracking-widest uppercase flex items-center gap-2">
                                        <TrendingUp size={12} /> Portfolio Growth
                                    </div>
                                    <div className="flex-1 w-full relative" ref={equityChartContainer}></div>
                                </div>
                            </div>

                            {/* RIGHT COLUMN: STATISTICS */}
                            <div className="lg:w-1/4 flex flex-col gap-6">
                                {/* Net Performance Card */}
                                <div className="bg-gray-900/50 backdrop-blur-md border border-cyan-500/30 rounded-2xl p-6 shadow-[0_0_30px_rgba(0,0,0,0.5)]">
                                    <h3 className="text-cyan-400 text-xs font-bold uppercase tracking-[0.2em] mb-4 flex items-center gap-2"><Zap size={14} /> Net Performance</h3>
                                    <div className={`text-4xl font-black font-mono mb-2 ${metrics?.net_profit >= 0 ? 'text-[#00ff41]' : 'text-[#ff0055]'}`}>
                                        ${metrics?.net_profit?.toLocaleString() || "0"}
                                    </div>
                                    <div className="flex justify-between items-end text-xs text-gray-400 mt-2">
                                        <span>Final Equity</span>
                                        <span className="text-white font-mono font-bold">${metrics?.final_balance?.toLocaleString()}</span>
                                    </div>
                                </div>

                                {/* Risk Analysis Card */}
                                <div className="bg-gray-900/30 border border-gray-800 rounded-2xl p-6">
                                    <h3 className="text-gray-500 text-xs font-bold uppercase tracking-[0.2em] mb-4 flex items-center gap-2"><Shield size={14} /> Risk Analysis</h3>
                                    <div className="space-y-3 font-mono text-sm">
                                        <StatRow label="Max Drawdown" value={`${metrics?.max_drawdown || 0}%`} color="text-red-400" />
                                        <div className="flex justify-between items-center text-sm border-b border-gray-800 pb-2 hover:bg-white/5 px-2 rounded transition">
                                            <span className="text-gray-500 text-xs uppercase flex items-center">Sharpe Ratio <InfoTooltip text="Reward per unit of risk." /></span>
                                            <span className="font-bold text-yellow-400">{metrics?.sharpe_ratio || 0}</span>
                                        </div>
                                        <div className="flex justify-between items-center text-sm border-b border-gray-800 pb-2 hover:bg-white/5 px-2 rounded transition">
                                            <span className="text-gray-500 text-xs uppercase flex items-center">Calmar Ratio <InfoTooltip text="Return / Max Drawdown." /></span>
                                            <span className="font-bold text-blue-400">{metrics?.calmar_ratio || 0}</span>
                                        </div>
                                    </div>
                                </div>

                                {/* Trade Stats Card */}
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

                        {/* --- STRATEGY MATRIX (COMPARISON) --- */}
                        <div className="mb-12">
                            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
                                STRATEGY MATRIX
                                <span className={`text-xs font-bold px-2 py-1 rounded-full border ${formData.direction === 'SHORT'
                                    ? 'bg-red-500/20 text-red-400 border-red-500/30'
                                    : 'bg-green-500/20 text-green-400 border-green-500/30'
                                    }`}>
                                    {formData.direction === 'SHORT' ? <ArrowDownRight size={12} className="inline" /> : <ArrowUpRight size={12} className="inline" />}
                                    {formData.direction}
                                </span>
                                <span className="text-sm text-gray-500 font-normal ml-2">Which logic fits {formData.symbol} best?</span>
                            </h2>
                            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 xl:grid-cols-5 gap-3">
                                {compLoading ? (
                                    <div className="col-span-5 text-center text-cyan-500 py-10 animate-pulse bg-gray-900/30 rounded-xl">Analyzing 10 Strategies ({formData.direction})...</div>
                                ) : (comparisonData ? comparisonData.map((s, idx) => (
                                    <div key={idx} className={`p-3 rounded-xl border backdrop-blur-sm transition hover:scale-105 ${idx === 0 ? 'border-yellow-500 border-2 bg-yellow-900/20' : (s.net_profit > 0 ? 'border-green-500/30 bg-green-900/10' : 'border-red-500/30 bg-red-900/10')}`}>
                                        <div className="flex justify-between items-start mb-1">
                                            <span className={`text-[10px] font-bold uppercase tracking-widest ${idx === 0 ? 'text-yellow-400' : 'text-gray-400'}`}>{s.strategy.replace("_PRO", " PRO")}</span>
                                            {idx === 0 && <span className="text-[9px] bg-yellow-500 text-black px-1 rounded font-bold">BEST</span>}
                                        </div>
                                        <div className={`text-xl font-black font-mono mb-1 ${s.net_profit > 0 ? 'text-green-400' : 'text-red-400'}`}>${s.net_profit.toLocaleString()}</div>
                                        {!s.is_hold && <div className="flex justify-between text-[10px] text-gray-500">
                                            <span>WR: {s.win_rate}%</span>
                                            <span>DD: {s.max_dd}%</span>
                                        </div>}
                                        {s.direction && !s.is_hold && (
                                            <div className={`mt-1 text-[9px] font-bold flex items-center gap-1 ${s.direction === 'SHORT' ? 'text-red-400' : 'text-green-400'}`}>
                                                {s.direction === 'SHORT' ? <ArrowDownRight size={10} /> : <ArrowUpRight size={10} />}
                                                {s.direction}
                                            </div>
                                        )}
                                    </div>
                                )) : <div className="col-span-5 text-center text-gray-600">Run backtest to see matrix.</div>)}
                            </div>
                        </div>

                        {/* --- MONTE CARLO SIMULATION --- */}
                        {!loading && metrics && (
                            <div className="mb-12">
                                <h2 className="text-2xl font-bold text-white mb-2 flex items-center gap-2">
                                    MONTE CARLO SIMULATION
                                    <span className="text-sm text-gray-500 font-normal ml-2">Stress test this strategy's path dependency</span>
                                </h2>
                                <MonteCarloChart
                                    symbol={formData.symbol}
                                    capital={formData.capital}
                                    strategy={formData.strategy}
                                    period={formData.period}
                                    timeframe={formData.timeframe}
                                />
                            </div>
                        )}

                        {/* --- PnL SEGMENTATION (Objective 3) --- */}
                        <div className="mb-12">
                            <div className="flex items-center gap-4 mb-4">
                                <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                                    📊 PnL Segmentation
                                </h2>
                                <div className="flex gap-1 bg-gray-900/60 p-1 rounded-lg border border-gray-700">
                                    {['COMBINED', 'LONG', 'SHORT'].map(mode => (
                                        <button
                                            key={mode}
                                            onClick={() => {
                                                setPnlFilter(mode);
                                                if (!dualData && !dualLoading) {
                                                    fetchDualBacktest();
                                                }
                                            }}
                                            className={`px-4 py-2 rounded-md text-xs font-bold transition-all ${pnlFilter === mode
                                                ? mode === 'LONG' ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                                                    : mode === 'SHORT' ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                                                        : 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                                                : 'text-gray-500 hover:text-gray-300'
                                                }`}
                                        >
                                            {mode === 'COMBINED' ? '🔄' : mode === 'LONG' ? '📈' : '📉'} {mode}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {dualLoading && <div className="text-cyan-400 animate-pulse text-center py-6">Running dual LONG+SHORT backtest...</div>}

                            {pnlError && !dualLoading && (
                                <div className="text-center py-4 px-6 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm">
                                    ⚠️ {pnlError}
                                </div>
                            )}

                            {dualData && (() => {
                                const m = pnlFilter === 'LONG' ? dualData.pnl_long
                                    : pnlFilter === 'SHORT' ? dualData.pnl_short
                                        : dualData.pnl_combined;
                                if (!m) return null;
                                return (
                                    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
                                        <div className="bg-gray-900/50 border border-gray-700 rounded-xl p-4 text-center">
                                            <div className="text-[10px] text-gray-500 uppercase font-bold">Net Profit</div>
                                            <div className={`text-xl font-black font-mono ${m.net_profit >= 0 ? 'text-green-400' : 'text-red-400'}`}>${m.net_profit?.toLocaleString()}</div>
                                        </div>
                                        <div className="bg-gray-900/50 border border-gray-700 rounded-xl p-4 text-center">
                                            <div className="text-[10px] text-gray-500 uppercase font-bold">Win Rate</div>
                                            <div className="text-xl font-black font-mono text-yellow-400">{m.win_rate}%</div>
                                        </div>
                                        <div className="bg-gray-900/50 border border-gray-700 rounded-xl p-4 text-center">
                                            <div className="text-[10px] text-gray-500 uppercase font-bold">Total Trades</div>
                                            <div className="text-xl font-black font-mono text-white">{m.total_trades}</div>
                                        </div>
                                        <div className="bg-gray-900/50 border border-gray-700 rounded-xl p-4 text-center">
                                            <div className="text-[10px] text-gray-500 uppercase font-bold">Max Drawdown</div>
                                            <div className="text-xl font-black font-mono text-red-400">{m.max_drawdown}%</div>
                                        </div>
                                        <div className="bg-gray-900/50 border border-gray-700 rounded-xl p-4 text-center">
                                            <div className="text-[10px] text-gray-500 uppercase font-bold">Sharpe Ratio</div>
                                            <div className="text-xl font-black font-mono text-blue-400">{m.sharpe_ratio}</div>
                                        </div>
                                        {pnlFilter === 'COMBINED' && m.pnl_long !== undefined && (
                                            <div className="bg-gray-900/50 border border-gray-700 rounded-xl p-4 text-center">
                                                <div className="text-[10px] text-gray-500 uppercase font-bold">Long / Short Split</div>
                                                <div className="text-sm font-mono">
                                                    <span className="text-green-400">${m.pnl_long?.toLocaleString()}</span>
                                                    <span className="text-gray-600 mx-1">/</span>
                                                    <span className="text-red-400">${m.pnl_short?.toLocaleString()}</span>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                );
                            })()}
                        </div>

                    </div>

                    {/* ============================================================= */}
                    {/* SIDEBAR-DRIVEN CONTENT SECTIONS                                */}
                    {/* ============================================================= */}

                    {/* === SCANNER SIGNALS === */}
                    {viewMode === 'SCANNER' && (
                        <div className="bg-gray-900/20 border border-cyan-900/30 rounded-3xl p-8 relative overflow-hidden mb-12 animate-fade-in-up">
                            <div className="flex flex-col md:flex-row justify-between items-center mb-8 gap-4">
                                <div>
                                    <h2 className="text-2xl font-bold text-white flex items-center gap-2"><Globe className="text-cyan-500" /> MARKET INTELLIGENCE</h2>
                                    <p className="text-gray-400 text-sm mt-1">Multi-sector analysis and algorithmic scanning.</p>
                                </div>
                                <div className="flex gap-4 items-center">
                                    <div className="flex items-center gap-1 bg-gray-900/60 p-1 rounded-lg border border-gray-700">
                                        <button onClick={() => setFormData(prev => ({ ...prev, direction: 'LONG' }))} className={`flex items-center gap-1 px-3 py-2 rounded-md text-xs font-bold transition-all ${formData.direction === 'LONG' ? 'bg-green-500/20 text-green-400 border border-green-500/30' : 'text-gray-500 hover:text-gray-300'}`}><ArrowUpRight size={14} /> Long</button>
                                        <button onClick={() => setFormData(prev => ({ ...prev, direction: 'SHORT' }))} className={`flex items-center gap-1 px-3 py-2 rounded-md text-xs font-bold transition-all ${formData.direction === 'SHORT' ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'text-gray-500 hover:text-gray-300'}`}><ArrowDownRight size={14} /> Short</button>
                                    </div>
                                    <button onClick={() => handleScanMarket(false)} disabled={isScanning} className="bg-cyan-600 hover:bg-cyan-500 text-white px-8 py-3 rounded-lg font-bold flex items-center gap-2 transition shadow-[0_0_20px_cyan]">
                                        {isScanning ? <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div> : <Search size={20} />}
                                        {isScanning ? `SCANNING ${scanProgress}%` : "SMART SCAN"}
                                    </button>
                                    <button onClick={() => { if (confirm("Reset all data cache and re-download from Binance? This will take time.")) handleScanMarket(true); }} disabled={isScanning} className="bg-gray-800 hover:bg-red-900/50 text-gray-400 hover:text-red-400 px-4 py-3 rounded-lg font-bold transition border border-gray-700" title="Reset Database & Rescan"><RefreshCw size={20} /></button>
                                </div>
                            </div>
                            {isScanning && (
                                <div className="w-full bg-gray-800 rounded-full h-2.5 mb-8 overflow-hidden relative">
                                    <div className="bg-cyan-500 h-2.5 rounded-full transition-all duration-300 ease-out" style={{ width: `${scanProgress}%` }}></div>
                                    <div className="absolute top-0 w-full h-full bg-white/10 animate-pulse"></div>
                                </div>
                            )}
                            {/* ELITE SIGNALS */}
                            {eliteSignals.length > 0 ? (
                                <div className="mb-10">
                                    <h3 className="text-lg font-bold text-yellow-400 mb-4 flex items-center gap-2"><AlertTriangle size={18} /> ELITE SIGNALS (Win Rate {'>'} 60%)</h3>
                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                                        {eliteSignals.map((sig, idx) => (
                                            <div key={idx} className="bg-yellow-900/10 border border-yellow-500/50 p-4 rounded-xl relative overflow-hidden hover:bg-yellow-900/20 transition cursor-pointer group" onClick={() => handleWatchlistSelect(sig.symbol)}>
                                                <div className="absolute top-0 right-0 bg-yellow-500 text-black text-[9px] font-bold px-2 py-0.5 rounded-bl">RANK #{idx + 1}</div>
                                                <div className="flex justify-between items-center mb-2">
                                                    <div className="font-bold text-white text-lg">{sig.symbol}</div>
                                                    <Badge text={sig.timeframe} color="bg-gray-700 text-gray-200" />
                                                </div>
                                                <div className="text-[10px] text-cyan-300 font-bold mb-3 flex items-center gap-1 bg-cyan-900/20 w-fit px-2 py-1 rounded"><Settings size={10} /> {sig.strategy}</div>
                                                <div className="grid grid-cols-2 gap-2 mb-3">
                                                    <div className="bg-gray-800/50 p-2 rounded text-center"><div className="text-[10px] text-gray-500">Win Rate</div><div className="text-green-400 font-bold">{sig.win_rate}%</div></div>
                                                    <div className="bg-gray-800/50 p-2 rounded text-center"><div className="text-[10px] text-gray-500">Profit</div><div className={`font-bold ${sig.profit > 0 ? 'text-green-400' : 'text-red-400'}`}>${sig.profit ? sig.profit.toLocaleString() : '0'}</div></div>
                                                </div>
                                                <div className="bg-black/40 p-2 rounded border border-gray-800 text-[10px] space-y-1 font-mono group-hover:border-yellow-500/30 transition">
                                                    <div className="flex justify-between"><span className="text-blue-400">ENTRY</span> <span>${sig.signal_data.price.toFixed(sig.signal_data.price < 1 ? 4 : 2)}</span></div>
                                                    <div className="flex justify-between"><span className="text-green-400">TP</span> <span>${sig.signal_data.setup_long.tp.toFixed(sig.signal_data.price < 1 ? 4 : 2)}</span></div>
                                                    <div className="flex justify-between"><span className="text-red-400">SL</span> <span>${sig.signal_data.setup_long.sl.toFixed(sig.signal_data.price < 1 ? 4 : 2)}</span></div>
                                                    <div className="flex justify-between border-t border-gray-700 pt-1 mt-1"><span className="text-yellow-400">R:R</span> <span>{sig.rr_ratio}</span></div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ) : (
                                !isScanning && <div className="text-center text-gray-600 italic mb-8">Click "SMART SCAN" to find elite opportunities.</div>
                            )}
                            {/* SECTOR GRIDS */}
                            <div className="space-y-8">
                                {SECTORS_LIST.map((sector) => (
                                    <div key={sector.id} className="border-t border-gray-800 pt-6">
                                        <h3 className="text-lg font-bold text-purple-400 mb-4 flex items-center gap-2"><Coins size={16} /> {sector.name}</h3>
                                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                                            {scanResults[sector.name] ? scanResults[sector.name].map((coin, idx) => (
                                                <div key={idx} className="bg-black/40 border border-gray-800 p-4 rounded-xl hover:border-cyan-500/50 transition group cursor-pointer" onClick={() => handleWatchlistSelect(coin.symbol)}>
                                                    <div className="flex justify-between items-start mb-2">
                                                        <div className="flex items-center gap-2">
                                                            <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-[10px] ${coin.profit > 0 ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'}`}>{coin.symbol.substring(0, 3)}</div>
                                                            <div><div className="font-bold text-sm text-white">{coin.symbol}</div><div className="text-[9px] text-gray-500">{coin.timeframe} • {coin.period}</div></div>
                                                        </div>
                                                        <div className={`text-sm font-mono font-bold ${coin.profit > 0 ? 'text-green-400' : 'text-red-400'}`}>{coin.profit > 0 ? '+' : ''}{coin.profit.toLocaleString()}</div>
                                                    </div>
                                                    <div className="flex justify-between items-end mt-2">
                                                        <div className="text-[10px] text-gray-500 uppercase tracking-wider">{coin.strategy}</div>
                                                        {coin.profit > 0 && <Shield size={12} className="text-green-500" />}
                                                    </div>
                                                </div>
                                            )) : <div className="col-span-4 text-xs text-gray-700">Waiting to scan...</div>}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* === MARKET ANALYTICS === */}
                    {viewMode === 'ANALYTICS' && (
                        <div className="animate-fade-in-up">
                            <div className="flex flex-wrap gap-2 mb-6 justify-center">
                                <button onClick={() => fetchAnalytics("ALL_SECTORS")} className={`px-4 py-1 rounded-full text-xs font-bold border transition ${selectedAnalyticsSector === "ALL_SECTORS" ? 'bg-purple-600 border-purple-400 text-white' : 'bg-gray-800 border-gray-700 text-gray-400 hover:bg-gray-700'}`}>ALL SECTORS</button>
                                {SECTORS_LIST.map((s) => (
                                    <button key={s.id} onClick={() => fetchAnalytics(s.id)} className={`px-4 py-1 rounded-full text-xs font-bold border transition ${selectedAnalyticsSector === s.id ? 'bg-cyan-600 border-cyan-400 text-white' : 'bg-gray-800 border-gray-700 text-gray-400 hover:bg-gray-700'}`}>{s.name}</button>
                                ))}
                            </div>
                            {isAnalyticsLoading ? (
                                <div className="text-center py-20 animate-pulse"><div className="text-cyan-400 text-xl font-bold">🚀 Computing Analytics...</div><div className="text-gray-500 text-sm mt-2">Aggregating cross-sector performance data.</div></div>
                            ) : (
                                <MarketAnalytics data={analyticsData} />
                            )}
                        </div>
                    )}

                    {/* === BOT TRACKER === */}
                    {viewMode === 'BOT_TRACKER' && <div className="animate-fade-in-up"><BotTracker /></div>}

                    {/* === PORTFOLIO === */}
                    {viewMode === 'PORTFOLIO' && <div className="animate-fade-in-up"><PortfolioPage /></div>}

                    {/* === RISK === */}
                    {viewMode === 'RISK' && <div className="animate-fade-in-up"><RiskDashboard /></div>}

                    {/* === FUND === */}
                    {viewMode === 'FUND' && <div className="animate-fade-in-up"><FundDashboard /></div>}

                    {/* === ELITE GEMS === */}
                    {viewMode === 'ELITE' && <div className="animate-fade-in-up"><EliteSignals onGemSelect={handleGemSelect} /></div>}

                    {/* === MACRO INTELLIGENCE === */}
                    {viewMode === 'MACRO' && <div className="animate-fade-in-up"><MacroDashboard /></div>}

                    {/* === ANOMALY SCANNER === */}
                    {viewMode === 'ANOMALY' && <div className="animate-fade-in-up"><AnomalyDashboard /></div>}

                    {/* === GLOBAL MARKET === */}
                    {viewMode === 'GLOBAL_MARKET' && <div className="animate-fade-in-up"><GlobalMarketDashboard /></div>}

                    {/* === AI INSIGHTS === */}
                    {viewMode === 'AI_INSIGHTS' && <div className="animate-fade-in-up"><AIDashboard /></div>}

                    {/* === WATCHLIST === */}
                    {viewMode === 'WATCHLIST' && (
                        <div className="bg-gray-900/40 backdrop-blur-md border border-cyan-500/30 rounded-3xl p-8 shadow-[0_0_20px_rgba(8,145,178,0.1)] animate-fade-in-up">
                            <Watchlist onSelectAsset={handleWatchlistSelect} />
                        </div>
                    )}

                </div>
            </div>
        </>
    );
};

// --- SUB-COMPONENTS ---
const InputGroup = ({ label, icon, children }) => (
    <div className="flex flex-col">
        <label className="text-[9px] text-cyan-500/80 font-bold uppercase ml-1 mb-1 tracking-wider flex items-center gap-1">{icon} {label}</label>
        {children}
    </div>
);

const Badge = ({ text, color }) => (
    <span className={`px-2 py-0.5 rounded text-[10px] font-mono border border-white/10 shadow-lg backdrop-blur-md ${color}`}>
        {text}
    </span>
);

const StatRow = ({ label, value, color = "text-gray-300" }) => (
    <div className="flex justify-between items-center text-sm border-b border-gray-800 pb-2 last:border-0 hover:bg-white/5 px-2 rounded transition">
        <span className="text-gray-500 text-xs uppercase">{label}</span>
        <span className={`font-bold ${color}`}>{value}</span>
    </div>
);

export default DashboardPage;