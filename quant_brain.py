"""
================================================================================
FILE: quant_brain.py
DESKRIPSI: Jembatan API Gemini (LLM Engine) dengan Auto-Discovery & Anti-Rate Limit.
Dilengkapi sistem 'Exponential Backoff' untuk mencegah Error 429 
(Quota Exceeded) saat menggunakan API versi gratis.
================================================================================
"""

import pandas as pd
import google.generativeai as genai
import json
import os
import time  # Modul waktu untuk menidurkan bot sementara

def prediksi_ai_market(df_chart, coin, current_price, timeframe, sentimen_global):
    narasi = f"**🧠 Gemini Quant Engine: {coin} ({timeframe})**\n\nSpot: **Rp {current_price:,.0f}** | Sentimen: **{sentimen_global}/100**\n\n"
    
    api_key = os.environ.get("GEMINI_API_KEY", "")
    
    if not api_key:
        return narasi + "⚠️ **MENUNGGU AKSES:** Kunci API Gemini belum dimasukkan di menu samping.", "HOLD"
        
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
        
        # Fitur Auto-Discovery Model
        model_list = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        if not model_list:
            return narasi + "💥 Kunci API Anda tidak memiliki akses ke model AI pembuat teks.", "ERROR"
        
        nama_model_terpilih = model_list[0] 
        for m in model_list:
            if 'flash' in m:
                nama_model_terpilih = m
                break
            elif 'pro' in m:
                nama_model_terpilih = m
                
        narasi += f"*(Terhubung dengan mesin dinamis: {nama_model_terpilih})*\n"
        model = genai.GenerativeModel(nama_model_terpilih)
        
        # ==========================================
        # FITUR BARU: ANTI-RATE LIMIT (RETRY LOGIC)
        # ==========================================
        max_percobaan = 3
        response = None
        
        for percobaan in range(max_percobaan):
            try:
                # Mencoba memanggil Google API
                response = model.generate_content(prompt)
                break  # Jika sukses, keluar dari loop percobaan
                
            except Exception as e:
                error_msg = str(e)
                # Jika error adalah 429 Quota Exceeded
                if "429" in error_msg or "Quota" in error_msg:
                    if percobaan < max_percobaan - 1:
                        # Tidurkan mesin selama 20 detik agar server Google dingin
                        time.sleep(20) 
                    else:
                        # Jika sudah 3 kali mencoba dan masih gagal
                        return narasi + "⏳ **Sistem Mendinginkan Diri:** Kuota API gratis menipis. Harap perlambat Kecepatan Pindai Bot di menu samping.", "HOLD"
                else:
                    # Jika error selain kuota, langsung laporkan
                    raise e
        
        # Jika berhasil mendapatkan respons, lanjutkan ekstraksi JSON
        if response:
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
        else:
            return narasi + "⚠️ Respons API kosong.", "HOLD"

    except json.JSONDecodeError:
        return narasi + "⚠️ Respons API gagal diurai menjadi JSON. AI menahan diri.", "HOLD"
    except Exception as e:
        return narasi + f"💥 Kesalahan Koneksi API: {e}", "ERROR"
