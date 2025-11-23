import pandas as pd
from binance.client import Client
import time
from datetime import datetime
import os

# 1. Konfigurasi
symbol = "BNBUSDT"
interval = Client.KLINE_INTERVAL_5MINUTE # Gunakan 5 Menit agar update-nya cepat terasa
csv_file = './Data/historical_bnb.csv'

client = Client()

def get_last_timestamp_from_csv(filename):
    """Membaca waktu terakhir yang tersimpan di CSV agar tidak duplikat"""
    if not os.path.exists(filename):
        return 0
    try:
        # Baca baris terakhir saja biar cepat
        df = pd.read_csv(filename)
        if not df.empty:
            return df.iloc[-1]['Open Time']
    except:
        return 0
    return 0

print(f"Memulai tracker real-time untuk {symbol}...")
print("Tekan Ctrl+C untuk berhenti.")

while True:
    try:
        # 2. Ambil data candle terbaru (ambil 2 terakhir untuk memastikan candle yang close)
        klines = client.get_klines(symbol=symbol, interval=interval, limit=2)
        
        # Ambil candle yang SUDAH SELESAI (index 0, karena index 1 adalah yang sedang jalan)
        # Jika Anda ingin data yang 'sedang jalan', ubah index ke [-1] tapi hati-hati duplikat
        latest_kline = klines[-1] 
        
        # Format data agar sesuai dengan struktur CSV sebelumnya
        # Structure kline: [Open Time, Open, High, Low, Close, Volume, ...]
        open_time_ms = latest_kline[0]
        open_time_human = pd.to_datetime(open_time_ms, unit='ms')
        
        new_data = {
            'Open Time': open_time_human,
            'Open': float(latest_kline[1]),
            'High': float(latest_kline[2]),
            'Low': float(latest_kline[3]),
            'Close': float(latest_kline[4]),
            'Volume': float(latest_kline[5])
        }
        
        # 3. Cek apakah data ini sudah ada di CSV
        last_saved_time = pd.to_datetime(get_last_timestamp_from_csv(csv_file))
        
        if new_data['Open Time'] > last_saved_time:
            # Buat DataFrame 1 baris
            df_new = pd.DataFrame([new_data])
            
            # 4. Append (Tambahkan) ke CSV tanpa menulis ulang Header
            # mode='a' artinya append (tambah di bawah)
            # header=False artinya jangan tulis judul kolom lagi
            df_new.to_csv(csv_file, mode='a', header=False, index=False)
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Data baru ditambahkan: Close Price {new_data['Close']}")
        else:
            # Jika waktu sama, berarti candle belum ganti (masih di menit yang sama)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Menunggu candle baru... Harga saat ini: {new_data['Close']}", end='\r')
            
        # Tunggu X detik sebelum request lagi (jangan spam API)
        time.sleep(5) 

    except Exception as e:
        print(f"Error: {e}")
        time.sleep(5)