"""
================================================================================
FILE: quant_brain.py
DESKRIPSI: Otak AI (Gemini) menggunakan SDK terbaru 'google-genai'.
Sistem ini kebal terhadap Syntax Error dan mendukung performa tinggi.
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
    
    # Gunakan cache selama 15 menit
    if kunci_koin in ingatan_ai:
        waktu_terakhir = ingatan_ai[kunci_koin]["waktu"]
        if (waktu_sekarang - waktu_terakhir) < 900: 
            return narasi_awal + "*(Membaca dari arsip memori...)*\n\n" + ingatan_ai[kunci_koin]["narasi"], ingatan_ai[kunci_koin]["keputusan"]

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return narasi_awal + "⚠️ Kunci API Gemini belum dimasukkan.", "HOLD"
        
    # Inisialisasi Client SDK Terbaru
    client = genai.Client(api_key=api_key)
    
    if len(df_chart) < 20: 
        return narasi_awal + "Data belum cukup untuk dianalisis.", "HOLD"
    
    try:
        df_recent = df_chart.tail(20)[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
        df_recent['Date'] = df_recent['Date'].astype(str)
        tabel_teks = df_recent.to_string(index=False)
        
        prompt = f"Analisis riwayat {coin} berikut: {tabel_teks}. Harga saat ini Rp {current_price}. Berikan keputusan BUY/SELL/HOLD dalam format JSON."
        
        # Eksekusi AI (Menggunakan model stabil)
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
            }
        )
        
        time.sleep(10) # Jeda aman kuota
        
        hasil_json = json.loads(response.text)
        keputusan = hasil_json.get("keputusan", "HOLD")
        analisis_teks = hasil_json.get("analisis", "Analisis berhasil dilakukan secara teknikal.")
        
        narasi_ai_saja = f"🤖 **Analisis AI:**\n{analisis_teks}\n\n"
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
        return narasi_awal + f"💥 Kendala Sistem: {str(e)}", "ERROR"
