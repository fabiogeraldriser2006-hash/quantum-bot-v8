"""
================================================================================
FILE: execution_bot.py
DESKRIPSI: Mesin Eksekusi dengan Mode Simulasi & Live Trading API Indodax.
Memiliki fitur Trailing Stop ATR dan terhubung ke sentimen fundamental.
================================================================================
"""
import time
import threading
from datetime import datetime
import urllib.parse
import hmac
import hashlib
import requests
import config
import data_engine
import quant_brain

# ==============================================================================
# STATE BOT: Menyimpan konfigurasi dan status terkini
# ==============================================================================
bot_state = {
    "selected_coin": "Bitcoin",   # Koin target dari UI
    "last_action": "Sistem bersiap...",
    "scan_speed": 60,             # Interval pemindaian (detik)
    "atr_multiplier": 2.0,        # Jarak Trailing Stop
    "mode_simulasi": True,        # TRUE = Uang bohongan, FALSE = Uang asli (API Indodax)
    "cash": 10000000.0,           # Saldo simulasi
    "positions": {},              # Catatan posisi untuk simulasi
    "api_key_indodax": "",        # Kunci API Indodax untuk live trading
    "secret_key_indodax": ""      # Kunci Rahasia Indodax untuk live trading
}

BOT_IS_RUNNING = False

# ==============================================================================
# FUNGSI KONEKSI API INDODAX (LIVE TRADING)
# ==============================================================================
def eksekusi_order_indodax(tipe_order, pair_indodax, harga, jumlah_rupiah=None, jumlah_koin=None):
    """
    Berkomunikasi langsung dengan server Indodax menggunakan HMAC-SHA512.
    tipe_order: 'buy' atau 'sell'
    pair_indodax: contoh 'btc_idr'
    """
    api_key = bot_state.get("api_key_indodax", "")
    secret_key = bot_state.get("secret_key_indodax", "")
    
    if not api_key or not secret_key:
        raise ValueError("Kredensial API Indodax belum diisi.")

    # Endpoint resmi Trade API Indodax
    url = "https://indodax.com/tapi"
    
    # Parameter dasar wajib
    data = {
        'method': 'trade',
        'timestamp': str(int(time.time() * 1000)),
        'pair': pair_indodax,
        'type': tipe_order,
        'price': str(harga)
    }
    
    # Tentukan jumlah berdasarkan tipe order
    if tipe_order == 'buy' and jumlah_rupiah:
        data['idr'] = str(jumlah_rupiah)
    elif tipe_order == 'sell' and jumlah_koin:
        data[pair_indodax.split('_')[0]] = str(jumlah_koin)
        
    # Proses Enkripsi Signature HMAC-SHA512
    post_data = urllib.parse.urlencode(data)
    sign = hmac.new(secret_key.encode('utf-8'), post_data.encode('utf-8'), hashlib.sha512).hexdigest()
    
    headers = {
        'Key': api_key,
        'Sign': sign,
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    # Kirim perintah ke server
    response = requests.post(url, headers=headers, data=data)
    return response.json()

# ==============================================================================
# RUTINITAS PEMINDAIAN UTAMA
# ==============================================================================
def rutinitas_pemindaian():
    """Siklus pemantauan koin tunggal yang berjalan terus-menerus di latar belakang."""
    global BOT_IS_RUNNING, bot_state
    
    while BOT_IS_RUNNING:
        try:
            # 1. Identifikasi koin yang dipilih pengguna
            koin_nama = bot_state["selected_coin"]
            data_koin = config.CRYPTO_MAP.get(koin_nama)
            
            if not data_koin:
                bot_state["last_action"] = f"⚠️ Konfigurasi {koin_nama} tidak ditemukan."
                time.sleep(10)
                continue

            bot_state["last_action"] = f"🔍 Memantau {koin_nama}..."
            pair_indodax = f"{data_koin['ticker'].split('IDR')[0].lower()}_idr"
            
            # 2. Tarik Data Live dari Public API Indodax
            data_live = data_engine.tarik_data_live_indodax()
            ticker = data_koin['ticker']
            
            if ticker in data_live:
                harga_skrg = float(data_live[ticker]['last'])
                
                # 3. Tarik Grafik, Indikator Teknikal, dan Sentimen Fundamental
                df_chart, _ = data_engine.tarik_grafik_klines_aman(data_koin['tv'], "15m", 50, data_live[ticker])
                
                if not df_chart.empty:
                    df_chart = data_engine.hitung_indikator_teknikal(df_chart)
                    atr_terbaru = float(df_chart.iloc[-1]['ATR'])
                    
                    # Mengambil sentimen fundamental dari data engine
                    try:
                        sentimen = data_engine.tarik_sentimen_global()
                    except Exception:
                        sentimen = 50 # Nilai netral jika gagal
                    
                    # 4. Panggil Otak AI Gemini secara langsung
                    narasi, keputusan = quant_brain.prediksi_ai_market(df_chart, koin_nama, harga_skrg, "15m", sentimen)
                    
                    # =================================================================
                    # LOGIKA EKSEKUSI (SIMULASI VS LIVE)
                    # =================================================================
                    if bot_state["mode_simulasi"]:
                        # ---------------- MODE SIMULASI ----------------
                        if koin_nama in bot_state["positions"]:
                            pos = bot_state["positions"][koin_nama]
                            if harga_skrg > pos["high_price"]: pos["high_price"] = harga_skrg
                            
                            batas_jual = pos["high_price"] - (atr_terbaru * bot_state["atr_multiplier"])
                            
                            if keputusan == "SELL" or harga_skrg <= batas_jual:
                                hasil_jual = pos["amount"] * harga_skrg * 0.997
                                bot_state["cash"] += hasil_jual
                                del bot_state["positions"][koin_nama]
                                alasan = "Sinyal AI" if keputusan == "SELL" else "Trailing Stop"
                                bot_state["last_action"] = f"✅ SIMULASI JUAL {koin_nama} di Rp {harga_skrg:,.0f} ({alasan})"
                            else:
                                bot_state["last_action"] = f"⚖️ HOLD {koin_nama} | Batas TS: Rp {batas_jual:,.0f}"

                        elif keputusan == "BUY" and bot_state["cash"] > 100000:
                            koin_didapat = (bot_state["cash"] / harga_skrg) * 0.997
                            bot_state["positions"][koin_nama] = {
                                "amount": koin_didapat, "buy_price": harga_skrg, 
                                "high_price": harga_skrg, "atr_saat_beli": atr_terbaru
                            }
                            bot_state["cash"] = 0
                            bot_state["last_action"] = f"🚀 SIMULASI BELI {koin_nama} di Rp {harga_skrg:,.0f}"
                        else:
                            if koin_nama not in bot_state["positions"]:
                                bot_state["last_action"] = f"💤 Standby {koin_nama} | Sinyal: {keputusan}"
                                
                    else:
                        # ---------------- MODE LIVE TRADING (ASLI) ----------------
                        # Catatan: Logika state positions harus diganti dengan memanggil saldo riil Indodax via API
                        # Untuk tahap awal, kita buat logikanya mengeksekusi langsung
                        try:
                            if keputusan == "BUY":
                                # Contoh: Beli dengan modal Rp 100.000
                                res = eksekusi_order_indodax('buy', pair_indodax, harga_skrg, jumlah_rupiah=100000)
                                bot_state["last_action"] = f"LIVE BUY ORDER: {res.get('success', 'Gagal')} - {res}"
                            elif keputusan == "SELL":
                                # Logika riil harus mengambil jumlah saldo koin yang ada di akun
                                bot_state["last_action"] = f"LIVE SELL: Membutuhkan verifikasi saldo koin."
                            else:
                                bot_state["last_action"] = f"LIVE STANDBY: Mengamati {koin_nama} | Harga: Rp {harga_skrg:,.0f}"
                        except Exception as api_err:
                            bot_state["last_action"] = f"❌ Gagal Live API: {str(api_err)}"

            time.sleep(bot_state["scan_speed"])
            
        except Exception as e:
            bot_state["last_action"] = f"⚠️ Jeda Sistem: {str(e)}"
            time.sleep(15)

def mulai_bot_latar_belakang():
    """Menyalakan thread pemindaian."""
    global BOT_IS_RUNNING
    if not BOT_IS_RUNNING:
        BOT_IS_RUNNING = True
        thread = threading.Thread(target=rutinitas_pemindaian, daemon=True)
        thread.start()

def hentikan_bot_latar_belakang():
    """Mematikan thread pemindaian."""
    global BOT_IS_RUNNING
    BOT_IS_RUNNING = False
