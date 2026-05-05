"""
================================================================================
FILE: quant_brain.py
DESKRIPSI: Otak AI Gemini dengan Fitur Auto-Discovery Model.
Mencegah Error 404 dengan mencari model yang aktif secara otomatis.
================================================================================
"""
import pandas as pd
from google import genai
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
        
    client = genai.Client(api_key=api_key)
    
    try:
        # --- FITUR ANTI-404: MENCARI MODEL YANG TERSEDIA ---
        model_aktif = "gemini-1.5-flash" # Default
        try:
            # Mengambil daftar model dan mencari yang berstatus 'flash'
            for m in client.models.list():
                if "flash" in m.name:
                    model_aktif = m.name
                    break
        except:
            pass # Jika gagal list, gunakan default
            
        df_recent = df_chart.tail(20)[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
        df_recent['Date'] = df_recent['Date'].astype(str)
        tabel_teks = df_recent.to_string(index=False)
        
        prompt = f"Analisis data harga {coin}: {tabel_teks}. Harga saat ini Rp {current_price}. Berikan keputusan BUY/SELL/HOLD dalam format JSON."
        
        response = client.models.generate_content(
            model=model_aktif,
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        
        time.sleep(15) # Jeda 15 detik agar aman dari limit gratis
        
        hasil_json = json.loads(response.text)
        keputusan = hasil_json.get("keputusan", "HOLD")
        analisis_teks = hasil_json.get("analisis", "Analisis teknikal selesai.")
        
        narasi_ai_saja = f"*(Menggunakan model: {model_aktif})*\n\n🤖 **Analisis AI:**\n{analisis_teks}\n\n"
        if keputusan == "BUY": narasi_ai_saja += "✅ **Rekomendasi AI:** EKSEKUSI (BUY)"
        elif keputusan == "SELL": narasi_ai_saja += "❌ **Rekomendasi AI:** PELEPASAN (SELL)"
        else: narasi_ai_saja += "⚖️ **Rekomendasi AI:** TAHAN (HOLD)"
            
        ingatan_ai[kunci_koin] = {
            "waktu": time.time(),
            "narasi": narasi_ai_saja,
            "keputusan": keputusan
        }
        simpan_ingatan(ingatan_ai)
        
        return narasi_awal + narasi_ai_saja, keputusan

    except Exception as e:
        return narasi_awal + f"💥 Kendala API: {str(e)}", "ERROR"
