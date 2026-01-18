import os
import csv
import pandas as pd
import numpy as np

# Konfigurasi Cleaning
WINDOW = 20
SIGMA = 3

def write_log(filepath, timestamp, original, cleaned, note):
    if not filepath: return
    file_exists = os.path.isfile(filepath)
    with open(filepath, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['Timestamp', 'Original_Close', 'Cleaned_Close', 'Note'])
        writer.writerow([timestamp, original, cleaned, note])

def clean_historical_batch(df_raw, log_filepath=None):
    df_clean = df_raw.copy()
    
    # 1. PAKSA SEMUA KOLOM JADI LOWERCASE (Sangat Penting)
    df_clean.columns = [str(c).lower().replace(" ", "_") for c in df_clean.columns]
    
    rolling_mean = df_clean['close'].rolling(window=WINDOW).mean()
    rolling_std = df_clean['close'].rolling(window=WINDOW).std()
    upper = rolling_mean + (SIGMA * rolling_std)
    lower = rolling_mean - (SIGMA * rolling_std)
    
    is_anomaly = (df_clean['close'] > upper) | (df_clean['close'] < lower)
    anomaly_groups = (is_anomaly != is_anomaly.shift()).cumsum()
    
    if is_anomaly.sum() > 0:
        for _, group in df_clean[is_anomaly].groupby(anomaly_groups):
            idx = group.index
            # Gunakan huruf kecil 'open_time' dan 'close'
            ts = df_clean.loc[idx[0], 'open_time']
            orig_close = df_clean.loc[idx[0], 'close']
            
            if len(idx) == 1: 
                i = idx[0]
                limit = upper[i] if df_clean.loc[i, 'close'] > upper[i] else lower[i]
                
                # Gunakan huruf kecil 'close', 'high', 'low'
                df_clean.loc[i, 'close'] = limit
                df_clean.loc[i, 'high'] = max(df_clean.loc[i, 'high'], limit)
                df_clean.loc[i, 'low'] = min(df_clean.loc[i, 'low'], limit)
                
                if log_filepath:
                    write_log(log_filepath, ts, orig_close, round(limit, 2), "Historical Spike (Cap)")
            else: 
                first_idx = idx[0]
                df_clean.loc[idx, ['close', 'high', 'low']] = np.nan
                df_clean['close'] = df_clean['close'].interpolate(method='linear')
                df_clean['high'] = df_clean['high'].fillna(df_clean['close'])
                df_clean['low'] = df_clean['low'].fillna(df_clean['close'])
                
                if log_filepath:
                    new_val = df_clean.loc[first_idx, 'close']
                    write_log(log_filepath, ts, orig_close, round(new_val, 2), f"Historical Error ({len(idx)} bars Smoothed)")

    return df_clean.round(2)

def clean_one_candle(new_row, last_window, log_filepath=None):
    # 1. Paksa history dan row baru menjadi lowercase agar sinkron
    last_window.columns = [str(c).lower().replace(" ", "_") for c in last_window.columns]
    
    # Buat copy dari new_row dengan kunci lowercase
    new_candle = {str(k).lower().replace(" ", "_"): v for k, v in new_row.items()}
    
    # 2. Hitung statistik
    mean = last_window['close'].mean()
    std = last_window['close'].std()
    upper = mean + (SIGMA * std)
    lower = mean - (SIGMA * std)
    
    price = new_candle['close']
    modified = False
    note = ""
    
    # 3. Deteksi Outlier
    if price > upper:
        new_candle['close'] = upper
        new_candle['high'] = max(new_candle.get('high', upper), upper)
        new_candle['low'] = min(new_candle.get('low', upper), upper)
        modified = True
        note = "Realtime Spike High (Cap)"
    elif price < lower:
        new_candle['close'] = lower
        new_candle['high'] = max(new_candle.get('high', lower), lower)
        new_candle['low'] = min(new_candle.get('low', lower), lower)
        modified = True
        note = "Realtime Spike Low (Cap)"
    
    # 4. Log jika ada perubahan
    if modified and log_filepath:
        ts = new_candle.get('open_time', 'N/A')
        write_log(log_filepath, ts, price, round(new_candle['close'], 2), note)
        
    # 5. Rounding semua field angka
    for k in ['open', 'high', 'low', 'close', 'volume']:
        if k in new_candle:
            new_candle[k] = round(float(new_candle[k]), 2)
        
    return new_candle