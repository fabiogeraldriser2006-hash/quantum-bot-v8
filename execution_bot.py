"""
================================================================================
FILE: execution_bot.py
VERSI: Full Documentation & Ultimate Features (Multi-Timeframe Integration)
DESKRIPSI: Mesin Eksekusi Utama. Menarik data Makro (4H) & Mikro (15M) 
untuk disuapkan ke AI Gemini.
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
# STATE BOT: Menyimpan status sementara selama bot menyala
# ==============================================================================
bot_state = {
    "selected_coin": "Bitcoin (BTC)",
    "last_action": "Sistem bersiap untuk memulai...",
    "scan_speed": 60,                 # Kecepatan refresh sistem (detik)
    "atr_multiplier": 2.0,            # Jarak pengaman Trailing Stop
    "mode_simulasi": True,            # Mode Uang Kertas (True) atau Uang Asli (False)
    "cash": 10000000.0,               # Modal bohongan untuk mode simulasi
    "positions": {},                  # Keranjang belanja simulasi
    "live_positions": {},             # Keranjang belanja uang asli
    "api_key_indodax": "",
    "secret_key_indodax": ""
}

BOT_IS_RUNNING = False # Sakelar utama penggerak mesin

# ==============================================================================
# FUNGSI KONEKSI PRIVATE API (EKSEKUSI BELI/JUAL ASLI)
# ==============================================================================
def panggil_api_private_indodax(method, parameter_tambahan=None):
    """
    Fungsi khusus untuk mengirim order Beli/Jual dan cek saldo ke akun Indodax Anda.
    Semua data dienkripsi menggunakan HMAC-SHA512.
    """
    api_key = bot_state.get("api_key_indodax", "")
    secret_key = bot_state.get("secret_key_indodax", "")
    
    if not api_key or not secret_key:
        raise ValueError("API Key atau Secret Key Indodax kosong. Harap isi di panel.")

    url = "https://indodax.com/tapi"
    
    data = {
        'method': method,
        'timestamp': str(int(time.time() * 1000)),
        'recvWindow': '10000'
    }
    
    if parameter_tambahan:
        data.update(parameter_tambahan)

    post_data = urllib.parse.urlencode(data)
    
    signature = hmac.new(
        secret_key.encode('utf-8'), 
        post_data.encode('utf-8'), 
        hashlib.sha512
    ).hexdigest()
    
    headers = {
        'Key': api_key,
        'Sign': signature,
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
    }
    
    response = requests.post(url, headers=headers, data=data, timeout=10)
    return response.json()

# ==============================================================================
# RUTINITAS UTAMA BOT (LOOPING)
# ==============================================================================
def rutinitas_pemindaian():
    """
    Jantung dari aplikasi. Menarik data ganda (4H & 15M), 
    bertanya ke AI, dan mengeksekusi order.
    """
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
            
            # Mempersiapkan format nama koin untuk API
            pair_indodax = data_koin['ticker'] 
            simbol_koin_kecil = pair_indodax.split('_')[0] 
            
            # Menarik Harga Spot Live
            data_live = data_engine.tarik_data_live_indodax()
            
            # Sabuk Pengaman Koneksi
            if data_live and pair_indodax in data_live:
                harga_skrg = float(data_live[pair_indodax]['last'])
                
                # =================================================================
                # FITUR BARU: TARIK 2 GRAFIK SEKALIGUS (MAKRO & MIKRO)
                # =================================================================
                df_macro, _ = data_engine.tarik_grafik_klines_aman(data_koin['tv'], "4h", 50, data_live[pair_indodax])
                df_micro, _ = data_engine.tarik_grafik_klines_aman(data_koin['tv'], "15m", 50, data_live[pair_indodax])
                
                # Pastikan kedua grafik berhasil ditarik dan tidak kosong
                if not df_macro.empty and not df_micro.empty:
                    
                    # Hitung Indikator Teknikal untuk kedua timeframe
                    df_macro = data_engine.hitung_indikator_teknikal(df_macro)
                    df_micro = data_engine.hitung_indikator_teknikal(df_micro)
                    
                    # Nilai ATR untuk batas Trailing Stop selalu diambil dari timeframe kecil (presisi)
                    atr_terbaru = float(df_micro.iloc[-1]['ATR'])
                    
                    try:
                        sentimen = data_engine.tarik_sentimen_global()
                    except Exception:
                        sentimen = 50 
                    
                    # Panggil AI Gemini dan berikan KEDUA grafik tersebut
                    narasi, keputusan = quant_brain.prediksi_ai_market(df_macro, df_micro, koin_nama, harga_skrg, sentimen)
                    
                    # =================================================================
                    # MODE SIMULASI (PAPER TRADING)
                    # =================================================================
                    if bot_state["mode_simulasi"]:
                        if koin_nama in bot_state["positions"]:
                            pos = bot_state["positions"][koin_nama]
                            
                            if harga_skrg > pos["high_price"]: 
                                pos["high_price"] = harga_skrg
                                
                            batas_jual = pos["high_price"] - (atr_terbaru * bot_state["atr_multiplier"])
                            
                            if keputusan == "SELL" or harga_skrg <= batas_jual:
                                hasil_jual = pos["amount"] * harga_skrg * 0.997 # Potong fee
                                bot_state["cash"] += hasil_jual
                                del bot_state["positions"][koin_nama] 
                                alasan = "Sinyal AI" if keputusan == "SELL" else "Terkena Trailing Stop"
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
                    # MODE LIVE TRADING (UANG ASLI)
                    # =================================================================
                    else:
                        try:
                            # Mengecek saldo Rupiah dan Koin di dompet
                            info_akun = panggil_api_private_indodax('getInfo')
                            
                            if info_akun.get('success') == 1:
                                saldo_idr_asli = float(info_akun['return']['balance']['idr'])
                                saldo_koin_asli = float(info_akun['return']['balance'].get(simbol_koin_kecil, 0))
                                
                                bot_state['cash'] = saldo_idr_asli
                                
                                # LOGIKA JUAL (Jika punya koin)
                                if saldo_koin_asli > 0.00001: 
                                    if koin_nama not in bot_state["live_positions"]:
                                        bot_state["live_positions"][koin_nama] = {"high_price": harga_skrg}
                                        
                                    pos_live = bot_state["live_positions"][koin_nama]
                                    if harga_skrg > pos_live["high_price"]:
                                        pos_live["high_price"] = harga_skrg
                                        
                                    batas_jual_live = pos_live["high_price"] - (atr_terbaru * bot_state["atr_multiplier"])
                                    
                                    if keputusan == "SELL" or harga_skrg <= batas_jual_live:
                                        parameter_jual = {
                                            'pair': pair_indodax,
                                            'type': 'sell',
                                            'price': str(int(harga_skrg)),
                                            simbol_koin_kecil: str(saldo_koin_asli) 
                                        }
                                        res_jual = panggil_api_private_indodax('trade', parameter_jual)
                                        
                                        if res_jual.get('success') == 1:
                                            alasan = "Sinyal AI" if keputusan == "SELL" else "Terkena Trailing Stop"
                                            bot_state["last_action"] = f"✅ LIVE SELL SUKSES: {koin_nama} ({alasan})"
                                            del bot_state["live_positions"][koin_nama] 
                                        else:
                                            bot_state["last_action"] = f"⚠️ Gagal Jual Asli: {res_jual.get('error')}"
                                    else:
                                        bot_state["last_action"] = f"⚖️ HOLD (Live) | Saldo: {saldo_koin_asli:.4f} {simbol_koin_kecil.upper()} | TS: Rp {batas_jual_live:,.0f}"
                                        
                                # LOGIKA BELI (Jika ada IDR)
                                elif keputusan == "BUY" and saldo_idr_asli > 15000: 
                                    jumlah_beli_idr = saldo_idr_asli * 0.99 
                                    parameter_beli = {
                                        'pair': pair_indodax,
                                        'type': 'buy',
                                        'price': str(int(harga_skrg)),
                                        'idr': str(int(jumlah_beli_idr))
                                    }
                                    res_beli = panggil_api_private_indodax('trade', parameter_beli)
                                    
                                    if res_beli.get('success') == 1:
                                        bot_state["last_action"] = f"🚀 LIVE BUY SUKSES: {koin_nama} senilai Rp {jumlah_beli_idr:,.0f}"
                                        bot_state["live_positions"][koin_nama] = {"high_price": harga_skrg} 
                                    else:
                                        bot_state["last_action"] = f"⚠️ Gagal Beli Asli: {res_beli.get('error')}"
                                        
                                else:
                                    bot_state["last_action"] = f"💤 LIVE STANDBY: {koin_nama} | Modal IDR: Rp {saldo_idr_asli:,.0f}"
                            else:
                                bot_state["last_action"] = f"❌ Gagal Akses Akun Indodax: {info_akun.get('error')}"
                                
                        except Exception as api_err:
                            bot_state["last_action"] = f"❌ Kesalahan Jaringan Server Indodax: {str(api_err)}"
            
            elif not data_live:
                bot_state["last_action"] = f"⚠️ Jaringan lambat, menunggu data dari server Indodax untuk {koin_nama}..."

            time.sleep(bot_state["scan_speed"])
            
        except Exception as e:
            bot_state["last_action"] = f"⚠️ Jeda Sistem Kritis: {str(e)}"
            time.sleep(15)

# ==============================================================================
# KONTROL THREAD (MENYALAKAN/MEMATIKAN BOT DARI UI)
# ==============================================================================
def mulai_bot_latar_belakang():
    global BOT_IS_RUNNING
    if not BOT_IS_RUNNING:
        BOT_IS_RUNNING = True
        thread = threading.Thread(target=rutinitas_pemindaian, daemon=True)
        thread.start()

def hentikan_bot_latar_belakang():
    global BOT_IS_RUNNING
    BOT_IS_RUNNING = False
