import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ReferenceLine, Cell, ComposedChart, Scatter, Customized
} from 'recharts';
import { Activity, RefreshCw, TrendingUp, TrendingDown, Minus,
  BarChart3, Zap, DollarSign, Users, AlertTriangle, Clock, Search,
  Brain, Shield, Target, ChevronDown, ChevronUp
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const DEFAULT_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'DOGEUSDT'];

const TRADE_FILTERS = [
  { value: 0, label: '>$0' },
  { value: 1000, label: '>$1K' },
  { value: 5000, label: '>$5K' },
  { value: 10000, label: '>$10K' },
  { value: 50000, label: '>$50K' },
  { value: 100000, label: '>$100K' },
];

const TIMEFRAMES = [
  { value: '5m', label: '5m' },
  { value: '15m', label: '15m' },
  { value: '30m', label: '30m' },
  { value: '1h', label: '1H' },
  { value: '4h', label: '4H' },
  { value: '1d', label: '1D' },
];

/* ═══════ TOOLTIP ═══════ */
const ChartTooltip = ({ active, payload, label, formatter }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'rgba(15, 23, 42, 0.95)', border: '1px solid rgba(100, 116, 139, 0.3)',
      borderRadius: 8, padding: '10px 14px', backdropFilter: 'blur(12px)',
      boxShadow: '0 8px 32px rgba(0,0,0,0.4)', zIndex: 999,
    }}>
      <p style={{ color: '#94a3b8', fontSize: 11, margin: 0, marginBottom: 4 }}>{label}</p>
      {payload.filter(e => e.value !== undefined && e.value !== null).map((entry, i) => (
        <p key={i} style={{ color: entry.color || '#e2e8f0', fontSize: 13, margin: '2px 0', fontWeight: 600 }}>
          {entry.name}: {formatter ? formatter(entry.value, entry.name) : typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}
        </p>
      ))}
    </div>
  );
};

/* ═══════ STAT CARD ═══════ */
const StatCard = ({ icon: Icon, label, value, subValue, trend, color }) => {
  const trendColor = trend === 'up' ? '#22c55e' : trend === 'down' ? '#ef4444' : '#64748b';
  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;
  return (
    <div style={{
      background: 'rgba(30, 41, 59, 0.6)', border: '1px solid rgba(100, 116, 139, 0.2)',
      borderRadius: 12, padding: '16px 20px', borderLeft: `3px solid ${color || '#6366f1'}`,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Icon size={16} style={{ color: color || '#6366f1' }} />
          <span style={{ color: '#94a3b8', fontSize: 12, textTransform: 'uppercase', letterSpacing: 1, fontWeight: 600 }}>{label}</span>
        </div>
        <TrendIcon size={14} style={{ color: trendColor }} />
      </div>
      <div style={{ fontSize: 22, fontWeight: 700, color: color || '#e2e8f0', marginBottom: 2 }}>{value}</div>
      {subValue && <div style={{ fontSize: 12, color: '#64748b' }}>{subValue}</div>}
    </div>
  );
};

/* ═══════ SENTIMENT BADGE ═══════ */
const SentimentBadge = ({ label, sentiment }) => {
  const config = {
    'BULLISH': { bg: 'rgba(34, 197, 94, 0.15)', color: '#22c55e', border: 'rgba(34, 197, 94, 0.3)' },
    'BEARISH': { bg: 'rgba(239, 68, 68, 0.15)', color: '#ef4444', border: 'rgba(239, 68, 68, 0.3)' },
    'NEUTRAL': { bg: 'rgba(100, 116, 139, 0.15)', color: '#94a3b8', border: 'rgba(100, 116, 139, 0.3)' },
    'LONG_CROWDED': { bg: 'rgba(234, 179, 8, 0.15)', color: '#eab308', border: 'rgba(234, 179, 8, 0.3)' },
    'SHORT_CROWDED': { bg: 'rgba(168, 85, 247, 0.15)', color: '#a855f7', border: 'rgba(168, 85, 247, 0.3)' },
    'BALANCED': { bg: 'rgba(59, 130, 246, 0.15)', color: '#3b82f6', border: 'rgba(59, 130, 246, 0.3)' },
  };
  const c = config[sentiment] || config['NEUTRAL'];
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: '6px 14px', borderRadius: 20,
      background: c.bg, border: `1px solid ${c.border}`,
    }}>
      <div style={{ width: 7, height: 7, borderRadius: '50%', background: c.color }} />
      <span style={{ color: c.color, fontSize: 12, fontWeight: 700, letterSpacing: 0.5 }}>{label || sentiment}</span>
    </div>
  );
};

/* ═══════ SECTION HEADER ═══════ */
const SectionHeader = ({ icon: Icon, title, subtitle, badge }) => (
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      {Icon && <Icon size={18} style={{ color: '#6366f1' }} />}
      <div>
        <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#e2e8f0' }}>{title}</h3>
        {subtitle && <p style={{ margin: 0, fontSize: 12, color: '#64748b' }}>{subtitle}</p>}
      </div>
    </div>
    {badge}
  </div>
);

/* ═══════ FORMAT HELPERS ═══════ */
const fmt = {
  usd: (v) => v >= 1e9 ? `$${(v/1e9).toFixed(2)}B` : v >= 1e6 ? `$${(v/1e6).toFixed(2)}M` : v >= 1e3 ? `$${(v/1e3).toFixed(1)}K` : `$${Number(v).toFixed(2)}`,
  pct: (v) => `${Number(v) >= 0 ? '+' : ''}${Number(v).toFixed(4)}%`,
  ratio: (v) => Number(v).toFixed(4),
  vol: (v) => v >= 1e6 ? `${(v/1e6).toFixed(1)}M` : v >= 1e3 ? `${(v/1e3).toFixed(0)}K` : Number(v).toFixed(0),
  price: (v) => Number(v) >= 100 ? Number(v).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) : Number(v).toFixed(4),
  time: (ts, includeDate = false) => {
    try {
      const d = new Date(Number(ts));
      if (includeDate) return d.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch { return ''; }
  },
};



/* ═══════════════════════════════════════════════════════════════════════════
   MAIN COMPONENT
   ═══════════════════════════════════════════════════════════════════════════ */
const AIDashboard = () => {
  const [selectedSymbol, setSelectedSymbol] = useState('BTCUSDT');
  const [customSymbol, setCustomSymbol] = useState('');
  const [selectedTimeframe, setSelectedTimeframe] = useState('5m');
  const [microData, setMicroData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const inputRef = useRef(null);

  // AI Decision State
  const [aiStatus, setAiStatus] = useState(null);
  const [aiDecision, setAiDecision] = useState(null);
  const [aiHistory, setAiHistory] = useState([]);
  const [aiLoading, setAiLoading] = useState(false);
  const [validationReport, setValidationReport] = useState(null);
  const [showDecisionLog, setShowDecisionLog] = useState(false);

  const fetchMicroData = useCallback(async (symbol, period) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/alpha-data/${symbol}?period=${period}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setMicroData(data);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err.message);
      setMicroData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchMicroData(selectedSymbol, selectedTimeframe); }, [selectedSymbol, selectedTimeframe, fetchMicroData]);

  // Fetch AI status + history + validation on mount
  useEffect(() => {
    fetch(`${API_BASE}/api/ai/status`).then(r => r.json()).then(setAiStatus).catch(() => {});
    fetch(`${API_BASE}/api/ai/decisions?limit=20`).then(r => r.json()).then(setAiHistory).catch(() => {});
    fetch(`${API_BASE}/api/validation/report`).then(r => r.json()).then(setValidationReport).catch(() => {});
  }, []);

  const handleAIDecision = async () => {
    setAiLoading(true);
    try {
      const sym = selectedSymbol.replace('USDT', '-USDT');
      const res = await fetch(`${API_BASE}/api/ai-decision/${sym}`, { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setAiDecision(data);
      // Refresh history
      const hist = await fetch(`${API_BASE}/api/ai/decisions?limit=20`);
      setAiHistory(await hist.json());
    } catch (err) {
      setAiDecision({ decision: 'ERROR', reasoning: err.message, confidence: 0 });
    } finally {
      setAiLoading(false);
    }
  };
  useEffect(() => {
    const interval = setInterval(() => fetchMicroData(selectedSymbol, selectedTimeframe), 120000);
    return () => clearInterval(interval);
  }, [selectedSymbol, selectedTimeframe, fetchMicroData]);

  const handleCustomSymbol = () => {
    const sym = customSymbol.trim().toUpperCase();
    if (!sym) return;
    const normalized = sym.includes('USDT') ? sym : sym + 'USDT';
    setSelectedSymbol(normalized);
    setCustomSymbol('');
    if (inputRef.current) inputRef.current.blur();
  };

  /* ─── DERIVED DATA ─── */
  const aggTrades = microData?.agg_trades || {};
  const funding = microData?.funding_rate || {};
  const oi = microData?.open_interest || {};
  const ls = microData?.long_short_ratio || {};
  const taker = microData?.taker_volume || {};
  const klines = microData?.klines || {};

  // CVD (Cumulative Volume Delta)
  const cvdData = (() => {
    const candles = klines.candles || [];
    let cumDelta = 0;
    return candles.map((c) => {
      // Approximate CVD from candle: bullish candle → positive delta, bearish → negative
      const bodyRatio = c.close >= c.open
        ? (c.close - c.open) / (c.high - c.low || 1)
        : (c.open - c.close) / (c.high - c.low || 1);
      const delta = c.close >= c.open ? c.volume * bodyRatio : -c.volume * bodyRatio;
      cumDelta += delta;
      return { time: fmt.time(c.timestamp), cvd: Math.round(cumDelta), delta: Math.round(delta) };
    });
  })();

  const fundingHistory = (funding.history || []).map((h, i) => ({
    idx: i, time: fmt.time(h.timestamp), rate: h.rate * 100,
  }));

  const oiHistory = (oi.history || []).map((h, i) => ({
    idx: i, time: fmt.time(h.timestamp), oi: h.oi_value || h.oi || 0,
  }));

  const lsHistory = (ls.history || []).map((h, i) => ({
    idx: i, time: fmt.time(h.timestamp),
    long: (h.long_ratio || 0) * 100, short: (h.short_ratio || 0) * 100,
  }));

  const takerHistory = (taker.history || []).map((h, i) => ({
    idx: i, time: fmt.time(h.timestamp),
    buy: h.buy_vol || 0, sell: h.sell_vol || 0,
    delta: (h.buy_vol || 0) - (h.sell_vol || 0),
  }));

  /* ─── SENTIMENT ─── */
  const overallSentiment = (() => {
    let score = 0;
    if (aggTrades.delta > 0) score++; if (aggTrades.delta < 0) score--;
    if (funding.current_rate > 0.0003) score++; if (funding.current_rate < -0.0001) score--;
    if (oi.trend === 'INCREASING') score++; if (oi.trend === 'DECREASING') score--;
    if (ls.bias === 'LONG_CROWDED') score--; if (ls.bias === 'SHORT_CROWDED') score++;
    if (taker.aggression?.includes('BUYERS')) score++; if (taker.aggression?.includes('SELLERS')) score--;
    return score >= 2 ? 'BULLISH' : score <= -2 ? 'BEARISH' : 'NEUTRAL';
  })();

  /* ═══════ RENDER ═══════ */
  return (
    <div style={{ fontFamily: "'Inter', -apple-system, sans-serif" }}>
      {/* HEADER */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 22, fontWeight: 800, color: '#e2e8f0', display: 'flex', alignItems: 'center', gap: 10 }}>
            <Activity size={22} style={{ color: '#6366f1' }} />
            Market Microstructure
          </h2>
          <p style={{ margin: '4px 0 0', fontSize: 13, color: '#64748b' }}>
            Real-time derivatives flow analysis • Powered by Binance Futures
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <SentimentBadge sentiment={overallSentiment} label={`Overall: ${overallSentiment}`} />
          {lastUpdated && (
            <span style={{ fontSize: 11, color: '#475569', display: 'flex', alignItems: 'center', gap: 4 }}>
              <Clock size={11} /> {lastUpdated.toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>

      {/* ══════ AI DECISION PANEL ══════ */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(139, 92, 246, 0.08))',
        border: '1px solid rgba(99, 102, 241, 0.25)', borderRadius: 14,
        padding: 20, marginBottom: 20,
      }}>
        {/* AI Status Bar */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Brain size={20} style={{ color: '#8b5cf6' }} />
            <span style={{ fontSize: 16, fontWeight: 800, color: '#e2e8f0' }}>AI Decision Engine</span>
            {aiStatus && (
              <span style={{
                padding: '3px 10px', borderRadius: 12, fontSize: 11, fontWeight: 700, letterSpacing: 0.5,
                background: aiStatus.mode === 'live' ? 'rgba(34, 197, 94, 0.15)' : 'rgba(234, 179, 8, 0.15)',
                color: aiStatus.mode === 'live' ? '#22c55e' : '#eab308',
                border: `1px solid ${aiStatus.mode === 'live' ? 'rgba(34, 197, 94, 0.3)' : 'rgba(234, 179, 8, 0.3)'}`,
              }}>
                {aiStatus.mode === 'live' ? ' LIVE' : ' MOCK'} • {aiStatus.model}
              </span>
            )}
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {aiStatus && (
              <span style={{ fontSize: 11, color: '#64748b' }}>
                {aiStatus.key_count || 0} API keys • {aiStatus.decisions_made || 0} decisions
              </span>
            )}
            <button onClick={handleAIDecision} disabled={aiLoading}
              style={{
                padding: '8px 18px', borderRadius: 8, border: 'none', cursor: aiLoading ? 'wait' : 'pointer',
                fontSize: 13, fontWeight: 700, letterSpacing: 0.5,
                background: aiLoading ? 'rgba(100, 116, 139, 0.3)' : 'linear-gradient(135deg, #8b5cf6, #6366f1)',
                color: '#fff', display: 'flex', alignItems: 'center', gap: 6,
                boxShadow: aiLoading ? 'none' : '0 4px 15px rgba(99, 102, 241, 0.3)',
                transition: 'all 0.2s ease',
              }}>
              <Target size={14} />
              {aiLoading ? 'Analyzing...' : `Get AI Decision for ${selectedSymbol.replace('USDT', '')}`}
            </button>
          </div>
        </div>

        {/* Decision Card */}
        {aiDecision && (
          <div style={{
            background: 'rgba(15, 23, 42, 0.6)', borderRadius: 12, padding: 16, marginBottom: 16,
            border: `1px solid ${
              aiDecision.decision === 'LONG' ? 'rgba(34, 197, 94, 0.3)'
              : aiDecision.decision === 'SHORT' ? 'rgba(239, 68, 68, 0.3)'
              : 'rgba(100, 116, 139, 0.3)'
            }`
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, flexWrap: 'wrap' }}>
              <div style={{ flex: 1, minWidth: 200 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                  <span style={{
                    fontSize: 18, fontWeight: 800, letterSpacing: 1,
                    color: aiDecision.decision === 'LONG' ? '#22c55e'
                         : aiDecision.decision === 'SHORT' ? '#ef4444' : '#eab308'
                  }}>
                    {aiDecision.decision === 'LONG' ? '' : aiDecision.decision === 'SHORT' ? '' : ''} {aiDecision.decision}
                  </span>
                  <span style={{
                    padding: '3px 10px', borderRadius: 8, fontSize: 12, fontWeight: 700,
                    background: (aiDecision.confidence || 0) >= 70
                      ? 'rgba(34, 197, 94, 0.15)'
                      : (aiDecision.confidence || 0) >= 50
                        ? 'rgba(234, 179, 8, 0.15)'
                        : 'rgba(239, 68, 68, 0.15)',
                    color: (aiDecision.confidence || 0) >= 70 ? '#22c55e'
                         : (aiDecision.confidence || 0) >= 50 ? '#eab308' : '#ef4444',
                  }}>
                    {aiDecision.confidence || 0}% confidence
                  </span>
                </div>
                <p style={{ margin: 0, fontSize: 13, color: '#94a3b8', lineHeight: 1.6 }}>
                  {aiDecision.reasoning || aiDecision._fallback_reason || 'No reasoning provided'}
                </p>
              </div>
              {(aiDecision.entry || aiDecision.sl || aiDecision.tp) && (
                <div style={{ display: 'flex', gap: 10 }}>
                  {[['Entry', aiDecision.entry, '#6366f1'], ['SL', aiDecision.sl, '#ef4444'], ['TP', aiDecision.tp, '#22c55e']].map(([label, val, color]) => (
                    val ? (
                      <div key={label} style={{ background: 'rgba(15, 23, 42, 0.8)', borderRadius: 8, padding: '8px 14px', borderTop: `2px solid ${color}` }}>
                        <div style={{ fontSize: 10, color: '#64748b', marginBottom: 2 }}>{label}</div>
                        <div style={{ fontSize: 15, fontWeight: 700, color }}>${Number(val).toLocaleString()}</div>
                      </div>
                    ) : null
                  ))}
                  {aiDecision.rr && (
                    <div style={{ background: 'rgba(15, 23, 42, 0.8)', borderRadius: 8, padding: '8px 14px', borderTop: '2px solid #eab308' }}>
                      <div style={{ fontSize: 10, color: '#64748b', marginBottom: 2 }}>R:R</div>
                      <div style={{ fontSize: 15, fontWeight: 700, color: '#eab308' }}>{aiDecision.rr}</div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Decision Log + Validation Summary */}
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 12 }}>
          {/* Decision Log */}
          <div>
            <button onClick={() => setShowDecisionLog(!showDecisionLog)} style={{
              background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 600, marginBottom: 8, padding: 0,
            }}>
              {showDecisionLog ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              Decision History ({Array.isArray(aiHistory) ? aiHistory.length : 0})
            </button>
            {showDecisionLog && Array.isArray(aiHistory) && aiHistory.length > 0 && (
              <div style={{ maxHeight: 200, overflowY: 'auto', borderRadius: 8 }}>
                <table style={{ width: '100%', fontSize: 11, borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ background: 'rgba(15, 23, 42, 0.5)' }}>
                      {['Symbol', 'Decision', 'Conf', 'Mode', 'Time'].map(h => (
                        <th key={h} style={{ padding: '6px 10px', textAlign: 'left', color: '#64748b', fontWeight: 600, borderBottom: '1px solid rgba(100,116,139,0.15)' }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {aiHistory.slice(0, 20).map((d, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid rgba(100,116,139,0.08)' }}>
                        <td style={{ padding: '5px 10px', color: '#e2e8f0', fontWeight: 600 }}>{d.symbol}</td>
                        <td style={{ padding: '5px 10px', color: d.decision === 'LONG' ? '#22c55e' : d.decision === 'SHORT' ? '#ef4444' : '#eab308', fontWeight: 700 }}>{d.decision}</td>
                        <td style={{ padding: '5px 10px', color: '#94a3b8' }}>{d.confidence}%</td>
                        <td style={{ padding: '5px 10px' }}>
                          <span style={{ padding: '1px 6px', borderRadius: 4, fontSize: 10, background: d.mode === 'live' ? 'rgba(34,197,94,0.15)' : 'rgba(234,179,8,0.15)', color: d.mode === 'live' ? '#22c55e' : '#eab308' }}>{d.mode}</span>
                        </td>
                        <td style={{ padding: '5px 10px', color: '#475569', fontSize: 10 }}>{d.timestamp ? new Date(d.timestamp).toLocaleString() : ''}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Validation Summary */}
          <div style={{ background: 'rgba(15, 23, 42, 0.4)', borderRadius: 10, padding: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
              <Shield size={14} style={{ color: '#6366f1' }} />
              <span style={{ fontSize: 12, fontWeight: 700, color: '#e2e8f0' }}>Validation Status</span>
            </div>
            {validationReport && validationReport.verdict ? (
              <>
                <div style={{ marginBottom: 8 }}>
                  <span style={{
                    padding: '3px 10px', borderRadius: 8, fontSize: 11, fontWeight: 700,
                    background: validationReport.verdict === 'VALIDATED' ? 'rgba(34,197,94,0.15)'
                             : validationReport.verdict === 'INSUFFICIENT_DATA' ? 'rgba(100,116,139,0.15)'
                             : 'rgba(239,68,68,0.15)',
                    color: validationReport.verdict === 'VALIDATED' ? '#22c55e'
                         : validationReport.verdict === 'INSUFFICIENT_DATA' ? '#94a3b8' : '#ef4444',
                  }}>
                    {validationReport.verdict}
                  </span>
                </div>
                {validationReport.metrics && (
                  <div style={{ display: 'grid', gap: 4, fontSize: 11 }}>
                    {Object.entries(validationReport.metrics).slice(0, 5).map(([k, v]) => (
                      <div key={k} style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8' }}>
                        <span>{k}</span>
                        <span style={{ color: '#e2e8f0', fontWeight: 600 }}>{typeof v === 'number' ? v.toFixed(2) : String(v)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <p style={{ margin: 0, fontSize: 11, color: '#475569' }}>No validation data yet. Need 200+ decisions.</p>
            )}
          </div>
        </div>
      </div>

      {/* SYMBOL SELECTOR + CUSTOM INPUT */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        {DEFAULT_SYMBOLS.map(s => (
          <button key={s} onClick={() => setSelectedSymbol(s)}
            style={{
              padding: '8px 18px', borderRadius: 8, border: 'none', cursor: 'pointer',
              fontSize: 13, fontWeight: 700, letterSpacing: 0.5, transition: 'all 0.2s ease',
              background: selectedSymbol === s ? 'linear-gradient(135deg, #6366f1, #8b5cf6)' : 'rgba(30, 41, 59, 0.6)',
              color: selectedSymbol === s ? '#fff' : '#94a3b8',
              boxShadow: selectedSymbol === s ? '0 4px 15px rgba(99, 102, 241, 0.3)' : 'none',
            }}
          >
            {s.replace('USDT', '')}
          </button>
        ))}
        {/* Custom symbol input */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 0,
          background: 'rgba(30, 41, 59, 0.6)', border: '1px solid rgba(100, 116, 139, 0.25)',
          borderRadius: 8, overflow: 'hidden',
        }}>
          <input
            ref={inputRef}
            type="text"
            placeholder="Custom (e.g. AVAX)"
            value={customSymbol}
            onChange={(e) => setCustomSymbol(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCustomSymbol()}
            style={{
              background: 'transparent', border: 'none', outline: 'none',
              color: '#e2e8f0', padding: '8px 12px', fontSize: 13, width: 150,
            }}
          />
          <button onClick={handleCustomSymbol}
            style={{
              background: 'rgba(99, 102, 241, 0.2)', border: 'none', borderLeft: '1px solid rgba(100, 116, 139, 0.2)',
              color: '#6366f1', padding: '8px 12px', cursor: 'pointer', display: 'flex', alignItems: 'center',
            }}
          >
            <Search size={14} />
          </button>
        </div>
        {/* Show current symbol if custom */}
        {!DEFAULT_SYMBOLS.includes(selectedSymbol) && (
          <span style={{
            padding: '8px 18px', borderRadius: 8, fontSize: 13, fontWeight: 700,
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', color: '#fff',
            boxShadow: '0 4px 15px rgba(99, 102, 241, 0.3)',
          }}>
            {selectedSymbol.replace('USDT', '')}
          </span>
        )}
        <button onClick={() => fetchMicroData(selectedSymbol, selectedTimeframe)}
          style={{
            padding: '8px 14px', borderRadius: 8, border: '1px solid rgba(99, 102, 241, 0.3)',
            background: 'rgba(99, 102, 241, 0.1)', color: '#6366f1', cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, fontWeight: 600,
          }}
        >
          <RefreshCw size={14} className={loading ? 'spin' : ''} /> Refresh
        </button>
      </div>

      {/* TIMEFRAME SELECTOR */}
      <div style={{
        display: 'flex', gap: 4, marginBottom: 20, alignItems: 'center',
        background: 'rgba(15, 23, 42, 0.5)', borderRadius: 10, padding: 4,
        border: '1px solid rgba(100, 116, 139, 0.15)', width: 'fit-content',
      }}>
        <span style={{ fontSize: 11, color: '#64748b', padding: '0 8px', fontWeight: 600 }}>Interval:</span>
        {TIMEFRAMES.map(tf => (
          <button key={tf.value} onClick={() => setSelectedTimeframe(tf.value)}
            style={{
              padding: '6px 14px', borderRadius: 7, border: 'none', cursor: 'pointer',
              fontSize: 12, fontWeight: 700, transition: 'all 0.15s ease',
              background: selectedTimeframe === tf.value ? '#6366f1' : 'transparent',
              color: selectedTimeframe === tf.value ? '#fff' : '#64748b',
            }}
          >
            {tf.label}
          </button>
        ))}
      </div>

      {/* LOADING / ERROR */}
      {loading && (
        <div style={{ textAlign: 'center', padding: 60, color: '#6366f1' }}>
          <RefreshCw size={28} className="spin" style={{ marginBottom: 12 }} />
          <p style={{ fontSize: 14 }}>Fetching microstructure data for {selectedSymbol}...</p>
        </div>
      )}
      {error && (
        <div style={{
          padding: 20, borderRadius: 12,
          background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', marginBottom: 20
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#ef4444', marginBottom: 8 }}>
            <AlertTriangle size={16} /><span style={{ fontWeight: 700 }}>Connection Error</span>
          </div>
          <p style={{ color: '#f87171', fontSize: 13, margin: 0 }}>{error}</p>
          <p style={{ color: '#64748b', fontSize: 12, marginTop: 8 }}>
            Make sure VPN is active and the symbol exists on Binance Futures.
          </p>
        </div>
      )}

      {!loading && microData && (
        <>
          {/* ══════ ROW 0: ORDER BOOK PRESSURE (Coinglass Embed) ══════ */}
          <div style={{
            background: 'rgba(30, 41, 59, 0.4)', border: '1px solid rgba(100, 116, 139, 0.15)',
            borderRadius: 14, overflow: 'hidden', marginBottom: 20,
          }}>
            {/* Minimal header */}
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '14px 20px', borderBottom: '1px solid rgba(100, 116, 139, 0.1)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <TrendingUp size={18} style={{ color: '#6366f1' }} />
                <span style={{ fontSize: 15, fontWeight: 800, color: '#e2e8f0' }}>
                  Order Book Pressure
                </span>
                <span style={{ fontSize: 11, color: '#475569', fontWeight: 500 }}>
                  Powered by Coinglass
                </span>
              </div>
              <a href="https://www.coinglass.com/orderbook-pressure" target="_blank" rel="noopener noreferrer"
                style={{
                  fontSize: 11, color: '#6366f1', textDecoration: 'none', fontWeight: 600,
                  background: 'rgba(99, 102, 241, 0.1)', padding: '4px 10px', borderRadius: 6,
                  border: '1px solid rgba(99, 102, 241, 0.2)',
                }}>
                Open Full ↗
              </a>
            </div>

            {/* Cropped iframe — hides Coinglass nav, ticker bar, and ads */}
            <div style={{
              position: 'relative',
              height: 794,
              overflow: 'hidden',
              background: '#0b0f19',
            }}>
              <iframe
                src="https://www.coinglass.com/orderbook-pressure"
                title="Coinglass Order Book Pressure"
                style={{
                  width: 'calc(100% + 20px)',
                  height: 1100,
                  border: 'none',
                  display: 'block',
                  marginTop: -200,
                  marginLeft: -10,
                }}
                loading="lazy"
                allow="clipboard-write"
              />
            </div>
          </div>

          {/* ══════ ROW 0B: CVD (Cumulative Volume Delta) ══════ */}
          {cvdData.length > 0 && (
            <div style={{
              background: 'rgba(30, 41, 59, 0.4)', border: '1px solid rgba(100, 116, 139, 0.15)',
              borderRadius: 14, padding: 20, marginBottom: 20,
            }}>
              <SectionHeader icon={BarChart3} title="Cumulative Volume Delta (CVD)"
                subtitle="Running total of buy - sell volume • Divergence from price = key signal"
                badge={<SentimentBadge
                  sentiment={cvdData[cvdData.length-1]?.cvd > 0 ? 'BULLISH' : cvdData[cvdData.length-1]?.cvd < 0 ? 'BEARISH' : 'NEUTRAL'}
                  label={cvdData[cvdData.length-1]?.cvd > 0 ? 'Net Buying' : 'Net Selling'}
                />}
              />
              <ResponsiveContainer width="100%" height={180}>
                <ComposedChart data={cvdData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                  <defs>
                    <linearGradient id="cvdGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.25}/>
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(100,116,139,0.08)" />
                  <XAxis dataKey="time" tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false}
                    interval={Math.max(Math.floor(cvdData.length / 8), 1)} />
                  <YAxis yAxisId="cvd" tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} axisLine={false}
                    tickFormatter={(v) => fmt.vol(v)} />
                  <YAxis yAxisId="delta" orientation="right" tick={{ fill: '#475569', fontSize: 9 }} tickLine={false}
                    axisLine={false} tickFormatter={(v) => fmt.vol(v)} />
                  <Tooltip content={<ChartTooltip formatter={(v) => fmt.vol(v)} />} />
                  <ReferenceLine yAxisId="cvd" y={0} stroke="#475569" strokeDasharray="3 3" />
                  <Bar yAxisId="delta" dataKey="delta" name="Delta" maxBarSize={6} radius={[2, 2, 0, 0]} opacity={0.5}>
                    {cvdData.map((entry, i) => (
                      <Cell key={i} fill={entry.delta >= 0 ? '#22c55e' : '#ef4444'} />
                    ))}
                  </Bar>
                  <Area yAxisId="cvd" type="monotone" dataKey="cvd" name="CVD" stroke="#6366f1" strokeWidth={2}
                    fill="url(#cvdGrad)" dot={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* ══════ ROW 1: KEY METRICS ══════ */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12, marginBottom: 24 }}>
            <StatCard icon={Zap} label="Trade Delta" color={aggTrades.delta > 0 ? '#22c55e' : '#ef4444'}
              value={fmt.usd(Math.abs(aggTrades.delta || 0))}
              subValue={`${aggTrades.delta > 0 ? 'Buyers' : 'Sellers'} dominate • ${aggTrades.total_trades || 0} trades`}
              trend={aggTrades.delta > 0 ? 'up' : 'down'} />
            <StatCard icon={DollarSign} label="Funding Rate" color={funding.current_rate > 0 ? '#22c55e' : '#ef4444'}
              value={fmt.pct(funding.current_rate || 0)}
              subValue={`Annualized: ${funding.annualized_pct || 0}%`}
              trend={funding.trend === 'POSITIVE' ? 'up' : funding.trend === 'NEGATIVE' ? 'down' : undefined} />
            <StatCard icon={BarChart3} label="Open Interest" color="#3b82f6"
              value={fmt.usd(oi.current_oi_value || oi.current_oi || 0)}
              subValue={`${oi.change_pct >= 0 ? '+' : ''}${oi.change_pct || 0}% • ${oi.trend || 'N/A'}`}
              trend={oi.trend === 'INCREASING' ? 'up' : oi.trend === 'DECREASING' ? 'down' : undefined} />
            <StatCard icon={Users} label="Long/Short Ratio"
              color={ls.bias === 'LONG_CROWDED' ? '#eab308' : ls.bias === 'SHORT_CROWDED' ? '#a855f7' : '#3b82f6'}
              value={fmt.ratio(ls.long_short_ratio || 0)}
              subValue={`L: ${((ls.long_ratio || 0) * 100).toFixed(1)}% / S: ${((ls.short_ratio || 0) * 100).toFixed(1)}%`}
              trend={ls.long_ratio > ls.short_ratio ? 'up' : 'down'} />
          </div>

          {/* ══════ ROW 2: TRADE DELTA + FUNDING RATE ══════ */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
            {/* TRADE DELTA */}
            <div style={{ background: 'rgba(30, 41, 59, 0.4)', border: '1px solid rgba(100, 116, 139, 0.15)', borderRadius: 14, padding: 20 }}>
              <SectionHeader icon={Zap} title="Trade Flow (Aggressor)"
                subtitle="Last 1000 trades — buyer vs seller"
                badge={<SentimentBadge sentiment={aggTrades.delta > 0 ? 'BULLISH' : aggTrades.delta < 0 ? 'BEARISH' : 'NEUTRAL'} />} />
              <div style={{ marginBottom: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span style={{ color: '#22c55e', fontSize: 13, fontWeight: 700 }}>Buy: {fmt.usd(aggTrades.buy_volume || 0)}</span>
                  <span style={{ color: '#ef4444', fontSize: 13, fontWeight: 700 }}>Sell: {fmt.usd(aggTrades.sell_volume || 0)}</span>
                </div>
                <div style={{ display: 'flex', height: 28, borderRadius: 8, overflow: 'hidden', gap: 2 }}>
                  {(() => {
                    const total = (aggTrades.buy_volume || 1) + (aggTrades.sell_volume || 1);
                    const buyPct = ((aggTrades.buy_volume || 0) / total * 100).toFixed(1);
                    const sellPct = ((aggTrades.sell_volume || 0) / total * 100).toFixed(1);
                    return (<>
                      <div style={{ width: `${buyPct}%`, background: 'linear-gradient(90deg, #22c55e, #4ade80)', borderRadius: '8px 0 0 8px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 700, color: '#fff', transition: 'width 0.5s ease' }}>{buyPct}%</div>
                      <div style={{ flex: 1, background: 'linear-gradient(90deg, #f87171, #ef4444)', borderRadius: '0 8px 8px 0', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 700, color: '#fff' }}>{sellPct}%</div>
                    </>);
                  })()}
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Delta (Net)', value: `${aggTrades.delta > 0 ? '+' : ''}${fmt.usd(aggTrades.delta || 0)}`, color: aggTrades.delta > 0 ? '#22c55e' : '#ef4444' },
                  { label: 'Avg Trade Size', value: fmt.usd(aggTrades.avg_trade_size || 0), color: '#e2e8f0' },
                  { label: 'Large Trades', value: aggTrades.large_trades || 0, color: '#eab308' },
                ].map((item, i) => (
                  <div key={i} style={{ background: 'rgba(15, 23, 42, 0.5)', borderRadius: 8, padding: '10px 12px', textAlign: 'center' }}>
                    <div style={{ fontSize: 11, color: '#64748b', marginBottom: 2 }}>{item.label}</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: item.color }}>{item.value}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* FUNDING RATE CHART */}
            <div style={{ background: 'rgba(30, 41, 59, 0.4)', border: '1px solid rgba(100, 116, 139, 0.15)', borderRadius: 14, padding: 20 }}>
              <SectionHeader icon={DollarSign} title="Funding Rate History"
                subtitle="8-hour rate • Positive = Longs pay Shorts"
                badge={<SentimentBadge
                  sentiment={funding.current_rate > 0.0003 ? 'LONG_CROWDED' : funding.current_rate < -0.0001 ? 'SHORT_CROWDED' : 'BALANCED'}
                  label={funding.current_rate > 0.0003 ? 'Longs Pay' : funding.current_rate < -0.0001 ? 'Shorts Pay' : 'Balanced'} />} />
              {fundingHistory.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={fundingHistory} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(100,116,139,0.1)" />
                    <XAxis dataKey="time" tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} />
                    <YAxis tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={(v) => `${v.toFixed(3)}%`} />
                    <Tooltip content={<ChartTooltip formatter={(v) => `${v.toFixed(4)}%`} />} />
                    <ReferenceLine y={0} stroke="#475569" strokeDasharray="3 3" />
                    <Bar dataKey="rate" radius={[3, 3, 0, 0]} maxBarSize={16} name="Funding Rate">
                      {fundingHistory.map((entry, i) => (
                        <Cell key={i} fill={entry.rate >= 0 ? (entry.rate > 0.01 ? '#ef4444' : '#22c55e') : '#8b5cf6'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#475569' }}>No funding rate history</div>
              )}
              <div style={{ display: 'flex', gap: 16, marginTop: 10, justifyContent: 'center' }}>
                {[['#22c55e', 'Normal'], ['#ef4444', 'Elevated'], ['#8b5cf6', 'Negative']].map(([c, l]) => (
                  <span key={l} style={{ fontSize: 11, color: '#64748b', display: 'flex', alignItems: 'center', gap: 4 }}>
                    <div style={{ width: 10, height: 10, borderRadius: 2, background: c }} /> {l}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* ══════ ROW 3: OI + L/S RATIO ══════ */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
            {/* OI */}
            <div style={{ background: 'rgba(30, 41, 59, 0.4)', border: '1px solid rgba(100, 116, 139, 0.15)', borderRadius: 14, padding: 20 }}>
              <SectionHeader icon={BarChart3} title="Open Interest"
                subtitle={`Total contracts open (${selectedTimeframe})`}
                badge={<SentimentBadge sentiment={oi.trend === 'INCREASING' ? 'BULLISH' : oi.trend === 'DECREASING' ? 'BEARISH' : 'NEUTRAL'} label={oi.trend || 'N/A'} />} />
              {oiHistory.length > 0 ? (
                <ResponsiveContainer width="100%" height={220}>
                  <AreaChart data={oiHistory} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                    <defs>
                      <linearGradient id="oiGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/><stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(100,116,139,0.1)" />
                    <XAxis dataKey="time" tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} />
                    <YAxis tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={(v) => fmt.usd(v)} />
                    <Tooltip content={<ChartTooltip formatter={(v) => fmt.usd(v)} />} />
                    <Area type="monotone" dataKey="oi" stroke="#3b82f6" strokeWidth={2} fill="url(#oiGrad)" dot={false} activeDot={{ r: 4, fill: '#3b82f6' }} name="Open Interest" />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ height: 220, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#475569', gap: 8 }}>
                  <BarChart3 size={24} /><span>No OI history — try 1H, 4H, or 1D</span>
                </div>
              )}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 12 }}>
                <div style={{ background: 'rgba(15, 23, 42, 0.5)', borderRadius: 8, padding: '10px 12px' }}>
                  <div style={{ fontSize: 11, color: '#64748b' }}>Current OI (Value)</div>
                  <div style={{ fontSize: 15, fontWeight: 700, color: '#3b82f6' }}>{fmt.usd(oi.current_oi_value || oi.current_oi || 0)}</div>
                </div>
                <div style={{ background: 'rgba(15, 23, 42, 0.5)', borderRadius: 8, padding: '10px 12px' }}>
                  <div style={{ fontSize: 11, color: '#64748b' }}>OI Change</div>
                  <div style={{ fontSize: 15, fontWeight: 700, color: oi.change_pct >= 0 ? '#22c55e' : '#ef4444' }}>
                    {oi.change_pct >= 0 ? '+' : ''}{oi.change_pct || 0}%
                  </div>
                </div>
              </div>
            </div>

            {/* L/S RATIO */}
            <div style={{ background: 'rgba(30, 41, 59, 0.4)', border: '1px solid rgba(100, 116, 139, 0.15)', borderRadius: 14, padding: 20 }}>
              <SectionHeader icon={Users} title="Long/Short Ratio"
                subtitle={`Global positioning (${selectedTimeframe})`}
                badge={<SentimentBadge sentiment={ls.bias || 'BALANCED'} />} />
              <div style={{ marginBottom: 14 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span style={{ color: '#22c55e', fontSize: 13, fontWeight: 700 }}>Long {((ls.long_ratio || 0) * 100).toFixed(1)}%</span>
                  <span style={{ color: '#ef4444', fontSize: 13, fontWeight: 700 }}>Short {((ls.short_ratio || 0) * 100).toFixed(1)}%</span>
                </div>
                <div style={{ display: 'flex', height: 22, borderRadius: 6, overflow: 'hidden', gap: 2 }}>
                  <div style={{ width: `${(ls.long_ratio || 0.5) * 100}%`, background: 'linear-gradient(90deg, #22c55e, #4ade80)', borderRadius: '6px 0 0 6px', transition: 'width 0.5s ease' }} />
                  <div style={{ flex: 1, background: 'linear-gradient(90deg, #f87171, #ef4444)', borderRadius: '0 6px 6px 0' }} />
                </div>
              </div>
              {lsHistory.length > 0 ? (
                <ResponsiveContainer width="100%" height={180}>
                  <LineChart data={lsHistory} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(100,116,139,0.1)" />
                    <XAxis dataKey="time" tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} />
                    <YAxis tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={(v) => `${v.toFixed(0)}%`} domain={[30, 70]} />
                    <Tooltip content={<ChartTooltip formatter={(v) => `${v.toFixed(1)}%`} />} />
                    <Line type="monotone" dataKey="long" stroke="#22c55e" strokeWidth={2} dot={false} name="Long %" />
                    <Line type="monotone" dataKey="short" stroke="#ef4444" strokeWidth={2} dot={false} name="Short %" />
                    <ReferenceLine y={50} stroke="#475569" strokeDasharray="3 3" />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ height: 180, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#475569' }}>No L/S history</div>
              )}
            </div>
          </div>

          {/* ══════ ROW 4: TAKER VOLUME ══════ */}
          <div style={{ background: 'rgba(30, 41, 59, 0.4)', border: '1px solid rgba(100, 116, 139, 0.15)', borderRadius: 14, padding: 20, marginBottom: 20 }}>
            <SectionHeader icon={Zap} title="Taker Buy/Sell Volume"
              subtitle={`Market order aggression (${selectedTimeframe})`}
              badge={<SentimentBadge
                sentiment={taker.aggression?.includes('BUYERS') ? 'BULLISH' : taker.aggression?.includes('SELLERS') ? 'BEARISH' : 'NEUTRAL'}
                label={taker.aggression || 'N/A'} />} />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 12, marginBottom: 16 }}>
              {[
                { label: 'Buy Volume', value: fmt.vol(taker.buy_vol || 0), color: '#22c55e' },
                { label: 'Sell Volume', value: fmt.vol(taker.sell_vol || 0), color: '#ef4444' },
                { label: 'Buy/Sell Ratio', value: (taker.buy_sell_ratio || 0).toFixed(3), color: (taker.buy_sell_ratio || 1) > 1 ? '#22c55e' : '#ef4444' },
                { label: 'Imbalance', value: `${((taker.imbalance || 0) * 100).toFixed(1)}%`, color: '#eab308' },
              ].map((item, i) => (
                <div key={i} style={{ background: 'rgba(15, 23, 42, 0.5)', borderRadius: 8, padding: '10px 14px' }}>
                  <div style={{ fontSize: 11, color: '#64748b' }}>{item.label}</div>
                  <div style={{ fontSize: 17, fontWeight: 700, color: item.color }}>{item.value}</div>
                </div>
              ))}
            </div>
            {takerHistory.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <ComposedChart data={takerHistory} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                  <defs>
                    <linearGradient id="buyG" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#22c55e" stopOpacity={0.25}/><stop offset="95%" stopColor="#22c55e" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="sellG" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#ef4444" stopOpacity={0.25}/><stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(100,116,139,0.1)" />
                  <XAxis dataKey="time" tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} />
                  <YAxis yAxisId="vol" tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={(v) => fmt.vol(v)} />
                  <YAxis yAxisId="delta" orientation="right" tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={(v) => fmt.vol(v)} />
                  <Tooltip content={<ChartTooltip formatter={(v) => fmt.vol(v)} />} />
                  <Area yAxisId="vol" type="monotone" dataKey="buy" stroke="#22c55e" strokeWidth={1.5} fill="url(#buyG)" name="Buy Vol" dot={false} />
                  <Area yAxisId="vol" type="monotone" dataKey="sell" stroke="#ef4444" strokeWidth={1.5} fill="url(#sellG)" name="Sell Vol" dot={false} />
                  <Line yAxisId="delta" type="monotone" dataKey="delta" stroke="#eab308" strokeWidth={2} dot={false} name="Delta" strokeDasharray="5 3" />
                </ComposedChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ height: 240, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#475569' }}>No taker volume history</div>
            )}
            <div style={{ display: 'flex', gap: 20, marginTop: 10, justifyContent: 'center' }}>
              {[['#22c55e', 'Buy Vol'], ['#ef4444', 'Sell Vol'], ['#eab308', 'Delta']].map(([c, l]) => (
                <span key={l} style={{ fontSize: 11, color: '#64748b', display: 'flex', alignItems: 'center', gap: 4 }}>
                  <div style={{ width: 14, height: 3, background: c, borderRadius: 2 }} /> {l}
                </span>
              ))}
            </div>
          </div>

          {/* ══════ ROW 5: INTERPRETATION GUIDE ══════ */}
          <div style={{ background: 'rgba(30, 41, 59, 0.4)', border: '1px solid rgba(100, 116, 139, 0.15)', borderRadius: 14, padding: 20 }}>
            <SectionHeader icon={AlertTriangle} title="How to Read This Data" subtitle="Quick interpretation guide" />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              {[
                { signal: '\u{1F7E2} Strong Bullish', condition: 'Delta positive + OI increasing + Funding moderate + Taker buyers aggressive + CVD rising' },
                { signal: '\u{1F534} Strong Bearish', condition: 'Delta negative + OI decreasing + Funding negative + Taker sellers aggressive + CVD falling' },
                { signal: '\u26A0\uFE0F Long Squeeze Risk', condition: 'Funding >0.03% + Long ratio >60% + OI very high \u2192 Violent reversal down' },
                { signal: '\u{1F7E3} CVD Divergence', condition: 'Price rising but CVD falling = hidden selling (bearish). Price falling but CVD rising = hidden buying (bullish)' },
              ].map((item, i) => (
                <div key={i} style={{ background: 'rgba(15, 23, 42, 0.5)', borderRadius: 8, padding: '12px 14px' }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: '#e2e8f0', marginBottom: 4 }}>{item.signal}</div>
                  <div style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.5 }}>{item.condition}</div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      <style>{`
        @keyframes spin { from { transform: rotate(0deg) } to { transform: rotate(360deg) } }
        .spin { animation: spin 1s linear infinite; }
      `}</style>
    </div>
  );
};

export default AIDashboard;
