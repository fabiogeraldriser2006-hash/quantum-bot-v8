"""
================================================================================
FILE: app.py
DESKRIPSI: Dashboard Streamlit Utama (Full Features).
Menampilkan Candlestick, Kontrol Mode Simulasi/Live, dan Koneksi Indodax.
================================================================================
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
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
    koin_aktif = execution_bot.bot_state.get("selected_coin", "Bitcoin")
    try:
        index_koin = daftar_koin.index(koin_aktif)
    except ValueError:
        index_koin = 0
        
    pilihan_koin = st.selectbox("Pilih koin pantauan:", daftar_koin, index=index_koin)
    execution_bot.bot_state["selected_coin"] = pilihan_koin
    
    st.markdown("---")
    
    # Mode Trading & Kredensial Indodax
    st.subheader("🏦 Mode Trading")
    mode_simulasi = st.toggle("Mode Simulasi (Paper Trading)", value=execution_bot.bot_state["mode_simulasi"])
    execution_bot.bot_state["mode_simulasi"] = mode_simulasi
    
    if not mode_simulasi:
        st.warning("⚠️ MODE LIVE AKTIF. Bot akan menggunakan saldo asli Indodax.")
        api_key = st.text_input("Indodax API Key", type="password")
        secret_key = st.text_input("Indodax Secret Key", type="password")
        execution_bot.bot_state["api_key_indodax"] = api_key
        execution_bot.bot_state["secret_key_indodax"] = secret_key
    else:
        st.info("✅ Mode Simulasi Aktif. Menggunakan uang virtual.")
        
    st.markdown("---")
    
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
# LAYAR UTAMA (GRAFIK & METRIK)
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
            st.metric("Cash Balance (Simulasi)", f"Rp {execution_bot.bot_state['cash']:,.0f}")
            
        st.markdown("---")
        
        # 2. Area Grafik Candlestick
        st.subheader(f"📈 Grafik Harga {koin_pilihan} (15 Menit)")
        try:
            # Mengambil data live untuk menggambar grafik
            data_live = data_engine.tarik_data_live_indodax()
            ticker = data_koin['ticker']
            
            if ticker in data_live:
                df_chart, _ = data_engine.tarik_grafik_klines_aman(data_koin['tv'], "15m", 50, data_live[ticker])
                
                if not df_chart.empty:
                    # Membuat Candlestick dengan Plotly
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
                st.error("Gagal terhubung ke data live Indodax.")
        except Exception as e:
            st.error(f"Grafik belum siap: {str(e)}")

        st.markdown("---")
        
        # 3. Log Aktivitas & Detail Posisi
        col_log, col_pos = st.columns([2, 1])
        
        with col_log:
            st.subheader("📝 Catatan Sistem (Live)")
            st.info(execution_bot.bot_state["last_action"])
            st.caption("Catatan: AI Gemini memperbarui analisis penuh setiap 72 menit untuk menghemat 20 kuota harian. Di sela waktu tersebut, Trailing Stop dan Indikator akan melindungi posisi Anda.")
            
        with col_pos:
            st.subheader("💼 Portofolio")
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

# Render halaman
render_layar_utama()

# ==============================================================================
# LOGIKA PENYEGARAN OTOMATIS (AUTO-REFRESH)
# ==============================================================================
if execution_bot.BOT_IS_RUNNING:
    time.sleep(3) # Menyegarkan UI setiap 3 detik agar grafik dan log selalu update
    st.rerun()
