"""
=========================================================
FILE: backtest_engine.py
DESKRIPSI: Mesin simulasi masa lalu. Bertugas menjalankan 
strategi AI pada data historis untuk menguji performa 
(Win Rate, PnL) sebelum menggunakan uang sungguhan.
=========================================================
"""

import pandas as pd
import config
import data_engine
import quant_brain

def jalankan_simulasi_backtest(koin, timeframe, durasi_hari, modal_awal, atr_multiplier):
    """
    Fungsi utama untuk memutar waktu ke belakang dan menguji AI.
    
    Parameter:
    - koin: Nama koin (contoh: "Bitcoin")
    - timeframe: Waktu lilin (contoh: "15m", "1h")
    - durasi_hari: Berapa hari ke belakang (contoh: 7, 14, 30)
    - modal_awal: Uang kas virtual saat simulasi dimulai
    - atr_multiplier: Pengali jarak Trailing Stop
    """
    
    # 1. Menyiapkan batas data yang akan diunduh
    if timeframe == "15m": limit_lilin = durasi_hari * 24 * 4
    elif timeframe == "1h": limit_lilin = durasi_hari * 24
    elif timeframe == "4h": limit_lilin = durasi_hari * 6
    else: limit_lilin = durasi_hari
    
    limit_lilin = min(limit_lilin, 1000) # Indodax membatasi maksimal 1000 data sekali tarik
    
    tv_simbol = config.CRYPTO_MAP[koin]["tv"]
    
    # 2. Mengunduh data masa lalu menggunakan Data Engine
    df_history, status_data = data_engine.tarik_grafik_klines_aman(tv_simbol, timeframe, limit_lilin, None)
    
    if df_history.empty:
        return None, "Gagal mengunduh data riwayat dari Indodax."
        
    df_history = data_engine.hitung_indikator_teknikal(df_history)
    
    # 3. Menyiapkan Variabel Simulasi
    kas_virtual = modal_awal
    koin_virtual = 0.0
    harga_beli_avg = 0.0
    harga_tertinggi_virtual = 0.0
    total_trade = 0
    trade_menang = 0
    jurnal_simulasi = []
    
    # 4. Memutar Waktu (Looping dari masa lalu ke masa kini)
    # Kita mulai dari lilin ke-50 agar AI punya cukup data untuk membaca indikator awal
    for i in range(50, len(df_history)):
        data_saat_ini = df_history.iloc[:i+1].copy()
        baris_terakhir = data_saat_ini.iloc[-1]
        
        harga_sekarang = float(baris_terakhir['Close'])
        waktu = baris_terakhir['Date']
        atr_sekarang = float(baris_terakhir['ATR'])
        
        # Sentimen kita asumsikan netral (50) untuk backtest sederhana
        _, keputusan = quant_brain.prediksi_ai_market(data_saat_ini, koin, harga_sekarang, timeframe, 50)
        
        # LOGIKA BELI (BUY)
        if keputusan == "BUY" and koin_virtual == 0:
            ukuran_beli = kas_virtual * 0.50 # Beli menggunakan 50% dari kas virtual
            koin_kotor = ukuran_beli / harga_sekarang
            koin_virtual = koin_kotor * (1 - config.FEE_RATE)
            kas_virtual -= ukuran_beli
            harga_beli_avg = harga_sekarang
            harga_tertinggi_virtual = harga_sekarang
            
            jurnal_simulasi.append({
                "Waktu": waktu.strftime("%Y-%m-%d %H:%M"),
                "Aksi": "🟢 BUY (AI Signal)",
                "Harga": f"Rp {harga_sekarang:,.0f}",
                "PnL": "-"
            })
            
        # LOGIKA JUAL (SELL / TRAILING STOP)
        elif koin_virtual > 0:
            if harga_sekarang > harga_tertinggi_virtual:
                harga_tertinggi_virtual = harga_sekarang
                
            batas_ts = harga_tertinggi_virtual - (atr_sekarang * atr_multiplier)
            batas_tp = harga_beli_avg * (1 + (config.FEE_RATE * 2) + 0.001)
            
            if (keputusan == "SELL" and harga_sekarang >= batas_tp) or (harga_sekarang <= batas_ts):
                nilai_jual_kotor = koin_virtual * harga_sekarang
                nilai_jual_bersih = nilai_jual_kotor * (1 - config.FEE_RATE)
                modal_awal_idr = koin_virtual * harga_beli_avg / (1 - config.FEE_RATE)
                pnl_trade = nilai_jual_bersih - modal_awal_idr
                
                kas_virtual += nilai_jual_bersih
                koin_virtual = 0.0
                total_trade += 1
                if pnl_trade > 0: trade_menang += 1
                
                alasan = "🔴 SELL (Take Profit)" if keputusan == "SELL" else "🛡️ SELL (Trailing Stop)"
                jurnal_simulasi.append({
                    "Waktu": waktu.strftime("%Y-%m-%d %H:%M"),
                    "Aksi": alasan,
                    "Harga": f"Rp {harga_sekarang:,.0f}",
                    "PnL": f"Rp {pnl_trade:,.0f}"
                })

    # 5. Menghitung Hasil Akhir
    pnl_bersih_total = kas_virtual - modal_awal
    win_rate = (trade_menang / total_trade * 100) if total_trade > 0 else 0
    
    hasil_akhir = {
        "modal_awal": modal_awal,
        "saldo_akhir": kas_virtual,
        "total_profit": pnl_bersih_total,
        "total_trade": total_trade,
        "win_rate": win_rate,
        "status_data": status_data
    }
    
    df_jurnal = pd.DataFrame(jurnal_simulasi)
    
    return hasil_akhir, df_jurnal
