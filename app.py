"""
================================================================================
FILE: app.py
DESKRIPSI: Dashboard Streamlit Utama (Full Features).
Menampilkan Candlestick, Kontrol Bot, Portofolio, dan Dasbor Statistik.
================================================================================
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from datetime import datetime
import config
import execution_bot
import data_engine

# 1. PENGATURAN HALAMAN DASBOR
st.set_page_config(
    page_title="Eagle Focus Quant OS",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

if "bot_started" not in st.session_state:
    st.session_state.bot_started = False

# ==============================================================================
# PANEL KENDALI (SIDEBAR)
# ==============================================================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/artificial-intelligence.png", width=60)
    st.title("⚙️ Panel Kendali")
    st.markdown("---")
    
    # Target Koin Tunggal
    st.subheader("🎯 Target Koin")
    daftar_koin = list(config.CRYPTO_MAP.keys())
    koin_aktif = execution_bot.bot_state.get("selected_coin", "Bitcoin (BTC)")
    try:
        index_koin = daftar_koin.index(koin_aktif)
    except ValueError:
        index_koin = 0
        
    pilihan_koin = st.selectbox("Pilih koin pantauan:", daftar_koin, index=index_koin)
    execution_bot.bot_state["selected_coin"] = pilihan_koin
    
    st.markdown("---")
    
    # Mode Trading & Kredensial Indodax
    st.subheader("🏦 Mode Trading")
    
    # Toggle Mode Simulasi
    mode_simulasi = st.toggle("Mode Simulasi (Paper Trading)", value=execution_bot.bot_state["mode_simulasi"])
    execution_bot.bot_state["mode_simulasi"] = mode_simulasi
    
    if not mode_simulasi:
        st.warning("⚠️ MODE LIVE AKTIF. Bot menggunakan saldo asli Indodax.")
        
        # Coba baca dari Streamlit Secrets terlebih dahulu
        rahasia_api = ""
        rahasia_secret = ""
        try:
            rahasia_api = st.secrets["INDODAX_API_KEY"]
            rahasia_secret = st.secrets["INDODAX_SECRET_KEY"]
            st.success("✅ Kredensial Indodax terdeteksi otomatis.")
        except Exception:
            st.info("Kredensial otomatis tidak ditemukan. Isi manual:")
            
        api_key = st.text_input("Indodax API Key", value=rahasia_api, type="password")
        secret_key = st.text_input("Indodax Secret Key", value=rahasia_secret, type="password")
        
        execution_bot.bot_state["api_key_indodax"] = api_key
        execution_bot.bot_state["secret_key_indodax"] = secret_key
    else:
        st.info("✅ Mode Simulasi Aktif. Menggunakan uang virtual.")
    
    # Parameter Keamanan
    st.subheader("🛡️ Manajemen Risiko")
    atr_input = st.number_input(
        "Pengali Trailing Stop (ATR)", 
        min_value=1.0, max_value=5.0, 
        value=execution_bot.bot_state["atr_multiplier"], step=0.1
    )
    execution_bot.bot_state["atr_multiplier"] = atr_input
    
    st.markdown("---")
    
    # Tombol Daya Bot
    col_start, col_stop = st.columns(2)
    with col_start:
        if st.button("▶️ START", use_container_width=True):
            execution_bot.mulai_bot_latar_belakang()
            st.session_state.bot_started = True
            st.success("Bot Dinyalakan!")
            time.sleep(1)
            st.rerun()
            
    with col_stop:
        if st.button("⏹️ STOP", use_container_width=True):
            execution_bot.hentikan_bot_latar_belakang()
            st.session_state.bot_started = False
            st.warning("Bot Dimatikan!")
            time.sleep(1)
            st.rerun()

    if execution_bot.BOT_IS_RUNNING:
        st.success("🟢 Bot Status: BERJALAN")
    else:
        st.error("🔴 Bot Status: BERHENTI")

# ==============================================================================
# LAYAR UTAMA (GRAFIK, LOG, & METRIK STATISTIK)
# ==============================================================================
st.title("🦅 Eagle Focus: Live Market & AI Analysis")
st.markdown("---")

placeholder_utama = st.empty()

def render_layar_utama():
    with placeholder_utama.container():
        koin_pilihan = execution_bot.bot_state["selected_coin"]
        data_koin = config.CRYPTO_MAP.get(koin_pilihan)
        
        # 1. Baris Metrik Atas
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Koin Aktif", koin_pilihan)
        with col2:
            mode_teks = "SIMULASI" if execution_bot.bot_state["mode_simulasi"] else "LIVE TRADING"
            st.metric("Mode Sistem", mode_teks)
        with col3:
            st.metric("Cash Balance", f"Rp {execution_bot.bot_state['cash']:,.0f}")
            
        st.markdown("---")
        
        # 2. Area Grafik Candlestick
        st.subheader(f"📈 Grafik Harga {koin_pilihan} (15 Menit)")
        try:
            data_live = data_engine.tarik_data_live_indodax()
            ticker = data_koin['ticker']
            
            if data_live and ticker in data_live:
                df_chart, _ = data_engine.tarik_grafik_klines_aman(data_koin['tv'], "15m", 50, data_live[ticker])
                
                if not df_chart.empty:
                    fig = go.Figure(data=[go.Candlestick(
                        x=df_chart['Date'],
                        open=df_chart['Open'],
                        high=df_chart['High'],
                        low=df_chart['Low'],
                        close=df_chart['Close'],
                        name="Harga"
                    )])
                    fig.update_layout(
                        xaxis_rangeslider_visible=False,
                        height=400,
                        margin=dict(l=0, r=0, t=30, b=0),
                        template="plotly_dark"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Menunggu data grafik terkumpul...")
            else:
                st.warning("Menunggu respons dari server Indodax...")
        except Exception as e:
            st.error(f"Grafik belum siap: {str(e)}")
            
        st.markdown("---")
        
        # 3. Log Aktivitas & Detail Posisi
        col_log, col_pos = st.columns([2, 1])
        
        with col_log:
            st.subheader("📝 Catatan Sistem (Live)")
            st.info(execution_bot.bot_state["last_action"])
            st.caption("Catatan: AI Gemini menganalisis data Makro (4H) dan Mikro (15M) sekaligus. Trailing Stop bekerja secara real-time di latar belakang.")
            
        with col_pos:
            st.subheader("💼 Portofolio Terbuka")
            if execution_bot.bot_state["positions"]:
                posisi = execution_bot.bot_state["positions"]
                df_posisi = pd.DataFrame.from_dict(posisi, orient='index')
                df_posisi = df_posisi.rename(columns={
                    "amount": "Koin",
                    "buy_price": "Harga Beli",
                    "high_price": "Titik Tertinggi (TS)"
                })
                kolom_tampil = ["Koin", "Harga Beli", "Titik Tertinggi (TS)"]
                st.dataframe(df_posisi[kolom_tampil].style.format("{:,.0f}", subset=["Harga Beli", "Titik Tertinggi (TS)"]))
            else:
                st.write("Belum ada posisi terbuka.")

        st.markdown("---")
        
        # =================================================================
        # FITUR BARU: 4. STATISTIK KINERJA BOT
        # =================================================================
        st.subheader("📊 Papan Skor Kinerja (Riwayat Perdagangan)")
        
        # Mengambil riwayat dari bot_state (dengan default list kosong agar tidak error)
        riwayat_trade = execution_bot.bot_state.get("trade_history", [])
        
        # Perhitungan Matematika Papan Skor
        total_trade = len(riwayat_trade)
        transaksi_profit = sum(1 for trade in riwayat_trade if trade.get("pnl", 0) > 0)
        win_rate = (transaksi_profit / total_trade * 100) if total_trade > 0 else 0.0
        total_pnl = sum(trade.get("pnl", 0) for trade in riwayat_trade)
        
        # Menampilkan metrik dalam 3 kolom
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("Total Eksekusi Jual", f"{total_trade} Transaksi")
        with col_stat2:
            st.metric("Tingkat Kemenangan (Win Rate)", f"{win_rate:.1f}%")
        with col_stat3:
            st.metric("Akumulasi Profit / Loss", f"Rp {total_pnl:,.0f}")
            
        # Menampilkan Tabel Riwayat Jika Ada
        if total_trade > 0:
            df_history = pd.DataFrame(riwayat_trade)
            # Menyusun urutan kolom agar rapi
            df_history = df_history[["waktu", "koin", "harga_beli", "harga_jual", "pnl", "alasan"]]
            df_history.columns = ["Waktu", "Aset", "Beli (Rp)", "Jual (Rp)", "Profit/Loss (Rp)", "Keterangan Keluar"]
            
            # Format tampilan angka di tabel
            st.dataframe(
                df_history.style.format({
                    "Beli (Rp)": "{:,.0f}", 
                    "Jual (Rp)": "{:,.0f}", 
                    "Profit/Loss (Rp)": "{:,.0f}"
                }), 
                use_container_width=True
            )
        else:
            st.info("Buku catatan masih kosong. Bot belum menyelesaikan transaksi jual apa pun sejak dihidupkan.")

# Render halaman
render_layar_utama()

# ==============================================================================
# LOGIKA PENYEGARAN OTOMATIS (AUTO-REFRESH)
# ==============================================================================
if execution_bot.BOT_IS_RUNNING:
    time.sleep(3) # Menyegarkan UI setiap 3 detik
    st.rerun()
