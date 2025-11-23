import pandas as pd
import numpy as np

# Konfigurasi Cleaning
WINDOW = 20
SIGMA = 3

def clean_historical_batch(df):
    """Membersihkan Dataframe Historis (Spike Cap & Smooth Error)"""
    print("[CLEAN] Membersihkan data historis...")
    df_clean = df.copy()
    
    # Hitung Stats
    rolling_mean = df_clean['Close'].rolling(window=WINDOW).mean()
    rolling_std = df_clean['Close'].rolling(window=WINDOW).std()
    upper = rolling_mean + (SIGMA * rolling_std)
    lower = rolling_mean - (SIGMA * rolling_std)
    
    # Deteksi Anomali
    is_anomaly = (df_clean['Close'] > upper) | (df_clean['Close'] < lower)
    anomaly_groups = (is_anomaly != is_anomaly.shift()).cumsum()
    
    if is_anomaly.sum() > 0:
        for _, group in df_clean[is_anomaly].groupby(anomaly_groups):
            idx = group.index
            if len(idx) == 1: # Cap
                i = idx[0]
                limit = upper[i] if df_clean.loc[i, 'Close'] > upper[i] else lower[i]
                df_clean.loc[i, 'Close'] = limit
                df_clean.loc[i, 'High'] = max(df_clean.loc[i, 'High'], limit)
                df_clean.loc[i, 'Low'] = min(df_clean.loc[i, 'Low'], limit)
            else: # Smooth
                df_clean.loc[idx, ['Close', 'High', 'Low']] = np.nan
                df_clean['Close'] = df_clean['Close'].interpolate(method='linear')
                df_clean['High'] = df_clean['High'].fillna(df_clean['Close'])
                df_clean['Low'] = df_clean['Low'].fillna(df_clean['Close'])

    # Rounding
    cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    df_clean[cols] = df_clean[cols].round(2)
    return df_clean

def clean_one_candle(new_candle, history_df):
    """
    Membersihkan 1 baris data Real-time.
    Hanya melakukan CAP (Winsorizing) berdasarkan data historis terakhir.
    """
    # Ambil 20 data terakhir untuk referensi
    last_data = history_df.tail(WINDOW)
    if len(last_data) < WINDOW:
        return new_candle # Belum cukup data, return asli

    mean = last_data['Close'].mean()
    std = last_data['Close'].std()
    upper = mean + (SIGMA * std)
    lower = mean - (SIGMA * std)
    
    price = new_candle['Close']
    
    # Logic Cap
    if price > upper:
        print(f"  [CLEAN] Spike High! {price} -> {upper:.2f}")
        new_candle['Close'] = upper
        new_candle['High'] = max(new_candle['High'], upper)
        new_candle['Low'] = min(new_candle['Low'], upper)
    elif price < lower:
        print(f"  [CLEAN] Spike Low! {price} -> {lower:.2f}")
        new_candle['Close'] = lower
        new_candle['High'] = max(new_candle['High'], lower)
        new_candle['Low'] = min(new_candle['Low'], lower)
        
    # Rounding
    for k in ['Open', 'High', 'Low', 'Close', 'Volume']:
        new_candle[k] = round(new_candle[k], 2)
        
    return new_candle