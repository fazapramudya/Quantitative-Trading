import os
import pandas as pd
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

FILE_PATH = DATA_PATH / 'raw' / 'bnbusdt_1m_21-11-2025_to_date.csv'

def main():
    if not os.path.exists(os.path.dirname(FILE_PATH)):
        os.makedirs(os.path.dirname(FILE_PATH))

    # ---------------------------------------------------------
    # STEP 1: HISTORICAL DATA (Retrieve -> Clean -> RSI -> Save)
    # ---------------------------------------------------------
    if not os.path.exists(FILE_PATH):
        print("--- FASE 1: INISIALISASI DATA ---")
        
        # 1. Retrieve
        df_raw = fetch_historical_data(SYMBOL, INTERVAL, START_DATE)
        
        # 2. Clean
        df_clean = clean_historical_batch(df_raw)
        
        # 3. [BARU] Hitung RSI
        print("[ANALYSIS] Menghitung RSI (14)...")
        df_final = add_rsi_indicator(df_clean, period=14)
        
        # Simpan
        df_final.to_csv(FILE_PATH, index=False, float_format='%.2f')
        print(f"Data historis + RSI tersimpan di: {FILE_PATH}")
    else:
        print(f"File {FILE_PATH} sudah ada. Langsung ke Real-time.")

    # ---------------------------------------------------------
    # STEP 2: REAL-TIME TRACKING (Manual Logic di sini agar RSI update)
    # ---------------------------------------------------------
    print("\n--- FASE 2: REAL-TIME TRACKING (1 Menit) ---")
    
    # Kita tidak bisa pakai fungsi start_realtime_tracking lama mentah-mentah
    # karena kita perlu menyisipkan perhitungan RSI sebelum save.
    # Jadi kita tulis ulang loop sederhananya disini atau update modul realtime.
    # Untuk kemudahan, saya tulis loopnya disini agar terlihat alurnya:
    
    client = Client()
    import time
    from datetime import datetime

    while True:
        try:
            # A. Baca History (Butuh minimal 15-20 data terakhir untuk RSI)
            if os.path.exists(FILE_PATH):
                # Baca 100 baris terakhir cukup
                df_history = pd.read_csv(FILE_PATH).tail(100)
                last_saved_time = pd.to_datetime(df_history.iloc[-1]['Open Time'])
            else:
                break

            # B. Get Live Data
            klines = client.get_klines(symbol=SYMBOL, interval=INTERVAL, limit=2)
            closed_candle = klines[0]
            candle_time = pd.to_datetime(closed_candle[0], unit='ms')

            # C. Jika Candle Baru Close
            if candle_time > last_saved_time:
                # 1. Siapkan Raw
                raw_row = {
                    'Open Time': candle_time,
                    'Open': float(closed_candle[1]), 'High': float(closed_candle[2]),
                    'Low': float(closed_candle[3]), 'Close': float(closed_candle[4]),
                    'Volume': float(closed_candle[5])
                }
                
                # 2. Clean Data Baru (Single Row)
                cleaned_row = clean_one_candle(raw_row, df_history)
                
                # 3. [PENTING] Hitung RSI Real-time
                # Gabungkan data baru ke dataframe history sementara untuk hitung RSI
                df_temp = pd.DataFrame([cleaned_row])
                df_concat = pd.concat([df_history, df_temp], ignore_index=True)
                
                # Hitung RSI ulang untuk data gabungan ini
                df_with_rsi = add_rsi_indicator(df_concat, period=14)
                
                # Ambil baris terakhir saja (yang baru kita tambahkan)
                final_row = df_with_rsi.iloc[-1]
                
                rsi_val = final_row['RSI']
                signal = check_rsi_signal(rsi_val)

                # 4. Simpan ke CSV
                # Kita ubah final_row kembali ke DataFrame untuk disimpan
                df_save = pd.DataFrame([final_row])
                df_save.to_csv(FILE_PATH, mode='a', header=False, index=False, float_format='%.2f')
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Close: {final_row['Close']} | RSI: {rsi_val} | Status: {signal}")
            
            else:
                # Monitoring Live
                live_price = float(klines[1][4])
                print(f"Waiting 1m Close... Price: {live_price:.2f}", end='\r')

            time.sleep(2)

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()