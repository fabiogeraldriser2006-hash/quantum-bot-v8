"""
================================================================================
FILE: quant_brain.py
DESKRIPSI: Jembatan API Gemini (LLM Engine) dengan Auto-Discovery.
Otomatis menarik daftar model yang tersedia dari server Google 
agar tidak pernah mengalami error 404 (Model Not Found) akibat 
perubahan nama versi API.
================================================================================
"""

import pandas as pd
import google.generativeai as genai
import json
import os

def prediksi_ai_market(df_chart, coin, current_price, timeframe, sentimen_global):
    narasi = f"**🧠 Gemini Quant Engine: {coin} ({timeframe})**\n\nSpot: **Rp {current_price:,.0f}** | Sentimen: **{sentimen_global}/100**\n\n"
    
    # Memeriksa Kunci API dari antarmuka
    api_key = os.environ.get("GEMINI_API_KEY", "")
    
    if not api_key:
        return narasi + "⚠️ **MENUNGGU AKSES:** Kunci API Gemini belum dimasukkan di menu samping (Sidebar).", "HOLD"
        
    genai.configure(api_key=api_key)
    
    if len(df_chart) < 20: 
        return narasi + "Data terlalu sedikit. Menunggu lilin grafik terbentuk...", "HOLD"
    
    try:
        # Menyiapkan Data Tabel untuk dianalisis
        df_recent = df_chart.tail(20)[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
        df_recent['Date'] = df_recent['Date'].astype(str)
        tabel_teks = df_recent.to_string(index=False)
        
        # Merakit Instruksi (Prompt)
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
        # FITUR BARU: AUTO-DISCOVERY MODEL (RADAR PINTAR)
        # ==========================================
        # Menarik daftar nama model resmi langsung dari server Google
        model_list = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        if not model_list:
            return narasi + "💥 Kunci API Anda tidak memiliki akses ke model AI pembuat teks.", "ERROR"
        
        # Otomatis memilih model: Prioritaskan 'flash' atau 'pro', jika tidak ada, ambil yang pertama
        nama_model_terpilih = model_list[0] 
        for m in model_list:
            if '1.5-flash' in m:
                nama_model_terpilih = m
                break
            elif '1.5-pro' in m:
                nama_model_terpilih = m
                
        narasi += f"*(Terhubung dengan mesin dinamis: {nama_model_terpilih})*\n"
        
        # Memanggil mesin AI yang pasti valid dan ada di daftar
        model = genai.GenerativeModel(nama_model_terpilih)
        response = model.generate_content(prompt)
        
        # Ekstraksi dan pembersihan JSON
        jawaban_teks = response.text.strip()
        if jawaban_teks.startswith("```json"):
            jawaban_teks = jawaban_teks[7:-3]
        elif jawaban_teks.startswith("```"):
            jawaban_teks = jawaban_teks[3:-3]
            
        hasil_json = json.loads(jawaban_teks)
        keputusan = hasil_json.get("keputusan", "HOLD")
        analisis = hasil_json.get("analisis", "Gagal mengurai narasi analisis dari teks.")
        
        narasi += f"🤖 **Analisis AI:**\n{analisis}\n\n"
        
        if keputusan == "BUY": narasi += "✅ **Rekomendasi AI:** EKSEKUSI PEMBELIAN (BUY)"
        elif keputusan == "SELL": narasi += "❌ **Rekomendasi AI:** PELEPASAN ASET (SELL)"
        else: narasi += "⚖️ **Rekomendasi AI:** TAHAN POSISI (HOLD)"
            
        return narasi, keputusan

    except json.JSONDecodeError:
        return narasi + "⚠️ Respons API gagal diurai menjadi JSON. Pastikan prompt AI tepat.", "HOLD"
    except Exception as e:
        return narasi + f"💥 Kesalahan Koneksi API: {e}", "ERROR"
