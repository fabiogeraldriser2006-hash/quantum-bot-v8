"""
================================================================================
FILE: quant_brain.py
DESKRIPSI: Jembatan API Gemini (LLM Engine).
Menggunakan Google Gemini API sebagai analis utama untuk membaca
data grafik dan memberikan keputusan BUY/SELL/HOLD secara instan.
================================================================================
"""

import pandas as pd
import google.generativeai as genai
import json

# ⚠️ PENTING: Masukkan API Key Gemini Anda di sini!
# Anda bisa mendapatkannya secara gratis di Google AI Studio (aistudio.google.com)
GEMINI_API_KEY = "MASUKKAN_API_KEY_GEMINI_ANDA_DI_SINI"
genai.configure(api_key=GEMINI_API_KEY)

def prediksi_ai_market(df_chart, coin, current_price, timeframe, sentimen_global):
    """
    Fungsi ini mengirim data grafik ke otak Gemini dan meminta analisis.
    """
    narasi = f"**🧠 Gemini Quant Engine: {coin} ({timeframe})**\n\nSpot: **Rp {current_price:,.0f}** | Sentimen: **{sentimen_global}/100**\n\n"
    
    if len(df_chart) < 20: 
        return narasi + "Data terlalu sedikit. Menunggu lilin grafik terbentuk...", "HOLD"
    
    try:
        # 1. Menyiapkan Data untuk Dikirim ke Gemini
        # Kita ambil 20 lilin terakhir agar saya tidak membaca terlalu banyak teks
        df_recent = df_chart.tail(20)[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
        df_recent['Date'] = df_recent['Date'].astype(str)
        tabel_teks = df_recent.to_string(index=False)
        
        # 2. Merakit Instruksi (Prompt Engineering) untuk Gemini
        prompt = f"""
        Anda adalah seorang Analis Kuantitatif Kripto Profesional tingkat institusi.
        Berikut adalah riwayat pergerakan harga {coin} (timeframe {timeframe}) dalam 20 periode terakhir:
        
        {tabel_teks}
        
        Harga saat ini: Rp {current_price}
        Indeks Ketakutan/Keserakahan Global (0-100): {sentimen_global}
        
        Tugas Anda:
        Analisis data tabel di atas. Perhatikan tren kenaikan/penurunan harga penutupan (Close) dan lonjakan Volume.
        Tentukan apakah saya harus BUY, SELL, atau HOLD.
        
        Anda HARUS membalas HANYA dengan format JSON yang valid persis seperti di bawah ini, tanpa awalan atau akhiran markdown (jangan gunakan ```json):
        {{
            "keputusan": "BUY" | "SELL" | "HOLD",
            "analisis": "Tuliskan 2-3 kalimat penjelasan tajam mengapa Anda mengambil keputusan ini berdasarkan data di atas."
        }}
        """
        
        # 3. Menghubungi Otak Gemini (Menggunakan model Flash agar eksekusi secepat kilat)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        # 4. Mengekstrak dan Membaca Jawaban JSON dari Gemini
        jawaban_teks = response.text.strip()
        
        # Pembersihan otomatis jika ada sisa format markdown
        if jawaban_teks.startswith("```json"):
            jawaban_teks = jawaban_teks[7:-3]
        elif jawaban_teks.startswith("```"):
            jawaban_teks = jawaban_teks[3:-3]
            
        hasil_json = json.loads(jawaban_teks)
        
        keputusan = hasil_json.get("keputusan", "HOLD")
        analisis = hasil_json.get("analisis", "Gagal mengurai narasi analisis dari API.")
        
        # 5. Merakit Tampilan untuk Layar Streamlit
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
