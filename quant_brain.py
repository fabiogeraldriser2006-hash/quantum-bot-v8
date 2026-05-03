"""
=========================================================
FILE: quant_brain.py
DESKRIPSI: Otak Artificial Intelligence (Jaringan Saraf).
Bertugas menganalisis data, menyimpan memori (file .pkl), 
dan memiliki sistem pemulihan mandiri (Auto-Healing) 
dari kerusakan file.
=========================================================
"""

import os
import joblib
import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
import config # Memanggil pengaturan pusat (seperti Biaya Fee)

def prediksi_ai_market(df_chart, coin, current_price, timeframe, sentimen_global):
    """
    Fungsi utama AI. Menerima data grafik, melatih model, 
    dan mengembalikan narasi serta konklusi (BUY/SELL/HOLD).
    """
    narasi = f"**🧠 AI Execution Engine: {coin} ({timeframe})**\n\nSpot: **Rp {current_price:,}** | Sentimen Global: **{sentimen_global}/100**\n\n"
    
    # AI butuh minimal 50 lilin/data untuk mulai berpikir
    if len(df_chart) < 50: 
        return narasi + "Data belum cukup untuk analisis.", "HOLD"
    
    # 1. PERSIAPAN DATA (FEATURE ENGINEERING)
    df = df_chart.copy()
    df['BB_Position'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
    df.fillna(0, inplace=True) 
    df['Sentiment'] = sentimen_global
    
    # Target: Apakah harga ke depan akan naik melebihi 2x lipat biaya transaksi?
    LOOKAHEAD_WINDOW = 4
    df['Future_Max'] = df['Close'].rolling(window=LOOKAHEAD_WINDOW).max().shift(-LOOKAHEAD_WINDOW)
    df['Target'] = (df['Future_Max'] > (df['Close'] * (1 + (config.FEE_RATE * 2)))).astype(int)
    
    train_data = df.dropna(subset=['Future_Max'])
    latest_data = df.iloc[-1:] 
    
    features = ['RSI', 'MACD_Hist', 'BB_Position', 'Volume', 'OBV', 'Sentiment']
    X_train = train_data[features]
    y_train = train_data['Target']
    X_latest = latest_data[features]
    
    model_file = f'ai_model_{coin}_{timeframe}_v3.pkl' 
    scaler_file = f'ai_scaler_{coin}_{timeframe}_v3.pkl'
    
    # 2. SISTEM PEMULIHAN MEMORI (AUTO-HEALING)
    # Mengecek apakah AI sudah punya pengalaman sebelumnya
    if os.path.exists(model_file) and os.path.exists(scaler_file):
        try:
            scaler = joblib.load(scaler_file)
            model = joblib.load(model_file)
            narasi += f"💾 *Memori AI V3 ({timeframe}) dimuat...*\n"
        except Exception as e:
            # Jika file .pkl rusak (corrupt), buat model baru yang segar tanpa error
            scaler = StandardScaler()
            model = MLPClassifier(hidden_layer_sizes=(128, 64), activation='relu', solver='adam', max_iter=1, random_state=42)
            narasi += f"⚠️ *File memori rusak akibat interupsi. Menciptakan ulang otak AI untuk {coin}...*\n"
    else:
        # Jika belum ada pengalaman, buat dari nol
        scaler = StandardScaler()
        model = MLPClassifier(hidden_layer_sizes=(128, 64), activation='relu', solver='adam', max_iter=1, random_state=42)
        narasi += f"🌱 *Menciptakan jaringan saraf Visi Masa Depan untuk {coin}...*\n"

    # 3. PROSES PEMBELAJARAN DAN PREDIKSI
    try:
        if not hasattr(scaler, 'n_samples_seen_'):
            X_train_scaled = scaler.fit_transform(X_train)
        else:
            X_train_scaled = scaler.transform(X_train)
            
        X_latest_scaled = scaler.transform(X_latest)
        
        # Belajar dari data terbaru
        model.partial_fit(X_train_scaled, y_train, classes=np.array([0, 1]))
        
        # Simpan kembali pengalaman ke dalam file .pkl
        joblib.dump(scaler, scaler_file)
        joblib.dump(model, model_file)
        
        # Menebak probabilitas kenaikan/penurunan
        probabilitas = model.predict_proba(X_latest_scaled)[0]
        prob_turun = probabilitas[0] * 100
        prob_naik = probabilitas[1] * 100
        
        narasi += f"- Probabilitas Profit (Net) : **{prob_naik:.1f}%**\n- Probabilitas Terkoreksi: **{prob_turun:.1f}%**\n\n"
        
        # Keputusan Akhir
        if prob_naik > 60:
            narasi += "✅ Jaringan Saraf mendeteksi tren kenaikan valid (Mampu menembus Fee)."
            konklusi = "BUY"
        elif prob_turun > 60:
            narasi += "❌ Jaringan Saraf merekomendasikan pelepasan aset."
            konklusi = "SELL"
        else:
            narasi += "⚖️ Pasar tidak menentu. AI menahan diri (HOLD)."
            konklusi = "HOLD"
            
        return narasi, konklusi
    except Exception as e: 
        return narasi + f"⚠️ Kesalahan Kognitif AI: {e}", "ERROR"
