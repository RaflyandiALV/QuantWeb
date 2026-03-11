import React, { useState, useCallback } from 'react';
import { Radar, Activity, Zap, Search, RefreshCw, AlertTriangle, TrendingUp, TrendingDown, BarChart3, Clock, Loader2, CheckCircle2, XCircle } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

// Anomaly type config
const ANOMALY_TYPES = [
    { id: 'volume_spike', label: 'Volume Spike', icon: BarChart3, color: '#22d3ee', desc: 'Volume > 2x 20-period SMA' },
    { id: 'order_book_imbalance', label: 'Order Book Imbalance', icon: Activity, desc: 'Bids > 1.5x Asks (top 10)' },
    { id: 'whale_activity', label: 'Whale Activity', icon: Zap, desc: 'Large trades above dynamic threshold' },
];

const QUICK_SYMBOLS = ['BTC-USDT', 'ETH-USDT', 'SOL-USDT', 'BNB-USDT', 'XRP-USDT', 'DOGE-USDT', 'ADA-USDT', 'AVAX-USDT'];

const SeverityGauge = ({ score }) => {
    const color = score >= 70 ? '#ef4444' : score >= 40 ? '#f59e0b' : '#22c55e';
    const label = score >= 70 ? 'HIGH' : score >= 40 ? 'MEDIUM' : 'LOW';
    const circumference = 2 * Math.PI * 36;
    const offset = circumference - (score / 100) * circumference;

    return (
        <div className="flex flex-col items-center">
            <svg width="90" height="90" viewBox="0 0 90 90">
                <circle cx="45" cy="45" r="36" stroke="#1e293b" strokeWidth="6" fill="none" />
                <circle cx="45" cy="45" r="36" stroke={color} strokeWidth="6" fill="none"
                    strokeDasharray={circumference} strokeDashoffset={offset}
                    strokeLinecap="round" transform="rotate(-90 45 45)"
                    style={{ transition: 'stroke-dashoffset 0.8s ease' }} />
                <text x="45" y="42" textAnchor="middle" fill={color} fontSize="18" fontWeight="900">{score}</text>
                <text x="45" y="56" textAnchor="middle" fill="#94a3b8" fontSize="8" fontWeight="600">{label}</text>
            </svg>
        </div>
    );
};

const AnomalyCard = ({ type, data, detected }) => {
    const config = ANOMALY_TYPES.find(t => t.id === type);
    if (!config) return null;
    const Icon = config.icon;

    return (
        <div className={`relative border rounded-2xl p-5 transition-all ${detected ? 'border-orange-500/50 bg-orange-900/10 shadow-[0_0_20px_rgba(249,115,22,0.1)]' : 'border-gray-800 bg-gray-900/40'}`}>
            {detected && <div className="absolute top-0 right-0 bg-orange-500 text-black text-[9px] font-bold px-2 py-0.5 rounded-bl rounded-tr-xl">DETECTED</div>}
            <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: `${config.color}15`, border: `1px solid ${config.color}30` }}>
                    <Icon size={20} style={{ color: config.color }} />
                </div>
                <div>
                    <div className="font-bold text-white text-sm">{config.label}</div>
                    <div className="text-[10px] text-gray-500">{config.desc}</div>
                </div>
            </div>

            {data ? (
                <div className="space-y-2 text-xs font-mono">
                    {Object.entries(data).map(([key, val]) => (
                        <div key={key} className="flex justify-between items-center border-b border-gray-800/50 pb-1">
                            <span className="text-gray-500 capitalize">{key.replace(/_/g, ' ')}</span>
                            <span className={detected ? 'text-orange-400 font-bold' : 'text-gray-300'}>
                                {typeof val === 'number' ? val.toFixed(4) : String(val)}
                            </span>
                        </div>
                    ))}
                </div>
            ) : (
                <div className="text-center text-gray-600 text-xs italic py-4">No data yet</div>
            )}
        </div>
    );
};

const AnomalyDashboard = () => {
    const [symbol, setSymbol] = useState('BTC-USDT');
    const [scanning, setScanning] = useState(false);
    const [results, setResults] = useState(null);
    const [error, setError] = useState(null);
    const [history, setHistory] = useState([]);
    const [batchScanning, setBatchScanning] = useState(false);
    const [batchResults, setBatchResults] = useState(null);

    const runScan = useCallback(async (sym) => {
        const targetSymbol = sym || symbol;
        setScanning(true);
        setError(null);
        setResults(null);
        try {
            const res = await fetch(`${API_URL}/api/anomaly-scan?symbol=${encodeURIComponent(targetSymbol)}`);
            if (!res.ok) throw new Error(`Scan failed: ${res.status}`);
            const data = await res.json();
            setResults(data);

            // Calculate severity score
            let score = 0;
            if (data.volume_spike?.detected) score += 35;
            if (data.order_book?.detected) score += 35;
            if (data.whale_activity?.detected) score += 30;

            // Add to history
            const entry = {
                symbol: targetSymbol,
                time: new Date().toLocaleTimeString(),
                score,
                anomalies: [
                    data.volume_spike?.detected && 'Volume',
                    data.order_book?.detected && 'OrderBook',
                    data.whale_activity?.detected && 'Whale',
                ].filter(Boolean),
            };
            setHistory(prev => [entry, ...prev.slice(0, 19)]);
        } catch (e) {
            setError(e.message);
        } finally {
            setScanning(false);
        }
    }, [symbol]);

    const runBatchScan = useCallback(async () => {
        setBatchScanning(true);
        setBatchResults(null);
        try {
            const res = await fetch(`${API_URL}/api/batch-anomaly-scan`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symbols: QUICK_SYMBOLS }),
            });
            if (!res.ok) throw new Error(`Batch scan failed: ${res.status}`);
            const data = await res.json();
            setBatchResults(data.results || []);
        } catch (e) {
            setError(e.message);
        } finally {
            setBatchScanning(false);
        }
    }, []);

    const severityScore = results ? (() => {
        let s = 0;
        if (results.volume_spike?.detected) s += 35;
        if (results.order_book?.detected) s += 35;
        if (results.whale_activity?.detected) s += 30;
        return s;
    })() : 0;

    return (
        <div className="space-y-8">
            {/* HEADER */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                        <Radar className="text-orange-500" /> ANOMALY SCANNER
                    </h2>
                    <p className="text-gray-400 text-sm mt-1">Detect volume spikes, order book imbalances, and whale activity in real-time.</p>
                </div>
            </div>

            {/* QUICK SCAN BAR */}
            <div className="bg-gray-900/40 border border-gray-800 rounded-2xl p-6">
                <div className="flex flex-col md:flex-row gap-4 items-end">
                    <div className="flex-1">
                        <label className="text-[10px] text-orange-400/80 font-bold uppercase mb-1 block tracking-wider">Symbol</label>
                        <input
                            type="text"
                            value={symbol}
                            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                            className="neon-input w-full !text-orange-300 !border-gray-700 focus:!border-orange-500"
                            placeholder="BTC-USDT"
                        />
                    </div>
                    <button
                        onClick={() => runScan()}
                        disabled={scanning || !symbol}
                        className="bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-500 hover:to-red-500 text-white px-8 py-2.5 rounded-lg font-bold flex items-center gap-2 transition-all shadow-[0_0_15px_rgba(249,115,22,0.3)] disabled:opacity-50"
                    >
                        {scanning ? <Loader2 size={18} className="animate-spin" /> : <Search size={18} />}
                        {scanning ? 'SCANNING...' : 'SCAN'}
                    </button>
                    <button
                        onClick={runBatchScan}
                        disabled={batchScanning}
                        className="bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white px-6 py-2.5 rounded-lg font-bold flex items-center gap-2 transition-all border border-gray-700 disabled:opacity-50"
                    >
                        {batchScanning ? <Loader2 size={18} className="animate-spin" /> : <RefreshCw size={18} />}
                        BATCH SCAN
                    </button>
                </div>

                {/* Quick symbol buttons */}
                <div className="flex flex-wrap gap-2 mt-4">
                    {QUICK_SYMBOLS.map(s => (
                        <button
                            key={s}
                            onClick={() => { setSymbol(s); runScan(s); }}
                            className={`px-3 py-1 rounded-full text-[11px] font-bold transition-all border ${symbol === s ? 'bg-orange-600/20 border-orange-500/50 text-orange-400' : 'bg-gray-900 border-gray-700 text-gray-500 hover:text-gray-300 hover:border-gray-600'}`}
                        >
                            {s.replace('-USDT', '')}
                        </button>
                    ))}
                </div>
            </div>

            {/* ERROR */}
            {error && (
                <div className="bg-red-900/20 border border-red-500/30 rounded-xl p-4 flex items-center gap-3">
                    <AlertTriangle className="text-red-400" size={18} />
                    <span className="text-red-300 text-sm">{error}</span>
                </div>
            )}

            {/* SCAN RESULTS */}
            {results && (
                <div className="animate-fade-in-up">
                    <div className="flex flex-col lg:flex-row gap-6">
                        {/* Severity Gauge */}
                        <div className="bg-gray-900/40 border border-gray-800 rounded-2xl p-6 flex flex-col items-center justify-center min-w-[160px]">
                            <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-2">Anomaly Score</div>
                            <SeverityGauge score={severityScore} />
                            <div className="text-lg font-bold text-white mt-2">{symbol}</div>
                            <div className="text-[10px] text-gray-500 mt-1">{new Date().toLocaleTimeString()}</div>
                        </div>

                        {/* Anomaly Cards */}
                        <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-4">
                            <AnomalyCard type="volume_spike" data={results.volume_spike?.data} detected={results.volume_spike?.detected} />
                            <AnomalyCard type="order_book_imbalance" data={results.order_book?.data} detected={results.order_book?.detected} />
                            <AnomalyCard type="whale_activity" data={results.whale_activity?.data} detected={results.whale_activity?.detected} />
                        </div>
                    </div>
                </div>
            )}

            {/* BATCH RESULTS */}
            {batchResults && (
                <div className="animate-fade-in-up">
                    <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2"><Activity size={18} className="text-orange-400" /> Batch Scan Results</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        {batchResults.map((item, idx) => {
                            let score = 0;
                            if (item.volume_spike?.detected) score += 35;
                            if (item.order_book?.detected) score += 35;
                            if (item.whale_activity?.detected) score += 30;
                            const hasAnomaly = score > 0;

                            return (
                                <div
                                    key={idx}
                                    onClick={() => { setSymbol(item.symbol); runScan(item.symbol); }}
                                    className={`border rounded-xl p-4 cursor-pointer transition-all hover:scale-[1.02] ${hasAnomaly ? 'border-orange-500/40 bg-orange-900/10' : 'border-gray-800 bg-gray-900/40'}`}
                                >
                                    <div className="flex justify-between items-center mb-2">
                                        <span className="font-bold text-white">{item.symbol}</span>
                                        <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${score >= 70 ? 'bg-red-500/20 text-red-400' : score >= 35 ? 'bg-orange-500/20 text-orange-400' : 'bg-green-500/20 text-green-400'}`}>
                                            {score}
                                        </span>
                                    </div>
                                    <div className="flex gap-2">
                                        {item.volume_spike?.detected && <span className="text-[9px] bg-cyan-900/30 text-cyan-400 px-1.5 py-0.5 rounded">VOL</span>}
                                        {item.order_book?.detected && <span className="text-[9px] bg-blue-900/30 text-blue-400 px-1.5 py-0.5 rounded">OB</span>}
                                        {item.whale_activity?.detected && <span className="text-[9px] bg-purple-900/30 text-purple-400 px-1.5 py-0.5 rounded">WHALE</span>}
                                        {!hasAnomaly && <span className="text-[9px] text-gray-600 italic">Clean</span>}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* HISTORY LOG */}
            {history.length > 0 && (
                <div className="bg-gray-900/40 border border-gray-800 rounded-2xl p-6">
                    <h3 className="text-sm font-bold text-gray-400 mb-3 flex items-center gap-2"><Clock size={14} /> Session History</h3>
                    <div className="space-y-2 max-h-60 overflow-y-auto">
                        {history.map((entry, idx) => (
                            <div key={idx} className="flex items-center gap-3 text-xs bg-black/30 rounded-lg px-3 py-2 border border-gray-800/50">
                                <span className="text-gray-500 w-16 flex-shrink-0">{entry.time}</span>
                                <span className="font-bold text-white w-20 flex-shrink-0">{entry.symbol.replace('-USDT', '')}</span>
                                <div className="flex-1 flex gap-1.5">
                                    {entry.anomalies.length > 0 ? entry.anomalies.map(a => (
                                        <span key={a} className="bg-orange-900/20 text-orange-400 px-1.5 py-0.5 rounded text-[9px] font-bold">{a}</span>
                                    )) : (
                                        <span className="text-gray-600 italic">No anomalies</span>
                                    )}
                                </div>
                                <span className={`font-bold ${entry.score >= 70 ? 'text-red-400' : entry.score >= 35 ? 'text-orange-400' : 'text-green-400'}`}>{entry.score}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default AnomalyDashboard;
