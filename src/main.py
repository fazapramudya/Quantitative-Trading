import os
from config.settings import DATA_PATH
from binance.client import Client
from data_prep.cleaning.anomaly_cleaner import clean_historical_batch
from data_prep.historical.fetch_binance import fetch_historical_data
from data_prep.realtime.stream_binance import start_realtime_tracking

# --- KONFIGURASI ---
SYMBOL = "BNBUSDT"
INTERVAL = Client.KLINE_INTERVAL_5MINUTE
START_DATE = "21 Nov, 2025"

FILE_PATH = DATA_PATH / 'raw' / 'bnbusdt_5m_21-11-2025_to_date.csv'

def main():
    # Buat folder Data jika belum ada
    if FILE_PATH.parent.exists() == False:
        FILE_PATH.parent.exists().mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------
    # STEP 1: CEK & AMBIL HISTORICAL DATA
    # ---------------------------------------------------------
    if not FILE_PATH.exists():
        print("--- FASE 1: INISIALISASI DATA ---")
        
        # A. Retrieve
        df_raw = fetch_historical_data(SYMBOL, INTERVAL, START_DATE)
        
        # B. Clean (Batch)
        df_clean = clean_historical_batch(df_raw)
        
        # C. Save
        df_clean.to_csv(FILE_PATH, index=False, float_format='%.2f')
        print(f"Data historis bersih tersimpan di: {FILE_PATH}")
    else:
        print(f"File {FILE_PATH} sudah ada. Langsung ke Real-time.")

    # ---------------------------------------------------------
    # STEP 2: JALANKAN REAL-TIME LOOP (Get -> Clean -> Append)
    # ---------------------------------------------------------
    print("\n--- FASE 2: REAL-TIME TRACKING ---")
    start_realtime_tracking(SYMBOL, INTERVAL, FILE_PATH)

if __name__ == "__main__":
    main()