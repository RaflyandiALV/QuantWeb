import sys, os
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Attempt to import backtest logic
try:
    from backtest import fetch_ohlcv_1y, compute_indicators, run_backtest, INITIAL_CAPITAL
except ImportError:
    print("[ERROR] Pastikan dijalankan dari dalam folder CRV-BOT")
    sys.exit(1)

def build_interactive_chart():
    print("[1/2] Menjalankan simulasi backtest...")
    df = fetch_ohlcv_1y()
    df = compute_indicators(df)
    df, trades, sig_l, sig_s, sig_sl, sig_cb = run_backtest(df)

    print("[2/2] Membangun grafik interaktif 3D (Plotly)...")
    
    # Buat figure dengan 3 baris: Price (besar), RSI (kecil), Equity (kecil)
    fig = make_subplots(
        rows=3, cols=1, 
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=("Harga CRV/USDT & Sinyal Entry/Exit", "RSI (14)", "Pertumbuhan Equity (Compounding)"),
        row_heights=[0.6, 0.2, 0.2]
    )

    # --- 1. PRICE CHART ---
    fig.add_trace(go.Candlestick(
        x=df['timestamp'],
        open=df['open'], high=df['high'],
        low=df['low'], close=df['close'],
        name="CRV/USDT",
        increasing_line_color='#26A69A', 
        decreasing_line_color='#EF5350'
    ), row=1, col=1)

    # Bollinger Bands
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['bb_upper'], line=dict(color='rgba(255, 255, 255, 0.3)', width=1), name='BB Upper', hoverinfo='skip'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['bb_lower'], line=dict(color='rgba(255, 255, 255, 0.3)', width=1), name='BB Lower', hoverinfo='skip', fill='tonexty', fillcolor='rgba(255, 255, 255, 0.05)'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['bb_mid'], line=dict(color='rgba(255, 255, 255, 0.5)', width=1, dash='dash'), name='BB Mid', hoverinfo='skip'), row=1, col=1)

    # Tandai Trade Entries & Exits dari Log trades
    long_entries_x, long_entries_y = [], []
    short_entries_x, short_entries_y = [], []
    exits_x, exits_y, exit_texts = [], [], []

    for t in trades:
        if t['direction'] == 'LONG':
            long_entries_x.append(t['entry_time'])
            long_entries_y.append(t['entry_price'])
        elif t['direction'] == 'SHORT':
            short_entries_x.append(t['entry_time'])
            short_entries_y.append(t['entry_price'])
        
        exits_x.append(t['exit_time'])
        exits_y.append(t['exit_price'])
        # Warna teks hover berdasarkan profit
        color = 'green' if t['pnl_usdt'] > 0 else 'red'
        exit_texts.append(f"Exit {t['direction']}<br>PnL: ${t['pnl_usdt']:.2f} ({t['pnl_pct']:.2f}%)<br>Reason: {t['exit_reason']}")

    fig.add_trace(go.Scatter(x=long_entries_x, y=long_entries_y, mode='markers', marker=dict(symbol='triangle-up', size=12, color='#00ff00', line=dict(width=1, color='black')), name='Open LONG'), row=1, col=1)
    fig.add_trace(go.Scatter(x=short_entries_x, y=short_entries_y, mode='markers', marker=dict(symbol='triangle-down', size=12, color='#ff0000', line=dict(width=1, color='black')), name='Open SHORT'), row=1, col=1)
    fig.add_trace(go.Scatter(x=exits_x, y=exits_y, mode='markers', marker=dict(symbol='x', size=8, color='yellow'), name='Close Position', text=exit_texts, hoverinfo='text'), row=1, col=1)

    # --- 2. RSI CHART ---
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['rsi'], line=dict(color='#8884d8', width=1.5), name='RSI'), row=2, col=1)
    # Garis overbought oversold
    fig.add_hline(y=71, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

    # --- 3. EQUITY CURVE ---
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['equity'], line=dict(color='#ffd700', width=2), name='Equity', fill='tozeroy', fillcolor='rgba(255, 215, 0, 0.1)'), row=3, col=1)

    # Calculate stats for title
    if trades:
        avg_pnl = sum(t['pnl_pct'] for t in trades) / len(trades)
        tdf = pd.DataFrame(trades)
        tdf['exit_time'] = pd.to_datetime(tdf['exit_time'], utc=True)
        tdf['quarter'] = tdf['exit_time'].dt.to_period('Q').astype(str)
        q_avg = tdf.groupby('quarter')['pnl_pct'].mean()
        quarterly_str = " | ".join([f"{q}: {val:.2f}%" for q, val in q_avg.items()])
    else:
        avg_pnl = 0
        quarterly_str = "N/A"
        
    title_text = f"Interactive CRV/USDT Backtest (Scroll to Zoom, Pan) <br><sup>Avg PNL/Trade: {avg_pnl:.2f}%  ||  Quarterly Avg PNL: {quarterly_str}</sup>"

    # Layout styling (Dark mode)
    fig.update_layout(
        title=title_text,
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        height=950,
        hovermode="x unified",
        margin=dict(l=50, r=50, t=95, b=50),
        updatemenus=[
            dict(
                type="buttons",
                direction="right",
                x=0.01,
                xanchor="left",
                y=0.22,
                yanchor="bottom",
                showactive=True,
                buttons=list([
                    dict(label="Log Scale", method="relayout", args=[{"yaxis3.type": "log"}]),
                    dict(label="Linear Scale", method="relayout", args=[{"yaxis3.type": "linear"}])
                ]),
                bgcolor="rgba(0,0,0,0.5)",
                bordercolor="#888",
                borderwidth=1
            )
        ]
    )
    
    # Update Equity chart to logarithmic scale
    fig.update_yaxes(type="log", row=3, col=1)
    
    # Hide rangesliders di subplots tapi pastikan axis tersambung
    fig.update_xaxes(rangeslider=dict(visible=False))

    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "interactive_result.html")
    fig.write_html(output_file)
    print(f"  [OK] Tersimpan! Silakan double-click file ini pada VSCode atau File Explorer: {output_file}")


if __name__ == "__main__":
    build_interactive_chart()
