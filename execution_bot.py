"""
================================================================================
FILE: execution_bot.py
DESKRIPSI: Mesin Eksekusi dengan Mode Simulasi & Live Trading API Indodax.
Terintegrasi penuh dengan sistem kriptografi Indodax (HMAC-SHA512).
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
# STATE BOT: Menyimpan konfigurasi, status terkini, dan kredensial
# ==============================================================================
bot_state = {
    "selected_coin": "Bitcoin",   
    "last_action": "Sistem bersiap...",
    "scan_speed": 60,             
    "atr_multiplier": 2.0,        
    "mode_simulasi": True,        
    "cash": 10000000.0,           # Saldo IDR untuk mode simulasi
    "positions": {},              # Pencatatan posisi untuk mode simulasi
    "live_positions": {},         # Pencatatan harga beli/high untuk mode live
    "api_key_indodax": "",        
    "secret_key_indodax": ""      
}

BOT_IS_RUNNING = False

# ==============================================================================
# FUNGSI KONEKTIVITAS PRIVATE API INDODAX
# ==============================================================================
def panggil_api_private_indodax(method, parameter_tambahan=None):
    """
    Fungsi inti untuk berkomunikasi dengan akun Indodax menggunakan HMAC-SHA512.
    Digunakan untuk cek saldo dan eksekusi order sungguhan.
    """
    api_key = bot_state.get("api_key_indodax", "")
    secret_key = bot_state.get("secret_key_indodax", "")
    
    if not api_key or not secret_key:
        raise ValueError("API Key atau Secret Key Indodax kosong. Harap isi di panel samping.")

    url = "https://indodax.com/tapi"
    
    # Parameter wajib API Indodax
    data = {
        'method': method,
        'timestamp': str(int(time.time() * 1000)),
        'recvWindow': '10000' # Batas waktu toleransi delay jaringan
    }
    
    if parameter_tambahan:
        data.update(parameter_tambahan)

    # Proses enkripsi (Signing)
    post_data = urllib.parse.urlencode(data)
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
    
    # Permintaan POST ke server Indodax
    response = requests.post(url, headers=headers, data=data, timeout=10)
    return response.json()

# ==============================================================================
# RUTINITAS PEMINDAIAN UTAMA LENGKAP
# ==============================================================================
def rutinitas_pemindaian():
    """Siklus pemantauan yang berjalan terus-menerus di latar belakang."""
    global BOT_IS_RUNNING, bot_state
    
    while BOT_IS_RUNNING:
        try:
            koin_nama = bot_state["selected_coin"]
            data_koin = config.CRYPTO_MAP.get(koin_nama)
            
            if not data_koin:
                bot_state["last_action"] = f"⚠️ Konfigurasi {koin_nama} tidak ditemukan."
                time.sleep(10)
                continue

            bot_state["last_action"] = f"🔍 Memantau {koin_nama}..."
            
            # Format pair untuk API Private (contoh: 'btc_idr')
            simbol_koin_kecil = data_koin['ticker'].split('IDR')[0].lower()
            pair_indodax = f"{simbol_koin_kecil}_idr"
            
            # Tarik Data Live Harga Publik
            data_live = data_engine.tarik_data_live_indodax()
            ticker = data_koin['ticker']
            
            if ticker in data_live:
                harga_skrg = float(data_live[ticker]['last'])
                
                # Tarik Grafik, Indikator (ATR), dan Sentimen
                df_chart, _ = data_engine.tarik_grafik_klines_aman(data_koin['tv'], "15m", 50, data_live[ticker])
                
                if not df_chart.empty:
                    df_chart = data_engine.hitung_indikator_teknikal(df_chart)
                    atr_terbaru = float(df_chart.iloc[-1]['ATR'])
                    
                    try:
                        sentimen = data_engine.tarik_sentimen_global()
                    except Exception:
                        sentimen = 50 
                    
                    # Panggil Otak AI Gemini (Manajemen kuota 72 menit ada di quant_brain)
                    narasi, keputusan = quant_brain.prediksi_ai_market(df_chart, koin_nama, harga_skrg, "15m", sentimen)
                    
                    # =================================================================
                    # EKSEKUSI: MODE SIMULASI
                    # =================================================================
                    if bot_state["mode_simulasi"]:
                        if koin_nama in bot_state["positions"]:
                            pos = bot_state["positions"][koin_nama]
                            
                            # Update harga tertinggi untuk Trailing Stop
                            if harga_skrg > pos["high_price"]: 
                                pos["high_price"] = harga_skrg
                            
                            batas_jual = pos["high_price"] - (atr_terbaru * bot_state["atr_multiplier"])
                            
                            if keputusan == "SELL" or harga_skrg <= batas_jual:
                                hasil_jual = pos["amount"] * harga_skrg * 0.997 # Fee 0.3%
                                bot_state["cash"] += hasil_jual
                                del bot_state["positions"][koin_nama]
                                alasan = "Sinyal AI" if keputusan == "SELL" else "Trailing Stop"
                                bot_state["last_action"] = f"✅ SIMULASI JUAL {koin_nama} di Rp {harga_skrg:,.0f} ({alasan})"
                            else:
                                bot_state["last_action"] = f"⚖️ HOLD (Simulasi) | Batas TS: Rp {batas_jual:,.0f}"

                        elif keputusan == "BUY" and bot_state["cash"] > 100000:
                            koin_didapat = (bot_state["cash"] / harga_skrg) * 0.997
                            bot_state["positions"][koin_nama] = {
                                "amount": koin_didapat, 
                                "buy_price": harga_skrg, 
                                "high_price": harga_skrg, 
                                "atr_saat_beli": atr_terbaru
                            }
                            bot_state["cash"] = 0
                            bot_state["last_action"] = f"🚀 SIMULASI BELI {koin_nama} di Rp {harga_skrg:,.0f}"
                        else:
                            bot_state["last_action"] = f"💤 Standby {koin_nama} | AI: {keputusan}"
                                
                    # =================================================================
                    # EKSEKUSI: MODE LIVE TRADING (ASLI)
                    # =================================================================
                    else:
                        try:
                            # 1. Cek Saldo Asli di Akun Indodax
                            info_akun = panggil_api_private_indodax('getInfo')
                            
                            if info_akun.get('success') == 1:
                                saldo_idr_asli = float(info_akun['return']['balance']['idr'])
                                saldo_koin_asli = float(info_akun['return']['balance'].get(simbol_koin_kecil, 0))
                                
                                # Sinkronisasi tampilan modal UI dengan saldo asli
                                bot_state['cash'] = saldo_idr_asli
                                
                                # 2. Logika Trailing Stop Live (Jika memiliki koin asli)
                                if saldo_koin_asli > 0.00001: # Toleransi saldo koin receh
                                    if koin_nama not in bot_state["live_positions"]:
                                        bot_state["live_positions"][koin_nama] = {"high_price": harga_skrg}
                                        
                                    pos_live = bot_state["live_positions"][koin_nama]
                                    if harga_skrg > pos_live["high_price"]:
                                        pos_live["high_price"] = harga_skrg
                                        
                                    batas_jual_live = pos_live["high_price"] - (atr_terbaru * bot_state["atr_multiplier"])
                                    
                                    # Eksekusi Jual Asli
                                    if keputusan == "SELL" or harga_skrg <= batas_jual_live:
                                        parameter_jual = {
                                            'pair': pair_indodax,
                                            'type': 'sell',
                                            'price': str(int(harga_skrg)), # Indodax IDR pair butuh integer
                                            simbol_koin_kecil: str(saldo_koin_asli) # Jual semua koin
                                        }
                                        res_jual = panggil_api_private_indodax('trade', parameter_jual)
                                        
                                        if res_jual.get('success') == 1:
                                            alasan = "Sinyal AI" if keputusan == "SELL" else "Trailing Stop"
                                            bot_state["last_action"] = f"✅ LIVE SELL SUKSES: {koin_nama} ({alasan})"
                                            del bot_state["live_positions"][koin_nama] # Reset tracker
                                        else:
                                            bot_state["last_action"] = f"⚠️ Gagal Jual Asli: {res_jual.get('error')}"
                                    else:
                                        bot_state["last_action"] = f"⚖️ HOLD (Live) | Saldo: {saldo_koin_asli:.4f} {simbol_koin_kecil.upper()} | TS: Rp {batas_jual_live:,.0f}"
                                        
                                # 3. Eksekusi Beli Asli
                                elif keputusan == "BUY" and saldo_idr_asli > 15000: # Minimal beli Indodax amannya di atas 10k
                                    jumlah_beli_idr = saldo_idr_asli * 0.99 # Alokasikan 99% IDR untuk beli
                                    
                                    parameter_beli = {
                                        'pair': pair_indodax,
                                        'type': 'buy',
                                        'price': str(int(harga_skrg)),
                                        'idr': str(int(jumlah_beli_idr))
                                    }
                                    res_beli = panggil_api_private_indodax('trade', parameter_beli)
                                    
                                    if res_beli.get('success') == 1:
                                        bot_state["last_action"] = f"🚀 LIVE BUY SUKSES: {koin_nama} senilai Rp {jumlah_beli_idr:,.0f}"
                                        bot_state["live_positions"][koin_nama] = {"high_price": harga_skrg} # Mulai lacak harga
                                    else:
                                        bot_state["last_action"] = f"⚠️ Gagal Beli Asli: {res_beli.get('error')}"
                                        
                                else:
                                    bot_state["last_action"] = f"💤 LIVE STANDBY: {koin_nama} | Modal IDR: Rp {saldo_idr_asli:,.0f}"
                            else:
                                bot_state["last_action"] = f"❌ Gagal Akses Akun: {info_akun.get('error')}"
                                
                        except Exception as api_err:
                            bot_state["last_action"] = f"❌ Kesalahan Jaringan Indodax: {str(api_err)}"

            time.sleep(bot_state["scan_speed"])
            
        except Exception as e:
            bot_state["last_action"] = f"⚠️ Jeda Sistem Kritis: {str(e)}"
            time.sleep(15)

def mulai_bot_latar_belakang():
    global BOT_IS_RUNNING
    if not BOT_IS_RUNNING:
        BOT_IS_RUNNING = True
        thread = threading.Thread(target=rutinitas_pemindaian, daemon=True)
        thread.start()

def hentikan_bot_latar_belakang():
    global BOT_IS_RUNNING
    BOT_IS_RUNNING = False
