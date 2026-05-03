"""
=========================================================
FILE: execution_bot.py
DESKRIPSI: Mesin Eksekusi Latar Belakang (Bot Auto-Pilot).
Beroperasi secara senyap menggunakan 'Threading' agar antarmuka
(UI) Streamlit tidak berkedip/reload. Menggabungkan data, AI, dan
logika Trailing Stop-Loss.
=========================================================
"""

import threading
import time
from datetime import datetime
import urllib.parse
import hmac
import hashlib
import requests

# Mengimpor modul-modul modular kita
import config
import data_engine
import quant_brain

# 1. STATUS DAN MEMORI BOT (Menggantikan st.session_state)
BOT_IS_RUNNING = False

bot_state = {
    "cash": config.MODAL_AWAL_DEFAULT,
    "positions": {},       # Menyimpan koin yang sedang dibeli
    "trade_history": [],   # Mencatat riwayat beli/jual
    "last_action": "Bot dalam posisi standby.",
    "scan_speed": 5,
    "atr_multiplier": 2.0,
    "buy_amount_idr": 10000.0,
    "api_key": "",
    "secret_key": ""
}

# 2. FUNGSI KONEKSI API PRIVATE INDODAX
def indodax_private_api(method, **kwargs):
    """Fungsi rahasia untuk mengeksekusi order jual/beli langsung ke Indodax."""
    if not bot_state["api_key"] or not bot_state["secret_key"]: 
        return {"success": 0, "error": "API Key/Secret kosong."}
    
    url = config.INDODAX_TAPI_URL
    data = {'method': method, 'timestamp': int(time.time() * 1000), 'recvWindow': 5000}
    data.update(kwargs)
    query_string = urllib.parse.urlencode(data)
    signature = hmac.new(bot_state["secret_key"].encode('utf-8'), query_string.encode('utf-8'), hashlib.sha512).hexdigest()
    headers = {'Key': bot_state["api_key"], 'Sign': signature}
    
    try: 
        return requests.post(url, headers=headers, data=data, timeout=10).json()
    except Exception as e: 
        return {"success": 0, "error": str(e)}

# 3. FUNGSI PENCATATAN JURNAL
def catat_log(aksi, koin, harga, jumlah, nilai, pnl="0"):
    """Mencatat setiap transaksi ke dalam riwayat trading."""
    bot_state["trade_history"].append({
        "Waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Aksi": aksi,
        "Koin": koin,
        "Harga (IDR)": f"Rp {int(harga):,}",
        "Kuantitas Koin": f"{jumlah:.6f}",
        "Total IDR (Bersih)": f"Rp {int(nilai):,}",
        "PnL (Net)": f"Rp {int(pnl):,}" if pnl != "0" and pnl != "-" else "-"
    })

# 4. MESIN UTAMA (BERJALAN DI LATAR BELAKANG)
def eksekusi_jual_beli():
    """Mesin yang berputar tanpa henti selama bot diaktifkan."""
    global BOT_IS_RUNNING
    
    while BOT_IS_RUNNING:
        try:
            # A. Tarik data pasar terbaru
            data_live = data_engine.tarik_data_live_indodax()
            sentimen_sekarang = data_engine.tarik_sentimen_global()
            
            if data_live:
                # B. Pindai setiap koin yang ada di konfigurasi
                for koin_target, data_koin in config.CRYPTO_MAP.items():
                    ticker_target = data_koin["ticker"]
                    tv_target = data_koin["tv"]
                    
                    koin_dimiliki = bot_state["positions"].get(koin_target, {}).get('amount', 0.0)
                    sedang_punya_koin = koin_dimiliki > 0
                    
                    if ticker_target in data_live:
                        harga_sekarang = int(data_live[ticker_target]['last'])
                        
                        # C. Tarik grafik masa lalu & hitung indikator
                        df_chart, status_sumber = data_engine.tarik_grafik_klines_aman(tv_target, "15m", 120, data_live[ticker_target])
                        
                        if not df_chart.empty:
                            df_chart = data_engine.hitung_indikator_teknikal(df_chart)
                            
                            # D. Minta pendapat Jaringan Saraf AI
                            _, konklusi_ai = quant_brain.prediksi_ai_market(df_chart, koin_target, harga_sekarang, "15m", sentimen_sekarang)
                            
                            # ==========================================
                            # LOGIKA 1: PEMBELIAN (BUY)
                            # ==========================================
                            if konklusi_ai == "BUY" and not sedang_punya_koin:
                                ukuran_beli = bot_state["buy_amount_idr"]
                                
                                if ukuran_beli >= 10000.0: # Minimal order Indodax
                                    # MODE LIVE
                                    if bot_state["api_key"] and bot_state["secret_key"]:
                                        res = indodax_private_api('trade', pair=ticker_target, type='buy', price=int(harga_sekarang*1.01), idr=ukuran_beli)
                                        if res.get('success') == 1:
                                            koin_bersih = (ukuran_beli / harga_sekarang) * (1 - config.FEE_RATE)
                                            bot_state["positions"][koin_target] = {'amount': koin_bersih, 'avg_price': harga_sekarang, 'highest_price': harga_sekarang}
                                            catat_log("🟢 LIVE AUTO BUY", koin_target, harga_sekarang, koin_bersih, ukuran_beli, "-")
                                    # MODE SIMULASI
                                    else:
                                        if ukuran_beli <= bot_state["cash"]:
                                            koin_bersih = (ukuran_beli / harga_sekarang) * (1 - config.FEE_RATE)
                                            bot_state["cash"] -= ukuran_beli
                                            bot_state["positions"][koin_target] = {'amount': koin_bersih, 'avg_price': harga_sekarang, 'highest_price': harga_sekarang}
                                            catat_log("🟢 SIM AUTO BUY", koin_target, harga_sekarang, koin_bersih, ukuran_beli, "-")
                                    
                                    bot_state["last_action"] = f"Membeli {koin_target} pada Rp {harga_sekarang:,}"

                            # ==========================================
                            # LOGIKA 2: PERLINDUNGAN (TRAILING STOP & SELL)
                            # ==========================================
                            elif sedang_punya_koin:
                                # Update Harga Tertinggi untuk menaikkan Jaring Pengaman ATR
                                harga_tercatat = bot_state["positions"][koin_target].get('highest_price', bot_state["positions"][koin_target]['avg_price'])
                                if harga_sekarang > harga_tercatat:
                                    bot_state["positions"][koin_target]['highest_price'] = harga_sekarang
                                    
                                harga_tertinggi = bot_state["positions"][koin_target].get('highest_price', harga_sekarang)
                                harga_beli_rata2 = bot_state["positions"][koin_target]['avg_price']
                                atr_sekarang = df_chart['ATR'].iloc[-1]
                                
                                # Kalkulasi Batas Bawah (Cut-loss dinamis) dan Batas Atas (Take Profit)
                                batas_trailing_stop = harga_tertinggi - (atr_sekarang * bot_state["atr_multiplier"])
                                batas_take_profit = harga_beli_rata2 * (1 + (config.FEE_RATE * 2) + 0.001)
                                
                                # Jika Harga Sentuh Take Profit ATAU Jatuh Kena Jaring Pengaman
                                if (konklusi_ai == "SELL" and harga_sekarang >= batas_take_profit) or (harga_sekarang <= batas_trailing_stop):
                                    nilai_jual_kotor = koin_dimiliki * harga_sekarang
                                    nilai_jual_bersih = nilai_jual_kotor * (1 - config.FEE_RATE)
                                    modal_awal_idr = koin_dimiliki * harga_beli_rata2 / (1 - config.FEE_RATE)
                                    pnl_bersih_akhir = nilai_jual_bersih - modal_awal_idr
                                    
                                    aksi_jual_live = "🔴 LIVE AUTO SELL" if konklusi_ai == "SELL" else "🛡️ LIVE TRAILING STOP"
                                    aksi_jual_sim = "🔴 SIM AUTO SELL" if konklusi_ai == "SELL" else "🛡️ SIM TRAILING STOP"
                                    
                                    # MODE LIVE
                                    if bot_state["api_key"] and bot_state["secret_key"]:
                                        res = indodax_private_api('trade', pair=ticker_target, type='sell', price=int(harga_sekarang*0.99), **{ticker_target.split('_')[0]: koin_dimiliki})
                                        if res.get('success') == 1:
                                            catat_log(aksi_jual_live, koin_target, harga_sekarang, koin_dimiliki, nilai_jual_bersih, pnl_bersih_akhir)
                                            del bot_state["positions"][koin_target]
                                    # MODE SIMULASI
                                    else:
                                        bot_state["cash"] += nilai_jual_bersih
                                        catat_log(aksi_jual_sim, koin_target, harga_sekarang, koin_dimiliki, nilai_jual_bersih, pnl_bersih_akhir)
                                        del bot_state["positions"][koin_target]
                                        
                                    bot_state["last_action"] = f"Menjual {koin_target} (PnL: Rp {int(pnl_bersih_akhir):,})"
                                else:
                                    bot_state["last_action"] = f"Mengamankan {koin_target} (Batas Perlindungan: Rp {int(batas_trailing_stop):,})"
            
            # Istirahatkan bot sejenak agar CPU tidak panas dan server tidak memblokir kita
            time.sleep(bot_state["scan_speed"])
            
        except Exception as e:
            bot_state["last_action"] = f"Error Latar Belakang: {e}"
            time.sleep(5) # Jeda jika terjadi error jaringan

# 5. SAKLAR KONTROL (Dipanggil dari app.py)
def mulai_bot_latar_belakang():
    """Mengaktifkan Thread pekerja."""
    global BOT_IS_RUNNING
    if not BOT_IS_RUNNING:
        BOT_IS_RUNNING = True
        pekerja = threading.Thread(target=eksekusi_jual_beli)
        pekerja.daemon = True # Thread mati saat aplikasi Streamlit ditutup
        pekerja.start()
        return True
    return False

def hentikan_bot_latar_belakang():
    """Mematikan Thread pekerja."""
    global BOT_IS_RUNNING
    BOT_IS_RUNNING = False
