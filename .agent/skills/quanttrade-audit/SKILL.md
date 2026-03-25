---
name: quanttrade-audit
description: Full deep audit of the QuantTrade Web App project from a quantitative finance and software engineering perspective. Use this skill whenever the user asks for a project audit, code review, defect analysis, or wants to understand issues in the QuantTrade backend/frontend, backtest engine, risk manager, paper trader, or any module. Also trigger when user asks "what's wrong with this", "find all bugs", or "how can I improve" the trading bot or platform.
---

# QuantTrade Project Audit Skill

This skill performs a comprehensive, structured, deep audit of the QuantTrade Web App — a crypto trading research platform built with FastAPI (backend) and React/Vite (frontend).

## Project Structure Reference

```
QuantTrade-Web-App/
├── backend/
│   ├── main.py              — FastAPI server, all API endpoints, scheduler
│   ├── strategy_core.py     — TradingEngine class: data fetch, backtesting, indicators
│   ├── risk_manager.py      — VaR, CVaR, pre-trade risk checks, circuit breakers
│   ├── portfolio_engine.py  — Equity curve, snapshot, daily PnL
│   ├── paper_trader.py      — Autonomous paper trading loop (threading)
│   ├── monte_carlo.py       — Bootstrap Monte Carlo, Kelly Criterion
│   ├── fund_analytics.py    — Sharpe, Sortino, Calmar ratios
│   ├── ai_brain.py          — AI decision layer
│   ├── alpha_data.py        — Market data provider
│   ├── execution_engine.py  — Order execution manager
│   ├── anomaly_scanner.py   — Volume/OB/Whale anomaly detection
│   ├── macro_intelligence.py — Macro regime analysis
│   └── global_market.py     — Cross-asset analysis
├── frontend/src/components/
│   ├── PaperTradingDashboard.jsx
│   ├── RiskDashboard.jsx
│   ├── PortfolioPage.jsx
│   ├── MonteCarloChart.jsx
│   ├── FundDashboard.jsx
│   ├── AIDashboard.jsx
│   └── ... (15 components total)
└── quant-formulas-playbook-gojo.ether.pdf  — Quant formula reference
```

## Audit Checklist

When auditing, always check these categories:

### 1. Quantitative Finance Integrity
- [ ] **Look-Ahead Bias** — Are future values being used in past calculations? Check `fillna()`, rolling windows, indicator lag
- [ ] **Overfitting / Multiple Comparisons** — Is there proper OOS validation? Walk-forward testing?
- [ ] **Transaction Costs** — Are fees, slippage, funding rates modeled?
- [ ] **Position Sizing Math** — Is Kelly Criterion, fixed fraction, or ATR-based sizing correct?
- [ ] **Risk Metrics** — Is Sharpe ratio using correct risk-free rate? Is VaR computed from proper returns?
- [ ] **Regime Awareness** — Is macro regime integrated into strategy selection?

### 2. Backend Software Quality
- [ ] **Thread Safety** — Are shared mutable states protected with locks/events?
- [ ] **DB Connection Management** — Are connections properly closed? Are WAL & timeout set?
- [ ] **Error Handling** — Do all exceptions fall back gracefully? Fail-open vs fail-close for risk checks?
- [ ] **API Design** — Are endpoints RESTful? Are Pydantic models used correctly?
- [ ] **Singleton Safety** — Are module-level singletons thread-safe?

### 3. Frontend Quality
- [ ] **Hardcoded URLs** — All API calls should use env variable (`VITE_API_BASE_URL`)
- [ ] **Auto-Refresh Strategy** — Is polling interval appropriate? Should WebSocket be used?
- [ ] **Error States** — Are loading/error/empty states handled for all async calls?
- [ ] **Real-time UX** — Are PnL and positions updating frequently enough?

### 4. DevOps & Configuration
- [ ] **requirements.txt** — No duplicates, all deps pinned to versions
- [ ] **env vars** — No hardcoded secrets or API keys in code
- [ ] **.env/.gitignore** — Sensitive files excluded from git

## Known Critical Defects (from initial audit March 2026)

| Severity | File | Defect |
|---|---|---|
| 🔴 CRITICAL | `strategy_core.py` | `df.fillna(0)` causes look-ahead bias on all indicators |
| 🔴 CRITICAL | `main.py` | Scanner scoring WinRate×Profit creates overfitting with 60 combos, no OOS validation |
| 🔴 CRITICAL | `strategy_core.py` | All-In position sizing for Basic strategies (100% capital per trade) |
| 🟡 MEDIUM | `fund_analytics.py` | Sharpe ratio assumes risk-free rate = 0 |
| 🟡 MEDIUM | `risk_manager.py` | Open position count SQL query inaccurate for multi-leg trades |
| 🟡 MEDIUM | `paper_trader.py` | `_running` state not protected by lock (race condition risk) |
| 🟡 MEDIUM | All frontend | API base URL hardcoded to `http://127.0.0.1:8000` |
| 🟢 MINOR | `requirements.txt` | `pandas` listed twice as duplicate |
| 🟢 MINOR | `main.py` | `MacroIntelligence` singleton accessed from both scheduler and request handler |
| 🟢 MINOR | `monte_carlo.py` | Kelly assumes independent trades (no multi-asset correlation) |

## Gojo PDF Applicability Assessment

When user asks about applying Gojo's quant playbook, evaluate each module:

| Module | Readiness | What to Apply |
|---|---|---|
| `monte_carlo.py` | ✅ High | Correlated MC (Cholesky), GBM, Extreme Value Theory |
| `risk_manager.py` | 🟡 Medium | Cornish-Fisher VaR, Expected Shortfall with EVT |
| `fund_analytics.py` | 🔴 Low (rewrite needed) | Information Ratio, MAE/MFE, Ulcer Index, Omega Ratio |
| `strategy_core.py` | 🟡 Medium | Kalman Filter, Hurst Exponent, OBV divergence |

## Broker Integration Guide

When user asks about broker connections or replacing paper trading:

**Current:** Binance via CCXT (both testnet and live)

**Swap to another crypto exchange (fastest):**
```python
# strategy_core.py → TradingEngine.__init__
self.exchange = ccxt.bybit(exchange_config)  # or kucoin, okx, etc.
```

**MT5 integration for Forex:**
- Use `MetaTrader5` Python package
- Create `broker_interface.py` abstraction layer
- MT5 connects via local terminal (not REST API)

**Recommended architecture:** `BrokerInterface` abstract class that Binance, Bybit, MT5 all implement.

## Levelup Roadmap

### Phase 1 — Fix Critical (1-2 weeks)
1. Fix `fillna(0)` in `strategy_core.prepare_indicators()` → use proper NaN masking
2. Add 0.1% per-side transaction cost to all backtests
3. Fix `requirements.txt` duplicates
4. Move API base URL to `VITE_API_BASE_URL` env variable

### Phase 2 — Quant Upgrade (2-4 weeks)
1. Walk-Forward Testing (70% train / 30% OOS)
2. Replace score = WinRate×Profit → use OOS Sharpe or IR
3. Implement Hurst Exponent for regime detection
4. Fix Sharpe with proper risk-free rate
5. Thread safety: `threading.Event` for paper trader

### Phase 3 — Architecture (1-2 months)
1. `BrokerInterface` abstraction layer
2. WebSocket for real-time price/PnL updates to frontend
3. Separate paper_trader into standalone microservice
4. Multi-asset correlated Monte Carlo
5. Audit trail for config changes

### Phase 4 — UI/UX (parallel with Phase 3)
1. Real-time candlestick chart via WebSocket (replace 15s polling)
2. P&L attribution per strategy/symbol
3. Monthly returns heatmap
4. Mobile-responsive layout improvements

## Output Format

When completing an audit, ALWAYS report:

1. **Executive Summary** — 2-3 sentences on overall health
2. **Critical Defects** (🔴) — Must fix before trusting results
3. **Medium Defects** (🟡) — Fix before production
4. **Minor Issues** (🟢) — Nice to have
5. **What's Working Well** — Don't only report negatives
6. **Quant Interpretation** — From the perspective of a quantitative researcher
7. **Recommended Next Step** — One concrete actionable improvement
