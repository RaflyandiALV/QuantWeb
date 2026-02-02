# QuantWeb - Algorithmic Trading Ecosystem 🚀

![Project Status](https://img.shields.io/badge/Status-MVP_Ready-success?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.95%2B-009688?style=for-the-badge&logo=fastapi)
![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react)
![Tailwind](https://img.shields.io/badge/Tailwind-CSS-38B2AC?style=for-the-badge&logo=tailwind-css)

**QuantWeb** is a high-performance, full-stack algorithmic trading platform designed to bridge the gap between quantitative research and live market execution. It serves as a centralized command center where users can visualize real-time market data, execute automated trading strategies (Grid, Mean Reversion), and monitor portfolio performance through a responsive modern interface.

This system is engineered to handle real-time data ingestion and acts as the **core backend API** for the companion [iOS Mobile App](https://github.com/raflyandialv/QuantIOS-MMS).

---

## 🌟 Key Features

### 🖥️ Interactive Web Dashboard
* **Real-Time Visualization:** Live candlestick charts and technical indicators (RSI, MACD, Bollinger Bands) powered by `Recharts`.
* **Strategy Control:** Start, stop, and configure trading bots dynamically without touching code.
* **Portfolio Analytics:** Track PnL (Profit and Loss), Equity Curve, and active positions in real-time.

### ⚙️ Powerful Quantitative Engine (Backend)
* **Multi-Strategy Support:** Native implementation of **Grid Trading**, **Mean Reversion**, and **Momentum** algorithms.
* **Backtesting Module:** Simulate strategies against historical data to calculate Sharpe Ratio and Max Drawdown before going live.
* **FastAPI Architecture:** Asynchronous, non-blocking API designed for low-latency financial data processing.

---

## 🛠️ Technology Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Frontend** | **React.js (Vite)** | Blazing fast build tool, component-based UI. |
| **Styling** | **Tailwind CSS** | Utility-first CSS for responsive, modern design. |
| **Backend** | **Python & FastAPI** | High-performance async framework for the API layer. |
| **Data Engine** | **Pandas & NumPy** | For vectorised financial calculations and data manipulation. |
| **Market Data** | **CCXT / YFinance** | Unified API for crypto exchanges and stock market data. |

---

## 🚀 Quick Start Guide (How to Run)

Follow these instructions to set up the project locally on your machine.

### Prerequisites
* **Python 3.9** or higher
* **Node.js** & **npm** (for frontend)

### Step 1: Setup Backend (Python API)

1.  Navigate to the backend directory:
    ```bash
    cd backend
    ```

2.  Create and activate Virtual Environment (Recommended):
    ```bash
    # Windows
    python -m venv venv
    venv\Scripts\activate

    # Mac/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  Install Dependencies:
    ```bash
    pip install -r requirements.txt
    ```

4.  Run the Server:
    ```bash
    uvicorn main:app --reload
    ```
    ✅ *Success! The API is now running at `http://127.0.0.1:8000`*

### Step 2: Setup Frontend (React Dashboard)

1.  Open a **new** terminal window (keep the backend terminal running).

2.  Navigate to frontend directory:
    ```bash
    cd frontend
    ```

3.  Install Node Modules:
    ```bash
    npm install
    ```

4.  Start the Development Server:
    ```bash
    npm run dev
    ```
    ✅ *Success! The Dashboard is now accessible at `http://localhost:5173`*

---

## 📸 Screenshots

*(Place your screenshots here)*

## 👤 Author

**Raflyandi Alviansyah**
* **GitHub:** [@RaflyandiALV](https://github.com/RaflyandiALV)
