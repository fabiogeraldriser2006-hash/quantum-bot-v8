"""
================================================================================
FILE: quant_brain.py
DESKRIPSI: Jembatan API Gemini (LLM Engine).
Otomatis membaca API Key dari layar antarmuka (app.py) melalui memori OS.
Memberikan keputusan BUY/SELL/HOLD secara instan menggunakan model gemini-pro.
================================================================================
"""

import pandas as pd
import google.generativeai as genai
import json
import os

def prediksi_ai_market(df_chart, coin, current_price, timeframe, sentimen_global):
    """
    Fungsi ini membaca API key dari memori, mengirim data grafik ke otak Gemini, 
    dan meminta analisis keputusan.
    """
    narasi = f"**🧠 Gemini Quant Engine: {coin} ({timeframe})**\n\nSpot: **Rp {current_price:,.0f}** | Sentimen: **{sentimen_global}/100**\n\n"
    
    # 1. Mengambil API Key dari memori sistem (yang diisi lewat app.py)
    api_key = os.environ.get("GEMINI_API_KEY", "")
    
    if not api_key:
        return narasi + "⚠️ **MENUNGGU AKSES:** Kunci API Gemini belum dimasukkan di menu samping (Sidebar).", "HOLD"
        
    # Konfigurasi kunci ke sistem Google
    genai.configure(api_key=api_key)
    
    if len(df_chart) < 20: 
        return narasi + "Data terlalu sedikit. Menunggu lilin grafik terbentuk...", "HOLD"
    
    try:
        # 2. Menyiapkan Data Tabel untuk Dikirim ke Gemini
        df_recent = df_chart.tail(20)[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
        df_recent['Date'] = df_recent['Date'].astype(str)
        tabel_teks = df_recent.to_string(index=False)
        
        # 3. Merakit Instruksi (Prompt Engineering)
        prompt = f"""
        Anda adalah seorang Analis Kuantitatif Kripto Profesional tingkat institusi.
        Berikut adalah riwayat pergerakan harga {coin} (timeframe {timeframe}) dalam 20 periode terakhir:
        
        {tabel_teks}
        
        Harga saat ini: Rp {current_price}
        Indeks Ketakutan/Keserakahan Global (0-100): {sentimen_global}
        
        Tugas Anda:
        Analisis data tabel di atas. Perhatikan tren kenaikan/penurunan harga penutupan (Close) dan lonjakan Volume.
        Tentukan apakah saya harus BUY, SELL, atau HOLD.
        
        Anda HARUS membalas HANYA dengan format JSON yang valid persis seperti di bawah ini, tanpa awalan atau akhiran markdown:
        {{
            "keputusan": "BUY" | "SELL" | "HOLD",
            "analisis": "Tuliskan 2-3 kalimat penjelasan tajam mengapa Anda mengambil keputusan ini berdasarkan data di atas."
        }}
        """
        
        # 4. Menghubungi Otak Gemini (PERBAIKAN: Menggunakan gemini-pro yang paling stabil)
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        
        # 5. Mengekstrak dan Membaca Jawaban JSON
        jawaban_teks = response.text.strip()
        
        # Pembersihan otomatis jika ada sisa format teks
        if jawaban_teks.startswith("```json"):
            jawaban_teks = jawaban_teks[7:-3]
        elif jawaban_teks.startswith("```"):
            jawaban_teks = jawaban_teks[3:-3]
            
        hasil_json = json.loads(jawaban_teks)
        
        keputusan = hasil_json.get("keputusan", "HOLD")
        analisis = hasil_json.get("analisis", "Gagal mengurai narasi analisis dari API.")
        
        # 6. Merakit Tampilan Layar
        narasi += f"🤖 **Analisis Gemini:**\n{analisis}\n\n"
        
        if keputusan == "BUY":
            narasi += "✅ **Rekomendasi AI:** EKSEKUSI PEMBELIAN (BUY)"
        elif keputusan == "SELL":
            narasi += "❌ **Rekomendasi AI:** PELEPASAN ASET (SELL)"
        else:
            narasi += "⚖️ **Rekomendasi AI:** TAHAN POSISI (HOLD)"
            
        return narasi, keputusan

    except json.JSONDecodeError:
        return narasi + "⚠️ Gemini merespons dengan format yang salah (Bukan JSON). AI Menahan diri.", "HOLD"
    except Exception as e:
        return narasi + f"💥 Gagal menghubungi Server Google Gemini: {e}", "ERROR"
