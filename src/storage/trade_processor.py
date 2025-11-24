import pandas as pd
from typing import Dict, Any
from db_ops import sb_fetch, sb_insert 


OHLCV_AGG_RULES = {
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}


def resample_ohlcv_data(
    df: pd.DataFrame, 
    opentime_column: str, 
    frequency: str
) -> pd.DataFrame:
    """
    Resamples high-frequency trading data (OHLCV) into a lower frequency.

    Args:
        df (pd.DataFrame): The input DataFrame with a datetime index and OHLCV columns.
        frequency (str): The target time frequency (e.g., '5T', '1H', '1D').
        
    Returns:
        pd.DataFrame: The resampled DataFrame.
    """
    ohlcv_df = df[['open', 'high', 'low', 'close', 'volume']].apply(pd.to_numeric, errors='coerce')
    
    resampled_df = ohlcv_df.resample(frequency).agg(OHLCV_AGG_RULES)
    
    resampled_df = resampled_df.dropna()
    
    resampled_df = resampled_df.reset_index().rename(columns={'index': opentime_column})
    
    resampled_df[opentime_column] = resampled_df[opentime_column].dt.strftime('%Y-%m-%d %H:%M:%S')

    return resampled_df


def fetch_resample_and_store(
    source_table: str, 
    target_table: str, 
    opentime_column: str = 'open_time',
    frequency: str = '5T'
) -> Dict[str, Any]:
    """
    Fetches raw data from Supabase, processes it by resampling, and stores the result.

    Args:
        source_table (str): The name of the high-frequency table (e.g., 'candles_1m').
        target_table (str): The name of the table to store the resampled data (e.g., 'candles_5m').
        frequency (str): The target time frequency (e.g., '5T' for 5 minutes).

    Returns:
        Dict[str, Any]: A summary of the operation status.
    """
    fetch_result = sb_fetch(source_table, select_columns=f"{opentime_column}, open, high, low, close, volume")
    
    if fetch_result.get("error") or not fetch_result.get("data"):
        return {"status": "FAILED", "reason": f"Failed to fetch data: {fetch_result.get('error', 'No data returned')}"}

    try:
        raw_data = fetch_result['data']
        df_raw = pd.DataFrame(raw_data)
        
        df_raw[opentime_column] = pd.to_datetime(df_raw[opentime_column])
        df_raw = df_raw.set_index(opentime_column)

        df_resampled = resample_ohlcv_data(df_raw, opentime_column, frequency)
        
    except Exception as e:
        return {"status": "FAILED", "reason": f"Data processing failed: {e}"}

    if df_resampled.empty:
        return {"status": "SUCCESS", "reason": "Resampling resulted in an empty dataset. Nothing to store."}
        
    data_to_store = df_resampled.to_dict('records')
    
    store_result = sb_insert(target_table, data_to_store, upsert=True)

    if store_result.get("error"):
        return {"status": "FAILED", "reason": f"Failed to store data: {store_result.get('error')}", "bars_processed": len(data_to_store)}
    
    return {
        "status": "SUCCESS", 
        "reason": "Data fetched, resampled, and stored successfully.",
        "bars_processed": len(raw_data),
        "bars_created": len(data_to_store)
    }

if __name__ == '__main__':
    # EXAMPLE: Convert 1-minute data into 1-hour data
    status = fetch_resample_and_store(
        source_table='btc_usdt_candles_1m',
        target_table='btc_usdt_candles_1h',
        opentime_column='open_time',
        frequency='1H'
    )
    print(status)