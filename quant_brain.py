import pandas as pd
from google import genai
import json
import os
import time

# Nama file untuk menyimpan memori analisis
CACHE_FILE = "ai_api_cache.json"

def baca_ingatan():
    """Membaca data analisis lama dari file JSON."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def simpan_ingatan(data):
    """Menyimpan data analisis baru ke file JSON."""
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(data, f)
    except Exception:
        pass

def prediksi_ai_market(df_chart, coin, current_price, timeframe, sentimen_global):
    """
    Menghitung apakah harus memanggil AI atau menggunakan cache.
    Interval: 72 menit (4320 detik) untuk 20 kuota/24 jam.
    """
    narasi_awal = f"**🧠 Gemini Quant Engine: {coin}**\n\nSpot: **Rp {current_price:,.0f}**\n"
    
    ingatan_ai = baca_ingatan()
    kunci_koin = f"{coin}_{timeframe}"
    waktu_sekarang = time.time()
    
    # 1. Cek apakah sudah waktunya update (72 menit)
    if kunci_koin in ingatan_ai:
        waktu_terakhir = ingatan_ai[kunci_koin]["waktu"]
        selisih = waktu_sekarang - waktu_terakhir
        
        # Jika belum 72 menit, gunakan cache agar kuota tidak habis
        if selisih < 4320:
            menit_sisa = int((4320 - selisih) / 60)
            return (
                narasi_awal + f"*(Hemat Kuota: Update {menit_sisa} mnt lagi)*\n\n" + 
                ingatan_ai[kunci_koin]["narasi"], 
                ingatan_ai[kunci_koin]["keputusan"]
            )

    # 2. Persiapan Koneksi AI
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return narasi_awal + "⚠️ API Key Gemini belum diatur di sistem.", "HOLD"
        
    client = genai.Client(api_key=api_key)
    
    try:
        # 3. Kirim data ke Gemini
        # Mengambil 10 baris terakhir data teknikal
        data_teknikal = df_chart.tail(10)[['Close', 'RSI', 'MACD', 'ATR']].to_string()
        
        prompt = (
            f"Analisis koin {coin} ({timeframe}). Data: {data_teknikal}. "
            f"Harga saat ini: {current_price}. Sentimen: {sentimen_global}. "
            "Berikan keputusan BUY, SELL, atau HOLD. "
            "Berikan jawaban dalam format JSON: {'keputusan': '...', 'analisis': '...'}"
        )
        
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        
        # Jeda sebentar untuk stabilitas
        time.sleep(5)
        
        hasil_json = json.loads(response.text)
        keputusan = hasil_json.get("keputusan", "HOLD")
        narasi_ai = hasil_json.get("analisis", "Analisis teknikal selesai.")
        
        # 4. Simpan ke Ingatan
        ingatan_ai[kunci_koin] = {
            "waktu": waktu_sekarang,
            "narasi": narasi_ai,
            "keputusan": keputusan
        }
        simpan_ingatan(ingatan_ai)
        
        return narasi_awal + "🤖 **Analisis Live:**\n" + narasi_ai, keputusan

    except Exception as e:
        # Jika kuota habis (Error 429), otomatis gunakan cache terakhir
        if "429" in str(e) and kunci_koin in ingatan_ai:
            return narasi_awal + "⏳ Kuota penuh, menggunakan data cache...\n\n" + ingatan_ai[kunci_koin]["narasi"], ingatan_ai[kunci_koin]["keputusan"]
        return narasi_awal + f"💥 Kendala API: {str(e)}", "ERROR"
