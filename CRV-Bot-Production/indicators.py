# =============================================================
# indicators.py — Technical Indicator Calculations
# BB(20, 2σ) + RSI(14) + ATR(14) — persis parameter dari backtest
# =============================================================

import pandas as pd
import numpy as np
from config import BB_PERIOD, BB_STD_DEV, RSI_PERIOD, ATR_PERIOD


def calculate_bollinger_bands(closes: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Bollinger Bands: Period=20, StdDev=2×
    Returns: (upper_band, middle_band, lower_band)
    """
    middle = closes.rolling(window=BB_PERIOD).mean()
    std    = closes.rolling(window=BB_PERIOD).std()  # ddof=1 default — persis QuantWeb
    upper  = middle + (BB_STD_DEV * std)
    lower  = middle - (BB_STD_DEV * std)
    return upper, middle, lower


def calculate_rsi(closes: pd.Series) -> pd.Series:
    """
    RSI: Period=14 (Wilder's smoothing via EWM)
    Returns: RSI series (0–100)
    """
    delta  = closes.diff()
    gain   = (delta.where(delta > 0, 0)).rolling(RSI_PERIOD).mean()
    loss   = (-delta.where(delta < 0, 0)).rolling(RSI_PERIOD).mean()

    # SMA Rolling RSI — persis QuantWeb strategy_core.py
    rs  = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_atr(highs: pd.Series, lows: pd.Series, closes: pd.Series) -> pd.Series:
    """
    ATR: Period=14 (Wilder's smoothing)
    True Range = max(H-L, |H-Cprev|, |L-Cprev|)
    Returns: ATR series
    """
    prev_close = closes.shift(1)
    tr = pd.concat([
        highs - lows,
        (highs - prev_close).abs(),
        (lows  - prev_close).abs()
    ], axis=1).max(axis=1)

    atr = tr.ewm(com=ATR_PERIOD - 1, min_periods=ATR_PERIOD).mean()
    return atr


def compute_all(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all indicators on a standard OHLCV DataFrame.
    Input columns: ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    Returns df with added columns: bb_upper, bb_mid, bb_lower, rsi, atr
    """
    df = df.copy()

    df["bb_upper"], df["bb_mid"], df["bb_lower"] = calculate_bollinger_bands(df["close"])
    df["rsi"]  = calculate_rsi(df["close"])
    df["atr"]  = calculate_atr(df["high"], df["low"], df["close"])

    return df


def get_latest_indicators(df: pd.DataFrame) -> dict:
    """
    Returns the most recent row's indicator values as a dict.
    Must call compute_all() first.
    """
    row = df.iloc[-1]
    return {
        "timestamp" : row["timestamp"],
        "close"     : row["close"],
        "bb_upper"  : row["bb_upper"],
        "bb_mid"    : row["bb_mid"],
        "bb_lower"  : row["bb_lower"],
        "rsi"       : row["rsi"],
        "atr"       : row["atr"],
    }
