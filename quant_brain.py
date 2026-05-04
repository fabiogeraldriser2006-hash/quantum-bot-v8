"""
=========================================================
FILE: quant_brain.py
DESKRIPSI: Quantum Brain 3.0 - Deep Nexus Architecture.
Mesin AI kelas institusi yang menggabungkan 5 algoritma 
Machine Learning (Neural Network, Random Forest, Gradient 
Boosting, SVM, dan KNN) dalam satu komite pemungutan suara.
Dilengkapi dengan Ultra-Feature Engineering.
=========================================================
"""

import os
import joblib
import numpy as np
import pandas as pd
import warnings

# Mengimpor 5 Senjata Utama Machine Learning dari scikit-learn
from sklearn.neural_network import MLPClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.pipeline import Pipeline

import config

# Mengabaikan peringatan kalkulasi internal agar log terminal tetap bersih
warnings.filterwarnings('ignore')

def ekstraksi_fitur_lanjutan(df_raw, sentimen_global):
    """
    Pabrik pengolahan data. Mengubah harga mentah menjadi puluhan 
    indikator teknikal dan matematika tingkat tinggi.
    """
    df = df_raw.copy()
    
    # 1. Fitur Harga Dasar & Relatif
    df['Log_Return'] = np.log(df['Close'] / df['Close'].shift(1))
    df['Log_Return_Volatility'] = df['Log_Return'].rolling(10).std()
    
    # 2. Fitur Pita Volatilitas (Bollinger Bands Advanced)
    df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['SMA_20']
    df['BB_Position'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
    
    # 3. Fitur Momentum Osilator (Stochastic RSI proxy)
    min_rsi = df['RSI'].rolling(14).min()
    max_rsi = df['RSI'].rolling(14).max()
    df['Stoch_RSI'] = (df['RSI'] - min_rsi) / (max_rsi - min_rsi + 1e-8)
    
    # 4. Proksi Volume Weighted Average Price (VWAP)
    # Menghitung harga rata-rata berdasarkan volume transaksi
    df['Typical_Price'] = (df['High'] + df['Low'] + df['Close']) / 3
    df['VP'] = df['Typical_Price'] * df['Volume']
    df['Cumulative_VP'] = df['VP'].rolling(window=20).sum()
    df['Cumulative_Volume'] = df['Volume'].rolling(window=20).sum()
    df['VWAP_20'] = df['Cumulative_VP'] / (df['Cumulative_Volume'] + 1e-8)
    df['Price_to_VWAP'] = df['Close'] / df['VWAP_20']
    
    # 5. Fitur Trend Akselerasi (Moving Average Distance)
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['Dist_SMA20'] = (df['Close'] - df['SMA_20']) / df['SMA_20']
    df['Dist_SMA50'] = (df['Close'] - df['SMA_50']) / df['SMA_50']
    
    # 6. Fitur Rasio Risiko (ATR & Sentimen)
    df['ATR_Ratio'] = df['ATR'] / df['Close']
    df['Sentiment'] = sentimen_global / 100.0 # Normalisasi sentimen 0-1
    
    # 7. Detektor Anomali Volume (Spike Detection)
    vol_mean = df['Volume'].rolling(20).mean()
    vol_std = df['Volume'].rolling(20).std()
    df['Volume_Anomaly'] = (df['Volume'] - vol_mean) / (vol_std + 1e-8)

    # Membersihkan baris yang kosong akibat perhitungan rolling
    df.fillna(0, inplace=True)
    return df

def prediksi_ai_market(df_chart, coin, current_price, timeframe, sentimen_global):
    """
    Fungsi eksekusi sentral. Menarik data, melatih komite 5 otak,
    dan mengambil keputusan strategis berdasarkan probabilitas matematis.
    """
    narasi = f"**🧠 Quantum Brain 3.0 (Mega-Ensemble): {coin} ({timeframe})**\n\n"
    narasi += f"Spot: **Rp {current_price:,.0f}** | Indeks Ketakutan: **{sentimen_global}/100**\n\n"
    
    # AI butuh minimal 50 data untuk membentuk struktur fondasi analitik
    if len(df_chart) < 50: 
        return narasi + "Sedang merakit matriks data dasar...", "HOLD"
    
    # ==========================================
    # FASE 1: FEATURE ENGINEERING & PENENTUAN TARGET
    # ==========================================
    df = ekstraksi_fitur_lanjutan(df_chart, sentimen_global)
    
    # Penentuan Target Super Ketat (Faktor Keamanan Tingkat Tinggi)
    # AI hanya disuruh belajar "Anggap ini angka 1 (Beli) HANYA JIKA..."
    # 1. Harga ke depan melampaui 3x lipat biaya transaksi (Profit bersih tinggi)
    # 2. Harga terendah ke depan tidak menyentuh Stop Loss dalam 3 candle berikutnya
    
    LOOKAHEAD = 3
    FEE_BUFFER = config.FEE_RATE * 3
    df['Future_High'] = df['Close'].rolling(window=LOOKAHEAD).max().shift(-LOOKAHEAD)
    df['Future_Low'] = df['Close'].rolling(window=LOOKAHEAD).min().shift(-LOOKAHEAD)
    
    # Syarat: Potensi untung harus menembus Fee, DAN potensi turun jangan terlalu dalam
    target_profit = df['Close'] * (1 + FEE_BUFFER)
    batas_koreksi = df['Close'] * 0.99 # Toleransi drawdown 1%
    
    kondisi_ideal = (df['Future_High'] > target_profit) & (df['Future_Low'] > batas_koreksi)
    df['Target'] = kondisi_ideal.astype(int)
    
    train_data = df.dropna(subset=['Future_High', 'Future_Low'])
    latest_data = df.iloc[-1:] 
    
    # Kolom fitur yang akan menjadi "Mata" dari AI
    daftar_fitur = [
        'RSI', 'Stoch_RSI', 'MACD_Hist', 'BB_Width', 'BB_Position', 
        'Log_Return', 'Log_Return_Volatility', 'Price_to_VWAP', 
        'Dist_SMA20', 'Dist_SMA50', 'ATR_Ratio', 'Volume_Anomaly', 'Sentiment'
    ]
    
    X_latest = latest_data[daftar_fitur]
    
    # ==========================================
    # FASE 2: MANAJEMEN MEMORI DINAMIS (SLIDING WINDOW)
    # ==========================================
    # Menggunakan memori khusus per koin dan per timeframe
    nama_file_memori = f'ai_nexus_buffer_{coin}_{timeframe}.pkl'
    
    if os.path.exists(nama_file_memori):
        try:
            memori_database = joblib.load(nama_file_memori)
        except:
            memori_database = pd.DataFrame()
    else:
        memori_database = pd.DataFrame()

    memori_database = pd.concat([memori_database, train_data])
    # Mempertahankan fondasi data sebanyak 2500 titik terkuat, buang sisa beban mati
    memori_database = memori_database.drop_duplicates(subset=['Date']).tail(2500)
    
    try:
        joblib.dump(memori_database, nama_file_memori)
    except Exception as e:
        pass # Abaikan error penyimpanan sementara jika disk sibuk

    X_train = memori_database[daftar_fitur]
    y_train = memori_database['Target']
    
    # Verifikasi Stabilitas Data
    if len(memori_database) < 150 or len(y_train.unique()) < 2:
        return narasi + "⚖️ Kapasitas memori struktural belum memadai. AI menahan eksekusi.", "HOLD"

    # ==========================================
    # FASE 3: KOMITE 5 OTAK (MEGA-ENSEMBLE)
    # ==========================================
    try:
        # Penskalaan ekstrim menggunakan RobustScaler (tahan terhadap harga outlier/abnormal)
        scaler = RobustScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_latest_scaled = scaler.transform(X_latest)
        
        # Merakit 5 Mesin Analitik
        # 1. Multi-Layer Perceptron (Jaringan Saraf Dalam)
        model_mlp = MLPClassifier(hidden_layer_sizes=(256, 128, 64), activation='relu', solver='adam', max_iter=200, random_state=42)
        
        # 2. Random Forest (Mencegah Overfitting)
        model_rf = RandomForestClassifier(n_estimators=150, max_depth=12, class_weight='balanced', random_state=42)
        
        # 3. Gradient Boosting (Spesialis memperbaiki prediksi yang meleset)
        model_gb = GradientBoostingClassifier(n_estimators=100, learning_rate=0.1, max_depth=5, random_state=42)
        
        # 4. Support Vector Machine (Mencari garis batas tegas antara beli dan jual)
        # probability=True wajib dinyalakan agar SVM bisa ikut voting persentase
        model_svm = SVC(kernel='rbf', C=1.0, probability=True, random_state=42)
        
        # 5. K-Nearest Neighbors (Mencari 15 momen sejarah yang paling mirip dengan detik ini)
        model_knn = KNeighborsClassifier(n_neighbors=15, weights='distance')
        
        # Menyatukan 5 Mesin ke dalam satu Komite (Soft Voting = Menggabungkan persentase)
        komite_nexus = VotingClassifier(
            estimators=[
                ('NeuralNet', model_mlp), 
                ('RandomForest', model_rf), 
                ('GradBoost', model_gb),
                ('SupportVector', model_svm),
                ('K-Nearest', model_knn)
            ],
            voting='soft',
            weights=[2, 2, 2, 1, 1] # NN, RF, dan GB diberi hak suara lebih besar (bobot 2)
        )
        
        # Melatih komite secara simultan
        komite_nexus.fit(X_train_scaled, y_train)
        
        # Membaca hasil diskusi kelima otak
        probabilitas = komite_nexus.predict_proba(X_latest_scaled)[0]
        prob_koreksi = probabilitas[0] * 100
        prob_profit = probabilitas[1] * 100
        
        # Menyusun Laporan Visual untuk Layar Streamlit
        narasi += f"⚙️ **Status Nexus:** Mengelola {len(memori_database)} titik pengalaman.\n"
        narasi += f"📊 **Resolusi Komite 5 Algoritma:**\n"
        narasi += f"🟢 Potensi Kenaikan Lanjutan : **{prob_profit:.2f}%**\n"
        narasi += f"🔴 Risiko Terkoreksi/Sideways : **{prob_koreksi:.2f}%**\n\n"
        
        # ==========================================
        # FASE 4: LOGIKA EKSEKUSI (KALIBRASI RISIKO)
        # ==========================================
        # AI hanya mengeksekusi jika probabilitasnya sangat tinggi
        BATAS_BELI = 75.0 # Komite harus 75% yakin untuk membeli
        BATAS_JUAL = 65.0 # Komite lebih sensitif (65% yakin) untuk menyelamatkan aset
        
        if prob_profit >= BATAS_BELI:
            narasi += f"✅ **KEPUTUSAN BULAT:** Parameter keamanan terpenuhi. Eksekusi Pembelian (BUY) direkomendasikan."
            konklusi = "BUY"
        elif prob_koreksi >= BATAS_JUAL:
            narasi += f"⚠️ **PERINGATAN STRUKTURAL:** Tekanan distribusi terdeteksi. Pelepasan Aset (SELL) disarankan."
            konklusi = "SELL"
        else:
            narasi += f"🛡️ **STANDBY:** Stabilitas pasar dipertanyakan. Komite menolak eksekusi (HOLD)."
            konklusi = "HOLD"
            
        return narasi, konklusi
        
    except Exception as e: 
        return narasi + f"💥 KRISIS SISTEM (Nexus Error): {e}", "ERROR"
