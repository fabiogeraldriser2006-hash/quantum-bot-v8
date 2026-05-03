"""
=========================================================
FILE: data_engine.py
DESKRIPSI: Mesin pengolah data. Bertugas menarik harga dari Indodax,
membuat data cadangan (sintetis) jika diblokir, dan menghitung indikator teknikal.
=========================================================
"""

import requests
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import random
import urllib3

import config # Mengambil pengaturan dari file config.py

# Matikan peringatan keamanan SSL saat menarik API
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def hitung_indikator_teknikal(df):
    """Menghitung indikator teknikal (RSI, MACD, Bollinger Bands, OBV, ATR)."""
    if df.empty: return df
    df = df.sort_values('Date').reset_index(drop=True)
    
    # RSI (Relative Strength Index)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df['RSI'] = df['RSI'].fillna(50)
    
    # MACD (Moving Average Convergence Divergence)
    ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema_12 - ema_26
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    
    # Bollinger Bands
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    std_20 = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['SMA_20'] + (std_20 * 2)
    df['BB_Lower'] = df['SMA_20'] - (std_20 * 2)
    
    # ATR (Average True Range) - Digunakan untuk Trailing Stop
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    df['ATR'] = np.max(ranges, axis=1).rolling(14).mean()
    
    # OBV (On-Balance Volume)
    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    df = df.bfill().fillna(0) 
    return df

def tarik_data_live_indodax():
    """Mengambil harga Spot terakhir untuk semua koin (Fungsi ringan)."""
    try: 
        return requests.get(config.INDODAX_PUBLIC_API_URL, timeout=5, verify=False).json()['tickers']
    except Exception: 
        return None

def buat_data_sintetis(ticker_data, limit=120, interval_minutes=15):
    """Pabrik lilin buatan jika Indodax memblokir koneksi kita."""
    try:
        current_price = float(ticker_data['last'])
        high_price = float(ticker_data['high'])
        low_price = float(ticker_data['low'])
        dates = [datetime.now() - timedelta(minutes=i*interval_minutes) for i in range(limit, -1, -1)]
        data = []
        sim_price = low_price + ((high_price - low_price) * 0.5) 
        
        for i, date in enumerate(dates):
            if i == len(dates) - 1:
                close_p = current_price; open_p = sim_price
                high_p = max(open_p, close_p) * (1 + random.uniform(0, 0.002))
                low_p = min(open_p, close_p) * (1 - random.uniform(0, 0.002))
            else:
                volatility = (high_price - low_price) * 0.05
                open_p = sim_price
                close_p = max(low_price, min(high_price, open_p + random.uniform(-volatility, volatility)))
                high_p = max(open_p, close_p) + random.uniform(0, volatility * 0.5)
                low_p = min(open_p, close_p) - random.uniform(0, volatility * 0.5)
                sim_price = close_p
            data.append([date, open_p, high_p, low_p, close_p, random.uniform(10, 1000)])
        return pd.DataFrame(data, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
    except Exception: 
        return pd.DataFrame()

def tarik_grafik_klines_aman(symbol, tf, limit, ticker_data=None):
    """Menarik sejarah harga, otomatis beralih ke data sintetis jika gagal."""
    interval_min = 15
    try:
        if tf == "1D": tf_api = "1D"; multiplier = 86400; interval_min = 1440
        elif tf == "4h": tf_api = "240"; multiplier = 240 * 60; interval_min = 240
        elif tf == "1h": tf_api = "60"; multiplier = 60 * 60; interval_min = 60
        else: tf_api = "15"; multiplier = 15 * 60; interval_min = 15
        
        end_time = int(time.time()); start_time = end_time - (limit * multiplier)
        url = f"https://indodax.com/tradingview/history_v2?symbol={symbol}&resolution={tf_api}&from={start_time}&to={end_time}"
        headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}
        res = requests.get(url, headers=headers, timeout=5, verify=False)
        data = res.json()
        
        if isinstance(data, dict) and data.get('s') == 'ok':
            return pd.DataFrame({'Date': pd.to_datetime(data['t'], unit='s'), 'Open': data['o'], 'High': data['h'], 'Low': data['l'], 'Close': data['c'], 'Volume': data['v']}), "Direct API"
        else: 
            raise ValueError("JSON Error")
    except Exception:
        if ticker_data: 
            df_sintetis = buat_data_sintetis(ticker_data, limit, interval_min)
            return df_sintetis, "Synthetic Engine Active"
        else: 
            return pd.DataFrame(), "Error"

def tarik_sentimen_global():
    """Menarik data Fear & Greed Index."""
    try:
        res = requests.get(config.ALTERNATIVE_ME_API_URL, timeout=5)
        return int(res.json()['data'][0]['value'])
    except Exception: 
        return 50 # Default netral
