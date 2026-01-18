import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# Di dalam models/kmeans.py
def prepare_features(df):
    df_feat = df.copy()
    # Paksa lowercase agar tidak bentrok
    df_feat.columns = [c.lower() for c in df_feat.columns]
    
    # Gunakan 'close' (huruf kecil)
    df_feat['dist_ema_50'] = (df_feat['close'] / df_feat['ema_50']) - 1
    df_feat['dist_ema_200'] = (df_feat['close'] / df_feat['ema_200']) - 1
    df_feat['vol_pct'] = df_feat['volume'].pct_change()
    
    feature_cols = ['rsi', 'dist_ema_50', 'dist_ema_200', 'vol_pct']
    df_feat = df_feat.dropna(subset=feature_cols)
    return df_feat, feature_cols

def init_kmeans(df_history, n_clusters=4):
    df_feat, feat_cols = prepare_features(df_history)
    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(df_feat[feat_cols])
    
    model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    model.fit(scaled_data)
    return model, scaler, feat_cols

def update_streaming_plot(df_latest, model, scaler, feat_cols, save_path):
    df_feat, _ = prepare_features(df_latest)
    if df_feat.empty: return
    
    scaled_data = scaler.transform(df_feat[feat_cols])
    df_feat['cluster'] = model.predict(scaled_data)
    
    plt.figure(figsize=(12, 6))
    colors = ['blue', 'green', 'red', 'orange', 'purple']
    for cluster_id in range(model.n_clusters):
        mask = df_feat['cluster'] == cluster_id
        if not mask.any(): continue
        plt.scatter(df_feat.index[mask], df_feat.loc[mask, 'close'], 
                    label=f'Cluster {cluster_id}', color=colors[cluster_id % 5], s=5)
    
    plt.title(f"Live Market Regime | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    plt.legend()
    plt.savefig(save_path)
    plt.close()
    return int(df_feat['cluster'].iloc[-1])