import os
import pandas as pd
import time
from datetime import datetime
from config.settings import DATA_PATH
from binance.client import Client
from data_prep.cleaning.anomaly_cleaner import clean_historical_batch, clean_one_candle
from data_prep.historical.fetch_binance import fetch_historical_data
from data_prep.realtime.stream_binance import start_realtime_tracking
from features.rsi import add_rsi_indicator, check_rsi_signal 

# --- KONFIGURASI ---
SYMBOL = "BNBUSDT"
INTERVAL = Client.KLINE_INTERVAL_1MINUTE
START_DATE = "21 Nov, 2025"

PATH_RAW = DATA_PATH / 'raw' / 'raw_bnbusdt_1m_21-11-2025_to_date.csv'
PATH_CLEAN = DATA_PATH / 'clean' / 'clean_bnbusdt_1m_21-11-2025_to_date.csv'
PATH_LOG = DATA_PATH / 'log' / 'log_bnbusdt_1m_21-11-2025_to_date.csv'

def process_and_save_rsi(df: pd.DataFrame, filepath):
    df_rsi = add_rsi_indicator(df, column_name='Close', period=14)
    df_rsi.to_csv(filepath, index=False, float_format='%.2f')


def main():
    if not os.path.exists(os.path.dirname(PATH_RAW)):
        os.makedirs(os.path.dirname(PATH_RAW))

    # ==========================================
    # FASE 1: HISTORICAL (BATCH)
    # ==========================================
    if not (os.path.exists(PATH_RAW) and os.path.exists(PATH_CLEAN)):
        print("--- [FASE 1] Menyiapkan Data Historis ---")
        
        # 1. Ambil Data
        df_raw = fetch_historical_data(SYMBOL, INTERVAL, START_DATE)
        
        # 2. Clean Data & CATAT LOG
        # Kita masukkan parameter log_filepath=PATH_LOG
        print(f"Cleaning data... Log disimpan di {PATH_LOG}")
        
        # Hapus log lama jika kita generate ulang history (biar gak numpuk)
        if os.path.exists(PATH_LOG):
            os.remove(PATH_LOG)
            
        df_clean = clean_historical_batch(df_raw, log_filepath=PATH_LOG)
        
        # 3. Save Files
        process_and_save_rsi(df_raw, PATH_RAW)
        process_and_save_rsi(df_clean, PATH_CLEAN)
        print("Data historis selesai.")
        
    else:
        print("Database ditemukan. Melanjutkan ke Real-time.")

    # ==========================================
    # FASE 2: REAL-TIME (PARALEL)
    # ==========================================
    print(f"\n--- [FASE 2] Real-Time Tracker ---")
    client = Client()
    
    while True:
        try:
            if os.path.exists(PATH_RAW) and os.path.exists(PATH_CLEAN):
                df_hist_raw = pd.read_csv(PATH_RAW).tail(100)
                df_hist_clean = pd.read_csv(PATH_CLEAN).tail(100)
                last_time = pd.to_datetime(df_hist_raw.iloc[-1]['Open Time'])
            else:
                break

            klines = client.get_klines(symbol=SYMBOL, interval=INTERVAL, limit=2)
            closed_candle = klines[0]
            candle_time = pd.to_datetime(closed_candle[0], unit='ms')

            if candle_time > last_time:
                # RAW
                row_raw = {
                    'Open Time': candle_time,
                    'Open': float(closed_candle[1]), 'High': float(closed_candle[2]),
                    'Low': float(closed_candle[3]), 'Close': float(closed_candle[4]),
                    'Volume': float(closed_candle[5])
                }
                
                # CLEAN (dengan Logging)
                # Kita masukkan parameter log_filepath=PATH_LOG
                row_clean = clean_one_candle(row_raw, df_hist_clean, log_filepath=PATH_LOG)
                
                # --- PROSES SIMPAN (RAW) ---
                df_temp_raw = pd.concat([df_hist_raw, pd.DataFrame([row_raw])], ignore_index=True)
                df_temp_raw = add_rsi_indicator(df_temp_raw)
                final_raw = df_temp_raw.iloc[-1]
                pd.DataFrame([final_raw]).to_csv(PATH_RAW, mode='a', header=False, index=False, float_format='%.2f')

                # --- PROSES SIMPAN (CLEAN) ---
                df_temp_clean = pd.concat([df_hist_clean, pd.DataFrame([row_clean])], ignore_index=True)
                df_temp_clean = add_rsi_indicator(df_temp_clean)
                final_clean = df_temp_clean.iloc[-1]
                pd.DataFrame([final_clean]).to_csv(PATH_CLEAN, mode='a', header=False, index=False, float_format='%.2f')

                print(f"[{datetime.now().strftime('%H:%M')}] Data Saved.")
                
            else:
                live = float(klines[1][4])
                print(f"Waiting Close... Live: {live:.2f}", end='\r')

            time.sleep(2)

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()