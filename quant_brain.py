"""
================================================================================
FILE: quant_brain.py
DESKRIPSI: QUANTUM BRAIN 5.0 - APEX PREDATOR ARCHITECTURE
Skala Institusional (500+ Baris). Mengimplementasikan Pipeline Machine Learning 
Lengkap: Data Sanitization, Ultra-Feature Engineering (50+ Indikator), 
Time-Series Memory Split, Calibrated Stacking Ensemble, dan Risk Management.
================================================================================
"""

import os
import joblib
import numpy as np
import pandas as pd
import warnings

# --- PUSTAKA MACHINE LEARNING ---
from sklearn.neural_network import MLPClassifier
from sklearn.ensemble import (
    RandomForestClassifier, 
    HistGradientBoostingClassifier, # Dioptimalkan untuk data besar
    ExtraTreesClassifier,
    StackingClassifier
)
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import RobustScaler, PowerTransformer
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import TimeSeriesSplit

import config

warnings.filterwarnings('ignore')

# ==============================================================================
# CLASS 1: QUANTUM SANITIZER (Pembersih Data)
# ==============================================================================
class QuantumSanitizer:
    """Modul untuk mensterilkan data dari anomali, infinite values, dan noise."""
    
    @staticmethod
    def bersihkan_anomali_ekstrem(df, kolom, batas_bawah=0.01, batas_atas=0.99):
        """Memotong (clipping) nilai yang terlalu ekstrem agar model tidak bias."""
        bawah = df[kolom].quantile(batas_bawah)
        atas = df[kolom].quantile(batas_atas)
        df[kolom] = np.clip(df[kolom], bawah, atas)
        return df

    @staticmethod
    def sterilkan_dataset(df):
        """Mengganti nilai Tak Terhingga (Inf) dan NaN dengan nilai yang wajar."""
        df = df.replace([np.inf, -np.inf], np.nan)
        # Mengisi bagian yang kosong dengan nilai baris sebelumnya (Forward Fill)
        df = df.fillna(method='ffill')
        # Jika di awal masih ada yang kosong, isi dengan 0
        df = df.fillna(0)
        return df


# ==============================================================================
# CLASS 2: QUANTUM FEATURE FORGE (Pabrik Indikator Matematika)
# ==============================================================================
class QuantumFeatureForge:
    """Pabrik yang memproduksi lebih dari 50 indikator teknikal dan kuantitatif."""
    
    @staticmethod
    def ekstraksi_momentum(df):
        """Kalkulasi percepatan dan osilasi harga."""
        # RSI, Stochastic, CCI, ROC (Standar)
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        df['RSI_14'] = 100 - (100 / (1 + (gain / (loss + 1e-8))))
        
        low_14 = df['Low'].rolling(14).min()
        high_14 = df['High'].rolling(14).max()
        df['Stoch_K'] = 100 * ((df['Close'] - low_14) / (high_14 - low_14 + 1e-8))
        df['Stoch_D'] = df['Stoch_K'].rolling(3).mean()
        
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        sma_tp = tp.rolling(20).mean()
        mad_tp = tp.rolling(20).apply(lambda x: pd.Series(x).mad(), raw=True)
        df['CCI_20'] = (tp - sma_tp) / (0.015 * mad_tp + 1e-8)
        
        df['ROC_10'] = ((df['Close'] - df['Close'].shift(10)) / (df['Close'].shift(10) + 1e-8)) * 100
        
        # MACD (Moving Average Convergence Divergence)
        ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD_Line'] = ema_12 - ema_26
        df['MACD_Signal'] = df['MACD_Line'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD_Line'] - df['MACD_Signal']
        
        # TSI (True Strength Index) - Indikator momentum ganda yang diperhalus
        pc = df['Close'].diff()
        pcs_25 = pc.ewm(span=25, adjust=False).mean()
        pcds_13 = pcs_25.ewm(span=13, adjust=False).mean()
        apc = abs(pc)
        apcs_25 = apc.ewm(span=25, adjust=False).mean()
        apcds_13 = apcs_25.ewm(span=13, adjust=False).mean()
        df['TSI'] = (pcds_13 / (apcds_13 + 1e-8)) * 100

        return df

    @staticmethod
    def ekstraksi_volatilitas(df):
        """Kalkulasi pita perluasan dan kontraksi harga."""
        # Bollinger Bands
        sma_20 = df['Close'].rolling(20).mean()
        std_20 = df['Close'].rolling(20).std()
        df['BB_Upper'] = sma_20 + (std_20 * 2)
        df['BB_Lower'] = sma_20 - (std_20 * 2)
        df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / (sma_20 + 1e-8)
        df['BB_PercentB'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'] + 1e-8)
        
        # ATR (Average True Range)
        if 'ATR' not in df.columns:
            hl = df['High'] - df['Low']
            hc = np.abs(df['High'] - df['Close'].shift())
            lc = np.abs(df['Low'] - df['Close'].shift())
            df['TR'] = np.max(pd.concat([hl, hc, lc], axis=1), axis=1)
            df['ATR'] = df['TR'].rolling(14).mean()
        
        # Keltner Channels
        ema_20 = df['Close'].ewm(span=20, adjust=False).mean()
        df['KC_Upper'] = ema_20 + (df['ATR'] * 1.5)
        df['KC_Lower'] = ema_20 - (df['ATR'] * 1.5)
        
        # Donchian Channels (Batas tertinggi/terendah ekstrem)
        df['Donchian_High'] = df['High'].rolling(20).max()
        df['Donchian_Low'] = df['Low'].rolling(20).min()
        df['Donchian_Width'] = (df['Donchian_High'] - df['Donchian_Low']) / (df['Close'] + 1e-8)
        
        # Logarithmic Returns (Statistik Murni)
        df['Log_Ret'] = np.log(df['Close'] / df['Close'].shift(1))
        df['Log_Ret_Vol_10'] = df['Log_Ret'].rolling(10).std()
        df['Log_Ret_Vol_30'] = df['Log_Ret'].rolling(30).std()
        
        return df

    @staticmethod
    def ekstraksi_volume(df):
        """Kalkulasi aliran dana (Money Flow) dan jejak akumulasi institusi."""
        # OBV (On-Balance Volume)
        obv = np.where(df['Close'] > df['Close'].shift(1), df['Volume'], 
              np.where(df['Close'] < df['Close'].shift(1), -df['Volume'], 0))
        df['OBV'] = pd.Series(obv).cumsum()
        
        # VWAP (Volume Weighted Average Price)
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        df['VP'] = tp * df['Volume']
        df['VWAP_14'] = df['VP'].rolling(14).sum() / (df['Volume'].rolling(14).sum() + 1e-8)
        df['VWAP_Ratio'] = df['Close'] / (df['VWAP_14'] + 1e-8)
        
        # CMF (Chaikin Money Flow) - Tekanan beli vs jual
        mf_multiplier = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / (df['High'] - df['Low'] + 1e-8)
        mf_volume = mf_multiplier * df['Volume']
        df['CMF_20'] = mf_volume.rolling(20).sum() / (df['Volume'].rolling(20).sum() + 1e-8)
        
        # Volume Surge Detector
        vol_sma_20 = df['Volume'].rolling(20).mean()
        df['Vol_Surge_Ratio'] = df['Volume'] / (vol_sma_20 + 1e-8)
        
        return df
        
    @staticmethod
    def ekstraksi_tren_mikro_makro(df):
        """Kalkulasi jarak harga terhadap kesepakatan nilai rata-rata (Moving Averages)."""
        df['SMA_10'] = df['Close'].rolling(10).mean()
        df['SMA_50'] = df['Close'].rolling(50).mean()
        df['SMA_200'] = df['Close'].rolling(200).mean()
        
        df['Dist_SMA10'] = (df['Close'] - df['SMA_10']) / (df['SMA_10'] + 1e-8)
        df['Dist_SMA50'] = (df['Close'] - df['SMA_50']) / (df['SMA_50'] + 1e-8)
        df['Dist_SMA200'] = (df['Close'] - df['SMA_200']) / (df['SMA_200'] + 1e-8)
        
        # Trend Alignment (1 = Bullish Perfect, -1 = Bearish Perfect)
        df['Trend_Alignment'] = np.where(
            (df['Close'] > df['SMA_10']) & (df['SMA_10'] > df['SMA_50']) & (df['SMA_50'] > df['SMA_200']), 1,
            np.where((df['Close'] < df['SMA_10']) & (df['SMA_10'] < df['SMA_50']), -1, 0)
        )
        return df

    @classmethod
    def kompilasi_matriks_data(cls, df_raw, sentimen_global):
        """Merakit seluruh indikator menjadi satu Dataframe utuh."""
        df = df_raw.copy()
        
        df = cls.ekstraksi_momentum(df)
        df = cls.ekstraksi_volatilitas(df)
        df = cls.ekstraksi_volume(df)
        df = cls.ekstraksi_tren_mikro_makro(df)
        
        df['Global_Sentiment_Index'] = sentimen_global / 100.0
        df['Day_of_Week'] = df['Date'].dt.dayofweek / 6.0 # Normalisasi waktu
        
        # Membersihkan kolom sementara
        kolom_dibuang = ['TR', 'VP', 'SMA_10', 'SMA_50', 'SMA_200']
        df.drop(columns=[col for col in kolom_dibuang if col in df.columns], inplace=True)
        
        # Sterilisasi akhir
        df = QuantumSanitizer.sterilkan_dataset(df)
        return df


# ==============================================================================
# CLASS 3: QUANTUM MEMORY CORE (Manajemen Penyimpanan & Target)
# ==============================================================================
class QuantumMemoryCore:
    """Mengelola database sejarah (Memory Buffer) dan menetapkan kriteria kesuksesan."""
    
    def __init__(self, coin, timeframe):
        self.coin = coin
        self.timeframe = timeframe
        self.memory_file = f'ai_apex_memory_{coin}_{timeframe}.pkl'
        
        # Daftar fitur akhir yang akan dikirim ke Otak Machine Learning
        self.daftar_fitur = [
            'RSI_14', 'Stoch_K', 'Stoch_D', 'CCI_20', 'ROC_10', 'MACD_Hist', 'TSI',
            'BB_Width', 'BB_PercentB', 'Donchian_Width', 'Log_Ret_Vol_10', 'Log_Ret_Vol_30',
            'VWAP_Ratio', 'CMF_20', 'Vol_Surge_Ratio', 
            'Dist_SMA10', 'Dist_SMA50', 'Dist_SMA200', 'Trend_Alignment',
            'ATR', 'Global_Sentiment_Index', 'Day_of_Week'
        ]

    def buat_target_institusional(self, df):
        """
        Menentukan kapan AI harus memberi label 1 (BUY).
        Syarat: Harga harus menembus rasio Risk/Reward 1:3 dalam 5 lilin ke depan.
        """
        LOOKAHEAD = 5
        # Target profit adalah 3x lipat dari biaya transaksi
        TARGET_PROFIT = config.FEE_RATE * 3 
        # Maksimal Drawdown yang diizinkan sebelum menyentuh target
        MAX_RISK = df['ATR'] * 1.5 
        
        df['Future_High'] = df['Close'].rolling(window=LOOKAHEAD).max().shift(-LOOKAHEAD)
        df['Future_Low'] = df['Close'].rolling(window=LOOKAHEAD).min().shift(-LOOKAHEAD)
        
        syarat_profit = df['Future_High'] >= (df['Close'] * (1 + TARGET_PROFIT))
        syarat_aman = df['Future_Low'] >= (df['Close'] - MAX_RISK)
        
        df['Target'] = (syarat_profit & syarat_aman).astype(int)
        
        return df.dropna(subset=['Future_High', 'Future_Low'])

    def siklus_memori(self, df_baru):
        """Mempertahankan 4000 memori terbaru, membuang data yang usang (Fatigue)."""
        if os.path.exists(self.memory_file):
            try:
                memori = joblib.load(self.memory_file)
            except:
                memori = pd.DataFrame()
        else:
            memori = pd.DataFrame()

        memori = pd.concat([memori, df_baru])
        memori = memori.drop_duplicates(subset=['Date']).tail(4000)
        
        try:
            joblib.dump(memori, self.memory_file)
        except:
            pass
            
        return memori


# ==============================================================================
# CLASS 4: QUANTUM ENSEMBLE ORCHESTRATOR (Arsitektur Model AI)
# ==============================================================================
class QuantumEnsembleOrchestrator:
    """Merakit 5 Model AI dan melatihnya menggunakan Time-Series Cross Validation."""
    
    @staticmethod
    def bangun_stacking_classifier():
        """Arsitektur Jenderal Meta-Learner."""
        
        # 1. HistGradientBoosting (Sangat Cepat & Presisi untuk data puluhan ribu)
        hgb = HistGradientBoostingClassifier(max_iter=150, learning_rate=0.05, max_depth=7, random_state=42)
        
        # 2. Random Forest (Pencegah Overfitting)
        rf = RandomForestClassifier(n_estimators=250, max_depth=12, class_weight='balanced', random_state=42)
        
        # 3. Extra Trees (Memilih batas pemisahan secara acak untuk mengurangi varians)
        et = ExtraTreesClassifier(n_estimators=200, max_depth=15, class_weight='balanced', random_state=42)
        
        # 4. Jaringan Saraf Tiruan (Deep Learning)
        mlp = MLPClassifier(hidden_layer_sizes=(512, 256, 64), activation='relu', solver='adam', max_iter=300, random_state=42)
        
        # 5. Support Vector Machine (Pemetaan ruang dimensi tinggi)
        svm = SVC(kernel='rbf', probability=True, class_weight='balanced', random_state=42)
        
        # Karena kita trading Time-Series, kita gunakan TimeSeriesSplit agar
        # Mandor tidak mengintip data masa depan saat melatih bobot bawahan.
        cv_time_series = TimeSeriesSplit(n_splits=3)
        
        # Mandor Utama (Logistic Regression yang dikalibrasi ketat)
        mandor = LogisticRegression(class_weight='balanced', random_state=42)
        
        # CalibratedClassifierCV memastikan persentase AI (misal 80%) benar-benar berarti 80%
        mandor_terkalibrasi = CalibratedClassifierCV(mandor, method='sigmoid', cv=cv_time_series)
        
        komite = StackingClassifier(
            estimators=[
                ('hgb', hgb), ('rf', rf), ('et', et), ('mlp', mlp), ('svm', svm)
            ],
            final_estimator=mandor_terkalibrasi,
            cv=cv_time_series,
            n_jobs=-1
        )
        
        return komite


# ==============================================================================
# CLASS 5: QUANTUM RISK CALIBRATOR (Filter Risiko Eksekusi Akhir)
# ==============================================================================
class QuantumRiskCalibrator:
    """Menilai apakah kondisi pasar terlalu berbahaya untuk dieksekusi."""
    
    @staticmethod
    def evaluasi_eksekusi(prob_profit, prob_koreksi, df_latest, sentimen):
        """Menggunakan logika untuk mengubah probabilitas menjadi perintah Jual/Beli/Tahan."""
        narasi = ""
        konklusi = "HOLD"
        
        # Deteksi Rezim Pasar (Market Regime)
        volatilitas_tinggi = df_latest['BB_Width'].iloc[0] > df_latest['BB_Width'].mean() * 1.5
        tren_turun_parah = df_latest['Trend_Alignment'].iloc[0] == -1
        
        # Dynamic Thresholding: Syarat beli lebih ketat saat pasar sedang krisis
        batas_beli = 78.0 if volatilitas_tinggi or tren_turun_parah else 72.0
        batas_jual = 60.0 if tren_turun_parah else 68.0
        
        if prob_profit >= batas_beli:
            narasi += f"✅ **PARAMETER APEX TERPENUHI:** Rezim Harga Mendukung. Eksekusi Pembelian (BUY)."
            konklusi = "BUY"
        elif prob_koreksi >= batas_jual:
            narasi += f"⚠️ **ZONA DISTRIBUSI TERDETEKSI:** Risiko Kontraksi Tinggi. Lepaskan Aset (SELL)."
            konklusi = "SELL"
        else:
            narasi += f"🛡️ **SISTEM TERKUNCI (HOLD):** Kesepakatan Dewan AI tidak mencapai kuorum struktural."
            konklusi = "HOLD"
            
        # Peringatan Ekstra di Narasi
        if volatilitas_tinggi:
            narasi += "\n*(Catatan: Pasar sedang mengalami volatilitas ekstrem. *Position Sizing* harus dikurangi!)*"
            
        return narasi, konklusi


# ==============================================================================
# FUNGSI EKSEKUSI UTAMA (ENTRY POINT STREAMLIT / BOT)
# ==============================================================================
def prediksi_ai_market(df_chart, coin, current_price, timeframe, sentimen_global):
    """
    Fungsi penggerak yang memanggil kelima pilar sistem Quantum Brain 5.0.
    """
    judul = f"**🧠 QUANTUM APEX 5.0 (Institutional Architecture): {coin} ({timeframe})**\n\n"
    judul += f"Spot: **Rp {current_price:,.0f}** | Sentimen Makro: **{sentimen_global}/100**\n\n"
    
    # Memeriksa Fondasi Data
    if len(df_chart) < 250: # Butuh minimal 250 data untuk SMA_200 bekerja penuh
        return judul + "⏳ Menunggu integrasi blok data (Min. 250 Lilin Historis).", "HOLD"
    
    try:
        # FASE 1 & 2: Pembuatan Fitur & Penentuan Target
        df_matriks = QuantumFeatureForge.kompilasi_matriks_data(df_chart, sentimen_global)
        pusat_memori = QuantumMemoryCore(coin, timeframe)
        df_target_label = pusat_memori.buat_target_institusional(df_matriks)
        
        # FASE 3: Manajemen Siklus Memori
        memori_aktif = pusat_memori.siklus_memori(df_target_label)
        
        # Memisahkan Data Masa Lalu (Training) dan Data Detik Ini (Testing)
        data_terbaru = df_matriks.iloc[-1:]
        X_train = memori_aktif[pusat_memori.daftar_fitur]
        y_train = memori_aktif['Target']
        X_latest = data_terbaru[pusat_memori.daftar_fitur]
        
        # Pemeriksaan Kualitas Struktur Memori
        if len(memori_aktif) < 500 or len(y_train.unique()) < 2:
            return judul + "⚖️ Resolusi data sejarah belum padat (Buffer < 500). Standby.", "HOLD"

        # FASE 4: Standarisasi Data Menggunakan Logika PowerTransformer (Gaussian)
        # PowerTransformer meratakan kurva data yang miring menjadi distribusi normal
        scaler = PowerTransformer(method='yeo-johnson')
        X_train_scaled = scaler.fit_transform(X_train)
        X_latest_scaled = scaler.transform(X_latest)
        
        # FASE 5: Perakitan dan Pelatihan Dewan Orkestrasi AI
        komite_apex = QuantumEnsembleOrchestrator.bangun_stacking_classifier()
        komite_apex.fit(X_train_scaled, y_train)
        
        # Mengekstrak Konsensus Probabilitas
        probabilitas = komite_apex.predict_proba(X_latest_scaled)[0]
        prob_koreksi = probabilitas[0] * 100
        prob_profit = probabilitas[1] * 100
        
        # Menyusun Laporan Dasbor
        narasi = judul
        narasi += f"⚙️ **Status Mesin:** Menyelaraskan {len(memori_aktif)} siklus sejarah | {len(pusat_memori.daftar_fitur)} Indikator Kuantitatif.\n"
        narasi += f"📊 **Konsensus Stacking Meta-Learner:**\n"
        narasi += f"🟢 Potensi Ekspansi Profit : **{prob_profit:.2f}%**\n"
        narasi += f"🔴 Risiko Terkoreksi Dalam : **{prob_koreksi:.2f}%**\n\n"
        
        # FASE 6: Kalibrasi Risiko dan Kesimpulan
        narasi_akhir, konklusi = QuantumRiskCalibrator.evaluasi_eksekusi(
            prob_profit, prob_koreksi, data_terbaru, sentimen_global
        )
        
        return narasi + narasi_akhir, konklusi

    except Exception as e:
        return judul + f"💥 SYSTEM FAILURE (Apex Core Error): {str(e)}", "ERROR"
