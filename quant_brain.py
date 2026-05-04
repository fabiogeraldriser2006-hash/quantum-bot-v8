"""
================================================================================
FILE: quant_brain.py
DESKRIPSI: Jembatan API Gemini (LLM Engine) dengan Cache System.
Menyimpan analisis terakhir selama 5 menit untuk menghemat kuota API 
Google secara drastis (mencegah Error 429 Quota Exceeded).
================================================================================
"""

import pandas as pd
import google.generativeai as genai
import json
import os
import time

# ==========================================
# LACI MEMORI GLOBAL (CACHE SYSTEM)
# Menyimpan jawaban API agar tidak perlu bertanya terus-menerus
# ==========================================
AI_CACHE = {}

def prediksi_ai_market(df_chart, coin, current_price, timeframe, sentimen_global):
    global AI_CACHE
    
    narasi_awal = f"**🧠 Gemini Quant Engine: {coin} ({timeframe})**\n\nSpot: **Rp {current_price:,.0f}** | Sentimen: **{sentimen_global}/100**\n\n"
    
    # ---------------------------------------------------------
    # 1. CEK MEMORI JANGKA PENDEK (CACHE)
    # ---------------------------------------------------------
    cache_key = f"{coin}_{timeframe}"
    waktu_sekarang = time.time()
    
    # Jika ada catatan di memori, dan usianya belum 5 menit (300 detik)
    if cache_key in AI_CACHE:
        waktu_terakhir = AI_CACHE[cache_key]["waktu"]
        if (waktu_sekarang - waktu_terakhir) < 300:
            narasi_cache = AI_CACHE[cache_key]["narasi"]
            keputusan_cache = AI_CACHE[cache_key]["keputusan"]
            pesan_hemat = "*(Menggunakan analisis memori untuk menghemat kuota API...)*\n\n"
            return narasi_awal + pesan_hemat + narasi_cache, keputusan_cache

    # ---------------------------------------------------------
    # 2. JIKA MEMORI KOSONG/USANG, HUBUNGI SERVER GOOGLE
    # ---------------------------------------------------------
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return narasi_awal + "⚠️ **MENUNGGU AKSES:** Kunci API Gemini belum dimasukkan di menu samping.", "HOLD"
        
    genai.configure(api_key=api_key)
    
    if len(df_chart) < 20: 
        return narasi_awal + "Data terlalu sedikit. Menunggu lilin grafik terbentuk...", "HOLD"
    
    try:
        df_recent = df_chart.tail(20)[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
        df_recent['Date'] = df_recent['Date'].astype(str)
        tabel_teks = df_recent.to_string(index=False)
        
        prompt = f"""
        Anda adalah Analis Kuantitatif Kripto Profesional.
        Berikut adalah riwayat harga {coin} (timeframe {timeframe}) 20 periode terakhir:
        
        {tabel_teks}
        
        Harga saat ini: Rp {current_price}
        Indeks Global: {sentimen_global}
        
        Tugas: Analisis tren harga dan volume di atas. Tentukan apakah harus BUY, SELL, atau HOLD.
        Anda HARUS membalas HANYA dengan format JSON yang valid persis seperti di bawah ini:
        {{
            "keputusan": "BUY" | "SELL" | "HOLD",
            "analisis": "Berikan penjelasan tajam maksimal 3 kalimat."
        }}
        """
        
        model_list = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        if not model_list:
            return narasi_awal + "💥 Kunci API Anda tidak memiliki akses ke model AI pembuat teks.", "ERROR"
        
        nama_model_terpilih = model_list[0] 
        for m in model_list:
            if 'flash' in m:
                nama_model_terpilih = m
                break
            elif 'pro' in m:
                nama_model_terpilih = m
                
        narasi_proses = f"*(Terhubung dengan mesin dinamis: {nama_model_terpilih})*\n"
        model = genai.GenerativeModel(nama_model_terpilih)
        
        # ---------------------------------------------------------
        # 3. ANTI-RATE LIMIT (RETRY LOGIC)
        # ---------------------------------------------------------
        max_percobaan = 3
        response = None
        
        for percobaan in range(max_percobaan):
            try:
                response = model.generate_content(prompt)
                break 
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "Quota" in error_msg:
                    if percobaan < max_percobaan - 1:
                        time.sleep(20) 
                    else:
                        return narasi_awal + narasi_proses + "⏳ **Sistem Mendinginkan Diri:** Kuota API gratis menipis. Harap perlambat Kecepatan Pindai Bot.", "HOLD"
                else:
                    raise e
        
        if response:
            jawaban_teks = response.text.strip()
            if jawaban_teks.startswith("```json"):
                jawaban_teks = jawaban_teks[7:-3]
            elif jawaban_teks.startswith("```"):
                jawaban_teks = jawaban_teks[3:-3]
                
            hasil_json = json.loads(jawaban_teks)
            keputusan = hasil_json.get("keputusan", "HOLD")
            analisis = hasil_json.get("analisis", "Gagal mengurai narasi analisis dari teks.")
            
            # Merakit narasi khusus dari AI
            narasi_ai_saja = f"🤖 **Analisis AI:**\n{analisis}\n\n"
            if keputusan == "BUY": narasi_ai_saja += "✅ **Rekomendasi AI:** EKSEKUSI PEMBELIAN (BUY)"
            elif keputusan == "SELL": narasi_ai_saja += "❌ **Rekomendasi AI:** PELEPASAN ASET (SELL)"
            else: narasi_ai_saja += "⚖️ **Rekomendasi AI:** TAHAN POSISI (HOLD)"
                
            # ---------------------------------------------------------
            # 4. SIMPAN KE LACI MEMORI
            # ---------------------------------------------------------
            AI_CACHE[cache_key] = {
                "waktu": waktu_sekarang,
                "narasi": narasi_ai_saja,
                "keputusan": keputusan
            }
            
            return narasi_awal + narasi_proses + narasi_ai_saja, keputusan
        else:
            return narasi_awal + "⚠️ Respons API kosong.", "HOLD"

    except json.JSONDecodeError:
        return narasi_awal + "⚠️ Respons API gagal diurai menjadi JSON. AI menahan diri.", "HOLD"
    except Exception as e:
        return narasi_awal + f"💥 Kesalahan Koneksi API: {e}", "ERROR"
