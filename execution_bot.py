"""
================================================================================
FILE: execution_bot.py
VERSI: Full Documentation & Ultimate Features
DESKRIPSI: Mesin Eksekusi Utama. Mengatur koneksi API Publik & Privat Indodax, 
menjalankan Trailing Stop berbasis ATR, dan mengarahkan perintah dari AI Gemini.
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
# 1. STATE BOT (VARIABEL GLOBAL UNTUK PENYIMPANAN DATA SEMENTARA)
# ==============================================================================
bot_state = {
    "selected_coin": "Bitcoin (BTC)", # Koin yang sedang dipantau di dashboard
    "last_action": "Sistem bersiap untuk memulai...",
    "scan_speed": 60,                 # Kecepatan putaran loop (dalam detik)
    "atr_multiplier": 2.0,            # Pengali toleransi risiko (Trailing Stop)
    "mode_simulasi": True,            # TRUE = Kertas/Simulasi, FALSE = Uang Asli
    "cash": 10000000.0,               # Modal Rupiah (IDR) untuk Mode Simulasi
    "positions": {},                  # Buku catatan pembelian Mode Simulasi
    "live_positions": {},             # Buku catatan pembelian Mode Live Trading
    "api_key_indodax": "",            # Kunci akses publik akun Indodax
    "secret_key_indodax": ""          # Kunci rahasia untuk tanda tangan digital
}

BOT_IS_RUNNING = False # Sakelar utama mesin bot

# ==============================================================================
# 2. FUNGSI KEAMANAN DAN KONEKSI PRIVATE API INDODAX
# ==============================================================================
def panggil_api_private_indodax(method, parameter_tambahan=None):
    """
    Fungsi ini mengenkripsi data menggunakan algoritma HMAC-SHA512.
    Wajib digunakan untuk setiap aktivitas yang melibatkan akun asli (Cek Saldo/Trade).
    """
    api_key = bot_state.get("api_key_indodax", "")
    secret_key = bot_state.get("secret_key_indodax", "")
    
    # Mencegah eksekusi jika kunci belum dimasukkan di UI
    if not api_key or not secret_key:
        raise ValueError("API Key atau Secret Key Indodax kosong. Harap isi di panel.")

    url = "https://indodax.com/tapi"
    
    # Parameter dasar wajib menurut dokumentasi resmi Indodax
    data = {
        'method': method,
        'timestamp': str(int(time.time() * 1000)),
        'recvWindow': '10000' # Batas kedaluwarsa request (10 detik)
    }
    
    # Jika ada instruksi tambahan (seperti harga beli/jual), gabungkan ke data
    if parameter_tambahan:
        data.update(parameter_tambahan)

    # Mengubah format data menjadi string yang bisa dikirim melalui URL
    post_data = urllib.parse.urlencode(data)
    
    # Membuat Tanda Tangan Digital (Signature) agar server percaya ini adalah Anda
    signature = hmac.new(
        secret_key.encode('utf-8'), 
        post_data.encode('utf-8'), 
        hashlib.sha512
    ).hexdigest()
    
    headers = {
        'Key': api_key,
        'Sign': signature,
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    # Melakukan PING ke server Indodax dan meminta jawaban dalam bentuk JSON
    response = requests.post(url, headers=headers, data=data, timeout=10)
    return response.json()

# ==============================================================================
# 3. RUTINITAS PEMINDAIAN UTAMA (LOOP)
# ==============================================================================
def rutinitas_pemindaian():
    """
    Fungsi ini adalah jantung bot. Akan terus berputar (loop) selama sakelar menyala.
    Fungsi ini membaca data, meminta prediksi AI, lalu menekan tombol Beli/Jual.
    """
    global BOT_IS_RUNNING, bot_state
    
    while BOT_IS_RUNNING:
        try:
            # A. PERSIAPAN DATA KOIN
            koin_nama = bot_state["selected_coin"]
            data_koin = config.CRYPTO_MAP.get(koin_nama)
            
            # Jika konfigurasi koin tidak ditemukan, bot istirahat sebentar lalu ulang
            if not data_koin:
                bot_state["last_action"] = f"⚠️ Konfigurasi {koin_nama} tidak ditemukan."
                time.sleep(10)
                continue

            bot_state["last_action"] = f"🔍 Memantau {koin_nama}..."
            
            # B. FORMATTING NAMA KOIN UNTUK INDODAX
            # Ticker dari config.py adalah format utuh. Contoh: 'btc_idr'
            pair_indodax = data_koin['ticker'] 
            
            # Memecah 'btc_idr' menjadi 'btc' saja untuk membaca saldo koin di dompet
            simbol_koin_kecil = pair_indodax.split('_')[0] 
            
            # C. MENARIK DATA HARGA LIVE
            data_live = data_engine.tarik_data_live_indodax()
            ticker = pair_indodax
            
            # --- SABUK PENGAMAN KONEKSI ---
            # Jika data_live berhasil ditarik dan ticker ditemukan di dalamnya
            if data_live and ticker in data_live:
                
                # Mengambil harga terakhir saat ini
                harga_skrg = float(data_live[ticker]['last'])
                
                # D. MENARIK GRAFIK & MENGHITUNG INDIKATOR TEKNIKAL
                df_chart, _ = data_engine.tarik_grafik_klines_aman(data_koin['tv'], "15m", 50, data_live[ticker])
                
                if not df_chart.empty:
                    # Menghitung Average True Range (ATR) untuk logika Trailing Stop
                    df_chart = data_engine.hitung_indikator_teknikal(df_chart)
                    atr_terbaru = float(df_chart.iloc[-1]['ATR'])
                    
                    # E. MENARIK SENTIMEN FUNDAMENTAL GLOBAL
                    try:
                        sentimen = data_engine.tarik_sentimen_global()
                    except Exception:
                        sentimen = 50 # Jika error, asumsikan sentimen netral (50)
                    
                    # F. MEMANGGIL OTAK AI GEMINI
                    # (quant_brain akan mengatur sendiri kuota 72 menit agar aman 24 jam)
                    narasi, keputusan = quant_brain.prediksi_ai_market(df_chart, koin_nama, harga_skrg, "15m", sentimen)
                    
                    # =================================================================
                    # TAHAP EKSEKUSI 1: MODE SIMULASI (PAPER TRADING)
                    # =================================================================
                    if bot_state["mode_simulasi"]:
                        
                        # JIKA SEDANG MEMILIKI KOIN (LOGIKA JUAL)
                        if koin_nama in bot_state["positions"]:
                            pos = bot_state["positions"][koin_nama]
                            
                            # Mengukur harga tertinggi yang pernah disentuh sejak dibeli
                            if harga_skrg > pos["high_price"]: 
                                pos["high_price"] = harga_skrg
                            
                            # Menghitung batas kerugian aman (Trailing Stop)
                            batas_jual = pos["high_price"] - (atr_terbaru * bot_state["atr_multiplier"])
                            
                            # Eksekusi Jual jika disuruh AI atau harga anjlok
                            if keputusan == "SELL" or harga_skrg <= batas_jual:
                                hasil_jual = pos["amount"] * harga_skrg * 0.997 # Dipotong fee Indodax 0.3%
                                bot_state["cash"] += hasil_jual
                                del bot_state["positions"][koin_nama] # Kosongkan keranjang
                                alasan = "Sinyal AI" if keputusan == "SELL" else "Terkena Trailing Stop"
                                bot_state["last_action"] = f"✅ SIMULASI JUAL {koin_nama} di Rp {harga_skrg:,.0f} ({alasan})"
                            else:
                                bot_state["last_action"] = f"⚖️ HOLD (Simulasi) | Batas TS: Rp {batas_jual:,.0f}"

                        # JIKA TIDAK MEMILIKI KOIN (LOGIKA BELI)
                        elif keputusan == "BUY" and bot_state["cash"] > 100000:
                            # Menghitung berapa banyak koin yang didapat dari seluruh kas
                            koin_didapat = (bot_state["cash"] / harga_skrg) * 0.997
                            
                            # Mencatat posisi baru
                            bot_state["positions"][koin_nama] = {
                                "amount": koin_didapat, 
                                "buy_price": harga_skrg, 
                                "high_price": harga_skrg, 
                                "atr_saat_beli": atr_terbaru
                            }
                            bot_state["cash"] = 0 # Kas habis dipakai beli
                            bot_state["last_action"] = f"🚀 SIMULASI BELI {koin_nama} di Rp {harga_skrg:,.0f}"
                        
                        # JIKA TIDAK ADA SINYAL (STANDBY)
                        else:
                            bot_state["last_action"] = f"💤 Standby {koin_nama} | AI: {keputusan}"
                                
                    # =================================================================
                    # TAHAP EKSEKUSI 2: MODE LIVE TRADING (UANG ASLI)
                    # =================================================================
                    else:
                        try:
                            # 1. Cek Saldo Asli di Akun Indodax
                            info_akun = panggil_api_private_indodax('getInfo')
                            
                            if info_akun.get('success') == 1:
                                saldo_idr_asli = float(info_akun['return']['balance']['idr'])
                                # Mengambil saldo koin berdasarkan simbol (misal 'btc' atau 'sol')
                                saldo_koin_asli = float(info_akun['return']['balance'].get(simbol_koin_kecil, 0))
                                
                                # Sinkronisasi tampilan modal UI dengan saldo asli
                                bot_state['cash'] = saldo_idr_asli
                                
                                # 2. LOGIKA JUAL LIVE TRADING
                                if saldo_koin_asli > 0.00001: # Toleransi saldo debu (dust balance)
                                    
                                    # Inisialisasi buku catatan live jika belum ada
                                    if koin_nama not in bot_state["live_positions"]:
                                        bot_state["live_positions"][koin_nama] = {"high_price": harga_skrg}
                                        
                                    pos_live = bot_state["live_positions"][koin_nama]
                                    
                                    # Update harga tertinggi
                                    if harga_skrg > pos_live["high_price"]:
                                        pos_live["high_price"] = harga_skrg
                                        
                                    batas_jual_live = pos_live["high_price"] - (atr_terbaru * bot_state["atr_multiplier"])
                                    
                                    # Eksekusi Jual Asli ke Indodax
                                    if keputusan == "SELL" or harga_skrg <= batas_jual_live:
                                        parameter_jual = {
                                            'pair': pair_indodax,
                                            'type': 'sell',
                                            'price': str(int(harga_skrg)), # Indodax butuh bilangan bulat untuk harga IDR
                                            simbol_koin_kecil: str(saldo_koin_asli) # Jual seluruh saldo koin tersebut
                                        }
                                        res_jual = panggil_api_private_indodax('trade', parameter_jual)
                                        
                                        if res_jual.get('success') == 1:
                                            alasan = "Sinyal AI" if keputusan == "SELL" else "Terkena Trailing Stop"
                                            bot_state["last_action"] = f"✅ LIVE SELL SUKSES: {koin_nama} ({alasan})"
                                            del bot_state["live_positions"][koin_nama] # Hapus catatan setelah terjual
                                        else:
                                            bot_state["last_action"] = f"⚠️ Gagal Jual Asli: {res_jual.get('error')}"
                                    else:
                                        bot_state["last_action"] = f"⚖️ HOLD (Live) | Saldo: {saldo_koin_asli:.4f} {simbol_koin_kecil.upper()} | TS: Rp {batas_jual_live:,.0f}"
                                        
                                # 3. LOGIKA BELI LIVE TRADING
                                elif keputusan == "BUY" and saldo_idr_asli > 15000: # Syarat minimum order Indodax
                                    jumlah_beli_idr = saldo_idr_asli * 0.99 # Hanya gunakan 99% saldo agar aman dari fee
                                    
                                    parameter_beli = {
                                        'pair': pair_indodax,
                                        'type': 'buy',
                                        'price': str(int(harga_skrg)),
                                        'idr': str(int(jumlah_beli_idr))
                                    }
                                    res_beli = panggil_api_private_indodax('trade', parameter_beli)
                                    
                                    if res_beli.get('success') == 1:
                                        bot_state["last_action"] = f"🚀 LIVE BUY SUKSES: {koin_nama} senilai Rp {jumlah_beli_idr:,.0f}"
                                        # Mulai lacak harga tertinggi untuk koin ini
                                        bot_state["live_positions"][koin_nama] = {"high_price": harga_skrg} 
                                    else:
                                        bot_state["last_action"] = f"⚠️ Gagal Beli Asli: {res_beli.get('error')}"
                                        
                                # 4. LOGIKA STANDBY LIVE TRADING
                                else:
                                    bot_state["last_action"] = f"💤 LIVE STANDBY: {koin_nama} | Modal IDR: Rp {saldo_idr_asli:,.0f}"
                                    
                            # GAGAL CEK SALDO
                            else:
                                bot_state["last_action"] = f"❌ Gagal Akses Akun Indodax: {info_akun.get('error')}"
                                
                        except Exception as api_err:
                            bot_state["last_action"] = f"❌ Kesalahan Jaringan Server Indodax: {str(api_err)}"
            
            # --- SABUK PENGAMAN (ALTERNATIF JIKA DATA KOSONG) ---
            # Jika respons dari Indodax kosong, bot tidak akan crash, melainkan menunggu.
            elif not data_live:
                bot_state["last_action"] = f"⚠️ Jaringan lambat, menunggu data dari server Indodax untuk {koin_nama}..."

            # G. JEDA LOOP SEBELUM MENGULANG DARI AWAL
            time.sleep(bot_state["scan_speed"])
            
        except Exception as e:
            # Menangkap semua error lain agar aplikasi tidak pernah tertutup (crash)
            bot_state["last_action"] = f"⚠️ Jeda Sistem Kritis: {str(e)}"
            time.sleep(15)

# ==============================================================================
# 4. KONTROL THREAD (MENYALAKAN DAN MEMATIKAN BOT)
# ==============================================================================
def mulai_bot_latar_belakang():
    """Menghidupkan loop utama di proses latar belakang agar UI Streamlit tidak macet."""
    global BOT_IS_RUNNING
    if not BOT_IS_RUNNING:
        BOT_IS_RUNNING = True
        thread = threading.Thread(target=rutinitas_pemindaian, daemon=True)
        thread.start()

def hentikan_bot_latar_belakang():
    """Menghentikan putaran loop utama dengan aman."""
    global BOT_IS_RUNNING
    BOT_IS_RUNNING = False
