import React, { useState, useEffect, useCallback } from 'react';
import {
    Shield, AlertTriangle, Settings, RefreshCw, Activity, TrendingDown,
    Layers, Zap, CheckCircle2, XCircle, Bell, Save
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';


// ======== GAUGE COMPONENT ========
const RiskGauge = ({ label, value, max, unit = '%', icon: Icon, warning = false, critical = false }) => {
    const pct = Math.min((Math.abs(value) / max) * 100, 100);
    const textColor = critical ? 'text-red-400' : warning ? 'text-yellow-400' : 'text-cyan-400';

    return (
        <div className={`p-4 rounded-xl border transition-all ${critical ? 'bg-red-900/10 border-red-500/30 animate-pulse' : warning ? 'bg-yellow-900/10 border-yellow-500/20' : 'bg-gray-900/40 border-gray-800'}`}>
            <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-1.5 text-[10px] uppercase font-bold text-gray-500">
                    {Icon && <Icon size={10} />} {label}
                </div>
                <span className={`text-[10px] font-mono ${textColor}`}>{value}{unit} / {max}{unit}</span>
            </div>
            <div className={`text-2xl font-black ${textColor}`}>{value}{unit}</div>
            <div className="w-full bg-gray-800 rounded-full h-2 mt-2 overflow-hidden">
                <div className={`h-2 rounded-full transition-all duration-500 ${critical ? 'bg-red-500' : warning ? 'bg-yellow-500' : 'bg-cyan-500'}`} style={{ width: `${pct}%` }} />
            </div>
        </div>
    );
};

const RiskDashboard = () => {
    const [dashboard, setDashboard] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [localConfig, setLocalConfig] = useState({});
    const [activeTab, setActiveTab] = useState('metrics'); // metrics | alerts | config

    const fetchDashboard = useCallback(async () => {
        setLoading(true);
        try {
            const res = await fetch(`${API_BASE}/api/risk-dashboard`);
            if (res.ok) {
                const data = await res.json();
                setDashboard(data);
                setLocalConfig(data.config || {});
            }
        } catch (err) {
            console.error("Risk dashboard fetch error:", err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchDashboard();
        const interval = setInterval(fetchDashboard, 30000);
        return () => clearInterval(interval);
    }, [fetchDashboard]);

    const handleSaveConfig = async () => {
        setSaving(true);
        try {
            const res = await fetch(`${API_BASE}/api/risk-config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(localConfig),
            });
            if (res.ok) {
                const data = await res.json();
                setDashboard(prev => ({ ...prev, config: data.config }));
            }
        } catch (err) {
            console.error("Config save error:", err);
        } finally {
            setSaving(false);
        }
    };

    const m = dashboard?.metrics || {};
    const alerts = dashboard?.alerts || [];

    const ddWarning = (m.current_drawdown_pct || 0) > (m.max_drawdown_limit || 15) * 0.6;
    const ddCritical = (m.current_drawdown_pct || 0) > (m.max_drawdown_limit || 15) * 0.9;
    const dlWarning = Math.abs(m.daily_pnl_pct || 0) > (m.daily_loss_limit || 3) * 0.6 && (m.daily_pnl_pct || 0) < 0;
    const dlCritical = Math.abs(m.daily_pnl_pct || 0) > (m.daily_loss_limit || 3) * 0.9 && (m.daily_pnl_pct || 0) < 0;
    const posWarning = (m.open_positions || 0) >= (m.max_positions || 5) - 1;
    const posCritical = (m.open_positions || 0) >= (m.max_positions || 5);

    return (
        <div className="animate-in slide-in-from-right-4 fade-in duration-300">

            {/* Header */}
            <div className="flex justify-between items-center mb-6">
                <div className="flex items-center gap-3">
                    <h2 className="text-xl font-black text-white flex items-center gap-2">
                        <Shield size={20} className="text-red-400" /> Risk Management
                    </h2>
                    <div className={`px-3 py-1 rounded-full text-xs font-bold border ${m.enabled ? 'bg-green-500/10 border-green-500/30 text-green-400' : 'bg-red-500/10 border-red-500/30 text-red-400'}`}>
                        {m.enabled ? ' ACTIVE' : ' DISABLED'}
                    </div>
                </div>
                <button onClick={fetchDashboard} disabled={loading} className="flex items-center gap-1 text-xs text-gray-400 hover:text-cyan-400 transition px-3 py-1.5 rounded-lg border border-gray-700 hover:border-cyan-500/30">
                    <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
                    {loading ? 'Loading...' : 'Refresh'}
                </button>
            </div>

            {/* Tab switcher */}
            <div className="flex gap-2 mb-6">
                {[
                    { id: 'metrics', label: 'Risk Meters', icon: Activity },
                    { id: 'alerts', label: `Alerts${alerts.length > 0 ? ` (${alerts.length})` : ''}`, icon: Bell },
                    { id: 'config', label: 'Settings', icon: Settings },
                ].map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`flex items-center gap-1.5 px-5 py-2 rounded-lg text-xs font-bold transition border ${activeTab === tab.id
                            ? 'bg-red-500/20 text-red-400 border-red-500/30'
                            : 'text-gray-500 border-gray-800 hover:text-white hover:border-gray-600'
                            }`}
                    >
                        <tab.icon size={14} /> {tab.label}
                    </button>
                ))}
            </div>

            {/* ================ METRICS TAB ================ */}
            {activeTab === 'metrics' && (
                <>
                    {/* Risk Gauges */}
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                        <RiskGauge
                            label="Drawdown"
                            icon={TrendingDown}
                            value={m.current_drawdown_pct || 0}
                            max={m.max_drawdown_limit || 15}
                            warning={ddWarning}
                            critical={ddCritical}
                        />
                        <RiskGauge
                            label="Daily PnL"
                            icon={Activity}
                            value={Math.abs(m.daily_pnl_pct || 0)}
                            max={m.daily_loss_limit || 3}
                            unit="%"
                            warning={dlWarning}
                            critical={dlCritical}
                        />
                        <RiskGauge
                            label="Open Positions"
                            icon={Layers}
                            value={m.open_positions || 0}
                            max={m.max_positions || 5}
                            unit=""
                            warning={posWarning}
                            critical={posCritical}
                        />
                        <RiskGauge
                            label="Exposure"
                            icon={Zap}
                            value={m.exposure_pct || 0}
                            max={100}
                        />
                    </div>

                    {/* HSB INVESTASI INTERVIEW: Advanced Risk Section */}
                    {m.advanced && (
                        <div className="mb-6 bg-gray-900/40 border border-gray-800 rounded-xl p-5">
                            <h3 className="text-sm font-bold text-gray-400 mb-4 flex items-center gap-2">
                                <Activity size={16} className="text-purple-500" /> INSTITUTIONAL RISK ANALYTICS
                            </h3>

                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                                {/* VaR & CVaR */}
                                <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/60">
                                    <div className="text-[10px] uppercase font-bold text-gray-500 mb-1">Historical VaR (95%)</div>
                                    <div className="text-xl font-black text-red-400">{m.advanced.historical_var_95}%</div>
                                    <div className="text-[9px] text-gray-600 mt-1">Expected max daily loss 95% of the time</div>
                                </div>
                                <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/60">
                                    <div className="text-[10px] uppercase font-bold text-gray-500 mb-1">Parametric VaR (95%)</div>
                                    <div className="text-xl font-black text-orange-400">{m.advanced.parametric_var_95}%</div>
                                    <div className="text-[9px] text-gray-600 mt-1">Normal distribution assumption</div>
                                </div>
                                <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/60">
                                    <div className="text-[10px] uppercase font-bold text-gray-500 mb-1">CVaR / Expected Shortfall</div>
                                    <div className="text-xl font-black text-red-500">{m.advanced.cvar_95}%</div>
                                    <div className="text-[9px] text-gray-600 mt-1">Avg loss in the worst 5% of cases (Tail Risk)</div>
                                </div>
                                <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/60">
                                    <div className="text-[10px] uppercase font-bold text-gray-500 mb-1">Sortino Ratio</div>
                                    <div className={`text-xl font-black ${m.advanced.sortino_ratio > 1 ? 'text-green-400' : 'text-yellow-400'}`}>
                                        {m.advanced.sortino_ratio}
                                    </div>
                                    <div className="text-[9px] text-gray-600 mt-1">Return relative to downside volatility</div>
                                </div>
                            </div>

                            {/* Stress Testing */}
                            <div className="mt-4 p-4 rounded-xl border border-red-500/20 bg-red-900/5">
                                <div className="text-[10px] uppercase font-bold text-red-400 mb-3 flex items-center gap-1">
                                    <AlertTriangle size={12} /> PORTFOLIO STRESS TESTS (Active Exposure Impact)
                                </div>
                                <div className="grid grid-cols-3 gap-3">
                                    <div>
                                        <div className="text-[10px] text-gray-500">BTC drops -10%</div>
                                        <div className="text-sm font-bold text-red-400">${m.advanced.stress_tests?.btc_drop_10pct?.toLocaleString()}</div>
                                    </div>
                                    <div>
                                        <div className="text-[10px] text-gray-500">BTC drops -20%</div>
                                        <div className="text-sm font-bold text-red-500">${m.advanced.stress_tests?.btc_drop_20pct?.toLocaleString()}</div>
                                    </div>
                                    <div>
                                        <div className="text-[10px] text-red-500">Flash Crash -30%</div>
                                        <div className="text-sm font-bold text-red-600">${m.advanced.stress_tests?.flash_crash_30pct?.toLocaleString()}</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Summary Cards */}
                    <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
                        <div className="bg-gray-900/40 border border-gray-800 p-5 rounded-xl">
                            <div className="text-gray-500 text-[10px] uppercase font-bold mb-1">Peak Equity</div>
                            <div className="text-2xl font-black text-white">${(m.peak_equity || 0).toLocaleString()}</div>
                        </div>
                        <div className="bg-gray-900/40 border border-gray-800 p-5 rounded-xl">
                            <div className="text-gray-500 text-[10px] uppercase font-bold mb-1">Current Equity</div>
                            <div className="text-2xl font-black text-cyan-400">${(m.total_equity || 0).toLocaleString()}</div>
                        </div>
                        <div className={`border p-5 rounded-xl ${(m.daily_pnl || 0) >= 0 ? 'bg-green-900/10 border-green-500/20' : 'bg-red-900/10 border-red-500/20'}`}>
                            <div className="text-gray-500 text-[10px] uppercase font-bold mb-1">Today's PnL</div>
                            <div className={`text-2xl font-black ${(m.daily_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                {(m.daily_pnl || 0) >= 0 ? '+' : ''}${(m.daily_pnl || 0).toLocaleString()}
                                <span className="text-sm ml-1">({(m.daily_pnl_pct || 0).toFixed(2)}%)</span>
                            </div>
                        </div>
                    </div>

                    {/* Status */}
                    <div className="bg-gray-900/40 border border-gray-800 p-5 rounded-xl">
                        <h3 className="text-sm font-bold text-gray-400 mb-3 flex items-center gap-2">
                            <CheckCircle2 size={14} className="text-green-500" /> RISK CHECK STATUS
                        </h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                            {[
                                { name: 'Drawdown Limit', ok: !ddCritical, detail: `${(m.current_drawdown_pct || 0).toFixed(1)}% / ${m.max_drawdown_limit || 15}%` },
                                { name: 'Daily Loss Limit', ok: !dlCritical, detail: `${(m.daily_pnl_pct || 0).toFixed(2)}% / -${m.daily_loss_limit || 3}%` },
                                { name: 'Max Positions', ok: !posCritical, detail: `${m.open_positions || 0} / ${m.max_positions || 5}` },
                                { name: 'Risk Per Trade', ok: true, detail: `${m.risk_per_trade || 1}% of equity` },
                            ].map((check, i) => (
                                <div key={i} className={`flex items-center justify-between p-3 rounded-lg border ${check.ok ? 'border-green-500/20 bg-green-900/5' : 'border-red-500/30 bg-red-900/10'}`}>
                                    <div className="flex items-center gap-2">
                                        {check.ok ? <CheckCircle2 size={14} className="text-green-400" /> : <XCircle size={14} className="text-red-400" />}
                                        <span className="text-xs font-bold text-white">{check.name}</span>
                                    </div>
                                    <span className={`text-xs font-mono ${check.ok ? 'text-gray-400' : 'text-red-400'}`}>{check.detail}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </>
            )}

            {/* ================ ALERTS TAB ================ */}
            {activeTab === 'alerts' && (
                <div className="bg-gray-900/40 border border-gray-800 rounded-xl p-6">
                    <h3 className="text-sm font-bold text-gray-400 mb-4 flex items-center gap-2">
                        <Bell size={14} className="text-yellow-500" /> RISK ALERTS HISTORY
                    </h3>

                    {alerts.length === 0 ? (
                        <div className="text-center py-16 border-2 border-dashed border-gray-800 rounded-xl">
                            <div className="text-4xl mb-3"></div>
                            <p className="text-gray-500 text-sm">No risk alerts yet.</p>
                            <p className="text-xs text-gray-600 mt-1">Alerts will appear when risk limits are triggered during trade execution.</p>
                        </div>
                    ) : (
                        <div className="space-y-2 max-h-[500px] overflow-y-auto pr-2">
                            {alerts.map((alert, i) => (
                                <div key={alert.id || i} className={`flex items-start gap-3 p-3 rounded-lg border ${alert.severity === 'CRITICAL' ? 'border-red-500/30 bg-red-900/10' : 'border-yellow-500/20 bg-yellow-900/5'}`}>
                                    <div className="mt-0.5">
                                        {alert.severity === 'CRITICAL' ? <XCircle size={16} className="text-red-400" /> : <AlertTriangle size={16} className="text-yellow-400" />}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${alert.severity === 'CRITICAL' ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'}`}>
                                                {alert.alert_type}
                                            </span>
                                            <span className="text-[10px] text-gray-600 font-mono">
                                                {new Date(alert.created_at).toLocaleString()}
                                            </span>
                                        </div>
                                        <p className="text-xs text-gray-300 break-words">{alert.message}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* ================ CONFIG TAB ================ */}
            {activeTab === 'config' && (
                <div className="bg-gray-900/40 border border-gray-800 rounded-xl p-6">
                    <h3 className="text-sm font-bold text-gray-400 mb-6 flex items-center gap-2">
                        <Settings size={14} className="text-purple-500" /> RISK PARAMETERS
                    </h3>

                    <div className="space-y-6">
                        {/* Enable/Disable */}
                        <div className="flex items-center justify-between p-4 rounded-xl border border-gray-700 bg-gray-900/60">
                            <div>
                                <div className="text-sm font-bold text-white">Risk Management</div>
                                <div className="text-xs text-gray-500">Enable or disable all risk checks</div>
                            </div>
                            <button
                                onClick={() => setLocalConfig(c => ({ ...c, enabled: !c.enabled }))}
                                className={`w-12 h-6 rounded-full transition-all relative ${localConfig.enabled ? 'bg-green-500' : 'bg-gray-700'}`}
                            >
                                <div className={`w-5 h-5 bg-white rounded-full absolute top-0.5 transition-all ${localConfig.enabled ? 'left-6' : 'left-0.5'}`} />
                            </button>
                        </div>

                        {/* Sliders */}
                        {[
                            { key: 'max_drawdown_pct', label: 'Max Drawdown', desc: 'Stop bot if portfolio drops below this from peak', min: 5, max: 50, step: 1, unit: '%' },
                            { key: 'max_position_pct', label: 'Max Position Size', desc: 'Max allocation per single coin', min: 1, max: 50, step: 1, unit: '%' },
                            { key: 'max_open_positions', label: 'Max Open Positions', desc: 'Maximum simultaneous positions', min: 1, max: 20, step: 1, unit: '' },
                            { key: 'daily_loss_limit_pct', label: 'Daily Loss Limit', desc: 'Pause bot if daily loss exceeds this', min: 1, max: 20, step: 0.5, unit: '%' },
                            { key: 'risk_per_trade_pct', label: 'Risk Per Trade', desc: 'Max equity risked per trade', min: 0.1, max: 5, step: 0.1, unit: '%' },
                        ].map(param => (
                            <div key={param.key} className="p-4 rounded-xl border border-gray-800">
                                <div className="flex justify-between items-center mb-2">
                                    <div>
                                        <div className="text-sm font-bold text-white">{param.label}</div>
                                        <div className="text-[10px] text-gray-500">{param.desc}</div>
                                    </div>
                                    <div className="text-lg font-black text-cyan-400">
                                        {localConfig[param.key] ?? ''}{param.unit}
                                    </div>
                                </div>
                                <input
                                    type="range"
                                    min={param.min}
                                    max={param.max}
                                    step={param.step}
                                    value={localConfig[param.key] ?? param.min}
                                    onChange={(e) => setLocalConfig(c => ({ ...c, [param.key]: parseFloat(e.target.value) }))}
                                    className="w-full h-2 bg-gray-700 rounded-full appearance-none cursor-pointer accent-cyan-500"
                                />
                                <div className="flex justify-between text-[9px] text-gray-600 mt-1">
                                    <span>{param.min}{param.unit}</span>
                                    <span>{param.max}{param.unit}</span>
                                </div>
                            </div>
                        ))}

                        {/* Save Button */}
                        <button
                            onClick={handleSaveConfig}
                            disabled={saving}
                            className="w-full py-3 bg-gradient-to-r from-red-600 to-orange-600 hover:from-red-500 hover:to-orange-500 text-white font-bold rounded-xl flex items-center justify-center gap-2 transition-all shadow-[0_0_20px_rgba(239,68,68,0.3)] disabled:opacity-50"
                        >
                            <Save size={16} /> {saving ? 'Saving...' : 'Save Risk Configuration'}
                        </button>
                    </div>
                </div>
            )}

            {/* Info footer */}
            <div className="mt-6 bg-red-900/10 border border-red-500/20 p-4 rounded-xl">
                <h4 className="font-bold text-red-400 text-sm mb-1"> How Risk Management Works</h4>
                <p className="text-xs text-red-200/80 leading-relaxed">
                    Before every trade, the bot runs 4 risk checks: <strong>Max Drawdown</strong> (stop if portfolio drops too far),{' '}
                    <strong>Position Size</strong> (max % of equity per coin), <strong>Max Positions</strong> (cap simultaneous trades),{' '}
                    and <strong>Daily Loss Limit</strong> (pause if losing too much today). Any failed check blocks the trade and logs an alert.
                </p>
            </div>
        </div>
    );
};

export default RiskDashboard;
