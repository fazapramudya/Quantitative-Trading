import os
import pandas as pd
import numpy as np  # Pastikan numpy di-import
import time
from datetime import datetime
import traceback
from datetime import datetime
from binance.client import Client

# Import Modul Lokal
from config.settings import DATA_PATH
from storage.db_ops import sb_insert, sb_bulk_upsert_csv
from data_prep.cleaning.anomaly_cleaner import clean_historical_batch, clean_one_candle
from data_prep.historical.fetch_binance import fetch_historical_data
from features.rsi import add_rsi_indicator
from features.ema import add_ema_indicator
from models.kmeans import init_kmeans, update_streaming_plot, prepare_features

# --- KONFIGURASI ---
SYMBOL = "BNBUSDT"
INTERVAL = Client.KLINE_INTERVAL_1MINUTE
START_DATE = "17 Jan, 2026"

PATH_RAW = DATA_PATH / 'raw' / 'raw_bnbusdt_5m.csv'
PATH_CLEAN = DATA_PATH / 'clean' / 'clean_bnbusdt_5m.csv'
PATH_LOG = DATA_PATH / 'log' / 'anomaly_log.csv'
PATH_KMEANS_PNG = "data/k-means/live_regime_plot.png"

def apply_indicators(df):
    """Menghitung indikator dengan pembersihan kolom lama"""
    # 1. Paksa semua kolom menjadi lowercase di awal
    df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
    
    # 2. Hapus kolom indikator lama jika ada agar tidak duplikat (rsi, ema_50, ema_200)
    cols_to_drop = ['rsi', 'ema_50', 'ema_200']
    df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])
    
    # 3. Hitung Indikator (Gunakan 'close' kecil)
    df_res = add_rsi_indicator(df, column_name='close', period=14)
    df_res = add_ema_indicator(df_res, column_name='close', period=50)
    df_res = add_ema_indicator(df_res, column_name='close', period=200)
    
    # 4. Paksa semua hasil menjadi lowercase (RSI -> rsi, EMA_50 -> ema_50)
    df_res.columns = [str(c).lower().replace(" ", "_") for c in df_res.columns]
    
    return df_res

def main():
    # Pembuatan folder
    for folder in [PATH_RAW, PATH_CLEAN, PATH_LOG]:
        os.makedirs(os.path.dirname(folder), exist_ok=True)
    os.makedirs("data/k-means", exist_ok=True)

    # ==========================================
    # FASE 1: HISTORICAL DATA
    # ==========================================
    if not os.path.exists(PATH_CLEAN):
        print("--- [FASE 1] Mengunduh & Membersihkan Data Historis ---")
        raw_data = fetch_historical_data(SYMBOL, INTERVAL, START_DATE)
        clean_data = clean_historical_batch(raw_data, log_filepath=PATH_LOG)
        
        df_final_clean = apply_indicators(clean_data)
        df_final_clean.to_csv(PATH_CLEAN, index=False)
        
        print("Uploading to Supabase...")
        sb_bulk_upsert_csv(table_name="trading_data", file_path=str(PATH_CLEAN), on_conflict="open_time")
        print("Historical Upload Selesai.")
    
    # ==========================================
    # INISIALISASI K-MEANS
    # ==========================================
    # Baca data dan pastikan kolom lowercase
    df_hist = pd.read_csv(PATH_CLEAN)
    df_hist.columns = [str(c).lower().replace(" ", "_") for c in df_hist.columns]
    
    print("--- [K-MEANS] Training Model ---")
    km_model, km_scaler, km_features = init_kmeans(df_hist)

    # ==========================================
    # FASE 2: REAL-TIME TRACKER
    # ==========================================
    print(f"\n--- [FASE 2] Streaming: {SYMBOL} ---")
    client = Client()
    
    while True:
        try:
            # Refresh data history dari memori (Pastikan tetap lowercase)
            df_hist = pd.read_csv(PATH_CLEAN)
            df_hist.columns = [str(c).lower().replace(" ", "_") for c in df_hist.columns]
            
            last_time = pd.to_datetime(df_hist.iloc[-1]['open_time'])

            # Cek Binance
            klines = client.get_klines(symbol=SYMBOL, interval=INTERVAL, limit=2)
            closed_candle = klines[0]
            candle_time = pd.to_datetime(closed_candle[0], unit='ms')

            if candle_time > last_time:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Candle Closed!")
                
                # 1. Siapkan data mentah dari klines binance
                row_raw = {
                    'open_time': candle_time,
                    'open': float(closed_candle[1]), 
                    'high': float(closed_candle[2]),
                    'low': float(closed_candle[3]), 
                    'close': float(closed_candle[4]),
                    'volume': float(closed_candle[5])
                }
                
                # 2. Proses pembersihan data (cleaning)
                # Output dari clean_one_candle sekarang sudah berupa dict dengan key lowercase
                row_clean = clean_one_candle(row_raw, df_hist.tail(300), log_filepath=PATH_LOG)
                
                # 3. DEFINISIKAN new_row_df DI SINI (Penyebab error sebelumnya)
                new_row_df = pd.DataFrame([row_clean])
                
                # 4. Gabungkan dengan data historis
                df_temp = pd.concat([df_hist, new_row_df], ignore_index=True)
                
                # 5. Hitung Indikator
                df_res = apply_indicators(df_temp)
                
                # 6. Update Plot K-Means & Prediksi Cluster
                last_cluster = update_streaming_plot(df_res.tail(1000), km_model, km_scaler, km_features, PATH_KMEANS_PNG)
                
                # 7. Ambil baris terakhir hasil kalkulasi
                final_row_df = df_res.iloc[[-1]]
                
                # 8. Simpan ke CSV (Append)
                final_row_df.to_csv(PATH_CLEAN, mode='a', header=False, index=False)
                
                # 9. Sync ke Supabase (db_ops)
                db_data = final_row_df.iloc[0].to_dict()
                db_data['cluster'] = int(last_cluster)
                
                # --- PERBAIKAN: Konversi semua tipe data agar JSON Safe ---
                for k, v in db_data.items():
                    # 1. Konversi Waktu (Timestamp -> String ISO)
                    if isinstance(v, (pd.Timestamp, datetime)):
                        db_data[k] = v.isoformat()
                    
                    # 2. Konversi Angka Desimal (Numpy Float -> Python Float)
                    elif isinstance(v, (np.float64, np.float32)):
                        db_data[k] = float(v)
                    
                    # 3. Konversi Angka Bulat (Numpy Int -> Python Int)
                    elif isinstance(v, (np.int64, np.int32)):
                        db_data[k] = int(v)

                # Sekarang aman untuk dikirim
                sb_insert(table_name="trading_data", data=db_data, upsert=True)
                print(f"Cloud Sync Success: Cluster {last_cluster} | Price: {db_data['close']}")
                
            else:
                live_p = float(klines[1][4])
                print(f"Waiting {INTERVAL}... Price: {live_p:.2f}    ", end='\r')

            time.sleep(2) # Poll lebih cepat agar responsif

        except Exception as e:
            print(f"\n!!! ERROR TERDETEKSI !!!")
            # Ini akan mencetak detail baris mana yang error
            traceback.print_exc() 
            time.sleep(10)

if __name__ == "__main__":
    main()