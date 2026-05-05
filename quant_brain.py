"""
================================================================================
FILE: quant_brain.py
DESKRIPSI: Jembatan API Gemini dengan Persistent Cache & Auto-Discovery.
Kode ini telah disterilkan dari Syntax Error. Menggunakan logika dasar Python
untuk memastikan kompatibilitas penuh dengan server Streamlit.
================================================================================
"""
import pandas as pd
import google.generativeai as genai
import json
import os
import time

# ==========================================
# LACI MEMORI PERMANEN (HARD DRIVE CACHE)
# ==========================================
CACHE_FILE = "ai_api_cache.json"

def baca_ingatan():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def simpan_ingatan(data):
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(data, f)
    except Exception:
        pass

# ==========================================
# OTAK AI UTAMA
# ==========================================
def prediksi_ai_market(df_chart, coin, current_price, timeframe, sentimen_global):
    narasi_awal = f"**🧠 Gemini Quant Engine: {coin} ({timeframe})**\n\nSpot: **Rp {current_price:,.0f}** | Sentimen: **{sentimen_global}/100**\n\n"
    
    # 1. BACA FILE MEMORI
    ingatan_ai = baca_ingatan()
    kunci_koin = f"{coin}_{timeframe}"
    waktu_sekarang = time.time()
    
    # Hemat kuota dengan menggunakan memori selama 15 menit (900 detik)
    if kunci_koin in ingatan_ai:
        waktu_terakhir = ingatan_ai[kunci_koin]["waktu"]
        if (waktu_sekarang - waktu_terakhir) < 900: 
            return narasi_awal + "*(Menggunakan data memori untuk hemat kuota...)*\n\n" + ingatan_ai[kunci_koin]["narasi"], ingatan_ai[kunci_koin]["keputusan"]

    # 2. PERSIAPAN KONEKSI GOOGLE
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return narasi_awal + "⚠️ Kunci API Gemini belum dimasukkan.", "HOLD"
        
    genai.configure(api_key=api_key)
    if len(df_chart) < 20: 
        return narasi_awal + "Data belum cukup terbentuk...", "HOLD"
    
    try:
        df_recent = df_chart.tail(20)[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
        df_recent['Date'] = df_recent['Date'].astype(str)
        tabel_teks = df_recent.to_string(index=False)
        
        prompt = f"""
        Anda adalah Analis Kuantitatif Kripto Profesional. Riwayat {coin} 20 periode terakhir:
        {tabel_teks}
        
        Harga: Rp {current_price} | Sentimen: {sentimen_global}
        Tentukan BUY, SELL, atau HOLD berdasarkan data di atas.
        BALAS HANYA DENGAN FORMAT JSON:
        {{
            "keputusan": "BUY" | "SELL" | "HOLD",
            "analisis": "Penjelasan tajam maksimal 3 kalimat."
        }}
        """
        
        # ---------------------------------------------------------
        # FITUR RADAR PINTAR (AUTO-DISCOVERY)
        # ---------------------------------------------------------
        model_list = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if not model_list:
            return narasi_awal + "💥 Tidak ada akses ke model AI di kunci API Anda.", "ERROR"
            
        # Pilih otomatis: prioritaskan 'flash', jika tidak ada cari 'pro'
        nama_model = model_list[0]
        for m in model_list:
            if 'flash' in m:
                nama_model = m
                break
            elif 'pro' in m:
                nama_model = m
                
        model = genai.GenerativeModel(nama_model)
        
        # Eksekusi API
        response = model.generate_content(prompt)
        
        # ---------------------------------------------------------
        # REM OTOMATIS: WAJIB TIDUR 15 DETIK
        # ---------------------------------------------------------
        time.sleep(15) 
        
        # Ekstraksi Jawaban (Pembersihan Teks)
        jawaban_teks = response.text.strip()
        if jawaban_teks.startswith("```json"):
            jawaban_teks = jawaban_teks[7:]
        if jawaban_teks.startswith("
```"):
            jawaban_teks = jawaban_teks[3:]
        if jawaban_teks.endswith("```"):
            jawaban_teks = jawaban_teks[:-3]
            
        jawaban_teks = jawaban_teks.strip()
        
        hasil_json = json.loads(jawaban_teks)
        keputusan = hasil_json.get("keputusan", "HOLD")
        
        narasi_ai_saja = f"🤖 **Analisis AI:**\n{hasil_json.get('analisis', 'Gagal urai narasi.')}\n\n"
        if keputusan == "BUY": 
            narasi_ai_saja += "✅ **Rekomendasi AI:** EKSEKUSI (BUY)"
        elif keputusan == "SELL": 
            narasi_ai_saja += "❌ **Rekomendasi AI:** PELEPASAN (SELL)"
        else: 
            narasi_ai_saja += "⚖️ **Rekomendasi AI:** TAHAN (HOLD)"
            
        # Simpan ke File Memori Permanen
        ingatan_ai[kunci_koin] = {"waktu": time.time(), "narasi": narasi_ai_saja, "keputusan": keputusan}
        simpan_ingatan(ingatan_ai)
        
        return narasi_awal + f"*(Live Data: {nama_model})*\n" + narasi_ai_saja, keputusan

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "Quota" in error_msg:
            return narasi_awal + "⏳ **Google Rate Limit:** Bot rehat sejenak karena kuota penuh.", "HOLD"
        return narasi_awal + f"💥 Error API: {e}", "ERROR"
