import pandas as pd
from binance.client import Client
import time
from datetime import datetime
import os

# Import Fungsi Cleaning Single Candle
from Clean_Data.cleaning_data import clean_one_candle

def start_realtime_tracking(symbol, interval, csv_file):
    print(f"[REALTIME] Memulai tracker {symbol}...")
    client = Client()
    
    while True:
        try:
            # 1. Baca Data Historis Terakhir (Untuk referensi cleaning)
            if os.path.exists(csv_file):
                # Baca 50 baris terakhir saja biar cepat
                df_history = pd.read_csv(csv_file).tail(50)
                last_saved_time = pd.to_datetime(df_history.iloc[-1]['Open Time'])
            else:
                print("Error: File CSV tidak ditemukan.")
                break

            # 2. Ambil Data Live dari Binance
            klines = client.get_klines(symbol=symbol, interval=interval, limit=2)
            closed_candle = klines[0] # Candle yang baru close (index 0)
            
            candle_time = pd.to_datetime(closed_candle[0], unit='ms')

            # 3. Jika ada candle baru (Waktunya > Waktu terakhir di CSV)
            if candle_time > last_saved_time:
                # Siapkan Raw Data
                raw_data = {
                    'Open Time': candle_time,
                    'Open': float(closed_candle[1]),
                    'High': float(closed_candle[2]),
                    'Low': float(closed_candle[3]),
                    'Close': float(closed_candle[4]),
                    'Volume': float(closed_candle[5])
                }
                
                # -------------------------------------------------
                # 4. PROSES CLEANING REAL-TIME DI SINI
                # -------------------------------------------------
                final_data = clean_one_candle(raw_data, df_history)
                
                # 5. Append ke CSV
                df_new = pd.DataFrame([final_data])
                df_new.to_csv(csv_file, mode='a', header=False, index=False, float_format='%.2f')
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Data Masuk & Cleaned: {final_data['Close']}")
            
            else:
                # Display Loading
                live_price = float(klines[1][4])
                print(f"Waiting Close... Live Price: {live_price:.2f}", end='\r')

            time.sleep(2)

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)