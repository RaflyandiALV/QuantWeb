import React, { useState, useEffect } from 'react';
import { Eye, Trash2, Plus, Bell, Activity, TrendingUp, Clock, Settings, Calendar, Sliders, X } from 'lucide-react';

const Watchlist = ({ onSelectAsset }) => {
    const [coins, setCoins] = useState([]);
    const [newCoin, setNewCoin] = useState('');
    const [loading, setLoading] = useState(false);
    
    // State untuk Advanced Settings
    const [showSettings, setShowSettings] = useState(false);
    const [mode, setMode] = useState("AUTO");
    const [strategy, setStrategy] = useState("MOMENTUM");
    const [timeframe, setTimeframe] = useState("1d");
    const [period, setPeriod] = useState("1y");

    const API_URL = `${import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'}/api/watchlist`;

    useEffect(() => {
        fetchWatchlist();
    }, []);

    const fetchWatchlist = async () => {
        try {
            const res = await fetch(API_URL);
            if(res.ok) {
                const data = await res.json();
                setCoins(data);
            }
        } catch (err) {
            console.error("Error fetching watchlist", err);
        }
    };

    const addCoin = async () => {
        if (!newCoin) return;
        if (coins.length >= 10) return alert("Maksimal 10 Koin untuk Personal Watchlist!");
        
        setLoading(true);
        try {
            // Payload menyesuaikan mode
            const payload = {
                symbol: newCoin.toUpperCase().trim(),
                mode: mode
            };
            
            // Jika Manual, masukkan setting
            if (mode === "MANUAL") {
                payload.strategy = strategy;
                payload.timeframe = timeframe;
                payload.period = period;
            }

            const res = await fetch(API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if(res.ok) {
                setNewCoin('');
                setShowSettings(false); // Tutup setting setelah add
                setMode("AUTO"); // Reset ke default
                fetchWatchlist();
            } else {
                const err = await res.json();
                alert(err.detail);
            }
        } catch (err) {
            alert("Gagal menambah koin");
        }
        setLoading(false);
    };

    const removeCoin = async (symbol, e) => {
        e.stopPropagation(); 
        try {
            await fetch(`${API_URL}/${symbol}`, { method: 'DELETE' });
            fetchWatchlist();
        } catch (err) {
            alert("Gagal menghapus koin");
        }
    };

    return (
        <div className="h-full flex flex-col">
            <div className="flex flex-col xl:flex-row justify-between items-start xl:items-center mb-6 gap-4">
                <h2 className="text-lg font-bold text-white flex items-center gap-2 tracking-wider">
                    <Eye className="text-cyan-400" size={20}/> PERSONAL WATCHLIST 
                    <span className="text-xs bg-gray-800 px-2 py-1 rounded text-gray-400">{coins.length}/10</span>
                </h2>
                
                {/* INPUT AREA */}
                <div className="flex flex-col gap-2 w-full xl:w-auto">
                    <div className="flex gap-2">
                        <input 
                            type="text" 
                            value={newCoin}
                            onChange={(e) => setNewCoin(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && addCoin()}
                            placeholder="ADD SYMBOL (e.g. SOL-USD)"
                            className="flex-1 xl:w-48 bg-black/50 text-white px-3 py-2 rounded-lg border border-gray-700 focus:border-cyan-500 focus:outline-none text-sm font-mono uppercase"
                        />
                        
                        {/* Tombol Toggle Settings */}
                        <button 
                            onClick={() => setShowSettings(!showSettings)}
                            className={`p-2 rounded-lg border transition ${showSettings ? 'bg-gray-700 border-gray-500 text-white' : 'bg-gray-900 border-gray-700 text-gray-400 hover:text-white'}`}
                            title="Bot Settings"
                        >
                            <Sliders size={18} />
                        </button>

                        <button 
                            onClick={addCoin}
                            disabled={loading || coins.length >= 10}
                            className="bg-cyan-600 hover:bg-cyan-500 text-white px-3 py-2 rounded-lg disabled:opacity-50 transition shadow-[0_0_10px_cyan]"
                        >
                            {loading ? <Activity className="animate-spin" size={16}/> : <Plus size={18}/>}
                        </button>
                    </div>

                    {/* SETTINGS PANEL (Muncul jika toggle ON) */}
                    {showSettings && (
                        <div className="bg-gray-800/80 p-3 rounded-lg border border-gray-600 flex flex-wrap gap-2 items-center animate-in slide-in-from-top-2 text-xs">
                            <div className="flex flex-col">
                                <label className="text-gray-400 mb-1">MODE</label>
                                <select value={mode} onChange={(e) => setMode(e.target.value)} className="bg-black text-white p-1 rounded border border-gray-600 cursor-pointer">
                                    <option value="AUTO">🤖 AUTO (AI Scan)</option>
                                    <option value="MANUAL">🛠️ MANUAL (Custom)</option>
                                </select>
                            </div>

                            {mode === "MANUAL" && (
                                <>
                                    <div className="flex flex-col">
                                        <label className="text-gray-400 mb-1">STRAT</label>
                                        <select value={strategy} onChange={(e) => setStrategy(e.target.value)} className="bg-black text-white p-1 rounded border border-gray-600 cursor-pointer">
                                            <option value="MOMENTUM">Momentum</option>
                                            <option value="MEAN_REVERSAL">Mean Reversal</option>
                                            <option value="GRID">Grid Trading</option>
                                            <option value="MULTITIMEFRAME">Multi TF</option>
                                        </select>
                                    </div>
                                    <div className="flex flex-col">
                                        <label className="text-gray-400 mb-1">TF</label>
                                        <select value={timeframe} onChange={(e) => setTimeframe(e.target.value)} className="bg-black text-white p-1 rounded border border-gray-600 cursor-pointer">
                                            <option value="1h">1H</option>
                                            <option value="4h">4H</option>
                                            <option value="1d">1D</option>
                                        </select>
                                    </div>
                                    <div className="flex flex-col">
                                        <label className="text-gray-400 mb-1">PERIOD</label>
                                        <select value={period} onChange={(e) => setPeriod(e.target.value)} className="bg-black text-white p-1 rounded border border-gray-600 cursor-pointer">
                                            <option value="6mo">6 Mo</option>
                                            <option value="1y">1 Year</option>
                                        </select>
                                    </div>
                                </>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* List - Grid Layout */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                {coins.map((coinData) => (
                    <div 
                        key={coinData.symbol} 
                        onClick={() => onSelectAsset(coinData.symbol)}
                        className={`group relative bg-gray-800/40 border p-4 rounded-xl hover:bg-gray-800 transition cursor-pointer flex flex-col justify-between ${coinData.mode === 'MANUAL' ? 'border-purple-500/30' : 'border-gray-700/50 hover:border-cyan-500/50'}`}
                    >
                        {/* Header Kartu */}
                        <div className="flex justify-between items-start mb-3">
                            <div className="flex items-center gap-2">
                                <div className={`w-2 h-2 rounded-full shadow-[0_0_5px] animate-pulse ${coinData.mode === 'MANUAL' ? 'bg-purple-500 shadow-purple-500' : 'bg-green-500 shadow-lime-500'}`}></div>
                                <div className="flex flex-col">
                                    <span className="font-bold text-lg text-gray-200 font-mono group-hover:text-cyan-300 transition leading-none">{coinData.symbol}</span>
                                    <span className={`text-[9px] font-bold mt-1 ${coinData.mode === 'MANUAL' ? 'text-purple-400' : 'text-gray-500'}`}>
                                        {coinData.mode === 'MANUAL' ? '🛠️ MANUAL' : '🤖 AUTO AI'}
                                    </span>
                                </div>
                            </div>
                            <button 
                                onClick={(e) => removeCoin(coinData.symbol, e)}
                                className="text-gray-600 hover:text-red-500 hover:bg-red-500/10 p-1 rounded transition"
                            >
                                <Trash2 size={14} />
                            </button>
                        </div>
                        
                        {/* INFO DETAIL (Strategy, TF, Profit) */}
                        <div className="space-y-2 mb-3">
                            <div className="bg-black/40 rounded p-2 text-[10px] space-y-1 font-mono border border-gray-800">
                                <div className="flex justify-between text-gray-400">
                                    <span className="flex items-center gap-1"><Settings size={8}/> STRAT</span>
                                    <span className="text-white font-bold">{coinData.strategy}</span>
                                </div>
                                <div className="flex justify-between text-gray-400">
                                    <span className="flex items-center gap-1"><Clock size={8}/> TIME</span>
                                    <span className="text-white">{coinData.timeframe}</span>
                                </div>
                                <div className="flex justify-between text-gray-400">
                                    <span className="flex items-center gap-1"><Calendar size={8}/> PERIOD</span>
                                    <span className="text-white">{coinData.period}</span>
                                </div>
                            </div>

                            {/* CAPITAL GROWTH (Changed from Equity Growth) */}
                            <div className="flex flex-col gap-1 bg-gray-900/50 p-2 rounded border border-gray-800">
                                <span className="text-[10px] text-gray-500 flex items-center gap-1 uppercase"><TrendingUp size={10}/> Capital Growth</span>
                                <div className="flex items-end justify-between">
                                    <span className={`text-sm font-bold font-mono ${coinData.growth_usd >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                        {coinData.growth_usd >= 0 ? '+' : ''}${Math.round(coinData.growth_usd).toLocaleString()}
                                    </span>
                                    <span className={`text-[10px] ${coinData.growth_pct >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                        ({coinData.growth_pct}%)
                                    </span>
                                </div>
                            </div>
                        </div>

                        {/* Footer Status */}
                        <div className="flex items-center justify-between text-[10px] text-gray-500 pt-2 border-t border-gray-800/50">
                             <div className="flex items-center gap-1">
                                <Bell size={10} className="text-yellow-500/70" /> Auto-Monitor
                             </div>
                             <div className="text-cyan-500/50 font-bold group-hover:text-cyan-400">VIEW CHART</div>
                        </div>
                    </div>
                ))}
                
                {coins.length === 0 && (
                    <div className="col-span-full py-8 text-center border-2 border-dashed border-gray-800 rounded-xl">
                        <p className="text-gray-500 text-sm">Watchlist kosong. Tambahkan koin untuk melihat analisis otomatis.</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default Watchlist;