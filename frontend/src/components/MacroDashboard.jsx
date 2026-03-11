import React, { useState, useEffect } from 'react';
import {
    Globe, TrendingUp, TrendingDown, Activity, Shield, AlertTriangle,
    RefreshCw, Minus, BarChart2, Target, Layers, Zap, ChevronRight
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

// ============================================================
// REGIME BADGE COMPONENT
// ============================================================
const RegimeBadge = ({ regime, confidence }) => {
    const colors = {
        BULLISH: { bg: 'rgba(16, 185, 129, 0.15)', border: '#10b981', text: '#34d399', icon: TrendingUp },
        BEARISH: { bg: 'rgba(239, 68, 68, 0.15)', border: '#ef4444', text: '#f87171', icon: TrendingDown },
        NEUTRAL: { bg: 'rgba(234, 179, 8, 0.15)', border: '#eab308', text: '#facc15', icon: Minus }
    };
    const c = colors[regime] || colors.NEUTRAL;
    const Icon = c.icon;

    return (
        <div style={{
            background: c.bg, border: `1px solid ${c.border}`, borderRadius: '16px',
            padding: '24px', textAlign: 'center', position: 'relative', overflow: 'hidden'
        }}>
            {/* Animated pulse background */}
            <div style={{
                position: 'absolute', inset: 0, opacity: 0.05,
                background: `radial-gradient(circle at center, ${c.border}, transparent 70%)`,
                animation: 'pulse 3s ease-in-out infinite'
            }} />
            <Icon size={48} color={c.text} style={{ margin: '0 auto 12px' }} />
            <div style={{ fontSize: '28px', fontWeight: 800, color: c.text, letterSpacing: '2px' }}>
                {regime}
            </div>
            <div style={{ fontSize: '14px', color: '#9ca3af', marginTop: '8px' }}>
                Market Regime • {confidence}% Confidence
            </div>
        </div>
    );
};

// ============================================================
// INDICATOR CARD COMPONENT
// ============================================================
const IndicatorCard = ({ name, label, data }) => {
    if (!data) return null;
    const isUp = data.trend === 'UP' || data.trend === 'GREEN';
    const isDown = data.trend === 'DOWN' || data.trend === 'RED';
    const trendColor = isUp ? '#10b981' : isDown ? '#ef4444' : '#eab308';
    const TrendIcon = isUp ? TrendingUp : isDown ? TrendingDown : Minus;

    // Format value based on indicator type
    let displayValue = '—';
    if (name === 'spx') {
        displayValue = data.value ? `$${data.value.toLocaleString()}` : '—';
    } else if (name === 'usdt_d' || name === 'btc_d') {
        displayValue = data.value ? `${data.value}%` : '—';
    } else if (name === 'total3' || name === 'others') {
        displayValue = data.value ? `$${(data.value / 1e9).toFixed(1)}B` : '—';
    }

    return (
        <div style={{
            background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '12px', padding: '16px', display: 'flex', alignItems: 'center',
            gap: '14px', transition: 'all 0.2s',
        }}
            onMouseEnter={e => {
                e.currentTarget.style.background = 'rgba(255,255,255,0.06)';
                e.currentTarget.style.borderColor = trendColor;
            }}
            onMouseLeave={e => {
                e.currentTarget.style.background = 'rgba(255,255,255,0.03)';
                e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)';
            }}
        >
            <div style={{
                width: '44px', height: '44px', borderRadius: '10px',
                background: `${trendColor}15`, display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}>
                <TrendIcon size={22} color={trendColor} />
            </div>
            <div style={{ flex: 1 }}>
                <div style={{ fontSize: '12px', color: '#9ca3af', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    {label}
                </div>
                <div style={{ fontSize: '18px', fontWeight: 700, color: '#e5e7eb', marginTop: '2px' }}>
                    {displayValue}
                </div>
            </div>
            <div style={{
                padding: '4px 10px', borderRadius: '20px',
                background: `${trendColor}20`, color: trendColor,
                fontSize: '12px', fontWeight: 700
            }}>
                {data.trend || 'N/A'}
                {name === 'spx' && data.daily_change !== undefined && (
                    <span style={{ marginLeft: '4px' }}>({data.daily_change > 0 ? '+' : ''}{data.daily_change}%)</span>
                )}
            </div>
        </div>
    );
};

// ============================================================
// CONDITIONS CHECKLIST
// ============================================================
const ConditionsChecklist = ({ title, conditions, color }) => {
    if (!conditions) return null;
    const entries = Object.entries(conditions);

    return (
        <div style={{
            background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: '12px', padding: '16px'
        }}>
            <div style={{ fontSize: '13px', fontWeight: 700, color: color, marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '1px' }}>
                {title}
            </div>
            {entries.map(([key, met]) => (
                <div key={key} style={{
                    display: 'flex', alignItems: 'center', gap: '8px',
                    padding: '6px 0', borderBottom: '1px solid rgba(255,255,255,0.04)'
                }}>
                    <span style={{ color: met ? '#10b981' : '#ef4444', fontSize: '14px' }}>
                        {met ? '✅' : '❌'}
                    </span>
                    <span style={{ fontSize: '13px', color: met ? '#d1d5db' : '#6b7280', fontFamily: 'monospace' }}>
                        {key.replace(/_/g, ' ').toUpperCase()}
                    </span>
                </div>
            ))}
        </div>
    );
};

// ============================================================
// S/R LEVELS TABLE
// ============================================================
const SRLevels = ({ levels }) => {
    if (!levels || levels.length === 0) return null;

    return (
        <div style={{
            background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: '12px', padding: '16px'
        }}>
            <div style={{ fontSize: '13px', fontWeight: 700, color: '#06b6d4', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '1px' }}>
                <Target size={14} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'middle' }} />
                SPX Support / Resistance
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: '6px' }}>
                {levels.map((l, i) => (
                    <div key={i} style={{
                        padding: '8px 10px', borderRadius: '8px', fontSize: '12px', fontFamily: 'monospace',
                        background: l.type === 'resistance' ? 'rgba(239, 68, 68, 0.1)' : l.type === 'support' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(234, 179, 8, 0.1)',
                        border: `1px solid ${l.type === 'resistance' ? 'rgba(239,68,68,0.3)' : l.type === 'support' ? 'rgba(16,185,129,0.3)' : 'rgba(234,179,8,0.3)'}`,
                        color: l.type === 'resistance' ? '#f87171' : l.type === 'support' ? '#34d399' : '#facc15'
                    }}>
                        <div style={{ fontWeight: 700 }}>${l.level?.toLocaleString()}</div>
                        <div style={{ fontSize: '10px', opacity: 0.7, marginTop: '2px' }}>
                            {l.type?.toUpperCase()} • {l.strength}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

// ============================================================
// MAIN: MACRO DASHBOARD COMPONENT
// ============================================================
const MacroDashboard = () => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [lastUpdated, setLastUpdated] = useState(null);

    const fetchMacroData = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(`${API_URL}/api/macro-intelligence`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const json = await res.json();
            setData(json);
            setLastUpdated(new Date().toLocaleTimeString());
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchMacroData();
        // Auto-refresh every 5 minutes
        const interval = setInterval(fetchMacroData, 5 * 60 * 1000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div style={{
            background: 'linear-gradient(135deg, rgba(15,23,42,0.95), rgba(15,23,42,0.85))',
            border: '1px solid rgba(255,255,255,0.08)', borderRadius: '20px',
            padding: '28px', color: '#e5e7eb'
        }}>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{
                        width: '42px', height: '42px', borderRadius: '12px',
                        background: 'linear-gradient(135deg, #06b6d4, #8b5cf6)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center'
                    }}>
                        <Globe size={22} color="white" />
                    </div>
                    <div>
                        <h2 style={{ fontSize: '20px', fontWeight: 800, margin: 0, color: '#f3f4f6' }}>
                            Macro Intelligence
                        </h2>
                        <p style={{ fontSize: '12px', color: '#6b7280', margin: 0 }}>
                            Automated Top-Down Market Screening
                        </p>
                    </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    {lastUpdated && (
                        <span style={{ fontSize: '11px', color: '#6b7280' }}>
                            Updated: {lastUpdated}
                        </span>
                    )}
                    <button
                        onClick={fetchMacroData}
                        disabled={loading}
                        style={{
                            background: 'rgba(6, 182, 212, 0.15)', border: '1px solid rgba(6, 182, 212, 0.3)',
                            borderRadius: '10px', padding: '8px 16px', color: '#06b6d4',
                            cursor: loading ? 'wait' : 'pointer', display: 'flex', alignItems: 'center', gap: '6px',
                            fontSize: '13px', fontWeight: 600, transition: 'all 0.2s'
                        }}
                    >
                        <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                        {loading ? 'Scanning...' : 'Refresh'}
                    </button>
                </div>
            </div>

            {/* Error State */}
            {error && (
                <div style={{
                    background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)',
                    borderRadius: '12px', padding: '14px', marginBottom: '16px',
                    color: '#f87171', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px'
                }}>
                    <AlertTriangle size={16} /> {error}
                </div>
            )}

            {/* Loading State */}
            {loading && !data && (
                <div style={{ textAlign: 'center', padding: '40px', color: '#6b7280' }}>
                    <Activity size={32} style={{ animation: 'pulse 1.5s ease-in-out infinite', margin: '0 auto 12px' }} />
                    <p>Fetching macro data from CoinGecko & Yahoo Finance...</p>
                </div>
            )}

            {/* Data Display */}
            {data && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                    {/* Regime Badge */}
                    <RegimeBadge regime={data.regime} confidence={data.confidence} />

                    {/* Recommendation Banner */}
                    {data.recommendation && (
                        <div style={{
                            background: data.regime === 'BULLISH' ? 'rgba(16,185,129,0.08)' :
                                data.regime === 'BEARISH' ? 'rgba(239,68,68,0.08)' : 'rgba(234,179,8,0.08)',
                            border: `1px solid ${data.regime === 'BULLISH' ? 'rgba(16,185,129,0.2)' :
                                data.regime === 'BEARISH' ? 'rgba(239,68,68,0.2)' : 'rgba(234,179,8,0.2)'}`,
                            borderRadius: '12px', padding: '14px 18px',
                            display: 'flex', alignItems: 'center', gap: '10px'
                        }}>
                            <ChevronRight size={16} color="#9ca3af" />
                            <div>
                                <span style={{ fontSize: '12px', fontWeight: 700, color: '#9ca3af' }}>RECOMMENDATION: </span>
                                <span style={{
                                    fontSize: '13px', fontWeight: 700,
                                    color: data.recommendation.direction === 'LONG' ? '#10b981' :
                                        data.recommendation.direction === 'SHORT' ? '#ef4444' : '#eab308'
                                }}>
                                    {data.recommendation.direction}
                                </span>
                                <span style={{ fontSize: '12px', color: '#9ca3af', marginLeft: '8px' }}>
                                    — {data.recommendation.note}
                                </span>
                            </div>
                        </div>
                    )}

                    {/* Indicator Cards Grid */}
                    <div>
                        <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#9ca3af', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '1px' }}>
                            <BarChart2 size={14} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'middle' }} />
                            Macro Indicators
                        </h3>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '10px' }}>
                            <IndicatorCard name="spx" label="S&P 500 (SPX)" data={data.indicators?.spx} />
                            <IndicatorCard name="usdt_d" label="USDT Dominance" data={data.indicators?.usdt_d} />
                            <IndicatorCard name="btc_d" label="BTC Dominance" data={data.indicators?.btc_d} />
                            <IndicatorCard name="total3" label="TOTAL3 (excl BTC+ETH)" data={data.indicators?.total3} />
                            <IndicatorCard name="others" label="OTHERS (Altcoin MCap)" data={data.indicators?.others} />
                        </div>
                    </div>

                    {/* Conditions Checklists */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                        <ConditionsChecklist
                            title={`Bullish Conditions (${data.bullish_score})`}
                            conditions={data.bullish_conditions}
                            color="#10b981"
                        />
                        <ConditionsChecklist
                            title={`Bearish Conditions (${data.bearish_score})`}
                            conditions={data.bearish_conditions}
                            color="#ef4444"
                        />
                    </div>

                    {/* S/R Levels */}
                    <SRLevels levels={data.spx_support_resistance} />
                </div>
            )}

            {/* CSS Animation */}
            <style>{`
                @keyframes pulse {
                    0%, 100% { opacity: 0.05; transform: scale(1); }
                    50% { opacity: 0.1; transform: scale(1.05); }
                }
            `}</style>
        </div>
    );
};

export default MacroDashboard;
