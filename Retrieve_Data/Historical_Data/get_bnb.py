from binance.client import Client
import pandas as pd
from datetime import datetime

# 1. Inisialisasi Client (Untuk data publik tidak wajib pakai API Key)
client = Client()

# 2. Tentukan Parameter
symbol = "BNBUSDT"  # Ticker (Pair)
interval = Client.KLINE_INTERVAL_5MINUTE  # Interval (1m, 1h, 1d, 1w, etc)
start_str = "1 Sep, 2025" # Tanggal mulai

# 3. Request Data Historis
# Fungsi ini akan mengambil semua data dari tanggal start sampai sekarang
print(f"Mengambil data {symbol}...")
klines = client.get_historical_klines(symbol, interval, start_str)

# 4. Masukkan ke Pandas DataFrame agar rapi
df = pd.DataFrame(klines, columns=[
    'Open Time', 'Open', 'High', 'Low', 'Close', 'Volume',
    'Close Time', 'Quote Asset Volume', 'Number of Trades',
    'Taker Buy Base Asset Vol', 'Taker Buy Quote Asset Vol', 'Ignore'
])

# 5. Format Data (Ubah tipe data string ke float/datetime)
df['Open Time'] = pd.to_datetime(df['Open Time'], unit='ms')
df['Close Time'] = pd.to_datetime(df['Close Time'], unit='ms')

cols_to_numeric = ['Open', 'High', 'Low', 'Close', 'Volume']
df[cols_to_numeric] = df[cols_to_numeric].apply(pd.to_numeric, axis=1)

# Pilih kolom yang penting saja
df = df[['Open Time', 'Open', 'High', 'Low', 'Close', 'Volume']]

# 6. Lihat hasil atau simpan ke CSV
print(df.head())
df.to_csv('./data/historical_bnb.csv', index=False)
print("Data berhasil disimpan ke data_historical_bnb.csv")