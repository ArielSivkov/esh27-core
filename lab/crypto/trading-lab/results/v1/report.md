# Backtest v1 — out-of-sample summary

| asset | OOS period | picked (in-sample) | OOS Sharpe | B&H OOS Sharpe | OOS max DD | random p95 | beats B&H |
|---|---|---|---|---|---|---|---|
| BTC 1d (Binance) | 2023-01-28→2026-06-16 | sma_cross {'fast': 5, 'slow': 100} | 0.997 | 0.9 | -0.2916 | 1.223 | yes |
| BTC 4h (Binance) | 2023-01-28→NaT | tsmom {'lookback': 250} | 1.153 | 0.913 | -0.3579 | 0.94 | yes |
| ethereum 1d (CoinGecko) | 2020-10-13→2024-03-27 | tsmom {'lookback': 20} | 0.785 | 1.21 | -0.7249 | 1.498 | no |
| solana 1d (CoinGecko) | 2022-08-27→2024-03-27 | donchian {'n': 55} | 2.074 | 1.548 | -0.3137 | 2.173 | yes |
| binancecoin 1d (CoinGecko) | 2021-08-17→2024-03-27 | sma_cross {'fast': 5, 'slow': 50} | 0.976 | 0.528 | -0.3376 | 0.981 | yes |
| cardano 1d (CoinGecko) | 2021-08-29→2024-03-27 | tsmom {'lookback': 20} | -0.352 | -0.31 | -0.8075 | 0.468 | no |
| dogecoin 1d (CoinGecko) | 2020-07-17→2024-03-27 | donchian {'n': 20} | 1.253 | 1.108 | -0.6563 | 1.247 | yes |
| chainlink 1d (CoinGecko) | 2021-09-07→2024-03-27 | rsi_mr {'n': 14, 'lo': 30, 'hi': 70} | -0.077 | 0.233 | -0.7896 | 0.8 | no |
| SPY 1d (US ETF) | 2012-10-10→2017-11-10 | rsi_mr {'n': 2, 'lo': 30, 'hi': 70} | 0.8 | 1.183 | -0.1291 | 1.207 | no |
| QQQ 1d (US ETF) | 2010-05-26→2017-11-10 | rsi_mr {'n': 2, 'lo': 10, 'hi': 50} | 0.367 | 1.157 | -0.1358 | 1.205 | no |
| IWM 1d (US ETF) | 2012-10-10→2017-11-10 | rsi_mr {'n': 2, 'lo': 30, 'hi': 50} | 0.676 | 0.894 | -0.2305 | 1.062 | no |
| DIA 1d (US ETF) | 2012-10-10→2017-11-10 | sma_cross {'fast': 50, 'slow': 200} | 0.969 | 1.194 | -0.2097 | 1.303 | no |
| AAPL 1d (US stock) | 2004-08-02→2017-11-10 | donchian {'n': 20} | 1.16 | 1.167 | -0.3465 | 1.134 | no |
| MSFT 1d (US stock) | 2005-03-09→2017-11-10 | rsi_mr {'n': 2, 'lo': 10, 'hi': 50} | 0.259 | 0.542 | -0.1501 | 0.629 | no |
| JPM 1d (US stock) | 1998-09-01→2017-11-10 | tsmom {'lookback': 20} | 0.216 | 0.364 | -0.6934 | 0.485 | no |
| XOM 1d (US stock) | 1998-09-01→2017-11-10 | rsi_mr {'n': 14, 'lo': 30, 'hi': 50} | 0.62 | 0.374 | -0.1542 | 0.455 | yes |
