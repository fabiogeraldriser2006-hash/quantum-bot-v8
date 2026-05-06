"""
================================================================================
FILE: app.py
DESKRIPSI: Dashboard Streamlit Utama (Eagle Focus / Koin Tunggal).
Menghubungkan kontrol UI dengan mesin latar belakang execution_bot.py.
================================================================================
"""
import streamlit as st
import pandas as pd
import time
import config
import execution_bot

# Mengatur tampilan halaman agar lebar dan menggunakan tema gelap
st.set_page_config(
    page_title="Prop Desk Quant OS - Single Focus",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inisialisasi otomatis mesin latar belakang jika belum berjalan
if "bot_started" not in st.session_state:
    st.session_state.bot_started = False

# ==============================================================================
# KOMPONEN SIDEBAR (KENDALI UTAMA)
# ==============================================================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/artificial-intelligence.png", width=60)
    st.title("⚙️ Panel Kendali")
    st.markdown("---")
    
    # 1. Pilihan Koin Tunggal
    st.subheader("🎯 Target Koin")
    daftar_koin = list(config.CRYPTO_MAP.keys())
    
    # Mencari indeks koin yang sedang aktif di bot_state
    koin_aktif = execution_bot.bot_state.get("selected_coin", "Bitcoin")
    try:
        index_koin = daftar_koin.index(koin_aktif)
    except ValueError:
        index_koin = 0
        
    pilihan_koin = st.selectbox(
        "Pilih koin untuk dipantau AI:",
        daftar_koin,
        index=index_koin
    )
    
    # Sinkronisasi pilihan UI ke mesin bot latar belakang
    execution_bot.bot_state["selected_coin"] = pilihan_koin
    
    st.markdown("---")
    
    # 2. Pengaturan Parameter Risiko
    st.subheader("🛡️ Manajemen Risiko")
    atr_input = st.number_input(
        "Pengali Trailing Stop (ATR)", 
        min_value=1.0, 
        max_value=5.0, 
        value=execution_bot.bot_state["atr_multiplier"], 
        step=0.1
    )
    execution_bot.bot_state["atr_multiplier"] = atr_input
    
    st.markdown("---")
    
    # 3. Tombol Start / Stop Bot
    st.subheader("🚀 Status Mesin")
    col_start, col_stop = st.columns(2)
    
    with col_start:
        if st.button("▶️ START", use_container_width=True):
            execution_bot.mulai_bot_latar_belakang()
            st.session_state.bot_started = True
            st.success("Mesin Dinyalakan!")
            time.sleep(1)
            st.rerun()
            
    with col_stop:
        if st.button("⏹️ STOP", use_container_width=True):
            execution_bot.hentikan_bot_latar_belakang()
            st.session_state.bot_started = False
            st.warning("Mesin Dimatikan!")
            time.sleep(1)
            st.rerun()

    # Indikator Visual Status Mesin
    if execution_bot.BOT_IS_RUNNING:
        st.success("🟢 Bot Sedang Berjalan")
    else:
        st.error("🔴 Bot Berhenti")

# ==============================================================================
# KOMPONEN LAYAR UTAMA (DASHBOARD METRIK)
# ==============================================================================
st.title("🦅 Prop Desk Quant OS: Eagle Focus")
st.markdown("Sistem *trading* kuantitatif dengan fokus koin tunggal dan manajemen kuota 24 Jam.")
st.markdown("---")

# Menggunakan elemen penampung agar bisa di-refresh tanpa me-reload seluruh halaman
placeholder_metrik = st.empty()

# Fungsi untuk merender ulang isi layar utama
def perbarui_layar_utama():
    with placeholder_metrik.container():
        # Baris 1: Informasi Koin dan Modal
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="Koin Dipantau", 
                value=execution_bot.bot_state["selected_coin"]
            )
            
        with col2:
            st.metric(
                label="Modal Tersedia (Cash)", 
                value=f"Rp {execution_bot.bot_state['cash']:,.0f}"
            )
            
        with col3:
            # Mengecek apakah bot sedang menahan (HOLD) koin atau kosong
            status_posisi = "KOSONG"
            koin_pilihan = execution_bot.bot_state["selected_coin"]
            if koin_pilihan in execution_bot.bot_state["positions"]:
                status_posisi = "MEMILIKI POSISI TERBUKA"
            st.metric(label="Status Portofolio", value=status_posisi)

        st.markdown("---")
        
        # Baris 2: Log Tindakan Terakhir dan Detail Posisi
        col_log, col_pos = st.columns([2, 1])
        
        with col_log:
            st.subheader("📝 Catatan Sistem (Live)")
            st.info(execution_bot.bot_state["last_action"])
            st.caption("Catatan: AI Gemini memperbarui analisis secara penuh setiap 72 menit untuk mempertahankan siklus kuota 24 jam. Di luar waktu tersebut, sistem menggunakan *cache* dinamis dan *trailing stop* teknikal.")
            
        with col_pos:
            st.subheader("💼 Detail Posisi")
            if execution_bot.bot_state["positions"]:
                posisi = execution_bot.bot_state["positions"]
                df_posisi = pd.DataFrame.from_dict(posisi, orient='index')
                
                # Format ulang kolom agar lebih mudah dibaca
                df_posisi = df_posisi.rename(columns={
                    "amount": "Jumlah Koin",
                    "buy_price": "Harga Beli",
                    "high_price": "Titik Tertinggi (TS)"
                })
                # Menyembunyikan kolom teknikal seperti ATR saat ditampilkan di UI
                kolom_tampil = ["Jumlah Koin", "Harga Beli", "Titik Tertinggi (TS)"]
                st.dataframe(df_posisi[kolom_tampil].style.format("{:,.0f}", subset=["Harga Beli", "Titik Tertinggi (TS)"]))
            else:
                st.write("Tidak ada koin yang sedang ditahan.")

# Panggil fungsi render sekali
perbarui_layar_utama()

# ==============================================================================
# LOGIKA AUTO-REFRESH (Penyegaran Tampilan UI)
# ==============================================================================
# Agar UI Streamlit bisa mengupdate tulisan log secara berkala saat bot berjalan
if execution_bot.BOT_IS_RUNNING:
    time.sleep(2) # Refresh UI setiap 2 detik
    st.rerun()
