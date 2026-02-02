# QuantWeb - Algorithmic Trading & Backtesting Platform 🚀

![React](https://img.shields.io/badge/Frontend-React_Vite-61DAFB?style=for-the-badge&logo=react)
![Python](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/Database-Supabase-3ECF8E?style=for-the-badge&logo=supabase)
![Telegram](https://img.shields.io/badge/Bot-Telegram_API-26A5E4?style=for-the-badge&logo=telegram)
![Status](https://img.shields.io/badge/Status-Live_Production-success?style=for-the-badge)

**QuantWeb** is a comprehensive quantitative trading analysis platform that allows users to backtest strategies, automate market scanning, and receive real-time trading signals via Telegram.

**The Problem Solved:**
* Validating trading strategies using data-driven backtesting instead of intuition.
* Automating 24/7 market monitoring without the need to constantly watch charts.

---

## 📸 Project Showcase

*(Please upload your 5 Landscape Screenshots here)*

| Dashboard Overview | Strategy Backtester |
| :---: | :---: |
| ![Dashboard](https://placehold.co/600x400/png?text=1+Dashboard+Overview) | ![Backtest](https://placehold.co/600x400/png?text=2+Backtest+Engine) |

| Market Scanner | Smart Watchlist | Telegram Integration |
| :---: | :---: | :---: |
| ![Scanner](https://placehold.co/600x400/png?text=3+Market+Scanner) | ![Watchlist](https://placehold.co/600x400/png?text=4+Watchlist) | ![Telegram](https://placehold.co/600x400/png?text=5+Telegram+Bot) |

---

## 🌟 Key Features

* **Real-time Market Scanner:** Automatically scans the market for coins with the highest Win Rate across various sectors (AI, Meme, Big Cap).
* **Backtesting Engine:** Rigorously tests strategies (Momentum, Mean Reversal, Grid) against historical data.
* **Smart Watchlist:** Integrated watchlist synchronized with the database.
* **Telegram AI Bot:** Automatically sends alert notifications to your phone when the server detects a BUY/SELL signal.

---

## 🛠️ Tech Stack & Architecture

**Data Flow:** `Market Data` -> `Python Backend` -> `Supabase/PostgreSQL` -> `Frontend React` / `Telegram Bot`

| Layer | Technology |
| :--- | :--- |
| **Frontend** | React.js (Vite), Tailwind CSS, Lucide Icons |
| **Backend** | Python, FastAPI, Uvicorn |
| **Database** | Supabase (PostgreSQL) |
| **Trading Libs** | Pandas, Custom Strategy Logic |
| **Notification** | Telegram Bot API |
| **Deployment** | Koyeb (Backend), Vercel (Frontend) |

---

## 💻 How to Run

### A. Local Environment Setup
1.  **Clone Repository:**
    ```bash
    git clone [https://github.com/RaflyandiALV/QuantWeb.git](https://github.com/RaflyandiALV/QuantWeb.git)
    ```
2.  **Environment Variables:**
    Create a `.env` file in the root directory:
    ```env
    DATABASE_URL=your_postgres_url
    TELEGRAM_TOKEN=your_bot_token
    TELEGRAM_CHAT_ID=your_chat_id
    ```

### B. Backend Setup
1.  Navigate to the backend folder and install libraries:
    ```bash
    pip install -r requirements.txt
    ```
2.  Run the Server:
    ```bash
    python -m uvicorn backend.main:app --reload
    ```

### C. Frontend Setup
1.  Navigate to the frontend folder and install packages:
    ```bash
    cd frontend
    npm install
    ```
2.  Run in Development Mode:
    ```bash
    npm run dev
    ```
    *Access the app at `http://localhost:5173/`*

---

## ⚠️ Engineering Challenges & Solutions

**1. Deployment on Linux (Koyeb)**
* **Challenge:** Encountered `ModuleNotFoundError` during cloud deployment.
* **Solution:** Implemented Python Package standards with `__init__.py` and configured `PYTHONPATH` in the runtime environment to ensure proper module resolution.

**2. Database Synchronization**
* **Challenge:** Connecting a relational database with a dynamic real-time dashboard.
* **Solution:** Configured CORS middleware to allow secure communication between the Vercel-hosted Frontend and Koyeb-hosted Backend.

---

## 🔗 Live Demo
* **Live Website:** [Click Here to View App](#) *(Update with your link)*
* **API Documentation:** [Click Here to View Swagger](#) *(Update with your link)*

## 👤 Author
**Raflyandi Alviansyah**
