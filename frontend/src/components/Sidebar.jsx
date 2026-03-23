import React, { useState, useRef, useEffect } from 'react';
import {
    Play, TrendingUp, Activity, Search, Globe, Shield, PieChart, Trophy, Gem,
    BarChart2, Layers, ChevronDown, Menu, X, Radar,
    ArrowLeftRight, LineChart, Eye, Brain, Zap
} from 'lucide-react';

const NAV_GROUPS = [
    {
        label: 'Core',
        items: [
            { id: 'BACKTEST', label: 'Backtest Lab', icon: Play, color: '#22d3ee' },
            { id: 'MATRIX', label: 'Strategy Matrix', icon: Layers, color: '#a78bfa' },
            { id: 'PNL', label: 'PnL Segmentation', icon: ArrowLeftRight, color: '#3b82f6' },
        ]
    },
    {
        label: 'Intelligence',
        items: [
            { id: 'SCANNER', label: 'Scanner Signals', icon: Search, color: '#6366f1' },
            { id: 'ANALYTICS', label: 'Market Analytics', icon: BarChart2, color: '#a855f7' },
            { id: 'ELITE', label: 'Elite Gems', icon: Gem, color: '#eab308' },
            { id: 'ANOMALY', label: 'Anomaly Scanner', icon: Radar, color: '#f97316' },
            { id: 'MACRO', label: 'Macro Intel', icon: Globe, color: '#06b6d4' },
            { id: 'GLOBAL_MARKET', label: 'Global Market', icon: LineChart, color: '#f59e0b' },
            { id: 'AI_INSIGHTS', label: 'AI Insights', icon: Brain, color: '#ec4899' },
        ]
    },
    {
        label: 'Operations',
        items: [
            { id: 'PAPER_TRADING', label: 'Paper Trading', icon: Zap, color: '#f97316' },
            { id: 'BOT_TRACKER', label: 'Bot Tracker', icon: Activity, color: '#22c55e' },
            { id: 'PORTFOLIO', label: 'Portfolio', icon: PieChart, color: '#10b981' },
            { id: 'RISK', label: 'Risk Dashboard', icon: Shield, color: '#ef4444' },
            { id: 'FUND', label: 'Fund Analytics', icon: Trophy, color: '#f59e0b' },
        ]
    },
    {
        label: 'Tools',
        items: [
            { id: 'WATCHLIST', label: 'Watchlist', icon: Eye, color: '#8b5cf6' },
        ]
    },
];

// Flatten for quick lookup
const ALL_ITEMS = NAV_GROUPS.flatMap(g => g.items);

const DropdownGroup = ({ group, activeView, onSelect }) => {
    const [open, setOpen] = useState(false);
    const ref = useRef(null);

    const hasActive = group.items.some(i => i.id === activeView);
    const activeItem = group.items.find(i => i.id === activeView);

    // Close on outside click
    useEffect(() => {
        const handler = (e) => {
            if (ref.current && !ref.current.contains(e.target)) setOpen(false);
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, []);

    return (
        <div className="topnav-group" ref={ref}>
            <button
                className={`topnav-group-btn ${hasActive ? 'topnav-group-btn--active' : ''}`}
                onClick={() => setOpen(!open)}
                style={hasActive && activeItem ? { '--accent': activeItem.color } : undefined}
            >
                <span className="topnav-group-label">{group.label}</span>
                <ChevronDown size={12} className={`topnav-chevron ${open ? 'topnav-chevron--open' : ''}`} />
                {hasActive && <div className="topnav-group-indicator" style={{ background: activeItem?.color }} />}
            </button>

            {open && (
                <div className="topnav-dropdown">
                    {group.items.map(item => {
                        const Icon = item.icon;
                        const isActive = activeView === item.id;
                        return (
                            <button
                                key={item.id}
                                className={`topnav-dropdown-item ${isActive ? 'topnav-dropdown-item--active' : ''}`}
                                onClick={() => { onSelect(item.id); setOpen(false); }}
                            >
                                <Icon size={15} style={{ color: item.color }} />
                                <span>{item.label}</span>
                                {isActive && <div className="topnav-item-dot" style={{ background: item.color }} />}
                            </button>
                        );
                    })}
                </div>
            )}
        </div>
    );
};

const Sidebar = ({ activeView, onViewChange }) => {
    const [mobileOpen, setMobileOpen] = useState(false);

    const handleSelect = (id) => {
        onViewChange(id);
        setMobileOpen(false);
    };

    const activeItem = ALL_ITEMS.find(i => i.id === activeView);

    return (
        <>
            {/* Top Navigation Bar */}
            <nav className="topnav">
                <div className="topnav-inner">
                    {/* Brand */}
                    <div className="topnav-brand">
                        <div className="topnav-brand-icon">Q</div>
                        <div className="topnav-brand-text">
                            <div className="topnav-brand-title">QUANTTRADE</div>
                            <div className="topnav-brand-subtitle">R&D Protocol</div>
                        </div>
                    </div>

                    {/* Desktop Nav Groups */}
                    <div className="topnav-groups">
                        {NAV_GROUPS.map(group => (
                            <DropdownGroup
                                key={group.label}
                                group={group}
                                activeView={activeView}
                                onSelect={handleSelect}
                            />
                        ))}
                    </div>

                    {/* Active View Badge (desktop) */}
                    {activeItem && (
                        <div className="topnav-active-badge" style={{ borderColor: activeItem.color + '40', color: activeItem.color }}>
                            <activeItem.icon size={12} />
                            <span>{activeItem.label}</span>
                        </div>
                    )}

                    {/* Mobile hamburger */}
                    <button
                        className="topnav-mobile-btn"
                        onClick={() => setMobileOpen(!mobileOpen)}
                        aria-label="Toggle navigation"
                    >
                        {mobileOpen ? <X size={20} /> : <Menu size={20} />}
                    </button>
                </div>

                {/* Mobile dropdown */}
                {mobileOpen && (
                    <div className="topnav-mobile-dropdown">
                        {NAV_GROUPS.map(group => (
                            <div key={group.label} className="topnav-mobile-group">
                                <div className="topnav-mobile-group-label">{group.label}</div>
                                {group.items.map(item => {
                                    const Icon = item.icon;
                                    const isActive = activeView === item.id;
                                    return (
                                        <button
                                            key={item.id}
                                            className={`topnav-mobile-item ${isActive ? 'topnav-mobile-item--active' : ''}`}
                                            onClick={() => handleSelect(item.id)}
                                        >
                                            <Icon size={16} style={{ color: item.color }} />
                                            <span>{item.label}</span>
                                        </button>
                                    );
                                })}
                            </div>
                        ))}
                    </div>
                )}
            </nav>
        </>
    );
};

export default Sidebar;
