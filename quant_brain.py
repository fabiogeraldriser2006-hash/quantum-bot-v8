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
            return narasi_awal + "*(Membaca memori...)*\n\n" + ingatan_ai[kunci_koin]["narasi"], ingatan_ai[kunci_koin]["keputusan"]

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return narasi_awal + "⚠️ Kunci API Gemini belum dimasukkan.", "HOLD"
        
    genai.configure(api_key=api_key)
    
    if len(df_chart) < 20: 
        return narasi_awal + "Data belum cukup...", "HOLD"
    
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
            "analisis": "Berikan alasan singkat."
        }}
        """
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        time.sleep(15) 
        
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
        analisis_teks = hasil_json.get("analisis", "Analisis tidak tersedia.")
        
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
        
        return narasi_awal + narasi_ai_saja, keputusan

    except Exception as e:
        if "429" in str(e) or "Quota" in str(e):
            return narasi_awal + "⏳ **Limit Google:** Kuota penuh, tunggu sebentar.", "HOLD"
        return narasi_awal + f"💥 Error API: {str(e)}", "ERROR"
