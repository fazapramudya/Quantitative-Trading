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
from models.kmeans import init_kmeans, update_streaming_plot

# --- KONFIGURASI ---
SYMBOL = "BNBUSDT"
INTERVAL = Client.KLINE_INTERVAL_1MINUTE
START_DATE = "5 Jan, 2026"

PATH_RAW = DATA_PATH / 'raw' / 'raw_bnbusdt_1m_21-11-2025_to_date.csv'
PATH_CLEAN = DATA_PATH / 'clean' / 'clean_bnbusdt_1m_21-11-2025_to_date.csv'
PATH_LOG = DATA_PATH / 'log' / 'log_bnbusdt_1m_21-11-2025_to_date.csv'

def calculate_indicators_only(df):
    """Fungsi helper untuk hitung indikator tanpa simpan ke CSV"""
    df_final = add_rsi_indicator(df, column_name='Close', period=14)
    df_final = add_ema_indicator(df_final, column_name='Close', period=50)
    df_final = add_ema_indicator(df_final, column_name='Close', period=200)
    return df_final

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

    kmeans_dir = os.path.join("data", "k-means")
    if not os.path.exists(kmeans_dir):
        os.makedirs(kmeans_dir)

    print("--- [K-MEANS] Training Initial Model ---")
    df_init = pd.read_csv(PATH_CLEAN)
    km_model, km_scaler, km_features = init_kmeans(df_init)

    # TAMBAHKAN: Gambar pertama kali saat inisialisasi (agar tidak nunggu 5 menit)
    print("--- Generating Initial Plot ---")
    df_init_feat = calculate_indicators_only(df_init)
    update_streaming_plot(df_init_feat.tail(1000), km_model, km_scaler, km_features, 
                          save_path=os.path.join(kmeans_dir, "live_regime_plot.png"))

    # ==========================================
    # FASE 2: REAL-TIME
    # ==========================================
    print(f"\n--- [FASE 2] Real-Time Tracker ---")
    client = Client()
    
    # Inisialisasi variabel di luar loop
    df_hist_clean = pd.read_csv(PATH_CLEAN)
    df_hist_raw = pd.read_csv(PATH_RAW)

    while True:
        try:
            last_time = pd.to_datetime(df_hist_clean.iloc[-1]['Open Time'])
            klines = client.get_klines(symbol=SYMBOL, interval=INTERVAL, limit=2)
            closed_candle = klines[0]
            candle_time = pd.to_datetime(closed_candle[0], unit='ms')

            if candle_time > last_time:
                # A. RAW
                row_raw = {
                    'Open Time': candle_time,
                    'Open': float(closed_candle[1]), 'High': float(closed_candle[2]),
                    'Low': float(closed_candle[3]), 'Close': float(closed_candle[4]),
                    'Volume': float(closed_candle[5])
                }
                df_hist_raw = pd.concat([df_hist_raw, pd.DataFrame([row_raw])], ignore_index=True)
                
                # PERBAIKAN: Gunakan fungsi yang sudah dibuat
                res_raw_full = calculate_indicators_only(df_hist_raw) 
                res_raw_full.tail(1).to_csv(PATH_RAW, mode='a', header=False, index=False)

                # B. CLEAN
                row_clean = clean_one_candle(row_raw, df_hist_clean.tail(300), log_filepath=PATH_LOG)
                df_hist_clean = pd.concat([df_hist_clean, pd.DataFrame([row_clean])], ignore_index=True)
                
                # PERBAIKAN: Gunakan fungsi yang sudah dibuat
                res_clean_full = calculate_indicators_only(df_hist_clean) 
                res_clean_full.tail(1).to_csv(PATH_CLEAN, mode='a', header=False, index=False)

                # UPDATE PLOT
                path_plot = os.path.join(kmeans_dir, "live_regime_plot.png")
                last_cluster = update_streaming_plot(
                    res_clean_full.tail(1000), 
                    km_model, km_scaler, km_features, 
                    save_path=path_plot
                )

                print(f"[{datetime.now().strftime('%H:%M')}] New Candle! Cluster: {last_cluster}")
                
            else:
                # 1. Ambil harga live saat ini
                live_price = float(klines[1][4])
                live_volume = float(klines[1][5])

                # 2. Buat dataframe sementara untuk menghitung indikator live
                # Kita tempelkan harga live ke data history terakhir
                df_live = df_hist_clean.tail(300).copy()
                
                # Buat baris sementara (unclosed candle)
                new_row_live = df_live.iloc[-1].copy()
                new_row_live['Close'] = live_price
                new_row_live['Volume'] = live_volume
                
                # Gabungkan
                df_live = pd.concat([df_live, pd.DataFrame([new_row_live])], ignore_index=True)
                
                # 3. Hitung Indikator untuk harga live
                df_live_ready = calculate_indicators_only(df_live)
                
                # 4. Prediksi Cluster untuk baris paling terakhir (yang sedang jalan)
                # Ambil fitur yang dibutuhkan saja
                from models.kmeans import prepare_features # Pastikan fungsi ini bisa diakses
                df_feat_live, feat_cols = prepare_features(df_live_ready.tail(5))
                
                if not df_feat_live.empty:
                    scaled_live = km_scaler.transform(df_feat_live[feat_cols])
                    live_cluster = km_model.predict(scaled_live)[-1]
                else:
                    live_cluster = "Calc..."

                # 5. Tampilkan hasilnya (Ganti '?' dengan live_cluster)
                print(f"Waiting {INTERVAL}... Live: {live_price:.2f} | Cluster Saat Ini: {live_cluster}    ", end='\r')
            time.sleep(2)

        except Exception as e:
            print(f"\nError di Main Loop: {e}") # Ini akan memberitahu jika ada error path atau fungsi
            time.sleep(5)

if __name__ == "__main__":
    main()