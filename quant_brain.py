"""
================================================================================
FILE: quant_brain.py
DESKRIPSI: Jembatan API Gemini dengan Persistent File Cache & Rate Limiter.
Menyimpan ingatan di file JSON agar tahan terhadap refresh Streamlit.
Memaksa jeda 15 detik setelah setiap panggilan untuk menjamin kuota aman.
================================================================================
"""

import pandas as pd
import google.generativeai as genai
import json
import os
import time

# ==========================================
# FUNGSI MANAJEMEN MEMORI PERMANEN (HARD DRIVE CACHE)
# ==========================================
CACHE_FILE = "ai_api_cache.json"

def baca_ingatan():
    """Membaca ingatan AI dari file fisik."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def simpan_ingatan(data):
    """Menyimpan ingatan AI ke file fisik."""
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(data, f)
    except Exception:
        pass

# ==========================================
# FUNGSI OTAK UTAMA
# ==========================================
def prediksi_ai_market(df_chart, coin, current_price, timeframe, sentimen_global):
    narasi_awal = f"**🧠 Gemini Quant Engine: {coin} ({timeframe})**\n\nSpot: **Rp {current_price:,.0f}** | Sentimen: **{sentimen_global}/100**\n\n"
    
    # ---------------------------------------------------------
    # 1. BACA FILE MEMORI (ANTI-STREAMLIT REFRESH)
    # ---------------------------------------------------------
    ingatan_ai = baca_ingatan()
    kunci_koin = f"{coin}_{timeframe}"
    waktu_sekarang = time.time()
    
    # Durasi ingatan disetel 15 menit (900 detik) untuk sangat menghemat kuota
    if kunci_koin in ingatan_ai:
        waktu_terakhir = ingatan_ai[kunci_koin]["waktu"]
        if (waktu_sekarang - waktu_terakhir) < 900:
            narasi_cache = ingatan_ai[kunci_koin]["narasi"]
            keputusan_cache = ingatan_ai[kunci_koin]["keputusan"]
            pesan_hemat = "*(Mengambil dari Arsip Memori. Menghemat Kuota API...)*\n\n"
            return narasi_awal + pesan_hemat + narasi_cache, keputusan_cache

    # ---------------------------------------------------------
    # 2. HUBUNGI GOOGLE JIKA INGATAN KOSONG / USANG
    # ---------------------------------------------------------
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return narasi_awal + "⚠️ **MENUNGGU AKSES:** Kunci API Gemini belum dimasukkan.", "HOLD"
        
    genai.configure(api_key=api_key)
    
    if len(df_chart) < 20: 
        return narasi_awal + "Data belum cukup untuk dianalisis.", "HOLD"
    
    try:
        # Menyiapkan data
        df_recent = df_chart.tail(20)[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
        df_recent['Date'] = df_recent['Date'].astype(str)
        tabel_teks = df_recent.to_string(index=False)
        
        prompt = f"""
        Anda adalah Analis Kuantitatif Kripto Profesional.
        Riwayat {coin} ({timeframe}) 20 periode terakhir:
        
        {tabel_teks}
        
        Harga: Rp {current_price} | Sentimen: {sentimen_global}
        
        Tentukan apakah harus BUY, SELL, atau HOLD berdasarkan tren harga dan volume.
        BALAS HANYA DENGAN FORMAT JSON:
        {{
            "keputusan": "BUY" | "SELL" | "HOLD",
            "analisis": "Penjelasan tajam maksimal 3 kalimat."
        }}
        """
        
        model_list = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if not model_list:
            return narasi_awal + "💥 API Key tidak memiliki akses ke model teks.", "ERROR"
            
        nama_model = next((m for m in model_list if 'flash' in m), model_list[0])
        model = genai.GenerativeModel(nama_model)
        
        # Eksekusi API
        response = model.generate_content(prompt)
        
        # ---------------------------------------------------------
        # 3. LAMPU LALU LINTAS (STRICT RATE LIMITER)
        # ---------------------------------------------------------
        # SETELAH SUKSES BERTANYA, WAJIB TIDUR 15 DETIK SEBELUM LANJUT KE KOIN BERIKUTNYA.
        # Ini menjamin aplikasi tidak akan pernah memanggil lebih dari 4 kali per menit.
        time.sleep(15)
        
        # Ekstraksi Jawaban
        jawaban_teks = response.text.strip().removeprefix("```json").removesuffix("```").strip()
        hasil_json = json.loads(jawaban_teks)
        
        keputusan = hasil_json.get("keputusan", "HOLD")
        analisis = hasil_json.get("analisis", "Gagal mengurai narasi.")
        
        narasi_ai_saja = f"🤖 **Analisis AI:**\n{analisis}\n\n"
        if keputusan == "BUY": narasi_ai_saja += "✅ **Rekomendasi AI:** EKSEKUSI (BUY)"
        elif keputusan == "SELL": narasi_ai_saja += "❌ **Rekomendasi AI:** PELEPASAN (SELL)"
        else: narasi_ai_saja += "⚖️ **Rekomendasi AI:** TAHAN (HOLD)"
            
        # ---------------------------------------------------------
        # 4. TULIS KE FILE MEMORI PERMANEN
        # ---------------------------------------------------------
        ingatan_ai[kunci_koin] = {
            "waktu": time.time(),
            "narasi": narasi_ai_saja,
            "keputusan": keputusan
        }
        simpan_ingatan(ingatan_ai)
        
        return narasi_awal + f"*(Live Data {nama_model})*\n" + narasi_ai_saja, keputusan

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "Quota" in error_msg:
            return narasi_awal + "⏳ **Google Rate Limit:** Terlalu banyak koin dipindai. Sistem akan otomatis menggunakan memori pada percobaan berikutnya.", "HOLD"
        return narasi_awal + f"💥 Error API: {e}", "ERROR"
