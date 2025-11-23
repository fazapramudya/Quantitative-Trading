import pandas as pd
from binance.client import Client

def fetch_historical_data(symbol, interval, start_date):
    print(f"[HISTORY] Mengunduh data {symbol}...")
    client = Client()
    klines = client.get_historical_klines(symbol, interval, start_date)
    
    data = []
    for k in klines:
        data.append({
            'Open Time': pd.to_datetime(k[0], unit='ms'),
            'Open': float(k[1]), 'High': float(k[2]), 'Low': float(k[3]),
            'Close': float(k[4]), 'Volume': float(k[5])
        })
    return pd.DataFrame(data)