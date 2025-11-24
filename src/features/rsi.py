# File: Analysis/indicators.py
import pandas as pd
import numpy as np

def add_rsi_indicator(df, period=14):
    """
    Menghitung RSI Periode 14.
    Menggunakan metode Wilder's Smoothing (Standar RSI).
    """
    # Copy agar tidak merusak dataframe asli
    df_result = df.copy()
    
    # 1. Hitung Selisih Harga (Delta)
    delta = df_result['Close'].diff()
    
    # 2. Pisahkan Gain (Naik) dan Loss (Turun)
    gain = (delta.where(delta > 0, 0))
    loss = (-delta.where(delta < 0, 0))
    
    # 3. Hitung Rata-rata Gain & Loss (Wilder's Smoothing)
    # alpha=1/period adalah ekuivalen matematis dari metode Wilder
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    # 4. Hitung RS dan RSI
    rs = avg_gain / avg_loss
    df_result['RSI'] = 100 - (100 / (1 + rs))
    
    # 5. Rounding 2 desimal
    df_result['RSI'] = df_result['RSI'].round(2)
    
    return df_result

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