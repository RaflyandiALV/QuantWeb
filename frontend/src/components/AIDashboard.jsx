import React, { useState, useEffect, useCallback } from 'react';
import {
    Brain, Activity, Zap, TrendingUp, TrendingDown, Shield, PlayCircle,
    StopCircle, RefreshCw, AlertTriangle, CheckCircle, XCircle, BarChart2,
    Target, Clock, Cpu, ArrowUpRight, ArrowDownRight, Minus, Eye
} from 'lucide-react';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// REUSABLE UI COMPONENTS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const GlassCard = ({ children, className = '', glow = '' }) => (
    <div className={`bg-gray-900/40 backdrop-blur-xl border border-gray-700/50 rounded-2xl p-6 
        shadow-[0_8px_32px_rgba(0,0,0,0.3)] hover:border-gray-600/60 transition-all duration-300 ${glow} ${className}`}>
        {children}
    </div>
);

const StatPill = ({ label, value, color = 'text-white', icon: Icon, sub = '' }) => (
    <div className="flex flex-col items-center gap-1 bg-black/30 rounded-xl px-4 py-3 border border-gray-800/50">
        {Icon && <Icon size={14} className="text-gray-500" />}
        <span className="text-[10px] text-gray-500 uppercase tracking-wider font-bold">{label}</span>
        <span className={`text-lg font-black font-mono ${color}`}>{value}</span>
        {sub && <span className="text-[9px] text-gray-600">{sub}</span>}
    </div>
);

const PulseDot = ({ active }) => (
    <span className="relative flex h-2.5 w-2.5">
        {active && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>}
        <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${active ? 'bg-green-400' : 'bg-gray-600'}`}></span>
    </span>
);

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// MAIN DASHBOARD COMPONENT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const AIDashboard = () => {
    const [aiStatus, setAiStatus] = useState(null);
    const [paperStatus, setPaperStatus] = useState(null);
    const [decisions, setDecisions] = useState([]);
    const [validationReport, setValidationReport] = useState(null);
    const [features, setFeatures] = useState(null);
    const [microData, setMicroData] = useState(null);
    const [loading, setLoading] = useState({});
    const [selectedSymbol, setSelectedSymbol] = useState('BTC-USDT');
    const [cycleResult, setCycleResult] = useState(null);
    const [activeTab, setActiveTab] = useState('overview');

    const SYMBOLS = ['BTC-USDT', 'ETH-USDT', 'SOL-USDT', 'BNB-USDT', 'XRP-USDT'];

    // ── FETCH HELPERS ──
    const safeFetch = async (url, options = {}) => {
        try {
            const res = await fetch(url, options);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        } catch (e) {
            console.error(`Fetch error: ${url}`, e);
            return null;
        }
    };

    const setLoadingKey = (key, val) => setLoading(prev => ({ ...prev, [key]: val }));

    // ── DATA FETCHERS ──
    const fetchAiStatus = useCallback(async () => {
        const data = await safeFetch(`${BASE_URL}/api/ai/status`);
        if (data) setAiStatus(data);
    }, []);

    const fetchPaperStatus = useCallback(async () => {
        const data = await safeFetch(`${BASE_URL}/api/paper-trader/status`);
        if (data) setPaperStatus(data);
    }, []);

    const fetchDecisions = useCallback(async () => {
        const data = await safeFetch(`${BASE_URL}/api/ai/decisions?limit=20`);
        if (data) setDecisions(Array.isArray(data) ? data : []);
    }, []);

    const fetchFeatures = useCallback(async (symbol) => {
        setLoadingKey('features', true);
        const data = await safeFetch(`${BASE_URL}/api/alpha-features/${symbol}`);
        if (data) setFeatures(data);
        setLoadingKey('features', false);
    }, []);

    const fetchValidation = useCallback(async () => {
        const data = await safeFetch(`${BASE_URL}/api/validation/report`);
        if (data) setValidationReport(data);
    }, []);

    const fetchMicroData = useCallback(async (symbol) => {
        setLoadingKey('micro', true);
        const data = await safeFetch(`${BASE_URL}/api/alpha-data/${symbol}`);
        if (data) setMicroData(data);
        setLoadingKey('micro', false);
    }, []);

    // ── ACTIONS ──
    const handleStartPaper = async () => {
        setLoadingKey('paper', true);
        await safeFetch(`${BASE_URL}/api/paper-trader/start`, { method: 'POST' });
        await fetchPaperStatus();
        setLoadingKey('paper', false);
    };

    const handleStopPaper = async () => {
        setLoadingKey('paper', true);
        await safeFetch(`${BASE_URL}/api/paper-trader/stop`, { method: 'POST' });
        await fetchPaperStatus();
        setLoadingKey('paper', false);
    };

    const handleRunCycle = async () => {
        setLoadingKey('cycle', true);
        const data = await safeFetch(`${BASE_URL}/api/paper-trader/cycle`, { method: 'POST' });
        if (data) setCycleResult(data);
        await fetchPaperStatus();
        await fetchDecisions();
        setLoadingKey('cycle', false);
    };

    const handleRunValidation = async () => {
        setLoadingKey('validation', true);
        const data = await safeFetch(`${BASE_URL}/api/validation/run`, { method: 'POST' });
        if (data) setValidationReport(data);
        setLoadingKey('validation', false);
    };

    const handleGetDecision = async () => {
        setLoadingKey('decision', true);
        const data = await safeFetch(`${BASE_URL}/api/ai-decision/${selectedSymbol}`, { method: 'POST' });
        if (data) {
            setCycleResult(prev => ({ ...prev, singleDecision: data }));
            await fetchDecisions();
        }
        setLoadingKey('decision', false);
    };

    // ── INITIAL LOAD ──
    useEffect(() => {
        fetchAiStatus();
        fetchPaperStatus();
        fetchDecisions();
        fetchValidation();
        fetchFeatures(selectedSymbol);
    }, []);

    useEffect(() => {
        fetchFeatures(selectedSymbol);
        fetchMicroData(selectedSymbol);
    }, [selectedSymbol]);

    // Auto-refresh every 30s
    useEffect(() => {
        const interval = setInterval(() => {
            fetchPaperStatus();
            fetchDecisions();
        }, 30000);
        return () => clearInterval(interval);
    }, []);

    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    // RENDER
    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    const tabs = [
        { id: 'overview', label: 'Overview', icon: Brain },
        { id: 'micro', label: 'Microstructure', icon: Eye },
        { id: 'features', label: 'Alpha Features', icon: BarChart2 },
        { id: 'decisions', label: 'Decision Log', icon: Target },
        { id: 'validation', label: 'Validation', icon: Shield },
    ];

    return (
        <div className="animate-fade-in-up">
            {/* ── HEADER ── */}
            <div className="mb-8">
                <div className="flex items-center gap-3 mb-2">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-pink-500 to-purple-600 flex items-center justify-center shadow-[0_0_20px_rgba(236,72,153,0.3)]">
                        <Brain size={22} className="text-white" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-black tracking-tight text-white">AI TRADING ENGINE</h1>
                        <p className="text-xs text-gray-500 font-mono tracking-wider">
                            HYBRID CLAUDE 3 HAIKU + RULE-BASED MOCK • PAPER TRADING • VALIDATION
                        </p>
                    </div>
                    <div className="ml-auto flex items-center gap-3">
                        <div className="flex items-center gap-2 bg-gray-900/60 px-3 py-1.5 rounded-lg border border-gray-700">
                            <PulseDot active={aiStatus?.mode === 'live'} />
                            <span className={`text-xs font-bold uppercase tracking-wider ${aiStatus?.mode === 'live' ? 'text-green-400' : 'text-yellow-400'}`}>
                                {aiStatus?.mode || 'loading...'}
                            </span>
                        </div>
                        <button onClick={() => { fetchAiStatus(); fetchPaperStatus(); fetchDecisions(); }}
                            className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white transition border border-gray-700">
                            <RefreshCw size={14} />
                        </button>
                    </div>
                </div>
            </div>

            {/* ── TAB BAR ── */}
            <div className="flex gap-1 mb-6 bg-gray-900/60 p-1 rounded-xl border border-gray-700/50 w-fit">
                {tabs.map(tab => {
                    const Icon = tab.icon;
                    return (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all ${activeTab === tab.id
                                ? 'bg-pink-500/20 text-pink-400 border border-pink-500/30 shadow-[0_0_10px_rgba(236,72,153,0.15)]'
                                : 'text-gray-500 hover:text-gray-300'
                                }`}
                        >
                            <Icon size={14} /> {tab.label}
                        </button>
                    );
                })}
            </div>

            {/* ━━━━━━━━━━━━━  OVERVIEW TAB  ━━━━━━━━━━━━━ */}
            {activeTab === 'overview' && (
                <div className="space-y-6">
                    {/* AI Status + Paper Trader Row */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* AI Status Card */}
                        <GlassCard glow="hover:shadow-[0_0_30px_rgba(236,72,153,0.1)]">
                            <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-pink-400 mb-4 flex items-center gap-2">
                                <Cpu size={14} /> AI Engine Status
                            </h3>
                            <div className="grid grid-cols-2 gap-3">
                                <StatPill label="Mode" value={aiStatus?.mode?.toUpperCase() || '—'} color={aiStatus?.mode === 'live' ? 'text-green-400' : 'text-yellow-400'} icon={Zap} />
                                <StatPill label="Model" value={aiStatus?.model?.split('-').slice(0, 2).join(' ') || '—'} color="text-purple-400" icon={Brain} />
                                <StatPill label="API Key" value={aiStatus?.has_api_key ? '✓ Set' : '✗ Missing'} color={aiStatus?.has_api_key ? 'text-green-400' : 'text-red-400'} icon={Shield} />
                                <StatPill label="Total Decisions" value={aiStatus?.total_decisions ?? '—'} color="text-cyan-400" icon={Target} />
                            </div>

                            {/* Quick Decision Button */}
                            <div className="mt-4 flex gap-2">
                                <select value={selectedSymbol} onChange={e => setSelectedSymbol(e.target.value)}
                                    className="bg-black/40 border border-gray-700 rounded-lg px-3 py-2 text-xs text-white font-mono">
                                    {SYMBOLS.map(s => <option key={s} value={s}>{s}</option>)}
                                </select>
                                <button onClick={handleGetDecision} disabled={loading.decision}
                                    className="flex-1 bg-gradient-to-r from-pink-600 to-purple-600 hover:from-pink-500 hover:to-purple-500 text-white px-4 py-2 rounded-lg text-xs font-bold flex items-center justify-center gap-2 transition-all shadow-[0_0_15px_rgba(236,72,153,0.3)] disabled:opacity-50">
                                    {loading.decision ? <RefreshCw size={14} className="animate-spin" /> : <Brain size={14} />}
                                    GET AI DECISION
                                </button>
                            </div>
                        </GlassCard>

                        {/* Paper Trader Card */}
                        <GlassCard glow="hover:shadow-[0_0_30px_rgba(34,197,94,0.1)]">
                            <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-green-400 mb-4 flex items-center gap-2">
                                <Activity size={14} /> Paper Trader
                                <PulseDot active={paperStatus?.running} />
                            </h3>
                            <div className="grid grid-cols-3 gap-3">
                                <StatPill label="Status" value={paperStatus?.running ? 'ACTIVE' : 'IDLE'} color={paperStatus?.running ? 'text-green-400' : 'text-gray-500'} icon={Activity} />
                                <StatPill label="Cycles" value={paperStatus?.cycle_count ?? 0} color="text-cyan-400" icon={RefreshCw} />
                                <StatPill label="Open Pos" value={paperStatus?.open_positions ?? 0} color="text-yellow-400" icon={Target} />
                                <StatPill label="Total PnL" value={`$${paperStatus?.total_pnl ?? 0}`} color={(paperStatus?.total_pnl ?? 0) >= 0 ? 'text-green-400' : 'text-red-400'} icon={TrendingUp} />
                                <StatPill label="Win Rate" value={`${paperStatus?.win_rate ?? 0}%`} color="text-yellow-400" icon={CheckCircle} />
                                <StatPill label="Trades" value={paperStatus?.total_trades ?? 0} color="text-white" icon={BarChart2} />
                            </div>
                            <div className="mt-4 flex gap-2">
                                <button onClick={handleStartPaper} disabled={paperStatus?.running || loading.paper}
                                    className="flex-1 bg-green-600/20 hover:bg-green-600/30 text-green-400 border border-green-500/30 px-4 py-2 rounded-lg text-xs font-bold flex items-center justify-center gap-2 transition disabled:opacity-30">
                                    <PlayCircle size={14} /> START
                                </button>
                                <button onClick={handleStopPaper} disabled={!paperStatus?.running || loading.paper}
                                    className="flex-1 bg-red-600/20 hover:bg-red-600/30 text-red-400 border border-red-500/30 px-4 py-2 rounded-lg text-xs font-bold flex items-center justify-center gap-2 transition disabled:opacity-30">
                                    <StopCircle size={14} /> STOP
                                </button>
                                <button onClick={handleRunCycle} disabled={loading.cycle}
                                    className="flex-1 bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-400 border border-cyan-500/30 px-4 py-2 rounded-lg text-xs font-bold flex items-center justify-center gap-2 transition disabled:opacity-50">
                                    {loading.cycle ? <RefreshCw size={14} className="animate-spin" /> : <Zap size={14} />}
                                    RUN CYCLE
                                </button>
                            </div>
                        </GlassCard>
                    </div>

                    {/* Latest Decision Result */}
                    {cycleResult?.singleDecision && (
                        <GlassCard glow={cycleResult.singleDecision.decision === 'LONG' ? 'border-green-500/40' : cycleResult.singleDecision.decision === 'SHORT' ? 'border-red-500/40' : ''}>
                            <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-purple-400 mb-3 flex items-center gap-2">
                                <Target size={14} /> Latest AI Decision — {selectedSymbol}
                            </h3>
                            <div className="flex flex-wrap gap-4 items-start">
                                <div className={`text-3xl font-black flex items-center gap-2 ${cycleResult.singleDecision.decision === 'LONG' ? 'text-green-400' :
                                    cycleResult.singleDecision.decision === 'SHORT' ? 'text-red-400' : 'text-gray-400'
                                    }`}>
                                    {cycleResult.singleDecision.decision === 'LONG' ? <ArrowUpRight size={28} /> :
                                        cycleResult.singleDecision.decision === 'SHORT' ? <ArrowDownRight size={28} /> : <Minus size={28} />}
                                    {cycleResult.singleDecision.decision}
                                </div>
                                <div className="flex-1 grid grid-cols-2 md:grid-cols-5 gap-3">
                                    <StatPill label="Confidence" value={`${cycleResult.singleDecision.confidence}%`}
                                        color={cycleResult.singleDecision.confidence >= 70 ? 'text-green-400' : 'text-yellow-400'} />
                                    <StatPill label="Entry" value={`$${Number(cycleResult.singleDecision.entry || 0).toLocaleString()}`} color="text-white" />
                                    <StatPill label="Stop Loss" value={`$${Number(cycleResult.singleDecision.stop_loss || 0).toLocaleString()}`} color="text-red-400" />
                                    <StatPill label="Take Profit" value={`$${Number(cycleResult.singleDecision.take_profit || 0).toLocaleString()}`} color="text-green-400" />
                                    <StatPill label="R:R" value={cycleResult.singleDecision.risk_reward || '—'} color="text-purple-400" />
                                </div>
                            </div>
                            {cycleResult.singleDecision.reasoning && (
                                <div className="mt-3 bg-black/30 rounded-xl p-4 border border-gray-800/50">
                                    <p className="text-xs text-gray-400 leading-relaxed font-mono">{cycleResult.singleDecision.reasoning}</p>
                                </div>
                            )}
                            {cycleResult.singleDecision.mode && (
                                <span className="inline-block mt-2 text-[9px] px-2 py-0.5 rounded-full border font-bold uppercase tracking-wider
                                    bg-gray-800/50 border-gray-700 text-gray-400">
                                    via {cycleResult.singleDecision.mode} engine
                                </span>
                            )}
                        </GlassCard>
                    )}

                    {/* Cycle Results */}
                    {cycleResult?.results && !cycleResult?.singleDecision && (
                        <GlassCard>
                            <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-cyan-400 mb-3 flex items-center gap-2">
                                <Zap size={14} /> Cycle #{cycleResult.cycle} Results
                            </h3>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                {Object.entries(cycleResult.results).map(([sym, data]) => (
                                    <div key={sym} className="bg-black/30 rounded-xl p-4 border border-gray-800/50">
                                        <div className="flex justify-between items-center mb-2">
                                            <span className="text-white font-bold text-sm">{sym}</span>
                                            {data.error ? (
                                                <span className="text-red-400 text-[10px]">ERROR</span>
                                            ) : (
                                                <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${data.decision?.decision === 'LONG' ? 'bg-green-500/20 text-green-400' :
                                                    data.decision?.decision === 'SHORT' ? 'bg-red-500/20 text-red-400' :
                                                        'bg-gray-700 text-gray-400'
                                                    }`}>
                                                    {data.decision?.decision || 'N/A'}
                                                </span>
                                            )}
                                        </div>
                                        {data.error ? (
                                            <p className="text-xs text-red-400">{data.error}</p>
                                        ) : (
                                            <div className="space-y-1 text-[10px] font-mono text-gray-500">
                                                <div className="flex justify-between"><span>Price</span><span className="text-white">${Number(data.price || 0).toLocaleString()}</span></div>
                                                <div className="flex justify-between"><span>Confidence</span><span className="text-yellow-400">{data.decision?.confidence ?? 0}%</span></div>
                                                <div className="flex justify-between"><span>Signal</span><span className="text-cyan-400">{data.features_summary?.overall_bias || 'N/A'}</span></div>
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </GlassCard>
                    )}
                </div>
            )}

            {/* ━━━━━━━━━━━━━  MICROSTRUCTURE TAB  ━━━━━━━━━━━━━ */}
            {activeTab === 'micro' && (
                <div className="space-y-6">
                    {/* Symbol Selector */}
                    <div className="flex gap-2 mb-4">
                        {SYMBOLS.map(s => (
                            <button key={s} onClick={() => setSelectedSymbol(s)}
                                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${selectedSymbol === s
                                    ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                                    : 'bg-gray-800/50 text-gray-500 hover:text-gray-300 border border-gray-700/50'
                                    }`}>
                                {s}
                            </button>
                        ))}
                        <button onClick={() => fetchMicroData(selectedSymbol)} disabled={loading.micro}
                            className="ml-auto p-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white transition border border-gray-700">
                            <RefreshCw size={14} className={loading.micro ? 'animate-spin' : ''} />
                        </button>
                    </div>

                    {loading.micro ? (
                        <div className="text-center py-20 animate-pulse">
                            <Eye size={40} className="text-cyan-400 mx-auto mb-3" />
                            <p className="text-cyan-400 font-bold">Fetching Microstructure Data...</p>
                            <p className="text-gray-600 text-xs mt-1">aggTrades • Funding • OI • L/S Ratio • Taker Vol</p>
                        </div>
                    ) : microData ? (
                        <div className="space-y-6">
                            {/* Row 1: Delta Volume + Funding Rate */}
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                {/* 1. DELTA VOLUME */}
                                <GlassCard glow="hover:shadow-[0_0_25px_rgba(34,211,238,0.08)]">
                                    <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-cyan-400 mb-4 flex items-center gap-2">
                                        <BarChart2 size={14} /> Trade Delta (Buy vs Sell)
                                    </h3>
                                    {(() => {
                                        const agg = microData.agg_trades || {};
                                        const buyVol = agg.buy_volume || 0;
                                        const sellVol = agg.sell_volume || 0;
                                        const total = buyVol + sellVol;
                                        const buyPct = total > 0 ? (buyVol / total * 100) : 50;
                                        const delta = agg.delta || 0;
                                        return (
                                            <div className="space-y-4">
                                                {/* Buy/Sell Bar */}
                                                <div>
                                                    <div className="flex justify-between text-[10px] mb-1">
                                                        <span className="text-green-400 font-bold">BUY {buyPct.toFixed(1)}%</span>
                                                        <span className="text-red-400 font-bold">SELL {(100 - buyPct).toFixed(1)}%</span>
                                                    </div>
                                                    <div className="w-full h-4 bg-red-500/30 rounded-full overflow-hidden flex">
                                                        <div className="h-full bg-gradient-to-r from-green-500 to-green-400 rounded-l-full transition-all duration-700"
                                                            style={{ width: `${buyPct}%` }} />
                                                    </div>
                                                </div>
                                                {/* Delta Value */}
                                                <div className="text-center py-3 bg-black/30 rounded-xl border border-gray-800/50">
                                                    <div className="text-[10px] text-gray-500 uppercase font-bold mb-1">Net Delta</div>
                                                    <div className={`text-2xl font-black font-mono ${delta >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                        {delta >= 0 ? '+' : ''}${Math.abs(delta).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                                                    </div>
                                                    <div className="text-[9px] text-gray-600 mt-1">({agg.delta_pct || 0}% imbalance)</div>
                                                </div>
                                                {/* Stats */}
                                                <div className="grid grid-cols-3 gap-2">
                                                    <StatPill label="Trades" value={agg.total_trades || 0} color="text-white" />
                                                    <StatPill label="Large" value={agg.large_trades || 0} color="text-yellow-400" />
                                                    <StatPill label="Avg Size" value={`$${(agg.avg_trade_size || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`} color="text-cyan-400" />
                                                </div>
                                            </div>
                                        );
                                    })()}
                                </GlassCard>

                                {/* 2. FUNDING RATE */}
                                <GlassCard glow="hover:shadow-[0_0_25px_rgba(236,72,153,0.08)]">
                                    <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-pink-400 mb-4 flex items-center gap-2">
                                        <TrendingUp size={14} /> Funding Rate
                                    </h3>
                                    {(() => {
                                        const fund = microData.funding || {};
                                        const rates = fund.rates_history || [];
                                        const current = fund.current_rate || 0;
                                        const annualized = fund.annualized_pct || 0;
                                        const maxRate = Math.max(...rates.map(Math.abs), 0.0001);
                                        return (
                                            <div className="space-y-4">
                                                {/* Current + Annualized */}
                                                <div className="grid grid-cols-2 gap-3">
                                                    <div className="text-center py-3 bg-black/30 rounded-xl border border-gray-800/50">
                                                        <div className="text-[10px] text-gray-500 uppercase font-bold mb-1">Current</div>
                                                        <div className={`text-xl font-black font-mono ${current >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                            {(current * 100).toFixed(4)}%
                                                        </div>
                                                    </div>
                                                    <div className="text-center py-3 bg-black/30 rounded-xl border border-gray-800/50">
                                                        <div className="text-[10px] text-gray-500 uppercase font-bold mb-1">Annualized</div>
                                                        <div className={`text-xl font-black font-mono ${annualized >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                            {annualized.toFixed(1)}%
                                                        </div>
                                                    </div>
                                                </div>
                                                {/* Sparkline */}
                                                {rates.length > 0 && (
                                                    <div className="bg-black/20 rounded-xl p-3 border border-gray-800/30">
                                                        <div className="text-[9px] text-gray-600 uppercase font-bold mb-2">Rate History</div>
                                                        <div className="flex items-end gap-[2px] h-16">
                                                            {rates.slice(-20).map((r, i) => {
                                                                const height = Math.max(Math.abs(r) / maxRate * 100, 5);
                                                                return (
                                                                    <div key={i} className="flex-1 flex flex-col justify-end items-center">
                                                                        <div className={`w-full rounded-sm transition-all ${r >= 0 ? 'bg-green-500/70' : 'bg-red-500/70'}`}
                                                                            style={{ height: `${height}%` }}
                                                                            title={`${(r * 100).toFixed(4)}%`} />
                                                                    </div>
                                                                );
                                                            })}
                                                        </div>
                                                        <div className="flex justify-between text-[8px] text-gray-600 mt-1">
                                                            <span>oldest</span><span>latest</span>
                                                        </div>
                                                    </div>
                                                )}
                                                {/* Trend Badge */}
                                                <div className="text-center">
                                                    <span className={`inline-block text-[10px] px-3 py-1 rounded-full font-bold border ${fund.trend === 'POSITIVE' ? 'bg-green-500/10 border-green-500/30 text-green-400' :
                                                            fund.trend === 'NEGATIVE' ? 'bg-red-500/10 border-red-500/30 text-red-400' :
                                                                'bg-gray-700/50 border-gray-600 text-gray-400'
                                                        }`}>
                                                        {fund.trend === 'POSITIVE' ? '📈 Longs Pay Shorts (Crowded Longs)' :
                                                            fund.trend === 'NEGATIVE' ? '📉 Shorts Pay Longs (Crowded Shorts)' :
                                                                '⚖️ Neutral Funding'}
                                                    </span>
                                                </div>
                                            </div>
                                        );
                                    })()}
                                </GlassCard>
                            </div>

                            {/* Row 2: Open Interest + L/S Ratio */}
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                {/* 3. OPEN INTEREST */}
                                <GlassCard glow="hover:shadow-[0_0_25px_rgba(168,85,247,0.08)]">
                                    <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-purple-400 mb-4 flex items-center gap-2">
                                        <Activity size={14} /> Open Interest
                                    </h3>
                                    {(() => {
                                        const oi = microData.open_interest || {};
                                        const history = oi.oi_history || [];
                                        const maxOI = history.length > 0 ? Math.max(...history.map(h => h.oi_value || 0)) : 1;
                                        return (
                                            <div className="space-y-4">
                                                <div className="grid grid-cols-2 gap-3">
                                                    <div className="text-center py-3 bg-black/30 rounded-xl border border-gray-800/50">
                                                        <div className="text-[10px] text-gray-500 uppercase font-bold mb-1">Current OI</div>
                                                        <div className="text-lg font-black font-mono text-white">
                                                            {(oi.current_oi || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}
                                                        </div>
                                                    </div>
                                                    <div className="text-center py-3 bg-black/30 rounded-xl border border-gray-800/50">
                                                        <div className="text-[10px] text-gray-500 uppercase font-bold mb-1">OI Value</div>
                                                        <div className="text-lg font-black font-mono text-purple-400">
                                                            ${(oi.current_oi_value || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                                                        </div>
                                                    </div>
                                                </div>
                                                {/* OI History Bars */}
                                                {history.length > 0 && (
                                                    <div className="bg-black/20 rounded-xl p-3 border border-gray-800/30">
                                                        <div className="text-[9px] text-gray-600 uppercase font-bold mb-2">OI History (Value)</div>
                                                        <div className="flex items-end gap-1 h-20">
                                                            {history.map((h, i) => {
                                                                const height = maxOI > 0 ? ((h.oi_value || 0) / maxOI * 100) : 10;
                                                                return (
                                                                    <div key={i} className="flex-1 bg-purple-500/50 hover:bg-purple-400/70 rounded-t transition-all cursor-default"
                                                                        style={{ height: `${Math.max(height, 3)}%` }}
                                                                        title={`$${(h.oi_value || 0).toLocaleString()}`} />
                                                                );
                                                            })}
                                                        </div>
                                                    </div>
                                                )}
                                                <div className="grid grid-cols-2 gap-3">
                                                    <StatPill label="Change" value={`${oi.change_pct >= 0 ? '+' : ''}${oi.change_pct || 0}%`}
                                                        color={(oi.change_pct || 0) >= 0 ? 'text-green-400' : 'text-red-400'} />
                                                    <StatPill label="Trend" value={oi.trend || 'UNKNOWN'}
                                                        color={oi.trend === 'INCREASING' ? 'text-green-400' : oi.trend === 'DECREASING' ? 'text-red-400' : 'text-gray-400'} />
                                                </div>
                                            </div>
                                        );
                                    })()}
                                </GlassCard>

                                {/* 4. LONG/SHORT RATIO GAUGE */}
                                <GlassCard glow="hover:shadow-[0_0_25px_rgba(234,179,8,0.08)]">
                                    <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-yellow-400 mb-4 flex items-center gap-2">
                                        <Target size={14} /> Long/Short Ratio
                                    </h3>
                                    {(() => {
                                        const ls = microData.long_short_ratio || {};
                                        const longPct = ((ls.long_ratio || 0.5) * 100);
                                        const shortPct = ((ls.short_ratio || 0.5) * 100);
                                        return (
                                            <div className="space-y-4">
                                                {/* Arc Gauge Visual */}
                                                <div className="flex justify-center py-2">
                                                    <svg width="200" height="120" viewBox="0 0 200 120">
                                                        {/* Background arc */}
                                                        <path d="M 20 110 A 80 80 0 0 1 180 110" fill="none" stroke="#1f2937" strokeWidth="12" strokeLinecap="round" />
                                                        {/* Long portion (green, from left) */}
                                                        <path d="M 20 110 A 80 80 0 0 1 180 110" fill="none" stroke="url(#lsGrad)" strokeWidth="12" strokeLinecap="round"
                                                            strokeDasharray={`${longPct * 2.51} 251`} />
                                                        {/* Needle */}
                                                        {(() => {
                                                            const angle = -180 + (longPct / 100) * 180;
                                                            const rad = angle * Math.PI / 180;
                                                            const nx = 100 + Math.cos(rad) * 55;
                                                            const ny = 110 + Math.sin(rad) * 55;
                                                            return <circle cx={nx} cy={ny} r="4" fill="#fbbf24" className="drop-shadow-[0_0_6px_rgba(251,191,36,0.6)]" />;
                                                        })()}
                                                        <defs>
                                                            <linearGradient id="lsGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                                                                <stop offset="0%" stopColor="#22c55e" />
                                                                <stop offset="100%" stopColor="#ef4444" />
                                                            </linearGradient>
                                                        </defs>
                                                        {/* Labels */}
                                                        <text x="20" y="118" fill="#22c55e" fontSize="9" fontWeight="bold">LONG</text>
                                                        <text x="160" y="118" fill="#ef4444" fontSize="9" fontWeight="bold">SHORT</text>
                                                        <text x="100" y="95" fill="white" fontSize="16" fontWeight="900" textAnchor="middle" fontFamily="monospace">
                                                            {(ls.long_short_ratio || 1).toFixed(2)}
                                                        </text>
                                                        <text x="100" y="108" fill="#6b7280" fontSize="8" textAnchor="middle">L/S RATIO</text>
                                                    </svg>
                                                </div>
                                                {/* Percentages */}
                                                <div className="grid grid-cols-2 gap-3">
                                                    <StatPill label="Long Acct" value={`${longPct.toFixed(1)}%`} color="text-green-400" icon={ArrowUpRight} />
                                                    <StatPill label="Short Acct" value={`${shortPct.toFixed(1)}%`} color="text-red-400" icon={ArrowDownRight} />
                                                </div>
                                                {/* Bias Badge */}
                                                <div className="text-center">
                                                    <span className={`inline-block text-[10px] px-3 py-1 rounded-full font-bold border ${ls.bias === 'LONG_CROWDED' ? 'bg-green-500/10 border-green-500/30 text-green-400' :
                                                            ls.bias === 'SHORT_CROWDED' ? 'bg-red-500/10 border-red-500/30 text-red-400' :
                                                                'bg-gray-700/50 border-gray-600 text-gray-400'
                                                        }`}>
                                                        {ls.bias === 'LONG_CROWDED' ? '⚠️ Long Crowded — Contrarian Short Bias' :
                                                            ls.bias === 'SHORT_CROWDED' ? '⚠️ Short Crowded — Contrarian Long Bias' :
                                                                '⚖️ Balanced — No Extreme'}
                                                    </span>
                                                </div>
                                            </div>
                                        );
                                    })()}
                                </GlassCard>
                            </div>

                            {/* Row 3: Taker Volume (Full Width) */}
                            <GlassCard glow="hover:shadow-[0_0_25px_rgba(34,197,94,0.08)]">
                                <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-green-400 mb-4 flex items-center gap-2">
                                    <Zap size={14} /> Taker Buy/Sell Volume
                                </h3>
                                {(() => {
                                    const tv = microData.taker_volume || {};
                                    const buyVol = tv.buy_vol || 0;
                                    const sellVol = tv.sell_vol || 0;
                                    const total = buyVol + sellVol;
                                    const history = tv.history || [];
                                    const maxHist = history.length > 0 ? Math.max(...history.map(h => Math.max(h.buy_vol || 0, h.sell_vol || 0))) : 1;
                                    return (
                                        <div className="space-y-4">
                                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                                                {/* Current Summary */}
                                                <div className="space-y-3">
                                                    <StatPill label="Buy/Sell Ratio" value={(tv.buy_sell_ratio || 1).toFixed(3)}
                                                        color={(tv.buy_sell_ratio || 1) > 1.05 ? 'text-green-400' : (tv.buy_sell_ratio || 1) < 0.95 ? 'text-red-400' : 'text-gray-400'} />
                                                    <StatPill label="Imbalance" value={`${((tv.imbalance || 0) * 100).toFixed(2)}%`}
                                                        color={(tv.imbalance || 0) > 0 ? 'text-green-400' : 'text-red-400'} />
                                                    <div className="text-center">
                                                        <span className={`inline-block text-[10px] px-3 py-1 rounded-full font-bold border ${tv.aggression === 'BUYERS_AGGRESSIVE' ? 'bg-green-500/10 border-green-500/30 text-green-400' :
                                                                tv.aggression === 'SELLERS_AGGRESSIVE' ? 'bg-red-500/10 border-red-500/30 text-red-400' :
                                                                    'bg-gray-700/50 border-gray-600 text-gray-400'
                                                            }`}>{tv.aggression || 'BALANCED'}</span>
                                                    </div>
                                                </div>
                                                {/* Buy vs Sell Comparison */}
                                                <div className="bg-black/20 rounded-xl p-4 border border-gray-800/30">
                                                    <div className="text-[9px] text-gray-600 uppercase font-bold mb-3">Volume Comparison</div>
                                                    <div className="space-y-3">
                                                        <div>
                                                            <div className="flex justify-between text-[10px] mb-1">
                                                                <span className="text-green-400 font-bold">Buy Vol</span>
                                                                <span className="text-white font-mono">${buyVol.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                                                            </div>
                                                            <div className="w-full h-3 bg-gray-800 rounded-full overflow-hidden">
                                                                <div className="h-full bg-gradient-to-r from-green-600 to-green-400 rounded-full transition-all duration-500"
                                                                    style={{ width: `${total > 0 ? buyVol / total * 100 : 50}%` }} />
                                                            </div>
                                                        </div>
                                                        <div>
                                                            <div className="flex justify-between text-[10px] mb-1">
                                                                <span className="text-red-400 font-bold">Sell Vol</span>
                                                                <span className="text-white font-mono">${sellVol.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                                                            </div>
                                                            <div className="w-full h-3 bg-gray-800 rounded-full overflow-hidden">
                                                                <div className="h-full bg-gradient-to-r from-red-600 to-red-400 rounded-full transition-all duration-500"
                                                                    style={{ width: `${total > 0 ? sellVol / total * 100 : 50}%` }} />
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                                {/* Taker History */}
                                                {history.length > 0 && (
                                                    <div className="bg-black/20 rounded-xl p-4 border border-gray-800/30">
                                                        <div className="text-[9px] text-gray-600 uppercase font-bold mb-2">Taker History (Buy=Green / Sell=Red)</div>
                                                        <div className="flex items-end gap-[3px] h-20">
                                                            {history.map((h, i) => {
                                                                const bH = maxHist > 0 ? ((h.buy_vol || 0) / maxHist * 100) : 5;
                                                                const sH = maxHist > 0 ? ((h.sell_vol || 0) / maxHist * 100) : 5;
                                                                return (
                                                                    <div key={i} className="flex-1 flex gap-[1px] items-end">
                                                                        <div className="flex-1 bg-green-500/50 rounded-t" style={{ height: `${Math.max(bH, 3)}%` }} />
                                                                        <div className="flex-1 bg-red-500/50 rounded-t" style={{ height: `${Math.max(sH, 3)}%` }} />
                                                                    </div>
                                                                );
                                                            })}
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    );
                                })()}
                            </GlassCard>
                        </div>
                    ) : (
                        <div className="text-center py-20 text-gray-600">
                            <Eye size={40} className="mx-auto mb-3 opacity-30" />
                            <p>Select a symbol to view microstructure data</p>
                            <p className="text-[10px] mt-1 text-gray-700">Requires VPN if Binance Futures API is blocked in your region</p>
                        </div>
                    )}
                </div>
            )}

            {/* ━━━━━━━━━━━━━  FEATURES TAB  ━━━━━━━━━━━━━ */}
            {activeTab === 'features' && (
                <div className="space-y-6">
                    <div className="flex gap-2 mb-4">
                        {SYMBOLS.map(s => (
                            <button key={s} onClick={() => setSelectedSymbol(s)}
                                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${selectedSymbol === s
                                    ? 'bg-pink-500/20 text-pink-400 border border-pink-500/30'
                                    : 'bg-gray-800/50 text-gray-500 hover:text-gray-300 border border-gray-700/50'
                                    }`}>
                                {s}
                            </button>
                        ))}
                    </div>

                    {loading.features ? (
                        <div className="text-center py-20 animate-pulse">
                            <Brain size={40} className="text-pink-400 mx-auto mb-3" />
                            <p className="text-pink-400 font-bold">Computing Alpha Features...</p>
                        </div>
                    ) : features ? (
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            {/* Features Grid */}
                            <GlassCard>
                                <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-cyan-400 mb-4 flex items-center gap-2">
                                    <BarChart2 size={14} /> Feature Z-Scores
                                </h3>
                                <div className="space-y-3">
                                    {features.z_scores && Object.entries(features.z_scores).map(([key, val]) => {
                                        const numVal = Number(val) || 0;
                                        const pct = Math.min(Math.max((numVal + 3) / 6 * 100, 0), 100);
                                        return (
                                            <div key={key} className="space-y-1">
                                                <div className="flex justify-between text-[10px] uppercase">
                                                    <span className="text-gray-400 font-bold tracking-wider">{key.replace(/_/g, ' ')}</span>
                                                    <span className={`font-mono font-bold ${numVal > 1 ? 'text-green-400' : numVal < -1 ? 'text-red-400' : 'text-gray-400'}`}>
                                                        {numVal.toFixed(2)}
                                                    </span>
                                                </div>
                                                <div className="w-full bg-gray-800 rounded-full h-1.5">
                                                    <div className={`h-1.5 rounded-full transition-all duration-500 ${numVal > 1 ? 'bg-green-500' : numVal < -1 ? 'bg-red-500' : 'bg-gray-600'
                                                        }`} style={{ width: `${pct}%` }} />
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </GlassCard>

                            {/* Signal Summary */}
                            <GlassCard>
                                <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-purple-400 mb-4 flex items-center gap-2">
                                    <Zap size={14} /> Signal Synthesis
                                </h3>
                                {features.signals && (
                                    <div className="space-y-4">
                                        <div className="text-center py-6 bg-black/30 rounded-xl border border-gray-800/50">
                                            <div className={`text-4xl font-black mb-2 ${features.signals.overall_bias === 'BULLISH' ? 'text-green-400' :
                                                features.signals.overall_bias === 'BEARISH' ? 'text-red-400' : 'text-gray-400'
                                                }`}>
                                                {features.signals.overall_bias === 'BULLISH' ? <ArrowUpRight size={40} className="mx-auto" /> :
                                                    features.signals.overall_bias === 'BEARISH' ? <ArrowDownRight size={40} className="mx-auto" /> :
                                                        <Minus size={40} className="mx-auto" />}
                                                {features.signals.overall_bias || 'NEUTRAL'}
                                            </div>
                                            <div className="text-sm text-gray-400">
                                                Confidence: <span className="text-white font-bold">{features.signals.confidence_score?.toFixed(1) ?? 0}%</span>
                                            </div>
                                        </div>

                                        <div className="grid grid-cols-2 gap-3">
                                            <StatPill label="Bullish" value={features.signals.bullish_count ?? 0} color="text-green-400" icon={ArrowUpRight} />
                                            <StatPill label="Bearish" value={features.signals.bearish_count ?? 0} color="text-red-400" icon={ArrowDownRight} />
                                        </div>

                                        {/* Raw Features */}
                                        {features.features && (
                                            <div className="bg-black/20 rounded-xl p-4 border border-gray-800/30">
                                                <div className="text-[9px] text-gray-600 uppercase font-bold mb-2">Raw Feature Values</div>
                                                <div className="space-y-1">
                                                    {Object.entries(features.features).map(([k, v]) => (
                                                        <div key={k} className="flex justify-between text-[10px] font-mono">
                                                            <span className="text-gray-500">{k.replace(/_/g, ' ')}</span>
                                                            <span className="text-white">{typeof v === 'number' ? v.toFixed(4) : String(v)}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </GlassCard>
                        </div>
                    ) : (
                        <div className="text-center py-20 text-gray-600">
                            <BarChart2 size={40} className="mx-auto mb-3 opacity-30" />
                            <p>Select a symbol to view alpha features</p>
                        </div>
                    )}
                </div>
            )}

            {/* ━━━━━━━━━━━━━  DECISIONS TAB  ━━━━━━━━━━━━━ */}
            {activeTab === 'decisions' && (
                <div className="space-y-6">
                    <GlassCard>
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-purple-400 flex items-center gap-2">
                                <Target size={14} /> AI Decision History
                            </h3>
                            <button onClick={fetchDecisions}
                                className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white transition border border-gray-700">
                                <RefreshCw size={12} />
                            </button>
                        </div>

                        {decisions.length === 0 ? (
                            <div className="text-center py-12 text-gray-600">
                                <Target size={32} className="mx-auto mb-2 opacity-30" />
                                <p className="text-sm">No decisions yet. Run the AI or start the paper trader.</p>
                            </div>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="w-full text-xs">
                                    <thead>
                                        <tr className="text-gray-500 border-b border-gray-800">
                                            <th className="text-left py-2 px-3 font-bold uppercase tracking-wider">Time</th>
                                            <th className="text-left py-2 px-3 font-bold uppercase tracking-wider">Symbol</th>
                                            <th className="text-center py-2 px-3 font-bold uppercase tracking-wider">Decision</th>
                                            <th className="text-center py-2 px-3 font-bold uppercase tracking-wider">Confidence</th>
                                            <th className="text-right py-2 px-3 font-bold uppercase tracking-wider">Entry</th>
                                            <th className="text-right py-2 px-3 font-bold uppercase tracking-wider">SL</th>
                                            <th className="text-right py-2 px-3 font-bold uppercase tracking-wider">TP</th>
                                            <th className="text-center py-2 px-3 font-bold uppercase tracking-wider">Mode</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {decisions.map((d, i) => (
                                            <tr key={i} className="border-b border-gray-800/50 hover:bg-white/[0.02] transition">
                                                <td className="py-2 px-3 text-gray-500 font-mono">{d.timestamp?.split('T')[1]?.substring(0, 8) || '—'}</td>
                                                <td className="py-2 px-3 text-white font-bold">{d.symbol}</td>
                                                <td className="py-2 px-3 text-center">
                                                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${d.decision === 'LONG' ? 'bg-green-500/20 text-green-400' :
                                                        d.decision === 'SHORT' ? 'bg-red-500/20 text-red-400' :
                                                            'bg-gray-700 text-gray-400'
                                                        }`}>{d.decision}</span>
                                                </td>
                                                <td className="py-2 px-3 text-center font-mono text-yellow-400">{d.confidence}%</td>
                                                <td className="py-2 px-3 text-right font-mono text-white">${Number(d.entry_price || 0).toLocaleString()}</td>
                                                <td className="py-2 px-3 text-right font-mono text-red-400">${Number(d.stop_loss || 0).toLocaleString()}</td>
                                                <td className="py-2 px-3 text-right font-mono text-green-400">${Number(d.take_profit || 0).toLocaleString()}</td>
                                                <td className="py-2 px-3 text-center">
                                                    <span className={`text-[9px] px-1.5 py-0.5 rounded border ${d.mode === 'live' ? 'bg-green-900/30 border-green-500/30 text-green-400' : 'bg-gray-800 border-gray-700 text-gray-500'
                                                        }`}>{d.mode}</span>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </GlassCard>
                </div>
            )}

            {/* ━━━━━━━━━━━━━  VALIDATION TAB  ━━━━━━━━━━━━━ */}
            {activeTab === 'validation' && (
                <div className="space-y-6">
                    <div className="flex justify-between items-center">
                        <h3 className="text-lg font-bold text-white flex items-center gap-2">
                            <Shield size={18} className="text-purple-400" /> Statistical Validation
                        </h3>
                        <button onClick={handleRunValidation} disabled={loading.validation}
                            className="bg-purple-600/20 hover:bg-purple-600/30 text-purple-400 border border-purple-500/30 px-4 py-2 rounded-lg text-xs font-bold flex items-center gap-2 transition disabled:opacity-50">
                            {loading.validation ? <RefreshCw size={14} className="animate-spin" /> : <Shield size={14} />}
                            RUN VALIDATION
                        </button>
                    </div>

                    {validationReport ? (
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            {/* Walk-Forward */}
                            <GlassCard>
                                <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-cyan-400 mb-4 flex items-center gap-2">
                                    <TrendingUp size={14} /> Walk-Forward Analysis
                                </h3>
                                {validationReport.walk_forward ? (
                                    <div className="space-y-3">
                                        <div className="text-center py-4 bg-black/30 rounded-xl border border-gray-800/50">
                                            <div className={`text-xl font-black ${validationReport.walk_forward.is_valid ? 'text-green-400' : 'text-red-400'}`}>
                                                {validationReport.walk_forward.verdict || 'N/A'}
                                            </div>
                                            <div className="text-[10px] text-gray-500 mt-1">
                                                Split: {validationReport.walk_forward.split || '—'}
                                            </div>
                                        </div>
                                        {validationReport.walk_forward.in_sample && (
                                            <div className="grid grid-cols-2 gap-3">
                                                <StatPill label="IS Profit Factor" value={validationReport.walk_forward.in_sample.profit_factor || '—'} color="text-cyan-400" />
                                                <StatPill label="OOS Profit Factor" value={validationReport.walk_forward.out_of_sample?.profit_factor || '—'} color="text-purple-400" />
                                                <StatPill label="IS Win Rate" value={`${validationReport.walk_forward.in_sample.win_rate || 0}%`} color="text-green-400" />
                                                <StatPill label="Degradation" value={`${validationReport.walk_forward.degradation_pct || 0}%`}
                                                    color={(validationReport.walk_forward.degradation_pct || 0) < 50 ? 'text-green-400' : 'text-red-400'} />
                                            </div>
                                        )}
                                    </div>
                                ) : (
                                    <div className="text-center py-8 text-gray-600 text-sm">
                                        {validationReport.message || 'Not enough data yet'}
                                    </div>
                                )}
                            </GlassCard>

                            {/* Monte Carlo */}
                            <GlassCard>
                                <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-pink-400 mb-4 flex items-center gap-2">
                                    <Activity size={14} /> Monte Carlo Simulation
                                </h3>
                                {validationReport.monte_carlo ? (
                                    <div className="space-y-3">
                                        <div className="text-center py-4 bg-black/30 rounded-xl border border-gray-800/50">
                                            <div className={`text-xl font-black ${validationReport.monte_carlo.is_valid ? 'text-green-400' : 'text-red-400'}`}>
                                                {validationReport.monte_carlo.verdict || 'N/A'}
                                            </div>
                                            <div className="text-[10px] text-gray-500 mt-1">
                                                {validationReport.monte_carlo.iterations || 0} iterations
                                            </div>
                                        </div>
                                        <div className="grid grid-cols-2 gap-3">
                                            <StatPill label="Profit Prob" value={`${validationReport.monte_carlo.probability_profit || 0}%`}
                                                color={(validationReport.monte_carlo.probability_profit || 0) >= 60 ? 'text-green-400' : 'text-red-400'} />
                                            <StatPill label="Median PnL" value={`$${validationReport.monte_carlo.median_pnl || 0}`}
                                                color={(validationReport.monte_carlo.median_pnl || 0) > 0 ? 'text-green-400' : 'text-red-400'} />
                                            <StatPill label="P5" value={`$${validationReport.monte_carlo.percentile_5 || 0}`} color="text-red-400" />
                                            <StatPill label="P95" value={`$${validationReport.monte_carlo.percentile_95 || 0}`} color="text-green-400" />
                                        </div>
                                    </div>
                                ) : (
                                    <div className="text-center py-8 text-gray-600 text-sm">
                                        {validationReport.message || 'Not enough data yet'}
                                    </div>
                                )}
                            </GlassCard>

                            {/* Overall Verdict */}
                            {validationReport.overall_verdict && (
                                <GlassCard className="lg:col-span-2">
                                    <div className="text-center py-4">
                                        <div className="text-2xl font-black mb-2">{validationReport.overall_verdict}</div>
                                        <div className="text-xs text-gray-500">
                                            Data Source: {validationReport.data_source || 'N/A'} •
                                            Total Decisions: {validationReport.total_decisions ?? 0} •
                                            Total Trades: {validationReport.total_trades ?? 0}
                                        </div>
                                        {!validationReport.sufficient_data && (
                                            <div className="mt-3 text-[10px] bg-yellow-500/10 border border-yellow-500/30 rounded-lg px-4 py-2 text-yellow-400 inline-block">
                                                <AlertTriangle size={12} className="inline mr-1" />
                                                Need 200+ decisions for full statistical significance
                                            </div>
                                        )}
                                    </div>
                                </GlassCard>
                            )}
                        </div>
                    ) : (
                        <GlassCard>
                            <div className="text-center py-16 text-gray-600">
                                <Shield size={48} className="mx-auto mb-4 opacity-20" />
                                <p className="text-lg font-bold mb-2">No Validation Report Yet</p>
                                <p className="text-sm">Run validation to analyze your AI trading edge using walk-forward and Monte Carlo methods.</p>
                            </div>
                        </GlassCard>
                    )}
                </div>
            )}
        </div>
    );
};

export default AIDashboard;
