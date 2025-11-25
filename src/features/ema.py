import pandas as pd

def add_ema_indicator(df, column_name='Close', period=50):
    """
    Menghitung Exponential Moving Average (EMA).
    Output kolom: EMA_{period} (contoh: EMA_50)
    """
    df_res = df.copy()
    
    # Rumus EMA di Pandas menggunakan ewm(span=period)
    # adjust=False penting agar perhitungan mirip dengan TradingView/Binance
    col_result = f"EMA_{period}"
    df_res[col_result] = df_res[column_name].ewm(span=period, adjust=False).mean()
    
    # Rounding 2 desimal
    df_res[col_result] = df_res[col_result].round(2)
    
    return df_res