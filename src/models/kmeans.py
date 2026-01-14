import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

def prepare_features(df):
    """
    Mengubah data raw indicators menjadi fitur untuk K-Means.
    """
    df_feat = df.copy()
    
    # Feature Engineering
    df_feat['dist_ema_50'] = (df_feat['Close'] / df_feat['EMA_50']) - 1
    df_feat['dist_ema_200'] = (df_feat['Close'] / df_feat['EMA_200']) - 1
    df_feat['vol_pct'] = df_feat['Volume'].pct_change()
    
    feature_cols = ['RSI', 'dist_ema_50', 'dist_ema_200', 'vol_pct']
    
    # Hapus NaN agar tidak error saat scaling
    df_feat = df_feat.dropna(subset=feature_cols)
    return df_feat, feature_cols

def init_kmeans(df_history, n_clusters=4):
    """
    Melakukan training awal pada data historis.
    Return: model, scaler, dan list nama fitur.
    """
    df_feat, feat_cols = prepare_features(df_history)
    
    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(df_feat[feat_cols])
    
    model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    model.fit(scaled_data)
    
    return model, scaler, feat_cols

def update_streaming_plot(df_latest, model, scaler, feat_cols, save_path="regime_live.png"):
    """
    Prediksi cluster untuk data terbaru dan update gambar.
    """
    # 1. Siapkan fitur
    df_feat, _ = prepare_features(df_latest)
    if df_feat.empty: return
    
    # 2. Prediksi
    scaled_data = scaler.transform(df_feat[feat_cols])
    df_feat['cluster'] = model.predict(scaled_data)
    
    # 3. Plotting
    plt.figure(figsize=(12, 6))
    colors = ['blue', 'green', 'red', 'orange', 'purple']
    
    for cluster_id in range(model.n_clusters):
        mask = df_feat['cluster'] == cluster_id
        if not mask.any(): continue
        
        plt.scatter(
            df_feat.index[mask], 
            df_feat.loc[mask, 'Close'], 
            label=f'Cluster {cluster_id}', 
            color=colors[cluster_id % len(colors)],
            s=5, alpha=0.7
        )
    
    plt.title(f"Live Market Regime | Last: {df_feat.index[-1]}")
    plt.legend(loc='upper left')
    plt.grid(True, alpha=0.2)
    plt.savefig(save_path)
    plt.close() # WAJIB: Agar memory tidak leak
    
    return df_feat['cluster'].iloc[-1] # Mengembalikan cluster terakhir