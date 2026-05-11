"""
================================================================================
FILE: quant_brain.py
DESKRIPSI: Otak AI Fleksibel (Multi-Brain Engine).
Menganalisis Tren Makro (4H) dan Presisi Mikro (15m) secara bersamaan.
Mendukung perpindahan mesin AI (Gemini, OpenAI, Anthropic, Groq) secara Live.
================================================================================
"""
import pandas as pd
from google import genai
import json
import os
import time
import requests # Digunakan untuk menembak API AI selain Gemini

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
# FUNGSI UTAMA AI (SEKARANG MENERIMA PARAMETER 'ai_choice')
# ==============================================================================
def prediksi_ai_market(df_macro, df_micro, coin, current_price, sentimen_global, ai_choice="Gemini"):
    """
    Fungsi utama AI. 
    Mengevaluasi tren 4 Jam (Macro) dan momentum 15 Menit (Micro) menggunakan Otak AI pilihan.
    """
    narasi_awal = f"**🧠 Quant Engine ({ai_choice} Multi-TF): {coin}**\n\nSpot: **Rp {current_price:,.0f}** | Sentimen: **{sentimen_global}/100**\n\n"
    
    ingatan_ai = baca_ingatan()
    # Kunci cache digabungkan dengan nama AI agar arsip tidak tertukar
    kunci_koin = f"{coin}_{ai_choice}_MultiTF" 
    waktu_sekarang = time.time()
    
    # --- MANAJEMEN KUOTA (Sistem Jeda 72 Menit Tetap Dipertahankan) ---
    if kunci_koin in ingatan_ai:
        waktu_terakhir = ingatan_ai[kunci_koin]["waktu"]
        selisih_waktu = waktu_sekarang - waktu_terakhir
        
        if selisih_waktu < 4320:
            sisa_menit = int((4320 - selisih_waktu) / 60)
            return narasi_awal + f"*(Arsip Memori {ai_choice}: Diperbarui {sisa_menit} menit lagi)*\n\n" + ingatan_ai[kunci_koin]["narasi"], ingatan_ai[kunci_koin]["keputusan"]

    # Pastikan data grafik cukup sebelum memanggil API apapun
    if len(df_macro) < 10 or len(df_micro) < 20: 
        return narasi_awal + "Data grafik belum lengkap (Tunggu 1-2 menit lagi).", "HOLD"
    
    try:
        # 1. Siapkan Tabel Makro (4 Jam)
        df_macro_recent = df_macro.tail(5)[['Date', 'Close', 'MACD', 'RSI']].copy()
        df_macro_recent['Date'] = df_macro_recent['Date'].astype(str)
        tabel_makro = df_macro_recent.to_string(index=False)
        
        # 2. Siapkan Tabel Mikro (15 Menit)
        df_micro_recent = df_micro.tail(15)[['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'ATR']].copy()
        df_micro_recent['Date'] = df_micro_recent['Date'].astype(str)
        tabel_mikro = df_micro_recent.to_string(index=False)
        
        # 3. Prompt Utama Terstandarisasi untuk SEMUA AI
        prompt_system = "Anda adalah AI Quant Trader. Analisis data market dan kembalikan HANYA format JSON murni tanpa markdown, tanpa penjelasan luar."
        prompt_user = f"""
        Lakukan 'Top-Down Analysis' pada aset kripto {coin}.
        Harga Spot Saat Ini: Rp {current_price}
        Sentimen Pasar Makro (Fear & Greed Index): {sentimen_global} (0 = Ketakutan Ekstrem, 100 = Keserakahan Ekstrem).

        DATA MAKRO (Grafik 4 Jam) - Tentukan Tren Utama:
        {tabel_makro}
        
        DATA MIKRO (Grafik 15 Menit) - Tentukan Presisi Titik Masuk/Keluar:
        {tabel_mikro}
        
        TUGAS ANDA:
        1. Baca tren utama dari data 4 Jam (Apakah Bullish atau Bearish?).
        2. Tentukan keputusan di data 15 Menit HANYA SEARAH dengan tren 4 Jam (Jika 4H Bullish, cari peluang BUY).
        3. Tentukan keputusan akhir: BUY, SELL, atau HOLD.
        
        BALAS HANYA DENGAN FORMAT JSON INI:
        {{
            "keputusan": "BUY" | "SELL" | "HOLD",
            "analisis": "Berikan 2 kalimat alasan logis."
        }}
        """
        
        jawaban_teks = ""
        model_aktif = ai_choice

        # =================================================================
        # ROUTER / SAKELAR AI (PILIH OTAK BERDASARKAN INPUT)
        # =================================================================
        if ai_choice == "Gemini":
            api_key = os.environ.get("GEMINI_API_KEY", "")
            if not api_key: return narasi_awal + "⚠️ Kunci API Gemini belum dimasukkan.", "HOLD"
            
            client = genai.Client(api_key=api_key)
            model_aktif = "gemini-1.5-flash" 
            try:
                for m in client.models.list():
                    if "flash" in m.name:
                        model_aktif = m.name
                        break
            except Exception: pass 
            
            response = client.models.generate_content(
                model=model_aktif,
                contents=prompt_user,
                config={'response_mime_type': 'application/json'}
            )
            jawaban_teks = response.text
            
        elif ai_choice == "OpenAI (ChatGPT)":
            api_key = os.environ.get("OPENAI_API_KEY", "")
            if not api_key: return narasi_awal + "⚠️ Kunci API OpenAI belum dimasukkan.", "HOLD"
            
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": prompt_system},
                    {"role": "user", "content": prompt_user}
                ],
                "response_format": { "type": "json_object" }
            }
            res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload).json()
            jawaban_teks = res['choices'][0]['message']['content']

        elif ai_choice == "Anthropic (Claude)":
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if not api_key: return narasi_awal + "⚠️ Kunci API Anthropic belum dimasukkan.", "HOLD"
            
            headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
            payload = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 500,
                "system": prompt_system,
                "messages": [{"role": "user", "content": prompt_user}]
            }
            res = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload).json()
            jawaban_teks = res['content'][0]['text']

        elif ai_choice == "Groq (Llama-3)":
            api_key = os.environ.get("GROQ_API_KEY", "")
            if not api_key: return narasi_awal + "⚠️ Kunci API Groq belum dimasukkan.", "HOLD"
            
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "llama3-70b-8192",
                "messages": [
                    {"role": "system", "content": prompt_system},
                    {"role": "user", "content": prompt_user}
                ],
                "response_format": { "type": "json_object" }
            }
            res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload).json()
            jawaban_teks = res['choices'][0]['message']['content']
        else:
            return narasi_awal + f"⚠️ Model {ai_choice} tidak dikenali.", "HOLD"

        # --- Jeda Wajib & Pembersihan Teks Aman ---
        time.sleep(5) 
        
        jawaban_teks = jawaban_teks.strip()
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
        if "429" in error_msg or "Quota" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            if kunci_koin in ingatan_ai:
                return narasi_awal + f"⏳ **Limit {ai_choice} Habis:** Menampilkan data terakhir.\n\n" + ingatan_ai[kunci_koin]["narasi"], ingatan_ai[kunci_koin]["keputusan"]
            return narasi_awal + f"⏳ **Limit {ai_choice}:** Kuota habis, tunggu siklus besok atau ganti AI.", "HOLD"
        
        return narasi_awal + f"💥 Error API {ai_choice}: {error_msg}", "ERROR"
