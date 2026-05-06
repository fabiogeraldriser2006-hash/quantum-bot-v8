"""
================================================================================
FILE: execution_bot.py
VERSI: Full Documentation & Ultimate Features (Fixed Ticker Format)
DESKRIPSI: Mesin Eksekusi Utama. Mengatur koneksi API Publik & Privat Indodax.
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

bot_state = {
    "selected_coin": "Bitcoin (BTC)",
    "last_action": "Sistem bersiap untuk memulai...",
    "scan_speed": 60,
    "atr_multiplier": 2.0,
    "mode_simulasi": True,
    "cash": 10000000.0,
    "positions": {},
    "live_positions": {},
    "api_key_indodax": "",
    "secret_key_indodax": ""
}

BOT_IS_RUNNING = False

def panggil_api_private_indodax(method, parameter_tambahan=None):
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
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    response = requests.post(url, headers=headers, data=data, timeout=10)
    return response.json()

def rutinitas_pemindaian():
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
            
            # --- LOGIKA KECERDASAN TEKS (MEMISAHKAN PUBLIK & PRIVAT) ---
            # 1. Ticker Publik: Untuk menarik harga live dari server terbuka (Contoh: 'solidr')
            ticker_publik = data_koin['ticker'] 
            
            # 2. Ticker Privat: Untuk transaksi uang asli. Kita potong 'idr' lalu gabung pakai '_'
            simbol_koin_kecil = ticker_publik.replace('idr', '') # Menjadi 'sol'
            pair_indodax = f"{simbol_koin_kecil}_idr"            # Menjadi 'sol_idr'
            
            # Menarik Harga Live
            data_live = data_engine.tarik_data_live_indodax()
            
            # Pengecekan Sabuk Pengaman dengan format Publik
            if data_live and ticker_publik in data_live:
                harga_skrg = float(data_live[ticker_publik]['last'])
                
                # Tarik Grafik 15 Menit
                df_chart, _ = data_engine.tarik_grafik_klines_aman(data_koin['tv'], "15m", 50, data_live[ticker_publik])
                
                if not df_chart.empty:
                    df_chart = data_engine.hitung_indikator_teknikal(df_chart)
                    atr_terbaru = float(df_chart.iloc[-1]['ATR'])
                    
                    try:
                        sentimen = data_engine.tarik_sentimen_global()
                    except Exception:
                        sentimen = 50 
                    
                    narasi, keputusan = quant_brain.prediksi_ai_market(df_chart, koin_nama, harga_skrg, "15m", sentimen)
                    
                    # =================================================================
                    # MODE SIMULASI
                    # =================================================================
                    if bot_state["mode_simulasi"]:
                        if koin_nama in bot_state["positions"]:
                            pos = bot_state["positions"][koin_nama]
                            
                            if harga_skrg > pos["high_price"]: pos["high_price"] = harga_skrg
                            batas_jual = pos["high_price"] - (atr_terbaru * bot_state["atr_multiplier"])
                            
                            if keputusan == "SELL" or harga_skrg <= batas_jual:
                                hasil_jual = pos["amount"] * harga_skrg * 0.997
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
                            info_akun = panggil_api_private_indodax('getInfo')
                            
                            if info_akun.get('success') == 1:
                                saldo_idr_asli = float(info_akun['return']['balance']['idr'])
                                saldo_koin_asli = float(info_akun['return']['balance'].get(simbol_koin_kecil, 0))
                                bot_state['cash'] = saldo_idr_asli
                                
                                if saldo_koin_asli > 0.00001: 
                                    if koin_nama not in bot_state["live_positions"]:
                                        bot_state["live_positions"][koin_nama] = {"high_price": harga_skrg}
                                        
                                    pos_live = bot_state["live_positions"][koin_nama]
                                    if harga_skrg > pos_live["high_price"]:
                                        pos_live["high_price"] = harga_skrg
                                        
                                    batas_jual_live = pos_live["high_price"] - (atr_terbaru * bot_state["atr_multiplier"])
                                    
                                    if keputusan == "SELL" or harga_skrg <= batas_jual_live:
                                        parameter_jual = {
                                            'pair': pair_indodax, # Menggunakan format Privat 'sol_idr'
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
                                        
                                elif keputusan == "BUY" and saldo_idr_asli > 15000: 
                                    jumlah_beli_idr = saldo_idr_asli * 0.99 
                                    parameter_beli = {
                                        'pair': pair_indodax, # Menggunakan format Privat 'sol_idr'
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

def mulai_bot_latar_belakang():
    global BOT_IS_RUNNING
    if not BOT_IS_RUNNING:
        BOT_IS_RUNNING = True
        thread = threading.Thread(target=rutinitas_pemindaian, daemon=True)
        thread.start()

def hentikan_bot_latar_belakang():
    global BOT_IS_RUNNING
    BOT_IS_RUNNING = False
