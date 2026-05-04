"""
================================================================================
FILE: quant_brain.py
DESKRIPSI: Jembatan API Gemini (LLM Engine).
Dilengkapi dengan sistem Fallback Model. Jika mesin utama gagal, 
sistem akan otomatis mencoba mesin cadangan agar tidak crash.
================================================================================
"""

import pandas as pd
import google.generativeai as genai
import json
import os

def prediksi_ai_market(df_chart, coin, current_price, timeframe, sentimen_global):
    narasi = f"**🧠 Gemini Quant Engine: {coin} ({timeframe})**\n\nSpot: **Rp {current_price:,.0f}** | Sentimen: **{sentimen_global}/100**\n\n"
    
    api_key = os.environ.get("GEMINI_API_KEY", "")
    
    if not api_key:
        return narasi + "⚠️ **MENUNGGU AKSES:** Kunci API Gemini belum dimasukkan di menu samping (Sidebar).", "HOLD"
        
    genai.configure(api_key=api_key)
    
    if len(df_chart) < 20: 
        return narasi + "Data terlalu sedikit. Menunggu lilin grafik terbentuk...", "HOLD"
    
    try:
        # Menyiapkan Data Tabel
        df_recent = df_chart.tail(20)[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
        df_recent['Date'] = df_recent['Date'].astype(str)
        tabel_teks = df_recent.to_string(index=False)
        
        # Merakit Instruksi
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
        
        # ==========================================
        # SISTEM FALLBACK (ANTI-CRASH)
        # ==========================================
        try:
            # Percobaan 1: Menggunakan mesin tercepat dan terbaru
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
        except Exception as e_flash:
            try:
                # Percobaan 2: Jika gagal, gunakan mesin legacy yang paling universal
                narasi += "*(Pindah ke mesin cadangan...)*\n"
                model = genai.GenerativeModel('gemini-pro')
                response = model.generate_content(prompt)
            except Exception as e_pro:
                return narasi + f"💥 Gagal menghubungi kedua Server API: {e_pro}", "ERROR"
        
        # Ekstraksi JSON
        jawaban_teks = response.text.strip()
        if jawaban_teks.startswith("```json"):
            jawaban_teks = jawaban_teks[7:-3]
        elif jawaban_teks.startswith("```"):
            jawaban_teks = jawaban_teks[3:-3]
            
        hasil_json = json.loads(jawaban_teks)
        keputusan = hasil_json.get("keputusan", "HOLD")
        analisis = hasil_json.get("analisis", "Gagal mengurai narasi analisis.")
        
        narasi += f"🤖 **Analisis AI:**\n{analisis}\n\n"
        
        if keputusan == "BUY": narasi += "✅ **Rekomendasi AI:** EKSEKUSI PEMBELIAN (BUY)"
        elif keputusan == "SELL": narasi += "❌ **Rekomendasi AI:** PELEPASAN ASET (SELL)"
        else: narasi += "⚖️ **Rekomendasi AI:** TAHAN POSISI (HOLD)"
            
        return narasi, keputusan

    except json.JSONDecodeError:
        return narasi + "⚠️ Respons API gagal diurai. AI Menahan diri.", "HOLD"
    except Exception as e:
        return narasi + f"💥 Kesalahan Sistem: {e}", "ERROR"
