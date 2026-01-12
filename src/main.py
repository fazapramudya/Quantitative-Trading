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
from features.ema import add_ema_indicator

# --- KONFIGURASI ---
SYMBOL = "BNBUSDT"
INTERVAL = Client.KLINE_INTERVAL_5MINUTE
START_DATE = "1 Jan, 2026"

PATH_RAW = DATA_PATH / 'raw' / 'raw_bnbusdt_1m_21-11-2025_to_date.csv'
PATH_CLEAN = DATA_PATH / 'clean' / 'clean_bnbusdt_1m_21-11-2025_to_date.csv'
PATH_LOG = DATA_PATH / 'log' / 'log_bnbusdt_1m_21-11-2025_to_date.csv'

def apply_indicators_and_save(df, filepath, mode='w', header=True):
    """
    Helper: Menghitung RSI, EMA 50, EMA 200 lalu simpan.
    Bisa dipakai untuk Batch (sejarah) maupun Real-time (append).
    """
    # 1. Hitung RSI (Periode 14)
    df_final = add_rsi_indicator(df, column_name='Close', period=14)
    
    # 2. Hitung EMA 50 (Trend Jangka Pendek / Dinamis S/R)
    df_final = add_ema_indicator(df_final, column_name='Close', period=50)
    
    # 3. Hitung EMA 200 (Trend Utama)
    df_final = add_ema_indicator(df_final, column_name='Close', period=200)
    
    # 4. Simpan
    # Jika mode 'a' (append), kita hanya simpan baris terakhir
    if mode == 'a':
        row_to_save = df_final.iloc[[-1]] # Ambil baris terakhir sebagai DataFrame
        row_to_save.to_csv(filepath, mode='a', header=False, index=False, float_format='%.2f')
    else:
        # Jika mode 'w' (write), simpan semua
        df_final.to_csv(filepath, mode='w', header=True, index=False, float_format='%.2f')
        
    return df_final # Return df agar bisa diprint/dicek


def main():
    if not os.path.exists(os.path.dirname(PATH_RAW)):
        os.makedirs(os.path.dirname(PATH_RAW))

    # ==========================================
    # FASE 1: HISTORICAL (BATCH)
    # ==========================================
    if not (os.path.exists(PATH_RAW) and os.path.exists(PATH_CLEAN)):
        print("--- [FASE 1] Menyiapkan Data Historis + EMA ---")
        
        # 1. Ambil Data
        df_raw = fetch_historical_data(SYMBOL, INTERVAL, START_DATE)
        
        # 2. Clean Data (dengan Log)
        if os.path.exists(PATH_LOG): os.remove(PATH_LOG)
        df_clean = clean_historical_batch(df_raw, log_filepath=PATH_LOG)
        
        # 3. Hitung Indikator & Simpan RAW
        print(f"Processing Raw Data -> {PATH_RAW}")
        apply_indicators_and_save(df_raw, PATH_RAW, mode='w')
        
        # 4. Hitung Indikator & Simpan CLEANED
        print(f"Processing Cleaned Data -> {PATH_CLEAN}")
        apply_indicators_and_save(df_clean, PATH_CLEAN, mode='w')
        
        print("Inisialisasi Selesai.")
    else:
        print("Database ditemukan. Melanjutkan ke Real-time.")

    # ==========================================
    # FASE 2: REAL-TIME (PARALEL)
    # ==========================================
    print(f"\n--- [FASE 2] Real-Time Tracker (RSI + EMA 50/200) ---")
    client = Client()
    
    while True:
        try:
            # 1. BACA HISTORY
            # [PENTING] Kita butuh minimal 200 data terakhir untuk EMA 200 yang akurat.
            # Kita set 300 agar aman.
            if os.path.exists(PATH_RAW) and os.path.exists(PATH_CLEAN):
                df_hist_raw = pd.read_csv(PATH_RAW).tail(300) 
                df_hist_clean = pd.read_csv(PATH_CLEAN).tail(300)
                
                last_time = pd.to_datetime(df_hist_raw.iloc[-1]['Open Time'])
            else:
                break

            # 2. GET LIVE DATA
            klines = client.get_klines(symbol=SYMBOL, interval=INTERVAL, limit=2)
            closed_candle = klines[0]
            candle_time = pd.to_datetime(closed_candle[0], unit='ms')

            # 3. PROSES DATA BARU
            if candle_time > last_time:
                # --- SIAPKAN DATA ---
                row_raw = {
                    'Open Time': candle_time,
                    'Open': float(closed_candle[1]), 'High': float(closed_candle[2]),
                    'Low': float(closed_candle[3]), 'Close': float(closed_candle[4]),
                    'Volume': float(closed_candle[5])
                }
                
                # --- JALUR 1: RAW ---
                # Gabung -> Hitung Semua Indikator -> Simpan Baris Terakhir
                df_concat_raw = pd.concat([df_hist_raw, pd.DataFrame([row_raw])], ignore_index=True)
                # Fungsi ini otomatis menghitung RSI, EMA50, EMA200 dan menyimpan ke CSV
                res_raw = apply_indicators_and_save(df_concat_raw, PATH_RAW, mode='a')
                final_raw = res_raw.iloc[-1]

                # --- JALUR 2: CLEANED ---
                # Bersihkan dulu baris barunya
                row_clean = clean_one_candle(row_raw, df_hist_clean, log_filepath=PATH_LOG)
                
                # Gabung -> Hitung Semua Indikator -> Simpan Baris Terakhir
                df_concat_clean = pd.concat([df_hist_clean, pd.DataFrame([row_clean])], ignore_index=True)
                res_clean = apply_indicators_and_save(df_concat_clean, PATH_CLEAN, mode='a')
                final_clean = res_clean.iloc[-1]

                # --- DISPLAY ---
                print(f"[{datetime.now().strftime('%H:%M')}] Saved.")
                print(f" RAW | Close:{final_raw['Close']} | RSI:{final_raw['RSI']} | EMA50:{final_raw['EMA_50']} | EMA200:{final_raw['EMA_200']}")
                print(f" CLN | Close:{final_clean['Close']} | RSI:{final_clean['RSI']} | EMA50:{final_clean['EMA_50']} | EMA200:{final_clean['EMA_200']}")
                print("-" * 60)
                
            else:
                live = float(klines[1][4])
                print(f"Waiting 5m Close... Live: {live:.2f}", end='\r')

            time.sleep(2)

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()