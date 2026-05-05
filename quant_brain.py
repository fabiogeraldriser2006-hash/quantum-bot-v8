import pandas as pd
import google.generativeai as genai
import json
import os
import time

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

def prediksi_ai_market(df_chart, coin, current_price, timeframe, sentimen_global):
    narasi_awal = f"**🧠 Gemini Quant Engine: {coin} ({timeframe})**\n\nSpot: **Rp {current_price:,.0f}** | Sentimen: **{sentimen_global}/100**\n\n"
    
    ingatan_ai = baca_ingatan()
    kunci_koin = f"{coin}_{timeframe}"
    waktu_sekarang = time.time()
    
    if kunci_koin in ingatan_ai:
        waktu_terakhir = ingatan_ai[kunci_koin]["waktu"]
        if (waktu_sekarang - waktu_terakhir) < 900: 
            return narasi_awal + "*(Membaca dari arsip memori...)*\n\n" + ingatan_ai[kunci_koin]["narasi"], ingatan_ai[kunci_koin]["keputusan"]

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return narasi_awal + "⚠️ Kunci API Gemini belum dimasukkan.", "HOLD"
        
    genai.configure(api_key=api_key)
    
    if len(df_chart) < 20: 
        return narasi_awal + "Data belum cukup untuk dianalisis.", "HOLD"
    
    try:
        df_recent = df_chart.tail(20)[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
        df_recent['Date'] = df_recent['Date'].astype(str)
        tabel_teks = df_recent.to_string(index=False)
        
        prompt = f"""
        Analisis data harga kripto ini (20 periode terakhir):
        {tabel_teks}
        Harga: Rp {current_price} | Sentimen: {sentimen_global}
        Tentukan BUY, SELL, atau HOLD.
        BALAS HANYA DENGAN FORMAT JSON:
        {{
            "keputusan": "BUY" | "SELL" | "HOLD",
            "analisis": "Berikan alasan maksimal 3 kalimat."
        }}
        """
        
        # --- FITUR RADAR PINTAR (ANTI ERROR 404) ---
        model_list = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if not model_list:
            return narasi_awal + "💥 Tidak ada akses ke model AI di kunci API Anda.", "ERROR"
            
        # Prioritaskan mencari nama model yang mengandung kata 'flash'
        nama_model = model_list[0] # Cadangan jika tidak ada 'flash'
        for m in model_list:
            if 'flash' in m:
                nama_model = m
                break
                
        model = genai.GenerativeModel(nama_model)
        
        # Eksekusi API
        response = model.generate_content(prompt)
        
        # --- FITUR REM OTOMATIS (ANTI ERROR 429 KUOTA HABIS) ---
        time.sleep(15) 
        
        # Pembersihan Teks Aman (Anti Syntax Error)
        jawaban_teks = response.text.strip()
        jawaban_teks = jawaban_teks.replace('```json', '').replace('
```', '').strip()
            
        hasil_json = json.loads(jawaban_teks)
        keputusan = hasil_json.get("keputusan", "HOLD")
        analisis_teks = hasil_json.get("analisis", "Gagal mengurai narasi AI.")
        
        narasi_ai_saja = f"🤖 **Analisis AI:**\n{analisis_teks}\n\n"
        if keputusan == "BUY": 
            narasi_ai_saja += "✅ **Rekomendasi AI:** EKSEKUSI (BUY)"
        elif keputusan == "SELL": 
            narasi_ai_saja += "❌ **Rekomendasi AI:** PELEPASAN (SELL)"
        else: 
            narasi_ai_saja += "⚖️ **Rekomendasi AI:** TAHAN (HOLD)"
            
        ingatan_ai[kunci_koin] = {
            "waktu": time.time(),
            "narasi": narasi_ai_saja,
            "keputusan": keputusan
        }
        simpan_ingatan(ingatan_ai)
        
        return narasi_awal + f"*(Live Data: {nama_model})*\n" + narasi_ai_saja, keputusan

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "Quota" in error_msg:
            return narasi_awal + "⏳ **Limit Google:** Kuota penuh, tunggu sebentar.", "HOLD"
        return narasi_awal + f"💥 Error API: {error_msg}", "ERROR"
