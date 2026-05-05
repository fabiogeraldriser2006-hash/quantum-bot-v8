"""
================================================================================
FILE: execution_bot.py
DESKRIPSI: Pekerja Latar Belakang (Auto-Pilot).
Bertugas memindai pasar, membaca sinyal dari quant_brain, dan
mengeksekusi transaksi. Semua tipe data angka telah menggunakan float()
untuk mencegah error pada pembacaan koin berharga desimal.
================================================================================
"""
import time
import threading
import urllib.parse
import urllib.request
import hashlib
import hmac
import json
from datetime import datetime

import config
import data_engine
import quant_brain

# ==========================================
# VARIABEL GLOBAL & STATE BOT
# ==========================================
BOT_IS_RUNNING = False
thread_bot = None

# Menyimpan status, kunci API, portofolio, dan riwayat di memori
bot_state = {
    "api_key": "",
    "secret_key": "",
    "cash": config.MODAL_AWAL_DEFAULT if hasattr(config, 'MODAL_AWAL_DEFAULT') else 10000000.0,
    "positions": {},
    "trade_history": [],
    "buy_amount_idr": 0.0,
    "scan_speed": 60,
    "atr_multiplier": 2.0,
    "last_action": "Menunggu diaktifkan..."
}

# ==========================================
# KONEKSI PRIVATE API INDODAX
# ==========================================
def indodax_private_api(method, **params):
    """Fungsi untuk menghubungi API Pribadi Indodax (Cek Saldo/Trade)"""
    if not bot_state["api_key"] or not bot_state["secret_key"]:
        return {"success": 0, "error": "API Key atau Secret Key kosong."}
        
    params['method'] = method
    params['nonce'] = int(time.time() * 1000)
    
    post_data = urllib.parse.urlencode(params).encode('utf-8')
    sign = hmac.new(bot_state["secret_key"].encode('utf-8'), post_data, hashlib.sha512).hexdigest()
    
    headers = {
        'Key': bot_state["api_key"],
        'Sign': sign,
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    try:
        req = urllib.request.Request('https://indodax.com/tapi', data=post_data, headers=headers)
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        return {"success": 0, "error": str(e)}

# ==========================================
# LOGIKA UTAMA AUTO-PILOT (BERJALAN DI BACKGROUND)
# ==========================================
def rutinitas_pemindaian():
    global BOT_IS_RUNNING, bot_state
    
    while BOT_IS_RUNNING:
        try:
            bot_state["last_action"] = f"Memindai pasar pada {datetime.now().strftime('%H:%M:%S')}..."
            
            # 1. Tarik Harga Live & Sentimen Global
            data_live = data_engine.tarik_data_live_indodax()
            sentimen = data_engine.tarik_sentimen_global()
            
            if not data_live:
                time.sleep(5)
                continue

            # 2. Pindai Setiap Koin di Config
            for koin_nama, data_koin in config.CRYPTO_MAP.items():
                if not BOT_IS_RUNNING: break # Berhenti instan jika dimatikan pengguna
                
                ticker_koin = data_koin['ticker']
                tv_simbol = data_koin['tv']
                
                if ticker_koin not in data_live: continue
                
                # PERBAIKAN BUG: Menggunakan float() untuk mencegah error desimal
                harga_sekarang = float(data_live[ticker_koin]['last'])
                
                # 3. Tarik Grafik Historis untuk Otak AI
                df_chart, _ = data_engine.tarik_grafik_klines_aman(tv_simbol, "15m", 30, data_live[ticker_koin])
                if df_chart.empty: continue
                
                df_chart = data_engine.hitung_indikator_teknikal(df_chart)
                baris_terakhir = df_chart.iloc[-1]
                atr_sekarang = float(baris_terakhir['ATR']) if 'ATR' in df_chart.columns else 0.0
                
                # 4. Tanya Keputusan ke Otak AI Gemini
                _, keputusan_ai = quant_brain.prediksi_ai_market(df_chart, koin_nama, harga_sekarang, "15m", sentimen)
                
                mode_asli = bool(bot_state["api_key"] and bot_state["secret_key"])
                
                # ---------------------------------------------------------
                # LOGIKA BELI (BUY)
                # ---------------------------------------------------------
                if keputusan_ai == "BUY" and koin_nama not in bot_state["positions"]:
                    anggaran_beli = bot_state["buy_amount_idr"]
                    
                    if mode_asli:
                        # Simulasi pencatatan jika terhubung API asli
                        bot_state["last_action"] = f"API Asli: Rekomendasi BUY {koin_nama} terdeteksi."
                    else:
                        # Simulasi Uang Virtual
                        if bot_state["cash"] >= anggaran_beli and anggaran_beli > 0:
                            koin_kotor = anggaran_beli / harga_sekarang
                            koin_bersih = koin_kotor * (1 - config.FEE_RATE) # Potong biaya admin
                            
                            bot_state["cash"] -= anggaran_beli
                            bot_state["positions"][koin_nama] = {
                                "amount": koin_bersih,
                                "avg_price": harga_sekarang,
                                "highest_price": harga_sekarang,
                                "atr_at_buy": atr_sekarang
                            }
                            
                            bot_state["trade_history"].append({
                                "Waktu": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "Koin": koin_nama,
                                "Aksi": "🟢 BUY",
                                "Harga": f"Rp {harga_sekarang:,.2f}",
                                "PnL": "-"
                            })
                            bot_state["last_action"] = f"Simulasi Beli {koin_nama} berhasil."

                # ---------------------------------------------------------
                # LOGIKA JUAL / TRAILING STOP (SELL)
                # ---------------------------------------------------------
                elif koin_nama in bot_state["positions"]:
                    posisi = bot_state["positions"][koin_nama]
                    
                    # Pembaruan Titik Tertinggi untuk Trailing Stop
                    if harga_sekarang > posisi["highest_price"]:
                        posisi["highest_price"] = harga_sekarang
                        
                    batas_ts = posisi["highest_price"] - (atr_sekarang * bot_state["atr_multiplier"])
                    
                    terkena_ts = harga_sekarang <= batas_ts
                    disuruh_ai = keputusan_ai == "SELL"
                    
                    if disuruh_ai or terkena_ts:
                        if mode_asli:
                            bot_state["last_action"] = f"API Asli: Sinyal SELL {koin_nama} diterbitkan."
                        else:
                            nilai_jual_kotor = posisi["amount"] * harga_sekarang
                            nilai_jual_bersih = nilai_jual_kotor * (1 - config.FEE_RATE)
                            modal_awal = (posisi["amount"] * posisi["avg_price"]) / (1 - config.FEE_RATE)
                            pnl = nilai_jual_bersih - modal_awal
                            
                            bot_state["cash"] += nilai_jual_bersih
                            del bot_state["positions"][koin_nama]
                            
                            alasan = "🔴 SELL (AI)" if disuruh_ai else "🛡️ SELL (Trailing Stop)"
                            bot_state["trade_history"].append({
                                "Waktu": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "Koin": koin_nama,
                                "Aksi": alasan,
                                "Harga": f"Rp {harga_sekarang:,.2f}",
                                "PnL": f"Rp {pnl:,.2f}"
                            })
                            bot_state["last_action"] = f"Simulasi Jual {koin_nama} tereksekusi."

            # Istirahat sesuai dengan Kecepatan Pindai di Slider
            time.sleep(bot_state["scan_speed"])
            
        except Exception as e:
            # Cegah crash total, laporkan error, dan istirahat 10 detik
            bot_state["last_action"] = f"Error Latar Belakang: {str(e)}"
            time.sleep(10) 

# ==========================================
# KONTROL THREAD BOT (DIPANGGIL OLEH APP.PY)
# ==========================================
def mulai_bot_latar_belakang():
    global BOT_IS_RUNNING, thread_bot
    if not BOT_IS_RUNNING:
        BOT_IS_RUNNING = True
        thread_bot = threading.Thread(target=rutinitas_pemindaian, daemon=True)
        thread_bot.start()
        bot_state["last_action"] = "Auto-Pilot diaktifkan."
        return "Bot dijalankan."
    return "Bot sudah berjalan."

def hentikan_bot_latar_belakang():
    global BOT_IS_RUNNING
    BOT_IS_RUNNING = False
    bot_state["last_action"] = "Auto-Pilot dimatikan."
    return "Bot dihentikan."
