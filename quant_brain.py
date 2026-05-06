"""
================================================================================
FILE: quant_brain.py
DESKRIPSI: Otak AI Gemini (Multi-Timeframe Engine).
Menganalisis Tren Makro (4H) dan Presisi Mikro (15m) secara bersamaan.
Dilengkapi JSON Parser Aman dan Manajemen Kuota 24 Jam.
================================================================================
"""
import pandas as pd
from google import genai
import json
import os
import time

CACHE_FILE = "ai_api_cache.json"

def baca_ingatan():
    """Membaca arsip analisis dari file untuk menghemat kuota."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def simpan_ingatan(data):
    """Menyimpan hasil analisis baru ke dalam sistem."""
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(data, f)
    except Exception:
        pass

# ==============================================================================
# PERUBAHAN UTAMA: PARAMETER MENERIMA DF MAKRO DAN DF MIKRO
# ==============================================================================
def prediksi_ai_market(df_macro, df_micro, coin, current_price, sentimen_global):
    """
    Fungsi utama AI. 
    Mengevaluasi tren 4 Jam (Macro) dan momentum 15 Menit (Micro) sekaligus.
    """
    narasi_awal = f"**🧠 Gemini Quant Engine (Multi-TF): {coin}**\n\nSpot: **Rp {current_price:,.0f}** | Sentimen: **{sentimen_global}/100**\n\n"
    
    ingatan_ai = baca_ingatan()
    kunci_koin = f"{coin}_MultiTF" # Kunci cache diperbarui
    waktu_sekarang = time.time()
    
    # --- MANAJEMEN 20 KUOTA HARIAN (SURVIVAL 24 JAM) ---
    if kunci_koin in ingatan_ai:
        waktu_terakhir = ingatan_ai[kunci_koin]["waktu"]
        selisih_waktu = waktu_sekarang - waktu_terakhir
        
        # 4320 detik = 72 menit (1440 menit sehari / 20 kuota = 72 menit)
        if selisih_waktu < 4320:
            sisa_menit = int((4320 - selisih_waktu) / 60)
            return narasi_awal + f"*(Arsip Memori: Diperbarui {sisa_menit} menit lagi untuk menghemat kuota)*\n\n" + ingatan_ai[kunci_koin]["narasi"], ingatan_ai[kunci_koin]["keputusan"]

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return narasi_awal + "⚠️ Kunci API Gemini belum dimasukkan.", "HOLD"
        
    client = genai.Client(api_key=api_key)
    
    # Pastikan kedua grafik memiliki data yang cukup
    if len(df_macro) < 10 or len(df_micro) < 20: 
        return narasi_awal + "Data belum cukup untuk dianalisis (Butuh Klines Makro & Mikro).", "HOLD"
    
    try:
        # =================================================================
        # LOGIKA MULTI-TIMEFRAME: MENGGABUNGKAN 2 TABEL DATA
        # =================================================================
        
        # 1. Siapkan Tabel Makro (4 Jam)
        df_macro_recent = df_macro.tail(5)[['Date', 'Close', 'MACD', 'RSI']].copy()
        df_macro_recent['Date'] = df_macro_recent['Date'].astype(str)
        tabel_makro = df_macro_recent.to_string(index=False)
        
        # 2. Siapkan Tabel Mikro (15 Menit)
        df_micro_recent = df_micro.tail(15)[['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'ATR']].copy()
        df_micro_recent['Date'] = df_micro_recent['Date'].astype(str)
        tabel_mikro = df_micro_recent.to_string(index=False)
        
        # 3. Rancang Prompt Top-Down Analysis
        prompt = f"""
        Lakukan 'Top-Down Analysis' pada aset kripto {coin}.
        Harga Spot Saat Ini: Rp {current_price}
        Sentimen Pasar Makro (Fear & Greed Index): {sentimen_global} (0 = Ketakutan Ekstrem, 100 = Keserakahan Ekstrem).

        DATA MAKRO (Grafik 4 Jam) - Tentukan Tren Utama:
        {tabel_makro}
        
        DATA MIKRO (Grafik 15 Menit) - Tentukan Presisi Titik Masuk/Keluar:
        {tabel_mikro}
        
        TUGAS ANDA:
        1. Baca tren utama dari data 4 Jam (Apakah Bullish atau Bearish?).
        2. Tentukan keputusan di data 15 Menit HANYA SEARAH dengan tren 4 Jam (Jika 4H Bullish, cari peluang BUY. Jangan Counter-Trend).
        3. Tentukan keputusan akhir: BUY, SELL, atau HOLD.
        
        BALAS HANYA DENGAN FORMAT JSON INI, TANPA KATA-KATA LAIN:
        {{
            "keputusan": "BUY" | "SELL" | "HOLD",
            "analisis": "Berikan 2 kalimat alasan: 1 kalimat kondisi makro 4H, dan 1 kalimat kondisi eksekusi mikro 15M."
        }}
        """
        
        # --- RADAR PENCARI MODEL OTOMATIS ---
        model_aktif = "gemini-1.5-flash" 
        try:
            for m in client.models.list():
                if "flash" in m.name:
                    model_aktif = m.name
                    break
        except Exception:
            pass 
        
        # Eksekusi pemanggilan AI
        response = client.models.generate_content(
            model=model_aktif,
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        
        time.sleep(15) # Jeda untuk kestabilan koneksi API
        
        # --- PEMBERSIHAN TEKS AMAN ---
        jawaban_teks = response.text.strip()
        jawaban_teks = jawaban_teks.replace('```json', '').replace('```', '').strip()
        
        hasil_json = json.loads(jawaban_teks)
        keputusan = hasil_json.get("keputusan", "HOLD")
        analisis_teks = hasil_json.get("analisis", "Gagal mengurai narasi AI.")
        
        # Menyusun tampilan antarmuka
        narasi_ai_saja = f"🤖 **Analisis AI Multi-TF ({model_aktif}):**\n{analisis_teks}\n\n"
        if keputusan == "BUY": 
            narasi_ai_saja += "✅ **Rekomendasi Strategis:** EKSEKUSI (BUY)"
        elif keputusan == "SELL": 
            narasi_ai_saja += "❌ **Rekomendasi Strategis:** PELEPASAN (SELL)"
        else: 
            narasi_ai_saja += "⚖️ **Rekomendasi Strategis:** TAHAN (HOLD)"
            
        # Simpan hasil live ke dalam memori
        ingatan_ai[kunci_koin] = {
            "waktu": time.time(),
            "narasi": narasi_ai_saja,
            "keputusan": keputusan
        }
        simpan_ingatan(ingatan_ai)
        
        return narasi_awal + narasi_ai_saja, keputusan

    except Exception as e:
        error_msg = str(e)
        # --- FALLBACK DATA JIKA KUOTA HABIS (ERROR 429) ---
        if "429" in error_msg or "Quota" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            if kunci_koin in ingatan_ai:
                return narasi_awal + "⏳ **Limit Google (20 Kuota Habis):** Menampilkan data terakhir.\n\n" + ingatan_ai[kunci_koin]["narasi"], ingatan_ai[kunci_koin]["keputusan"]
            return narasi_awal + "⏳ **Limit Google:** Kuota habis, tunggu siklus besok.", "HOLD"
        
        return narasi_awal + f"💥 Error API Gemini: {error_msg}", "ERROR"
