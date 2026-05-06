import pandas as pd
from google import genai
import json
import os
import time

# File untuk menyimpan hasil analisis agar hemat kuota
CACHE_FILE = "ai_api_cache.json"

def baca_ingatan():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except Exception: return {}
    return {}

def simpan_ingatan(data):
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(data, f)
    except Exception: pass

def prediksi_ai_market(df_chart, coin, current_price, timeframe, sentimen_global):
    """
    Fungsi ini mengatur kapan AI harus dipanggil.
    Target: 24 jam / 20 kuota = 1 analisis per 72 menit (4320 detik).
    """
    narasi_awal = f"**🧠 Gemini Quant Engine: {coin}**\n\nSpot: **Rp {current_price:,.0f}**\n"
    
    ingatan_ai = baca_ingatan()
    kunci_koin = f"{coin}_{timeframe}"
    waktu_sekarang = time.time()
    
    # --- LOGIKA SURVIVAL 24 JAM ---
    if kunci_koin in ingatan_ai:
        waktu_terakhir = ingatan_ai[kunci_koin]["waktu"]
        selisih = waktu_sekarang - waktu_terakhir
        
        # Jika belum lewat 72 menit, gunakan cache
        if selisih < 4320:
            menit_sisa = int((4320 - selisih) / 60)
            return narasi_awal + f"*(Mode Hemat: Update {menit_sisa} mnt lagi)*\n\n" + ingatan_ai[kunci_koin]["narasi"], ingatan_ai[kunci_koin]["keputusan"]

    # Ambil API Key dari Environment System
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key: 
        return narasi_awal + "⚠️ API Key tidak ditemukan!", "HOLD"
        
    client = genai.Client(api_key=api_key)
    
    try:
        # Menyiapkan data teknikal singkat untuk dikirim ke AI
        data_singkat = df_chart.tail(10)[['Close', 'RSI', 'MACD']].to_string()
        prompt = f"Analisis koin {coin}. Data: {data_singkat}. Harga: {current_price}. Sentimen: {sentimen_global}. Jawab JSON: keputusan (BUY/SELL/HOLD) & analisis."
        
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        
        # Jeda 10 detik untuk stabilitas koneksi
        time.sleep(10)
        
        hasil_json = json.loads(response.text)
        keputusan = hasil_json.get("keputusan", "HOLD")
        narasi_ai = hasil_json.get("analisis", "Analisis teknikal dilakukan.")
        
        # Simpan ke cache
        ingatan_ai[kunci_koin] = {
            "waktu": time.time(),
            "narasi": narasi_ai,
            "keputusan": keputusan
        }
        simpan_ingatan(ingatan_ai)
        
        return narasi_awal + "🤖 **Analisis Live:**\n" + narasi_ai, keputusan

    except Exception as e:
        if "429" in str(e):
            return narasi_awal + "⏳ Kuota penuh, mencoba mode hemat...", "HOLD"
        return narasi_awal + f"💥 Error API: {str(e)}", "ERROR"
