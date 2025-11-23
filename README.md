
```
quant-T
├─ .env
├─ .env.example
├─ .python-version
├─ data
│  ├─ processed
│  └─ raw
│     └─ bnb.csv
├─ pyproject.toml
├─ README.md
├─ src
│  ├─ backtest
│  │  ├─ data_loader.py
│  │  ├─ executor.py
│  │  ├─ metrics.py
│  │  └─ __init__.py
│  ├─ config
│  │  ├─ settings.py
│  │  └─ __init__.py
│  ├─ data_prep
│  │  ├─ cleaning
│  │  │  ├─ anomaly_cleaner.py
│  │  │  └─ __init__.py
│  │  ├─ historical
│  │  │  ├─ fetch_binance.py
│  │  │  ├─ fetch_yfinance.py
│  │  │  └─ __init__.py
│  │  ├─ realtime
│  │  │  ├─ stream_binance.py
│  │  │  └─ __init__.py
│  │  └─ __init__.py
│  ├─ exchange
│  │  ├─ binance_api.py
│  │  ├─ order_executor.py
│  │  ├─ trade_history.py
│  │  └─ __init__.py
│  ├─ features
│  │  ├─ cvd.py
│  │  ├─ dom.py
│  │  ├─ ema.py
│  │  ├─ rsi.py
│  │  ├─ volume.py
│  │  └─ __init__.py
│  ├─ main.py
│  ├─ models
│  │  ├─ clustering.py
│  │  ├─ probabilities.py
│  │  └─ __init__.py
│  ├─ pipeline
│  │  ├─ run_backtest.py
│  │  ├─ run_live_trading.py
│  │  ├─ run_prep.py
│  │  └─ __init__.py
│  ├─ storage
│  │  ├─ db_reader.py
│  │  ├─ db_writer.py
│  │  ├─ supabase_client.py
│  │  └─ __init__.py
│  └─ utils
│     ├─ decorators.py
│     ├─ logger.py
│     ├─ time_utils.py
│     └─ __init__.py
├─ tests
│  ├─ test_backtest.py
│  ├─ test_data_prep.py
│  ├─ test_exchange.py
│  ├─ test_features.py
│  ├─ test_models.py
│  └─ __init__.py
└─ uv.lock

```