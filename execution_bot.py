"""
================================================================================
FILE: execution_bot.py
VERSI: Ultimate Integrated (Portfolio + Trade History Sync + Multi-Brain)
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
import database

# ==============================================================================
# INITIAL LOAD: Memuat data dari Database
# ==============================================================================
database.inisialisasi_db()
data_tersimpan = database.muat_status_bot()

bot_state = {
    "selected_coin": "Bitcoin (BTC)",
    "selected_ai": "Gemini", 
    "last_action": "Sistem dimuat dari database permanen...",
    "scan_speed": 60,                 
    "atr_multiplier": 2.0,            
    "take_profit_pct": 1.0,           
    "mode_simulasi": True,            
    "cash": data_tersimpan["cash"],   
    "positions": data_tersimpan["positions"],     
    "live_positions": data_tersimpan["live_positions"], 
    "trade_history": database.ambil_riwayat(),    
    "api_key_indodax": "",
    "secret_key_indodax": ""
}

BOT_IS_RUNNING = False 

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
        'User-Agent': 'Mozilla/5.0'
    }
    
    response = requests.post(url, headers=headers, data=data, timeout=10)
    return response.json()

# ==============================================================================
# FUNGSI CEK RIWAYAT HARGA ASLI & PORTOFOLIO
# ==============================================================================
def cari_harga_beli_asli(pair):
    """Membaca riwayat order Indodax untuk mencari harga beli terakhir dari aset."""
    try:
        res = panggil_api_private_indodax('tradeHistory', {'pair': pair})
        if res.get('success') == 1:
            trades = res['return']['trades']
            for trade in trades:
                if trade['type'] == 'buy':
                    return float(trade['price'])
    except Exception:
        pass
    return None 

def ambil_seluruh_aset():
    """
    Menarik semua saldo koin yang kita miliki di Indodax untuk ditampilkan di UI.
    Telah diperbarui dengan filter absolut (> 0) agar saldo terkecil pun terbaca.
    """
    try:
        res = panggil_api_private_indodax('getInfo')
        if res.get('success') == 1:
            balances = res['return'].get('balance', {})
            frozen = res['return'].get('frozen', {})
            
            daftar_aset = []
            for koin, jumlah in balances.items():
                try:
                    jumlah_float = float(jumlah)
                    tertahan_float = float(frozen.get(koin, 0))
                    
                    # PERBAIKAN: Menggunakan filter > 0 agar Satoshi terkecil tidak terbuang
                    if (jumlah_float > 0 or tertahan_float > 0) and koin.lower() != 'idr':
                        daftar_aset.append({
                            "Aset": koin.upper(),
                            "Tersedia": jumlah_float,
                            "Tertahan (Order)": tertahan_float
                        })
                except:
                    pass
            return daftar_aset, None
        else:
            pesan_error = res.get('error', 'Permintaan ditolak tanpa alasan spesifik dari Indodax.')
            return [], pesan_error
    except Exception as e:
        return [], str(e)

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

            ai_aktif = bot_state.get("selected_ai", "Gemini")
            bot_state["last_action"] = f"🔍 Memantau {koin_nama} menggunakan {ai_aktif}..."
            
            pair_indodax = data_koin['ticker'] 
            simbol_koin_kecil = pair_indodax.split('_')[0] 
            
            data_live = data_engine.tarik_data_live_indodax()
            
            if data_live and pair_indodax in data_live:
                harga_skrg = float(data_live[pair_indodax]['last'])
                
                df_macro, _ = data_engine.tarik_grafik_klines_aman(data_koin['tv'], "4h", 50, data_live[pair_indodax])
                df_micro, _ = data_engine.tarik_grafik_klines_aman(data_koin['tv'], "15m", 50, data_live[pair_indodax])
                
                if not df_macro.empty and not df_micro.empty:
                    df_macro = data_engine.hitung_indikator_teknikal(df_macro)
                    df_micro = data_engine.hitung_indikator_teknikal(df_micro)
                    atr_terbaru = float(df_micro.iloc[-1]['ATR'])
                    
                    try: sentimen = data_engine.tarik_sentimen_global()
                    except: sentimen = 50 
                    
                    narasi, keputusan = quant_brain.prediksi_ai_market(
                        df_macro, df_micro, koin_nama, harga_skrg, sentimen, ai_choice=ai_aktif
                    )
                    
                    # --- MODE SIMULASI ---
                    if bot_state["mode_simulasi"]:
                        if koin_nama in bot_state["positions"]:
                            pos = bot_state["positions"][koin_nama]
                            if harga_skrg > pos["high_price"]: 
                                pos["high_price"] = harga_skrg
                                
                            batas_jual = pos["high_price"] - (atr_terbaru * bot_state["atr_multiplier"])
                            
                            harga_jual_bersih = harga_skrg * 0.997
                            persentase_profit_bersih = ((harga_jual_bersih - pos["buy_price"]) / pos["buy_price"]) * 100
                            kondisi_take_profit = persentase_profit_bersih >= bot_state["take_profit_pct"]
                            
                            if keputusan == "SELL" or harga_skrg <= batas_jual or kondisi_take_profit:
                                hasil_jual = pos["amount"] * harga_jual_bersih 
                                modal_awal = pos["amount"] * pos["buy_price"]
                                pnl_transaksi = hasil_jual - modal_awal
                                
                                if kondisi_take_profit:
                                    alasan_jual = f"Net Take Profit (+{persentase_profit_bersih:.2f}%)"
                                elif keputusan == "SELL":
                                    alasan_jual = "Sinyal AI"
                                else:
                                    alasan_jual = "Trailing Stop"
                                
                                trade_log = {
                                    "waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "koin": koin_nama, "harga_beli": pos["buy_price"],
                                    "harga_jual": harga_skrg, "pnl": pnl_transaksi,
                                    "alasan": alasan_jual
                                }
                                database.simpan_trade(trade_log)
                                
                                bot_state["cash"] += hasil_jual
                                bot_state["trade_history"] = database.ambil_riwayat()
                                del bot_state["positions"][koin_nama] 
                                
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
                            
                            database.simpan_status_bot(bot_state["cash"], bot_state["positions"], bot_state["live_positions"])
                            bot_state["last_action"] = f"🚀 SIMULASI BELI {koin_nama} di Rp {harga_skrg:,.0f}"

                    # --- MODE LIVE TRADING ---
                    else:
                        try:
                            info_akun = panggil_api_private_indodax('getInfo')
                            if info_akun.get('success') == 1:
                                saldo_idr_asli = float(info_akun['return']['balance']['idr'])
                                saldo_koin_asli = float(info_akun['return']['balance'].get(simbol_koin_kecil, 0))
                                bot_state['cash'] = saldo_idr_asli
                                
                                # PERBAIKAN: Menggunakan filter > 0 untuk adopsi saldo live
                                if saldo_koin_asli > 0: 
                                    if koin_nama not in bot_state["live_positions"]:
                                        harga_beli_riil = cari_harga_beli_asli(pair_indodax)
                                        
                                        if harga_beli_riil:
                                            harga_patokan = harga_beli_riil
                                            pesan_adopsi = f"📥 Adopsi {koin_nama} | Sync Harga Asli: Rp {harga_patokan:,.0f}"
                                        else:
                                            harga_patokan = harga_skrg
                                            pesan_adopsi = f"📥 Adopsi {koin_nama} | Riwayat nol, pakai Harga Estimasi: Rp {harga_patokan:,.0f}"

                                        bot_state["live_positions"][koin_nama] = {
                                            "high_price": harga_skrg, 
                                            "buy_price": harga_patokan 
                                        }
                                        
                                        database.simpan_status_bot(bot_state["cash"], bot_state["positions"], bot_state["live_positions"])
                                        bot_state["last_action"] = pesan_adopsi
                                        time.sleep(2) 
                                        
                                    pos_live = bot_state["live_positions"][koin_nama]
                                    if harga_skrg > pos_live["high_price"]: pos_live["high_price"] = harga_skrg
                                    batas_jual_live = pos_live["high_price"] - (atr_terbaru * bot_state["atr_multiplier"])
                                    
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
# KONTROL THREAD
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
