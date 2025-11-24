import os
import csv
import pandas as pd
import numpy as np

# Konfigurasi Cleaning
WINDOW = 20
SIGMA = 3

def write_log(filepath, timestamp, original, cleaned, note):
    """
    Fungsi kecil untuk mencatat perubahan ke file CSV log.
    Format: [Waktu, Harga Asli, Harga Baru, Keterangan]
    """
    if not filepath: return

    # Cek apakah file sudah ada (untuk header)
    file_exists = os.path.isfile(filepath)
    
    with open(filepath, mode='a', newline='') as f:
        writer = csv.writer(f)
        # Tulis Header jika file baru
        if not file_exists:
            writer.writerow(['Timestamp', 'Original_Close', 'Cleaned_Close', 'Note'])
        
        # Tulis Data Log
        writer.writerow([timestamp, original, cleaned, note])

def clean_historical_batch(df, log_filepath=None):
    """
    Cleaning Batch (Sejarah).
    Mencatat setiap perubahan ke log_filepath.
    """
    print("[CLEAN] Memproses cleaning historis...")
    df_clean = df.copy()
    
    rolling_mean = df_clean['Close'].rolling(window=WINDOW).mean()
    rolling_std = df_clean['Close'].rolling(window=WINDOW).std()
    upper = rolling_mean + (SIGMA * rolling_std)
    lower = rolling_mean - (SIGMA * rolling_std)
    
    is_anomaly = (df_clean['Close'] > upper) | (df_clean['Close'] < lower)
    anomaly_groups = (is_anomaly != is_anomaly.shift()).cumsum()
    
    if is_anomaly.sum() > 0:
        # Loop setiap grup anomali
        for _, group in df_clean[is_anomaly].groupby(anomaly_groups):
            idx = group.index
            
            # Ambil timestamp untuk log (dari baris pertama grup)
            ts = df_clean.loc[idx[0], 'Open Time']
            orig_close = df_clean.loc[idx[0], 'Close']
            
            if len(idx) == 1: 
                # === KASUS CAP (SPIKE) ===
                i = idx[0]
                limit = upper[i] if df_clean.loc[i, 'Close'] > upper[i] else lower[i]
                
                # Ubah Data
                df_clean.loc[i, 'Close'] = limit
                df_clean.loc[i, 'High'] = max(df_clean.loc[i, 'High'], limit)
                df_clean.loc[i, 'Low'] = min(df_clean.loc[i, 'Low'], limit)
                
                # CATAT KE LOG
                if log_filepath:
                    write_log(log_filepath, ts, orig_close, round(limit, 2), "Historical Spike (Cap)")
                    
            else: 
                # === KASUS SMOOTH (ERROR PANJANG) ===
                # Untuk log, kita catat range-nya saja
                first_idx = idx[0]
                last_idx = idx[-1]
                count = len(idx)
                
                df_clean.loc[idx, ['Close', 'High', 'Low']] = np.nan
                df_clean['Close'] = df_clean['Close'].interpolate(method='linear')
                df_clean['High'] = df_clean['High'].fillna(df_clean['Close'])
                df_clean['Low'] = df_clean['Low'].fillna(df_clean['Close'])
                
                # CATAT KE LOG
                if log_filepath:
                    new_val = df_clean.loc[first_idx, 'Close'] # Nilai setelah interpolasi
                    write_log(log_filepath, ts, orig_close, round(new_val, 2), f"Historical Error ({count} bars Smoothed)")

    return df_clean.round(2)

def clean_one_candle(candle_dict, history_df, log_filepath=None):
    """
    Cleaning Real-time (Single Row).
    Mencatat ke log jika ada perubahan.
    """
    new_candle = candle_dict.copy()
    
    last_window = history_df.tail(WINDOW)
    if len(last_window) < WINDOW:
        return new_candle

    mean = last_window['Close'].mean()
    std = last_window['Close'].std()
    upper = mean + (SIGMA * std)
    lower = mean - (SIGMA * std)
    
    price = new_candle['Close']
    modified = False
    note = ""
    
    if price > upper:
        new_candle['Close'] = upper
        new_candle['High'] = max(new_candle['High'], upper)
        new_candle['Low'] = min(new_candle['Low'], upper)
        modified = True
        note = "Realtime Spike High (Cap)"
        
    elif price < lower:
        new_candle['Close'] = lower
        new_candle['High'] = max(new_candle['High'], lower)
        new_candle['Low'] = min(new_candle['Low'], lower)
        modified = True
        note = "Realtime Spike Low (Cap)"
    
    # CATAT KE LOG JIKA ADA PERUBAHAN
    if modified and log_filepath:
        ts = new_candle['Open Time']
        write_log(log_filepath, ts, price, round(new_candle['Close'], 2), note)
        print(f"  [LOG] Perubahan dicatat ke {os.path.basename(log_filepath)}")
        
    # Rounding
    for k in ['Open', 'High', 'Low', 'Close', 'Volume']:
        new_candle[k] = round(new_candle[k], 2)
        
    return new_candle