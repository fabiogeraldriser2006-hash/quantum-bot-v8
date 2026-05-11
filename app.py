"""
================================================================================
FILE: app.py
DESKRIPSI: Dashboard Streamlit Utama (Full Features).
Menampilkan Candlestick, Kontrol Bot, Portofolio, Dasbor Statistik, Dompet Live,
Sistem Keamanan Login, dan Selektor Multi-Brain AI.
================================================================================
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
import os
from datetime import datetime
import config
import execution_bot
import data_engine
import anime_assistant

# 1. PENGATURAN HALAMAN DASBOR
st.set_page_config(
    page_title="Eagle Focus Quant OS",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 🔒 SISTEM KEAMANAN LOGIN
# ==============================================================================
def check_password():
    def password_entered():
        correct_password = st.secrets.get("APP_PASSWORD", "eagle123")
        input_user = st.session_state.get("password_input", "")
        
        if input_user == correct_password:
            st.session_state["password_correct"] = True
            if "password_input" in st.session_state:
                del st.session_state["password_input"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔒 Area Terbatas: Eagle Focus OS")
        st.text_input("🔑 Masukkan PIN/Password untuk mengakses Dasbor:", type="password", on_change=password_entered, key="password_input")
        return False
    
    elif not st.session_state["password_correct"]:
        st.title("🔒 Area Terbatas: Eagle Focus OS")
        st.text_input("🔑 Masukkan PIN/Password untuk mengakses Dasbor:", type="password", on_change=password_entered, key="password_input")
        st.error("❌ Password salah. Akses ditolak.")
        return False
    
    return True

if not check_password():
    st.stop()

# ==============================================================================
# INISIALISASI VARIABEL
# ==============================================================================
if "bot_started" not in st.session_state:
    st.session_state.bot_started = False

# ==============================================================================
# PANEL KENDALI (SIDEBAR)
# ==============================================================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/artificial-intelligence.png", width=60)
    st.title("⚙️ Panel Kendali")
    
    if st.button("🚪 Logout / Kunci Layar"):
        del st.session_state["password_correct"]
        st.rerun()

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
    
    # <--- TAMBAHAN BARU: SELEKTOR OTAK AI --->
    st.subheader("🧠 Pilih Otak AI")
    daftar_ai = ["Gemini", "OpenAI (ChatGPT)", "Anthropic (Claude)", "Groq (Llama-3)"]
    ai_saat_ini = execution_bot.bot_state.get("selected_ai", "Gemini")
    
    pilihan_ai = st.selectbox("Pilih mesin analitik:", daftar_ai, index=daftar_ai.index(ai_saat_ini))
    execution_bot.bot_state["selected_ai"] = pilihan_ai
    
    # Cek apakah API Key untuk AI yang dipilih sudah terpasang
    kunci_rahasia = ""
    if pilihan_ai == "Gemini":
        kunci_rahasia = os.environ.get("GEMINI_API_KEY", "")
    elif pilihan_ai == "OpenAI (ChatGPT)":
        kunci_rahasia = os.environ.get("OPENAI_API_KEY", "")
    elif pilihan_ai == "Anthropic (Claude)":
        kunci_rahasia = os.environ.get("ANTHROPIC_API_KEY", "")
    elif pilihan_ai == "Groq (Llama-3)":
        kunci_rahasia = os.environ.get("GROQ_API_KEY", "")
        
    if not kunci_rahasia:
        st.warning(f"⚠️ API Key untuk {pilihan_ai} belum ditemukan di sistem (Secrets).")
    
    st.markdown("---")
    
    # Mode Trading & Kredensial Indodax
    st.subheader("🏦 Mode Trading")
    mode_simulasi = st.toggle("Mode Simulasi (Paper Trading)", value=execution_bot.bot_state["mode_simulasi"])
    execution_bot.bot_state["mode_simulasi"] = mode_simulasi
    
    if not mode_simulasi:
        st.warning("⚠️ MODE LIVE AKTIF. Bot menggunakan saldo asli Indodax.")
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

    st.markdown("---")

    # Dompet Indodax
    if not mode_simulasi:
        with st.expander("💰 Lihat Dompet Indodax"):
            if st.button("🔄 Tarik Data Saldo", use_container_width=True):
                with st.spinner("Menghubungi Indodax..."):
                    aset_user = execution_bot.ambil_seluruh_aset()
                    if aset_user:
                        df_aset = pd.DataFrame(aset_user)
                        st.dataframe(df_aset, hide_index=True, use_container_width=True)
                    else:
                        st.info("Dompet kosong atau API Key belum valid.")
    else:
        with st.expander("💰 Lihat Dompet Indodax"):
            st.info("Matikan Mode Simulasi untuk melihat saldo Indodax asli.")

    # Asisten Anime
    anime_assistant.tampilkan_asisten(execution_bot.bot_state)

# ==============================================================================
# LAYAR UTAMA (GRAFIK, LOG, & METRIK STATISTIK)
# ==============================================================================
st.title("🦅 Eagle Focus: Live Market & AI Analysis")
st.markdown("---")

placeholder_utama = st.empty()

@st.fragment(run_every=3)
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
            st.caption("Catatan: AI menganalisis data Makro (4H) dan Mikro (15M) sekaligus. Trailing Stop bekerja secara real-time di latar belakang.")
            
        with col_pos:
            st.subheader("💼 Portofolio Terbuka")
            posisi_aktif = execution_bot.bot_state["positions"] if execution_bot.bot_state["mode_simulasi"] else execution_bot.bot_state["live_positions"]
            
            if posisi_aktif:
                df_posisi = pd.DataFrame.from_dict(posisi_aktif, orient='index')
                df_posisi = df_posisi.rename(columns={
                    "amount": "Koin",
                    "buy_price": "Harga Beli",
                    "high_price": "Titik Tertinggi (TS)"
                })
                if "Koin" in df_posisi.columns:
                    kolom_tampil = ["Koin", "Harga Beli", "Titik Tertinggi (TS)"]
                else:
                    kolom_tampil = ["Harga Beli", "Titik Tertinggi (TS)"]
                
                st.dataframe(df_posisi[kolom_tampil].style.format("{:,.0f}", subset=["Harga Beli", "Titik Tertinggi (TS)"]))
            else:
                st.write("Belum ada posisi terbuka.")

        st.markdown("---")
        
        # 4. STATISTIK KINERJA BOT
        st.subheader("📊 Papan Skor Kinerja (Riwayat Perdagangan)")
        
        riwayat_trade = execution_bot.bot_state.get("trade_history", [])
        
        total_trade = len(riwayat_trade)
        transaksi_profit = sum(1 for trade in riwayat_trade if trade.get("pnl", 0) > 0)
        win_rate = (transaksi_profit / total_trade * 100) if total_trade > 0 else 0.0
        total_pnl = sum(trade.get("pnl", 0) for trade in riwayat_trade)
        
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("Total Eksekusi Jual", f"{total_trade} Transaksi")
        with col_stat2:
            st.metric("Tingkat Kemenangan (Win Rate)", f"{win_rate:.1f}%")
        with col_stat3:
            st.metric("Akumulasi Profit / Loss", f"Rp {total_pnl:,.0f}")
            
        if total_trade > 0:
            df_history = pd.DataFrame(riwayat_trade)
            df_history = df_history[["waktu", "koin", "harga_beli", "harga_jual", "pnl", "alasan"]]
            df_history.columns = ["Waktu", "Aset", "Beli (Rp)", "Jual (Rp)", "Profit/Loss (Rp)", "Keterangan Keluar"]
            
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

# Memanggil fungsi render yang sudah di-fragmentasi
render_layar_utama()
