"""
=========================================================
FILE: app.py
DESKRIPSI: Layar Antarmuka Utama (User Interface) Streamlit.
Berfungsi sebagai 'Pos Pemantau'. Hanya mengambil data dari 
execution_bot.py dan tidak lagi menggunakan auto-reload 
sehingga layar bebas dari kedipan (flickering).
=========================================================
"""

import streamlit as st
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import glob
import os

# Memanggil modul-modul modular yang sudah kita buat
import config
import data_engine
import quant_brain
import execution_bot

# ==========================================
# 1. KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(
    page_title="Quantum Hedge Fund V8 - Modular Edition",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Desain CSS (Tampilan Visual)
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; padding-bottom: 0rem; max-width: 98%; }
    h1, h2, h3, p, span { color: #E0E0E0; font-family: 'Courier New', Courier, monospace; }
    .stMetric-value { color: #00FF00 !important; font-weight: bold; }
    .ai-box { background-color: #1A1A1A; padding: 20px; border-left: 5px solid #BB86FC; border-radius: 5px; margin-bottom: 15px;}
    .portfolio-box { background-color: #262730; padding: 15px; border-radius: 8px; border: 1px solid #444; }
    hr { margin-top: 1rem; margin-bottom: 1rem; border-color: #333; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. PANEL KENDALI (SIDEBAR)
# ==========================================
with st.sidebar:
    st.markdown("### 🤖 AUTO-PILOT CONTROL")
    
    # Tombol On/Off untuk menyalakan/mematikan pekerja latar belakang (Thread)
    auto_pilot_toggle = st.toggle("Aktifkan Auto-Pilot (Background)", value=execution_bot.BOT_IS_RUNNING)
    
    if auto_pilot_toggle:
        pesan = execution_bot.mulai_bot_latar_belakang()
        st.success("⚡ AUTO-PILOT ON (Berjalan di latar belakang)")
    else:
        pesan = execution_bot.hentikan_bot_latar_belakang()
        st.warning("⏸️ AUTO-PILOT OFF")
        
    st.info(f"Status Terakhir: {execution_bot.bot_state['last_action']}")
    
    # Tombol Refresh Manual: Kunci utama agar layar tidak berkedip otomatis!
    # Mengklik tombol ini hanya akan memaksa Streamlit memperbarui angka di layar 1 kali.
    st.button("🔄 Refresh Tampilan Layar", use_container_width=True)
    
    st.markdown("---")
    # Sinkronisasi pengaturan Slider ke Memori Bot di execution_bot.py
    execution_bot.bot_state["scan_speed"] = st.slider("⚡ Kecepatan Pindai Bot (Detik)", 3, 60, 5, 1)
    execution_bot.bot_state["atr_multiplier"] = st.slider("🛡️ Jarak Trailing Stop (ATR)", 1.0, 5.0, 2.0, 0.1)
        
    st.markdown("---")
    st.markdown("### 🔐 LIVE API CREDENTIALS")
    # Menyimpan kunci API langsung ke dalam memori bot
    execution_bot.bot_state["api_key"] = st.text_input("Indodax API Key", type="password")
    execution_bot.bot_state["secret_key"] = st.text_input("Indodax Secret Key", type="password")
    
    mode_trading = "🔴 LIVE TRADING" if execution_bot.bot_state["api_key"] else "🟢 SIMULATION"
    st.markdown(f"**Status Mode:** {mode_trading}")

    st.markdown("---")
    st.markdown("### 🏦 Capital & Sizing Engine")
    
    # Tombol Reset
    if st.button("🔄 Reset Portfolio & History"):
        execution_bot.bot_state["cash"] = config.MODAL_AWAL_DEFAULT
        execution_bot.bot_state["positions"] = {}
        execution_bot.bot_state["trade_history"] = []
        st.rerun()

    # Logika alokasi dana
    target_aum = st.number_input("Target Total AUM (IDR)", value=config.MODAL_AWAL_DEFAULT, step=10000000.0)
    position_size_perc = st.slider("Alokasi Beli per Trade (%)", 10.0, 100.0, 50.0, 5.0)
    execution_bot.bot_state["buy_amount_idr"] = target_aum * (position_size_perc / 100)
    
    st.info(f"**Dana Dieksekusi per Koin:** Rp {execution_bot.bot_state['buy_amount_idr']:,.0f}")
    
    st.markdown("---")
    st.markdown("### 🛠️ Maintenance Sistem")
    if st.button("🗑️ Reset & Perbaiki Memori AI", use_container_width=True):
        file_ditemukan = glob.glob("*.pkl")
        file_dihapus = 0
        for file_pkl in file_ditemukan:
            try:
                os.remove(file_pkl)
                file_dihapus += 1
            except Exception as e:
                st.error(f"Gagal menghapus {file_pkl}: {e}")
        if file_dihapus > 0:
            st.success(f"✅ {file_dihapus} file memori AI yang rusak berhasil dibersihkan!")
        else:
            st.info("ℹ️ Tidak ada file memori AI yang rusak.")

# ==========================================
# 3. LAYAR UTAMA (MAIN DASHBOARD)
# ==========================================
st.title("🦅 QUANTUM DESK V8 - Modular Architecture")

tab_live, tab_backtest = st.tabs(["🔴 Live Trading Dashboard", "⏪ Mesin Backtesting"])

# ---------------------------------------------------------
# TAB 1: LIVE DASHBOARD
# ---------------------------------------------------------
with tab_live:
    # Memilih Koin dari Peta Koin di config.py
    pilihan_koin = st.selectbox("Pilih Aset Kripto untuk Dipantau", list(config.CRYPTO_MAP.keys()))
    interval_chart = st.selectbox("Timeframe", ["15m", "1h", "4h", "1D"], index=0)

    ticker_koin = config.CRYPTO_MAP[pilihan_koin]["ticker"]
    tv_koin = config.CRYPTO_MAP[pilihan_koin]["tv"]
    
    # Menarik data dari data_engine.py
    data_live = data_engine.tarik_data_live_indodax()
    
    if data_live:
        ticker_data = data_live[ticker_koin]
        harga_sekarang = int(ticker_data['last'])
        
        # Menarik grafik dan status data (Asli/Sintetis)
        df_chart, status_data = data_engine.tarik_grafik_klines_aman(tv_koin, interval_chart, 120, ticker_data)
        
        if not df_chart.empty:
            # Menghitung MACD, RSI, dll dari data_engine.py
            df_chart = data_engine.hitung_indikator_teknikal(df_chart)
            c_chart, c_panel = st.columns([7, 3])
            
            with c_chart:
                st.markdown(f"### 📈 Institutional Chart - {tv_koin}")
                if "Synthetic" in status_data:
                    st.warning("⚠️ Indodax memblokir grafik. Menampilkan grafik cadangan (Sintetis).")
                    
                # Menggambar Grafik Candlestick
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
                fig.add_trace(go.Candlestick(x=df_chart['Date'], open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'], name='Spot'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_chart['Date'], y=df_chart['BB_Upper'], line=dict(color='rgba(255,255,255,0.2)', dash='dash'), name='BB Up'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_chart['Date'], y=df_chart['BB_Lower'], line=dict(color='rgba(255,255,255,0.2)', dash='dash'), name='BB Low', fill='tonexty'), row=1, col=1)
                colors = ['green' if val >= 0 else 'red' for val in df_chart['MACD_Hist']]
                fig.add_trace(go.Bar(x=df_chart['Date'], y=df_chart['MACD_Hist'], marker_color=colors, name='MACD Hist'), row=2, col=1)
                fig.add_trace(go.Scatter(x=df_chart['Date'], y=df_chart['MACD'], line=dict(color='#2196F3'), name='MACD'), row=2, col=1)
                fig.update_layout(height=650, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="#121212", plot_bgcolor="#121212", xaxis_rangeslider_visible=False, font=dict(color="#E0E0E0"), showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

            with c_panel:
                st.markdown("### 🧠 AI Analysis")
                sentimen_sekarang = data_engine.tarik_sentimen_global()
                
                # Memanggil Otak AI dari quant_brain.py
                narasi_ai, _ = quant_brain.prediksi_ai_market(df_chart, pilihan_koin, harga_sekarang, interval_chart, sentimen_sekarang)
                st.markdown(f"<div class='ai-box'>{narasi_ai}</div>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📋 Portofolio & Saldo")
        
        uang_kas = execution_bot.bot_state["cash"]
        st.info(f"💵 **Uang Kas Tersedia (Virtual/Simulasi):** Rp {uang_kas:,.0f}")

        if execution_bot.bot_state["positions"]:
            for koin, data in execution_bot.bot_state["positions"].items():
                hrg_koin_ini = int(data_live[config.CRYPTO_MAP[koin]["ticker"]]['last'])
                nilai_jual_bersih = (data['amount'] * hrg_koin_ini) * (1 - config.FEE_RATE)
                modal_awal_idr = (data['amount'] * data['avg_price']) / (1 - config.FEE_RATE)
                
                pnl_asli = nilai_jual_bersih - modal_awal_idr
                pnl_persen = (pnl_asli / modal_awal_idr) * 100
                warna = "#00FF00" if pnl_asli >= 0 else "#FF0000"
                
                st.markdown(f"<div class='portfolio-box'><strong>{koin}</strong><br>Koin Diterima: {data['amount']:.5f} | Avg Price: Rp {data['avg_price']:,.0f}<br>Estimasi Jual: Rp {nilai_jual_bersih:,.0f} <span style='color:{warna};'>({pnl_persen:+.2f}%)</span></div>", unsafe_allow_html=True)
        else:
            st.caption("Belum ada posisi terbuka.")

        st.markdown("---")
        st.markdown("### 📜 Riwayat Transaksi (Trade History)")
        if execution_bot.bot_state["trade_history"]:
            df_history = pd.DataFrame(execution_bot.bot_state["trade_history"])
            st.dataframe(df_history.iloc[::-1].reset_index(drop=True), use_container_width=True)
        else:
            st.caption("Belum ada riwayat transaksi.")

# ---------------------------------------------------------
# TAB 2: BACKTESTING ROOM (Mesin Waktu)
# ---------------------------------------------------------
with tab_backtest:
    st.markdown("### ⏪ Mesin Waktu Backtesting")
    st.markdown("Fitur Backtesting akan dibangun pada langkah berikutnya setelah fondasi Live Trading stabil.")
    st.info("Kini aplikasi Anda 100% termodularisasi dan bebas dari kedipan layar!")
