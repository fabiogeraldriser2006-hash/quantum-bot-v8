"""
================================================================================
FILE: execution_bot.py
VERSI: Ultimate Integrated (Multi-Timeframe + Scoreboard + SQLite Database + Net Take Profit)
DESKRIPSI: Mesin Eksekusi Utama. Menarik data Makro & Mikro, menjalankan AI, 
serta mencatat riwayat transaksi secara PERMANEN ke SQLite.
=========================================================
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
import database # <--- MENGHUBUNGKAN KE MODUL DATABASE

# ==============================================================================
# INITIAL LOAD: Memuat data dari Database saat file pertama kali dijalankan
# ==============================================================================
# Memastikan tabel database siap dan memuat data terakhir
database.inisialisasi_db()
data_tersimpan = database.muat_status_bot()

bot_state = {
    "selected_coin": "Bitcoin (BTC)",
    "last_action": "Sistem dimuat dari database permanen...",
    "scan_speed": 60,                 # Kecepatan refresh sistem (detik)
    "atr_multiplier": 2.0,            # Jarak pengaman Trailing Stop
    "take_profit_pct": 1.0,           # <--- DIUBAH: Target Net Profit 1.0%
    "mode_simulasi": True,            # Mode Uang Kertas (True) atau Uang Asli (False)
    "cash": data_tersimpan["cash"],   # Saldo dimuat dari DB
    "positions": data_tersimpan["positions"],     # Posisi simulasi dari DB
    "live_positions": data_tersimpan["live_positions"], # Posisi live dari DB
    "trade_history": database.ambil_riwayat(),    # Riwayat Papan Skor dari DB
    "api_key_indodax": "",
    "secret_key_indodax": ""
}

BOT_IS_RUNNING = False # Sakelar utama mesin

# ==============================================================================
# FUNGSI KONEKSI PRIVATE API (EKSEKUSI BELI/JUAL ASLI)
# ==============================================================================
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
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
    }
    
    response = requests.post(url, headers=headers, data=data, timeout=10)
    return response.json()

# ==============================================================================
# RUTINITAS UTAMA BOT (LOOPING) DENGAN INTEGRASI DATABASE
# ==============================================================================
def rutinitas_pemindaian():
    global BOT_IS_RUNNING, bot_state
    
    while BOT_IS_RUNNING:
        try:
            koin_nama = bot_state["selected_coin"]
            data_koin = config.CRYPTO_MAP.get(koin_nama)
            
            if not data_koin:
                bot_state["last_action"] = f"⚠️ Konfigurasi {koin_nama} tidak ditemukan."
                time.sleep(10); continue

            bot_state["last_action"] = f"🔍 Memantau {koin_nama}..."
            pair_indodax = data_koin['ticker'] 
            simbol_koin_kecil = pair_indodax.split('_')[0] 
            
            data_live = data_engine.tarik_data_live_indodax()
            
            if data_live and pair_indodax in data_live:
                harga_skrg = float(data_live[pair_indodax]['last'])
                
                # Tarik 2 Grafik Sekaligus (Multi-Timeframe)
                df_macro, _ = data_engine.tarik_grafik_klines_aman(data_koin['tv'], "4h", 50, data_live[pair_indodax])
                df_micro, _ = data_engine.tarik_grafik_klines_aman(data_koin['tv'], "15m", 50, data_live[pair_indodax])
                
                if not df_macro.empty and not df_micro.empty:
                    df_macro = data_engine.hitung_indikator_teknikal(df_macro)
                    df_micro = data_engine.hitung_indikator_teknikal(df_micro)
                    atr_terbaru = float(df_micro.iloc[-1]['ATR'])
                    
                    try: sentimen = data_engine.tarik_sentimen_global()
                    except: sentimen = 50 
                    
                    # Panggil AI Gemini (Logika Multi-TF)
                    narasi, keputusan = quant_brain.prediksi_ai_market(df_macro, df_micro, koin_nama, harga_skrg, sentimen)
                    
                    # --- MODE SIMULASI (PAPER TRADING) ---
                    if bot_state["mode_simulasi"]:
                        if koin_nama in bot_state["positions"]:
                            pos = bot_state["positions"][koin_nama]
                            if harga_skrg > pos["high_price"]: 
                                pos["high_price"] = harga_skrg
                                
                            batas_jual = pos["high_price"] - (atr_terbaru * bot_state["atr_multiplier"])
                            
                            # <--- DIUBAH: Kalkulasi Net Profit (Harga Jual dipotong fee 0.3% dulu) --->
                            harga_jual_bersih = harga_skrg * 0.997
                            persentase_profit_bersih = ((harga_jual_bersih - pos["buy_price"]) / pos["buy_price"]) * 100
                            kondisi_take_profit = persentase_profit_bersih >= bot_state["take_profit_pct"]
                            
                            if keputusan == "SELL" or harga_skrg <= batas_jual or kondisi_take_profit:
                                hasil_jual = pos["amount"] * harga_jual_bersih # hasil_jual_bersih sudah include 0.997
                                modal_awal = pos["amount"] * pos["buy_price"]
                                pnl_transaksi = hasil_jual - modal_awal
                                
                                if kondisi_take_profit:
                                    alasan_jual = f"Net Take Profit (+{persentase_profit_bersih:.2f}%)"
                                elif keputusan == "SELL":
                                    alasan_jual = "Sinyal AI"
                                else:
                                    alasan_jual = "Trailing Stop"
                                
                                # 1. Simpan ke Riwayat Database (Scoreboard)
                                trade_log = {
                                    "waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "koin": koin_nama, "harga_beli": pos["buy_price"],
                                    "harga_jual": harga_skrg, "pnl": pnl_transaksi,
                                    "alasan": alasan_jual
                                }
                                database.simpan_trade(trade_log)
                                
                                # 2. Update Memori State
                                bot_state["cash"] += hasil_jual
                                bot_state["trade_history"] = database.ambil_riwayat()
                                del bot_state["positions"][koin_nama] 
                                
                                # 3. Sinkronkan Status Aktif ke Database
                                database.simpan_status_bot(bot_state["cash"], bot_state["positions"], bot_state["live_positions"])
                                bot_state["last_action"] = f"✅ SIMULASI JUAL {koin_nama} | {alasan_jual} | PnL: Rp {pnl_transaksi:,.0f}"
                            else:
                                bot_state["last_action"] = f"⚖️ HOLD (Sim) | Net Profit: {persentase_profit_bersih:.2f}% | TS: Rp {batas_jual:,.0f}"

                        elif keputusan == "BUY" and bot_state["cash"] > 100000:
                            koin_didapat = (bot_state["cash"] / harga_skrg) * 0.997
                            bot_state["positions"][koin_nama] = {
                                "amount": koin_didapat, "buy_price": harga_skrg, 
                                "high_price": harga_skrg, "atr_saat_beli": atr_terbaru
                            }
                            bot_state["cash"] = 0 
                            
                            # Sinkronkan Status Aktif ke Database
                            database.simpan_status_bot(bot_state["cash"], bot_state["positions"], bot_state["live_positions"])
                            bot_state["last_action"] = f"🚀 SIMULASI BELI {koin_nama} di Rp {harga_skrg:,.0f}"

                    # --- MODE LIVE TRADING (UANG ASLI) ---
                    else:
                        try:
                            info_akun = panggil_api_private_indodax('getInfo')
                            if info_akun.get('success') == 1:
                                saldo_idr_asli = float(info_akun['return']['balance']['idr'])
                                saldo_koin_asli = float(info_akun['return']['balance'].get(simbol_koin_kecil, 0))
                                bot_state['cash'] = saldo_idr_asli
                                
                                if saldo_koin_asli > 0.00001: 
                                    if koin_nama not in bot_state["live_positions"]:
                                        bot_state["live_positions"][koin_nama] = {"high_price": harga_skrg, "buy_price": harga_skrg}
                                        
                                    pos_live = bot_state["live_positions"][koin_nama]
                                    if harga_skrg > pos_live["high_price"]: pos_live["high_price"] = harga_skrg
                                    batas_jual_live = pos_live["high_price"] - (atr_terbaru * bot_state["atr_multiplier"])
                                    
                                    # <--- DIUBAH: Kalkulasi Net Profit (Harga Jual dipotong fee 0.3% dulu) (Live) --->
                                    harga_jual_bersih = harga_skrg * 0.997
                                    persentase_profit_bersih = ((harga_jual_bersih - pos_live["buy_price"]) / pos_live["buy_price"]) * 100
                                    kondisi_take_profit = persentase_profit_bersih >= bot_state["take_profit_pct"]
                                    
                                    if keputusan == "SELL" or harga_skrg <= batas_jual_live or kondisi_take_profit:
                                        parameter_jual = {
                                            'pair': pair_indodax, 'type': 'sell',
                                            'price': str(int(harga_skrg)), simbol_koin_kecil: str(saldo_koin_asli) 
                                        }
                                        res_jual = panggil_api_private_indodax('trade', parameter_jual)
                                        if res_jual.get('success') == 1:
                                            # Hitung PnL dan Simpan ke DB
                                            modal_awal = saldo_koin_asli * pos_live["buy_price"]
                                            hasil_jual = saldo_koin_asli * harga_jual_bersih
                                            pnl = hasil_jual - modal_awal
                                            
                                            if kondisi_take_profit:
                                                alasan_jual = f"Net Take Profit (+{persentase_profit_bersih:.2f}%)"
                                            elif keputusan == "SELL":
                                                alasan_jual = "Sinyal AI"
                                            else:
                                                alasan_jual = "Trailing Stop"
                                            
                                            database.simpan_trade({
                                                "waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                                "koin": koin_nama, "harga_beli": pos_live["buy_price"],
                                                "harga_jual": harga_skrg, "pnl": pnl,
                                                "alasan": alasan_jual
                                            })
                                            
                                            del bot_state["live_positions"][koin_nama]
                                            bot_state["trade_history"] = database.ambil_riwayat()
                                            database.simpan_status_bot(bot_state["cash"], bot_state["positions"], bot_state["live_positions"])
                                            bot_state["last_action"] = f"✅ LIVE SELL SUKSES | {alasan_jual}"
                                    else:
                                        bot_state["last_action"] = f"⚖️ HOLD (Live) | Net Profit: {persentase_profit_bersih:.2f}% | TS: Rp {batas_jual_live:,.0f}"
                                        
                                elif keputusan == "BUY" and saldo_idr_asli > 15000: 
                                    jumlah_beli_idr = saldo_idr_asli * 0.99 
                                    parameter_beli = {
                                        'pair': pair_indodax, 'type': 'buy',
                                        'price': str(int(harga_skrg)), 'idr': str(int(jumlah_beli_idr))
                                    }
                                    res_beli = panggil_api_private_indodax('trade', parameter_beli)
                                    if res_beli.get('success') == 1:
                                        bot_state["live_positions"][koin_nama] = {"high_price": harga_skrg, "buy_price": harga_skrg} 
                                        database.simpan_status_bot(bot_state["cash"], bot_state["positions"], bot_state["live_positions"])
                                        bot_state["last_action"] = f"🚀 LIVE BUY SUKSES: {koin_nama}"

                        except Exception as api_err:
                            bot_state["last_action"] = f"❌ Error API: {str(api_err)}"
            
            elif not data_live:
                bot_state["last_action"] = f"⚠️ Menunggu data dari server Indodax..."

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
