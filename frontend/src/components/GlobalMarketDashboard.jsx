import React, { useState, useEffect, useMemo } from 'react';
import {
    Globe, TrendingUp, TrendingDown, Activity, RefreshCw, Minus,
    AlertTriangle, Info, Zap, Shield, ArrowUpRight, ArrowDownRight,
    BarChart2, Layers
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

// ============================================================
// % CHANGE CELL — color-coded price change
// ============================================================
const ChangeCell = ({ value, size = 'normal' }) => {
    if (value === null || value === undefined) {
        return (
            <div style={{
                padding: size === 'compact' ? '4px 6px' : '6px 10px',
                borderRadius: '6px', background: 'rgba(255,255,255,0.03)',
                color: '#4b5563', fontSize: size === 'compact' ? '11px' : '13px',
                fontFamily: 'monospace', textAlign: 'center', fontWeight: 600
            }}>—</div>
        );
    }

    const isPositive = value > 0;
    const isNeutral = Math.abs(value) < 0.1;
    const intensity = Math.min(Math.abs(value) / 10, 1); // 0-1 scale, capped at 10%

    let bgColor, textColor;
    if (isNeutral) {
        bgColor = 'rgba(255,255,255,0.05)';
        textColor = '#9ca3af';
    } else if (isPositive) {
        bgColor = `rgba(16, 185, 129, ${0.08 + intensity * 0.2})`;
        textColor = `rgb(${52 + intensity * 40}, ${211 - intensity * 20}, ${153 - intensity * 20})`;
    } else {
        bgColor = `rgba(239, 68, 68, ${0.08 + intensity * 0.2})`;
        textColor = `rgb(${248 - intensity * 20}, ${113 + intensity * 20}, ${113 + intensity * 20})`;
    }

    return (
        <div style={{
            padding: size === 'compact' ? '4px 6px' : '6px 10px',
            borderRadius: '6px', background: bgColor,
            color: textColor, fontSize: size === 'compact' ? '11px' : '13px',
            fontFamily: 'monospace', textAlign: 'center', fontWeight: 700,
            transition: 'all 0.3s'
        }}>
            {isPositive ? '+' : ''}{value.toFixed(2)}%
        </div>
    );
};

// ============================================================
// REGIME BADGE
// ============================================================
const RegimeBadge = ({ regime }) => {
    if (!regime) return null;

    const regimeStyles = {
        RISK_ON: { bg: 'rgba(16, 185, 129, 0.12)', border: '#10b981', text: '#34d399', label: 'RISK ON', icon: TrendingUp },
        RISK_OFF: { bg: 'rgba(239, 68, 68, 0.12)', border: '#ef4444', text: '#f87171', label: 'RISK OFF', icon: Shield },
        MIXED: { bg: 'rgba(234, 179, 8, 0.12)', border: '#eab308', text: '#facc15', label: 'MIXED', icon: Activity },
        LEANING_RISK_ON: { bg: 'rgba(16, 185, 129, 0.08)', border: '#059669', text: '#6ee7b7', label: 'LEANING RISK ON', icon: ArrowUpRight },
        LEANING_RISK_OFF: { bg: 'rgba(239, 68, 68, 0.08)', border: '#dc2626', text: '#fca5a5', label: 'LEANING RISK OFF', icon: ArrowDownRight },
        UNKNOWN: { bg: 'rgba(107, 114, 128, 0.12)', border: '#6b7280', text: '#9ca3af', label: 'UNKNOWN', icon: Minus },
    };

    const s = regimeStyles[regime.regime] || regimeStyles.UNKNOWN;
    const Icon = s.icon;

    return (
        <div style={{
            background: s.bg, border: `1px solid ${s.border}`, borderRadius: '16px',
            padding: '20px 24px', display: 'flex', alignItems: 'center', gap: '16px',
            position: 'relative', overflow: 'hidden'
        }}>
            <div style={{
                position: 'absolute', inset: 0, opacity: 0.04,
                background: `radial-gradient(circle at 20% 50%, ${s.border}, transparent 60%)`
            }} />
            <div style={{
                width: '52px', height: '52px', borderRadius: '14px',
                background: `${s.border}20`, display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexShrink: 0
            }}>
                <Icon size={26} color={s.text} />
            </div>
            <div style={{ flex: 1 }}>
                <div style={{ fontSize: '10px', color: '#6b7280', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '1.5px' }}>
                    Global Market Regime
                </div>
                <div style={{ fontSize: '22px', fontWeight: 800, color: s.text, letterSpacing: '1px', marginTop: '2px' }}>
                    {s.label}
                </div>
                <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '4px', lineHeight: '1.4' }}>
                    {regime.interpretation}
                </div>
            </div>
            <div style={{
                textAlign: 'center', padding: '8px 14px', borderRadius: '10px',
                background: 'rgba(255,255,255,0.05)', flexShrink: 0
            }}>
                <div style={{ fontSize: '22px', fontWeight: 800, color: s.text }}>{regime.confidence}%</div>
                <div style={{ fontSize: '9px', color: '#6b7280', fontWeight: 600 }}>CONFIDENCE</div>
            </div>
        </div>
    );
};

// ============================================================
// ASSET ROW — single row in the heatmap table
// ============================================================
const AssetRow = ({ asset, data }) => {
    if (!data) return null;

    const formatPrice = (price, key) => {
        if (!price) return '—';
        if (key === 'US10Y') return `${price.toFixed(2)}%`; // Yield, not price
        if (price >= 1000) return `$${price.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
        if (price >= 1) return `$${price.toFixed(2)}`;
        return `$${price.toFixed(4)}`;
    };

    const categoryColors = {
        COMMODITY: '#FFD700',
        EQUITY: '#4CAF50',
        CURRENCY: '#2196F3',
        BOND: '#9C27B0',
        CRYPTO: '#F7931A',
    };

    return (
        <div style={{
            display: 'grid',
            gridTemplateColumns: '200px 100px repeat(5, 1fr)',
            gap: '6px', alignItems: 'center', padding: '8px 12px',
            borderRadius: '8px', transition: 'all 0.2s',
            borderBottom: '1px solid rgba(255,255,255,0.04)',
        }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
        >
            {/* Asset Name */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '18px' }}>{data.icon}</span>
                <div>
                    <div style={{ fontSize: '13px', fontWeight: 700, color: '#e5e7eb' }}>{data.label}</div>
                    <div style={{
                        fontSize: '9px', fontWeight: 700, color: categoryColors[data.category] || '#6b7280',
                        textTransform: 'uppercase', letterSpacing: '0.5px'
                    }}>
                        {data.category}
                    </div>
                </div>
            </div>

            {/* Current Price */}
            <div style={{ fontSize: '13px', fontWeight: 700, color: '#d1d5db', fontFamily: 'monospace', textAlign: 'right' }}>
                {formatPrice(data.current_price, asset)}
            </div>

            {/* % Changes */}
            <ChangeCell value={data.changes?.['1d']} size="compact" />
            <ChangeCell value={data.changes?.['7d']} size="compact" />
            <ChangeCell value={data.changes?.['30d']} size="compact" />
            <ChangeCell value={data.changes?.['90d']} size="compact" />
            <ChangeCell value={data.changes?.['ytd']} size="compact" />
        </div>
    );
};

// ============================================================
// INSIGHT CARD
// ============================================================
const InsightCard = ({ insight }) => {
    const typeStyles = {
        WARNING: { bg: 'rgba(239, 68, 68, 0.08)', border: 'rgba(239, 68, 68, 0.25)', icon: AlertTriangle, color: '#f87171' },
        BULLISH: { bg: 'rgba(16, 185, 129, 0.08)', border: 'rgba(16, 185, 129, 0.25)', icon: TrendingUp, color: '#34d399' },
        INFO: { bg: 'rgba(59, 130, 246, 0.08)', border: 'rgba(59, 130, 246, 0.25)', icon: Info, color: '#60a5fa' },
        UNUSUAL: { bg: 'rgba(234, 179, 8, 0.08)', border: 'rgba(234, 179, 8, 0.25)', icon: Zap, color: '#facc15' },
    };

    const s = typeStyles[insight.type] || typeStyles.INFO;
    const Icon = s.icon;

    return (
        <div style={{
            background: s.bg, border: `1px solid ${s.border}`, borderRadius: '12px',
            padding: '14px 16px', display: 'flex', gap: '12px', alignItems: 'flex-start'
        }}>
            <Icon size={18} color={s.color} style={{ marginTop: '2px', flexShrink: 0 }} />
            <div>
                <div style={{ fontSize: '13px', fontWeight: 700, color: s.color }}>{insight.title}</div>
                <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '4px', lineHeight: '1.5' }}>{insight.message}</div>
            </div>
        </div>
    );
};

// ============================================================
// CORRELATION MINI MATRIX
// ============================================================
const CorrelationMatrix = ({ correlation }) => {
    if (!correlation || Object.keys(correlation).length === 0) return null;

    const keys = Object.keys(correlation);
    const shortLabels = {
        GOLD: 'Au', SILVER: 'Ag', OIL: 'Oil', SPX: 'SPX',
        EEM: 'EEM', DXY: 'DXY', US10Y: '10Y', BTC: 'BTC', ETH: 'ETH'
    };

    const getCorrColor = (val) => {
        if (val === undefined || val === null) return 'rgba(255,255,255,0.03)';
        if (val >= 0.7) return 'rgba(16, 185, 129, 0.5)';
        if (val >= 0.3) return 'rgba(16, 185, 129, 0.2)';
        if (val <= -0.7) return 'rgba(239, 68, 68, 0.5)';
        if (val <= -0.3) return 'rgba(239, 68, 68, 0.2)';
        return 'rgba(255,255,255,0.05)';
    };

    return (
        <div style={{
            background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: '12px', padding: '16px', overflow: 'auto'
        }}>
            <div style={{ fontSize: '13px', fontWeight: 700, color: '#9ca3af', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '1px' }}>
                <Layers size={14} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'middle' }} />
                30-Day Return Correlation Matrix
            </div>
            <div style={{ overflowX: 'auto' }}>
                <table style={{ borderCollapse: 'collapse', width: '100%', minWidth: '500px' }}>
                    <thead>
                        <tr>
                            <th style={{ padding: '4px 6px', fontSize: '10px', color: '#6b7280' }}></th>
                            {keys.map(k => (
                                <th key={k} style={{
                                    padding: '4px 6px', fontSize: '10px', color: '#9ca3af',
                                    fontWeight: 700, textAlign: 'center'
                                }}>
                                    {shortLabels[k] || k}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {keys.map(row => (
                            <tr key={row}>
                                <td style={{
                                    padding: '4px 6px', fontSize: '10px', color: '#9ca3af',
                                    fontWeight: 700, whiteSpace: 'nowrap'
                                }}>
                                    {shortLabels[row] || row}
                                </td>
                                {keys.map(col => {
                                    const val = correlation[row]?.[col];
                                    const isDiag = row === col;
                                    return (
                                        <td key={col} style={{
                                            padding: '3px', textAlign: 'center'
                                        }}>
                                            <div style={{
                                                background: isDiag ? 'rgba(255,255,255,0.1)' : getCorrColor(val),
                                                borderRadius: '4px', padding: '4px 2px',
                                                fontSize: '10px', fontFamily: 'monospace',
                                                color: isDiag ? '#6b7280' : '#d1d5db',
                                                fontWeight: 600
                                            }}>
                                                {isDiag ? '—' : (val !== undefined ? val.toFixed(2) : '—')}
                                            </div>
                                        </td>
                                    );
                                })}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

// ============================================================
// SIGNAL BREAKDOWN
// ============================================================
const SignalBreakdown = ({ signals }) => {
    if (!signals || Object.keys(signals).length === 0) return null;

    const signalLabels = {
        spx: 'S&P 500', btc: 'Bitcoin', gold: 'Gold',
        dxy: 'US Dollar', eem_vs_spx: 'EEM vs SPX', us10y: '10Y Yield'
    };

    return (
        <div style={{
            background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: '12px', padding: '16px'
        }}>
            <div style={{ fontSize: '13px', fontWeight: 700, color: '#9ca3af', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '1px' }}>
                <BarChart2 size={14} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'middle' }} />
                Regime Signal Breakdown (7D)
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {Object.entries(signals).map(([key, sig]) => {
                    const impColor = sig.implication === 'RISK_ON' ? '#10b981' :
                        sig.implication === 'RISK_OFF' ? '#ef4444' : '#eab308';
                    return (
                        <div key={key} style={{
                            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                            padding: '8px 10px', borderRadius: '8px',
                            background: 'rgba(255,255,255,0.02)',
                            borderBottom: '1px solid rgba(255,255,255,0.04)',
                        }}>
                            <span style={{ fontSize: '12px', color: '#d1d5db', fontWeight: 600 }}>
                                {signalLabels[key] || key}
                            </span>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span style={{ fontSize: '12px', color: '#9ca3af', fontFamily: 'monospace' }}>
                                    {sig.direction} ({sig.value > 0 ? '+' : ''}{sig.value}%)
                                </span>
                                <span style={{
                                    fontSize: '10px', fontWeight: 700, color: impColor,
                                    padding: '2px 8px', borderRadius: '10px',
                                    background: `${impColor}15`
                                }}>
                                    {sig.implication}
                                </span>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};


// ============================================================
// MAIN: GLOBAL MARKET DASHBOARD
// ============================================================
const GlobalMarketDashboard = () => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [lastUpdated, setLastUpdated] = useState(null);

    const fetchData = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(`${API_BASE}/api/global-market`);
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
        fetchData();
        const interval = setInterval(fetchData, 5 * 60 * 1000); // 5 min auto-refresh
        return () => clearInterval(interval);
    }, []);

    // Sort assets by category for better visual grouping
    const sortedAssets = useMemo(() => {
        if (!data?.assets) return [];
        const order = ['COMMODITY', 'EQUITY', 'CURRENCY', 'BOND', 'CRYPTO'];
        return Object.entries(data.assets).sort((a, b) => {
            const catA = order.indexOf(a[1].category);
            const catB = order.indexOf(b[1].category);
            return catA - catB;
        });
    }, [data]);

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
                        background: 'linear-gradient(135deg, #f59e0b, #ef4444)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center'
                    }}>
                        <Globe size={22} color="white" />
                    </div>
                    <div>
                        <h2 style={{ fontSize: '20px', fontWeight: 800, margin: 0, color: '#f3f4f6' }}>
                            Global Market Analysis
                        </h2>
                        <p style={{ fontSize: '12px', color: '#6b7280', margin: 0 }}>
                            Cross-Asset Performance & Capital Rotation Tracker
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
                        onClick={fetchData}
                        disabled={loading}
                        style={{
                            background: 'rgba(245, 158, 11, 0.15)', border: '1px solid rgba(245, 158, 11, 0.3)',
                            borderRadius: '10px', padding: '8px 16px', color: '#f59e0b',
                            cursor: loading ? 'wait' : 'pointer', display: 'flex', alignItems: 'center', gap: '6px',
                            fontSize: '13px', fontWeight: 600, transition: 'all 0.2s'
                        }}
                    >
                        <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                        {loading ? 'Scanning...' : 'Refresh'}
                    </button>
                </div>
            </div>

            {/* Error */}
            {error && (
                <div style={{
                    background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)',
                    borderRadius: '12px', padding: '14px', marginBottom: '16px',
                    color: '#f87171', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px'
                }}>
                    <AlertTriangle size={16} /> {error}
                </div>
            )}

            {/* Loading */}
            {loading && !data && (
                <div style={{ textAlign: 'center', padding: '40px', color: '#6b7280' }}>
                    <Activity size={32} style={{ animation: 'pulse 1.5s ease-in-out infinite', margin: '0 auto 12px' }} />
                    <p>Fetching global market data from Yahoo Finance & Binance...</p>
                </div>
            )}

            {/* Content */}
            {data && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                    {/* Regime Badge */}
                    <RegimeBadge regime={data.regime} />

                    {/* Heatmap Table */}
                    <div style={{
                        background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)',
                        borderRadius: '12px', padding: '16px', overflow: 'auto'
                    }}>
                        <div style={{ fontSize: '13px', fontWeight: 700, color: '#9ca3af', marginBottom: '14px', textTransform: 'uppercase', letterSpacing: '1px' }}>
                             Price Change Heatmap
                        </div>

                        {/* Table Header */}
                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: '200px 100px repeat(5, 1fr)',
                            gap: '6px', padding: '6px 12px', marginBottom: '4px',
                            borderBottom: '1px solid rgba(255,255,255,0.08)',
                        }}>
                            <div style={{ fontSize: '10px', color: '#6b7280', fontWeight: 700, textTransform: 'uppercase' }}>Asset</div>
                            <div style={{ fontSize: '10px', color: '#6b7280', fontWeight: 700, textTransform: 'uppercase', textAlign: 'right' }}>Price</div>
                            <div style={{ fontSize: '10px', color: '#6b7280', fontWeight: 700, textAlign: 'center' }}>1D</div>
                            <div style={{ fontSize: '10px', color: '#6b7280', fontWeight: 700, textAlign: 'center' }}>7D</div>
                            <div style={{ fontSize: '10px', color: '#6b7280', fontWeight: 700, textAlign: 'center' }}>30D</div>
                            <div style={{ fontSize: '10px', color: '#6b7280', fontWeight: 700, textAlign: 'center' }}>90D</div>
                            <div style={{ fontSize: '10px', color: '#6b7280', fontWeight: 700, textAlign: 'center' }}>YTD</div>
                        </div>

                        {/* Asset Rows */}
                        {sortedAssets.map(([key, assetData]) => (
                            <AssetRow key={key} asset={key} data={assetData} />
                        ))}
                    </div>

                    {/* Two-column layout: Signals + Insights */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                        {/* Signal Breakdown */}
                        <SignalBreakdown signals={data.regime?.signals} />

                        {/* Insights */}
                        {data.insights && data.insights.length > 0 && (
                            <div style={{
                                background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)',
                                borderRadius: '12px', padding: '16px'
                            }}>
                                <div style={{ fontSize: '13px', fontWeight: 700, color: '#9ca3af', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '1px' }}>
                                     Capital Rotation Insights
                                </div>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                    {data.insights.map((insight, i) => (
                                        <InsightCard key={i} insight={insight} />
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Correlation Matrix */}
                    <CorrelationMatrix correlation={data.correlation} />
                </div>
            )}

            <style>{`
                @keyframes pulse {
                    0%, 100% { opacity: 0.5; }
                    50% { opacity: 1; }
                }
            `}</style>
        </div>
    );
};

export default GlobalMarketDashboard;
