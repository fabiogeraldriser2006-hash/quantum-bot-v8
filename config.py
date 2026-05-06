"""
================================================================================
FILE: config.py
DESKRIPSI: Konfigurasi Daftar Koin Indodax (Format Ticker Diperbaiki)
================================================================================
"""

CRYPTO_MAP = {
    # --- Koin Utama Layer 1 & Altcoin ---
    "Bitcoin (BTC)": {
        "ticker": "btc_idr", # Ditambahkan garis bawah agar sesuai dengan server Indodax
        "tv": "INDODAX:BTCIDR"
    },
    "Ethereum (ETH)": {
        "ticker": "eth_idr", 
        "tv": "INDODAX:ETHIDR"
    },
    "Solana (SOL)": {
        "ticker": "sol_idr", 
        "tv": "INDODAX:SOLIDR"
    },
    "Binance Coin (BNB)": {
        "ticker": "bnb_idr", 
        "tv": "INDODAX:BNBIDR"
    },
    "Ripple (XRP)": {
        "ticker": "xrp_idr", 
        "tv": "INDODAX:XRPIDR"
    },
    
    # --- Meme Coins ---
    "Dogecoin (DOGE)": {
        "ticker": "doge_idr", 
        "tv": "INDODAX:DOGEIDR"
    },
    "Shiba Inu (SHIB)": {
        "ticker": "shib_idr", 
        "tv": "INDODAX:SHIBIDR"
    },
    "Pepe (PEPE)": {
        "ticker": "pepe_idr", 
        "tv": "INDODAX:PEPEIDR"
    },
    "Floki (FLOKI)": {
        "ticker": "floki_idr", 
        "tv": "INDODAX:FLOKIIDR"
    }
}
