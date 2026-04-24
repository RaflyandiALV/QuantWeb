# CRV-USDT Mean Reversion Bot

Automated trading bot for CRV/USDT USDT Perpetual Futures on Bybit.

## Strategy
- **Indicators**: Bollinger Bands (20, 2σ) + RSI (14) + ATR (14)
- **Timeframe**: 4H
- **Leverage**: 2×

| Signal | Condition |
|---|---|
| LONG Entry | RSI < 30 AND Close < BB Lower |
| LONG Exit | RSI > 70 AND Close > BB Upper |
| SHORT Entry | RSI > 70 AND Close > BB Upper |
| SHORT Exit | RSI < 30 AND Close < BB Lower |

**Position Flip**: When a SELL signal fires while LONG → close LONG + open SHORT in the same cycle (and vice versa).

## Risk Management
| Rule | Value |
|---|---|
| Per-trade Stop Loss | −15% from entry price |
| Portfolio Circuit Breaker | −35% from equity peak → bot halts |
| Liquidation boundary (2× lev) | −50% (SL fires at −15%, buffer = 35%) |

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure .env
```env
BYBIT_API_KEY=your_api_key
BYBIT_API_SECRET=your_api_secret
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
PAPER_TRADING=true   # change to false for live
```

### 3. Test in Paper Mode (no real orders)
```bash
python bot_runner.py
```

### 4. Go Live
Set `PAPER_TRADING=false` in `.env`, then:
```bash
python bot_runner.py
```

### Reset Circuit Breaker (after emergency stop)
```bash
python bot_runner.py --reset-cb
```

## File Structure
```
CRV-BOT/
├── .env                  # API keys & secrets (NEVER commit)
├── config.py             # All parameters
├── indicators.py         # BB + RSI + ATR
├── signal_engine.py      # Entry/exit logic
├── risk_manager.py       # Stop loss + circuit breaker
├── order_executor.py     # Bybit CCXT integration
├── bot_runner.py         # Main loop
├── notifier.py           # Telegram alerts
├── requirements.txt
└── bot_state.json        # Auto-generated runtime state
```

## VPS Deployment (Ubuntu/Debian)
```bash
# Install Python & pip
sudo apt update && sudo apt install python3 python3-pip -y

# Upload project files (use SCP or rsync)
# scp -r ./CRV-BOT user@your-vps-ip:~/

# Install dependencies
pip3 install -r requirements.txt

# Run with nohup (keeps running after SSH disconnect)
nohup python3 bot_runner.py > /dev/null 2>&1 &

# Or use screen
screen -S crv-bot
python3 bot_runner.py
# Ctrl+A, D to detach
```

## ⚠️ Security Checklist
- [ ] Revoke and regenerate Bybit API key if it was ever shared
- [ ] Bybit API permissions: Read-Write, Unified Trading (Orders + Positions) ONLY
- [ ] No withdrawal permissions on API key
- [ ] `.env` is in `.gitignore` — never pushed to GitHub
- [ ] Add VPS IP to API key whitelist after VPS is set up
