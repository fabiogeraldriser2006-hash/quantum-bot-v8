"""
=========================================================
FILE: config.py
DESKRIPSI: Buku catatan pengaturan pusat. 
Menyimpan variabel global, peta aset kripto, dan konfigurasi API.
=========================================================
"""

# 1. BIAYA TRANSAKSI (FEE)
# Biaya taker fee di Indodax saat ini adalah 0.3%
FEE_RATE = 0.003 

# 2. PETA ASET KRIPTO (CRYPTO MAP)
# Kamus ini menghubungkan nama koin dengan kode API Indodax (ticker) 
# dan kode grafik TradingView (tv).
CRYPTO_MAP = {
    "Bitcoin": {"ticker": "btc_idr", "tv": "BTCIDR"},
    "Ethereum": {"ticker": "eth_idr", "tv": "ETHIDR"},
    "Solana": {"ticker": "sol_idr", "tv": "SOLIDR"},
    "Dogecoin": {"ticker": "doge_idr", "tv": "DOGEIDR"},
    "Ripple": {"ticker": "xrp_idr", "tv": "XRPIDR"},
    "Cardano": {"ticker": "ada_idr", "tv": "ADAIDR"},
    "Pepe": {"ticker": "pepe_idr", "tv": "PEPEIDR"}
}

# 3. PENGATURAN MODAL AWAL VIRTUAL (SIMULASI)
MODAL_AWAL_DEFAULT = 1000000000.0 # Rp 1.000.000.000

# 4. PENGATURAN URL API INDODAX
INDODAX_TAPI_URL = "https://indodax.com/tapi"
INDODAX_PUBLIC_API_URL = "https://indodax.com/api/tickers"
ALTERNATIVE_ME_API_URL = "https://api.alternative.me/fng/?limit=1"
