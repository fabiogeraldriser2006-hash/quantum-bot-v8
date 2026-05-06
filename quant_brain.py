"""
================================================================================
FILE: quant_brain.py
DESKRIPSI: Otak AI Gemini Lengkap (Full Features).
Menggabungkan Auto-Discovery Model, JSON Parser Aman, dan Manajemen 20 Kuota.
================================================================================
"""
import pandas as pd
from google import genai
import json
import os
import time

# File memori untuk menyimpan analisis AI
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

def prediksi_ai_market(df_chart, coin, current_price, timeframe, sentimen_global):
    """
    Fungsi utama AI. 
    Mengatur pemanggilan Gemini dengan sistem kuota 24 jam (1 panggil / 72 menit).
    """
    narasi_awal = f"**🧠 Gemini Quant Engine: {coin} ({timeframe})**\n\nSpot: **Rp {current_price:,.0f}** | Sentimen: **{sentimen_global}/100**\n\n"
    
    ingatan_ai = baca_ingatan()
    kunci_koin = f"{coin}_{timeframe}"
    waktu_sekarang = time.time()
    
    # =================================================================
    # FITUR BARU: MANAJEMEN 20 KUOTA HARIAN (SURVIVAL 24 JAM)
    # =================================================================
    if kunci_koin in ingatan_ai:
        waktu_terakhir = ingatan_ai[kunci_koin]["waktu"]
        selisih_waktu = waktu_sekarang - waktu_terakhir
        
        # 4320 detik = 72 menit. (1440 menit sehari / 20 kuota = 72 menit)
        if selisih_waktu < 4320:
            sisa_menit = int((4320 - selisih_waktu) / 60)
            return narasi_awal + f"*(Arsip Memori: Diperbarui {sisa_menit} menit lagi untuk menghemat 20 kuota harian)*\n\n" + ingatan_ai[kunci_koin]["narasi"], ingatan_ai[kunci_koin]["keputusan"]

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return narasi_awal + "⚠️ Kunci API Gemini belum dimasukkan.", "HOLD"
        
    client = genai.Client(api_key=api_key)
    
    # Pastikan data grafik cukup panjang
    if len(df_chart) < 20: 
        return narasi_awal + "Data belum cukup untuk dianalisis.", "HOLD"
    
    try:
        # =================================================================
        # FITUR LAMA: PENYUSUNAN TABEL DATA TERPERINCI
        # =================================================================
        df_recent = df_chart.tail(20)[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
        df_recent['Date'] = df_recent['Date'].astype(str)
        tabel_teks = df_recent.to_string(index=False)
        
        prompt = f"""
        Analisis data harga kripto ini (20 periode terakhir):
        {tabel_teks}
        
        Harga saat ini: Rp {current_price} | Sentimen Global: {sentimen_global}
        
        Tentukan BUY, SELL, atau HOLD berdasarkan analisis teknikal.
        BALAS HANYA DENGAN FORMAT JSON:
        {{
            "keputusan": "BUY" | "SELL" | "HOLD",
            "analisis": "Berikan alasan teknikal maksimal 3 kalimat."
        }}
        """
        
        # =================================================================
        # FITUR LAMA: RADAR PENCARI MODEL OTOMATIS (ANTI ERROR 404)
        # =================================================================
        model_aktif = "gemini-1.5-flash" # Model cadangan utama
        try:
            for m in client.models.list():
                if "flash" in m.name:
                    model_aktif = m.name
                    break
        except Exception:
            pass # Lanjut menggunakan cadangan jika gagal memindai
        
        # Eksekusi pemanggilan AI
        response = client.models.generate_content(
            model=model_aktif,
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        
        time.sleep(15) # Jeda untuk kestabilan koneksi API
        
        # =================================================================
        # FITUR LAMA: PEMBERSIHAN TEKS AMAN (ANTI SYNTAX ERROR)
        # =================================================================
        jawaban_teks = response.text.strip()
        jawaban_teks = jawaban_teks.replace('```json', '').replace('```', '').strip()
        
        hasil_json = json.loads(jawaban_teks)
        keputusan = hasil_json.get("keputusan", "HOLD")
        analisis_teks = hasil_json.get("analisis", "Gagal mengurai narasi AI.")
        
        # Menyusun tampilan antarmuka
        narasi_ai_saja = f"🤖 **Analisis AI (Model: {model_aktif}):**\n{analisis_teks}\n\n"
        if keputusan == "BUY": 
            narasi_ai_saja += "✅ **Rekomendasi AI:** EKSEKUSI (BUY)"
        elif keputusan == "SELL": 
            narasi_ai_saja += "❌ **Rekomendasi AI:** PELEPASAN (SELL)"
        else: 
            narasi_ai_saja += "⚖️ **Rekomendasi AI:** TAHAN (HOLD)"
            
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
        # =================================================================
        # FITUR LAMA: FALLBACK DATA JIKA KUOTA BENAR-BENAR HABIS (ERROR 429)
        # =================================================================
        if "429" in error_msg or "Quota" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            if kunci_koin in ingatan_ai:
                return narasi_awal + "⏳ **Limit Google (20 Kuota Habis):** Menampilkan data terakhir.\n\n" + ingatan_ai[kunci_koin]["narasi"], ingatan_ai[kunci_koin]["keputusan"]
            return narasi_awal + "⏳ **Limit Google:** Kuota habis, tunggu siklus besok.", "HOLD"
        
        return narasi_awal + f"💥 Error API: {error_msg}", "ERROR"
