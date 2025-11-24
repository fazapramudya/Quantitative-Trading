# File: Analysis/indicators.py
import pandas as pd
import numpy as np

def add_rsi_indicator(df, column_name='Close', period=14):
    """
    Menghitung RSI berdasarkan kolom tertentu (default: Close).
    Mengembalikan DataFrame dengan tambahan kolom 'RSI'.
    """
    df_res = df.copy()
    delta = df_res[column_name].diff()
    
    gain = (delta.where(delta > 0, 0))
    loss = (-delta.where(delta < 0, 0))
    
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    df_res['RSI'] = 100 - (100 / (1 + rs))
    
    # Rounding
    df_res['RSI'] = df_res['RSI'].round(2)
    
    return df_res

def check_rsi_signal(rsi_value):
    """
    Mengembalikan status berdasarkan level custom:
    - Atas: 60 (Overbought / Strong Bullish Zone)
    - Bawah: 40 (Oversold / Bearish Zone)
    - Tengah: 50
    """
    if rsi_value >= 60:
        return "OVERBOUGHT (>60)"
    elif rsi_value <= 40:
        return "OVERSOLD (<40)"
    elif rsi_value > 50:
        return "BULLISH ZONE (50-60)"
    else:
        return "BEARISH ZONE (40-50)"