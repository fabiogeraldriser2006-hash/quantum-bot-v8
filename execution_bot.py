"""
================================================================================
FILE: execution_bot.py
DESKRIPSI: Mesin Eksekusi Utama (Single-Coin Focus & ATR Trailing Stop).
Berjalan di latar belakang dan disinkronkan dengan UI (app.py).
================================================================================
"""
import time
import threading
from datetime import datetime
import config
import data_engine
import quant_brain

# State bot agar bisa dikendalikan langsung dari layar utama
bot_state = {
    "selected_coin": "Bitcoin",  # Koin yang akan dipantau (default)
    "last_action": "Sistem bersiap...",
    "cash": 1000000.0,           # Modal simulasi (bisa disesuaikan)
    "positions": {},             # Keranjang untuk menyimpan koin yang dibeli
    "scan_speed": 60,            # Interval pengecekan harga di bursa (detik)
    "atr_multiplier": 2.0        # Jarak aman Trailing Stop (2x ATR)
}

BOT_IS_RUNNING = False

def rutinitas_pemindaian():
    """Siklus pemantauan koin tunggal yang berjalan terus-menerus."""
    global BOT_IS_RUNNING, bot_state
    
    while BOT_IS_RUNNING:
        try:
            # 1. Kunci fokus pada koin yang Anda pilih di UI
            koin_nama = bot_state["selected_coin"]
            data_koin = config.CRYPTO_MAP.get(koin_nama)
            
            if not data_koin:
                bot_state["last_action"] = f"⚠️ Konfigurasi {koin_nama} tidak ditemukan."
                time.sleep(10)
                continue

            bot_state["last_action"] = f"🔍 Memantau {koin_nama}..."
            
            # 2. Tarik Data Live dari Indodax
            data_live = data_engine.tarik_data_live_indodax()
            ticker = data_koin['ticker']
            
            if ticker in data_live:
                harga_skrg = float(data_live[ticker]['last'])
                
                # 3. Tarik Data Grafik & Hitung Indikator Teknikal Lengkap
                df_chart, _ = data_engine.tarik_grafik_klines_aman(data_koin['tv'], "15m", 50, data_live[ticker])
                
                if not df_chart.empty:
                    df_chart = data_engine.hitung_indikator_teknikal(df_chart)
                    
                    # Ambil nilai ATR terbaru untuk pengaman Trailing Stop
                    atr_terbaru = float(df_chart.iloc[-1]['ATR'])
                    
                    try:
                        sentimen = data_engine.tarik_sentimen_global()
                    except AttributeError:
                        sentimen = 50 # Default jika fungsi sentimen sedang offline
                    
                    # 4. Panggil Otak AI (Keamanan kuota diatur di dalam quant_brain.py)
                    narasi, keputusan = quant_brain.prediksi_ai_market(df_chart, koin_nama, harga_skrg, "15m", sentimen)
                    
                    # =================================================================
                    # FITUR LAMA: LOGIKA TRAILING STOP & EKSEKUSI JUAL
                    # =================================================================
                    if koin_nama in bot_state["positions"]:
                        pos = bot_state["positions"][koin_nama]
                        
                        # Selalu perbarui catatan harga tertinggi sejak dibeli
                        if harga_skrg > pos["high_price"]:
                            pos["high_price"] = harga_skrg
                        
                        # Rumus Trailing Stop: Harga Tertinggi - (2 x ATR)
                        batas_jual = pos["high_price"] - (atr_terbaru * bot_state["atr_multiplier"])
                        
                        # Bot menjual jika disuruh AI ATAU jika harga menembus Trailing Stop
                        if keputusan == "SELL" or harga_skrg <= batas_jual:
                            hasil_jual = pos["amount"] * harga_skrg * 0.997 # Dipotong simulasi fee 0.3%
                            bot_state["cash"] += hasil_jual
                            del bot_state["positions"][koin_nama]
                            
                            alasan = "Sinyal AI SELL" if keputusan == "SELL" else "Terkena Trailing Stop"
                            bot_state["last_action"] = f"✅ JUAL {koin_nama} di Rp {harga_skrg:,.0f} ({alasan})"
                        else:
                            bot_state["last_action"] = f"⚖️ HOLD {koin_nama} | Harga: Rp {harga_skrg:,.0f} | Batas Jual: Rp {batas_jual:,.0f}"

                    # =================================================================
                    # FITUR LAMA: LOGIKA EKSEKUSI BELI
                    # =================================================================
                    elif keputusan == "BUY":
                        if bot_state["cash"] > 100000: # Syarat saldo minimum Rp 100.000
                            # Membeli menggunakan seluruh uang kas (Dipotong simulasi fee 0.3%)
                            koin_didapat = (bot_state["cash"] / harga_skrg) * 0.997
                            
                            bot_state["positions"][koin_nama] = {
                                "amount": koin_didapat,
                                "buy_price": harga_skrg,
                                "high_price": harga_skrg, # Inisialisasi harga tertinggi awal
                                "atr_saat_beli": atr_terbaru
                            }
                            bot_state["cash"] = 0
                            bot_state["last_action"] = f"🚀 BELI {koin_nama} di Rp {harga_skrg:,.0f}"
                        else:
                            bot_state["last_action"] = f"💸 Sinyal BUY {koin_nama}, namun saldo tidak cukup."
                    
                    # =================================================================
                    # KONDISI STANDBY
                    # =================================================================
                    else: 
                        if koin_nama not in bot_state["positions"]:
                            bot_state["last_action"] = f"💤 Mengamati {koin_nama} | Sinyal: {keputusan}"

            # Jeda sebelum mengecek harga terbaru ke bursa
            time.sleep(bot_state["scan_speed"])
            
        except Exception as e:
            bot_state["last_action"] = f"⚠️ Jeda Sistem: {str(e)}"
            time.sleep(15)

def mulai_bot_latar_belakang():
    """Mengaktifkan mesin bot."""
    global BOT_IS_RUNNING
    if not BOT_IS_RUNNING:
        BOT_IS_RUNNING = True
        thread = threading.Thread(target=rutinitas_pemindaian, daemon=True)
        thread.start()

def hentikan_bot_latar_belakang():
    """Mematikan mesin bot."""
    global BOT_IS_RUNNING
    BOT_IS_RUNNING = False
