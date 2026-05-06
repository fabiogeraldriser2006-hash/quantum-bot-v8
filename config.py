"""
================================================================================
FILE: config.py
DESKRIPSI: Konfigurasi Daftar Koin Indodax (Penambahan XRP, DOGE & Meme Coins)
================================================================================
"""

# Daftar koin target untuk bot.
# Format: "Nama Tampilan di Layar": {"ticker": "Kode API Indodax", "tv": "Kode Grafik TradingView"}
CRYPTO_MAP = {
    # --- Koin Utama Layer 1 & Altcoin ---
    "Bitcoin (BTC)": {
        "ticker": "btcidr", 
        "tv": "INDODAX:BTCIDR"
    },
    "Ethereum (ETH)": {
        "ticker": "ethidr", 
        "tv": "INDODAX:ETHIDR"
    },
    "Solana (SOL)": {
        "ticker": "solidr", 
        "tv": "INDODAX:SOLIDR"
    },
    "Binance Coin (BNB)": {
        "ticker": "bnbidr", 
        "tv": "INDODAX:BNBIDR"
    },
    "Ripple (XRP)": {
        "ticker": "xrpidr", 
        "tv": "INDODAX:XRPIDR"
    },
    
    # --- Meme Coins ---
    "Dogecoin (DOGE)": {
        "ticker": "dogeidr", 
        "tv": "INDODAX:DOGEIDR"
    },
    "Shiba Inu (SHIB)": {
        "ticker": "shibidr", 
        "tv": "INDODAX:SHIBIDR"
    },
    "Pepe (PEPE)": {
        "ticker": "pepeidr", 
        "tv": "INDODAX:PEPEIDR"
    },
    "Floki (FLOKI)": {
        "ticker": "flokiidr", 
        "tv": "INDODAX:FLOKIIDR"
    }
}
