"""
================================================================================
FILE: data_engine.py
DESKRIPSI: Mesin Pengolah Data Utama (Data Engine).
Bertugas menarik harga Indodax dengan penyamaran anti-blokir Cloudflare,
menyediakan data sintetis saat offline, dan menghitung indikator teknikal.
================================================================================
"""

import requests
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import random
import urllib3
import config 

# Mematikan peringatan keamanan SSL saat menarik data dari API agar log terminal tetap bersih
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==============================================================================
# 1. MESIN KALKULASI INDIKATOR TEKNIKAL
# ==============================================================================
def hitung_indikator_teknikal(df):
    """
    Menghitung indikator teknikal komprehensif (RSI, MACD, Bollinger Bands, OBV, ATR).
    Fokus utama: Menghasilkan nilai ATR untuk manajemen risiko Trailing Stop.
    """
    if df.empty: return df
    
    # Mengurutkan data berdasarkan waktu dari terlama ke terbaru
    df = df.sort_values('Date').reset_index(drop=True)
    
    # --- RSI (Relative Strength Index) ---
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df['RSI'] = df['RSI'].fillna(50) # Nilai tengah default jika data kurang
    
    # --- MACD (Moving Average Convergence Divergence) ---
    ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema_12 - ema_26
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    
    # --- Bollinger Bands ---
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    std_20 = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['SMA_20'] + (std_20 * 2)
    df['BB_Lower'] = df['SMA_20'] - (std_20 * 2)
    
    # --- ATR (Average True Range) - Kunci untuk Trailing Stop ---
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    df['ATR'] = np.max(ranges, axis=1).rolling(14).mean()
    
    # --- OBV (On-Balance Volume) ---
    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    
    # Membersihkan baris yang kosong (NaN) akibat proses rolling
    df = df.bfill().fillna(0) 
    return df

# ==============================================================================
# 2. MESIN PENARIK HARGA LIVE (ANTI-BLOCK)
# ==============================================================================
def tarik_data_live_indodax():
    """
    Menarik daftar harga spot live seluruh koin di Indodax.
    Menggunakan penyamaran User-Agent tingkat tinggi untuk menembus Cloudflare.
    """
    url = "https://indodax.com/api/tickers" # Endpoint resmi publik
    
    # Identitas penyamaran sebagai browser Google Chrome di sistem Windows
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive'
    }
    
    try: 
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        if response.status_code == 200:
            return response.json()['tickers']
        return None
    except Exception as e: 
        print(f"Error tarik live data: {e}")
        return None

# ==============================================================================
# 3. MESIN GENERATOR DATA SINTETIS (FALLBACK)
# ==============================================================================
def buat_data_sintetis(ticker_data, limit=120, interval_minutes=15):
    """
    Membuat grafik lilin buatan (mock klines) jika API Grafik TradingView Indodax down.
    Sangat berguna agar bot tetap bisa mensimulasikan ATR saat koneksi terputus.
    """
    try:
        current_price = float(ticker_data['last'])
        high_price = float(ticker_data['high'])
        low_price = float(ticker_data['low'])
        dates = [datetime.now() - timedelta(minutes=i*interval_minutes) for i in range(limit, -1, -1)]
        
        data = []
        sim_price = low_price + ((high_price - low_price) * 0.5) 
        
        for i, date in enumerate(dates):
            if i == len(dates) - 1:
                close_p = current_price
                open_p = sim_price
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

# ==============================================================================
# 4. MESIN PENARIK GRAFIK KLINES (TRADINGVIEW INDODAX)
# ==============================================================================
def tarik_grafik_klines_aman(symbol, tf, limit, ticker_data=None):
    """
    Menarik sejarah harga (Klines/Candlestick) dari API TradingView Indodax.
    Dilengkapi sistem fallback otomatis ke Data Sintetis jika jaringan putus.
    """
    interval_min = 15
    try:
        # Menyesuaikan kerangka waktu (Timeframe) dengan format API Indodax
        if tf == "1D": tf_api = "1D"; multiplier = 86400; interval_min = 1440
        elif tf == "4h": tf_api = "240"; multiplier = 240 * 60; interval_min = 240
        elif tf == "1h": tf_api = "60"; multiplier = 60 * 60; interval_min = 60
        else: tf_api = "15"; multiplier = 15 * 60; interval_min = 15
        
        end_time = int(time.time())
        start_time = end_time - (limit * multiplier)
        
        url = f"https://indodax.com/tradingview/history_v2?symbol={symbol}&resolution={tf_api}&from={start_time}&to={end_time}"
        
        # Penyamaran browser yang lebih kuat
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json'
        }
        
        res = requests.get(url, headers=headers, timeout=10, verify=False)
        data = res.json()
        
        if isinstance(data, dict) and data.get('s') == 'ok':
            # Mengubah format Unix Timestamp dari Indodax menjadi DataFrame Pandas
            df = pd.DataFrame({
                'Date': pd.to_datetime(data['t'], unit='s'), 
                'Open': data['o'], 
                'High': data['h'], 
                'Low': data['l'], 
                'Close': data['c'], 
                'Volume': data['v']
            })
            return df, "Direct API"
        else: 
            raise ValueError("Data TradingView Kosong atau Ditolak")
            
    except Exception:
        # Jika gagal terhubung, langsung aktifkan mesin cadangan data sintetis
        if ticker_data: 
            df_sintetis = buat_data_sintetis(ticker_data, limit, interval_min)
            return df_sintetis, "Synthetic Engine Active"
        else: 
            return pd.DataFrame(), "Error"

# ==============================================================================
# 5. MESIN SENTIMEN FUNDAMENTAL (FEAR & GREED)
# ==============================================================================
def tarik_sentimen_global():
    """
    Menarik data Fear & Greed Index (0-100) dari Alternative.me.
    Digunakan AI sebagai konteks psikologi pasar makro.
    """
    try:
        url = "https://api.alternative.me/fng/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        
        if res.status_code == 200:
            return int(res.json()['data'][0]['value'])
        return 50 # Nilai netral jika gagal
    except Exception: 
        return 50
