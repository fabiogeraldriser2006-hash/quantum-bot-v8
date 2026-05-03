"""
=========================================================
FILE: app.py
DESKRIPSI: Layar Antarmuka Utama (User Interface) Streamlit.
Berfungsi sebagai 'Pos Pemantau'. Menggunakan float() untuk
mendukung harga koin mikro (desimal) seperti Pepe atau SHIB.
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
import backtest_engine

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
    
    auto_pilot_toggle = st.toggle("Aktifkan Auto-Pilot (Background)", value=execution_bot.BOT_IS_RUNNING)
    
    if auto_pilot_toggle:
        pesan = execution_bot.mulai_bot_latar_belakang()
        st.success("⚡ AUTO-PILOT ON (Berjalan di latar belakang)")
    else:
        pesan = execution_bot.hentikan_bot_latar_belakang()
        st.warning("⏸️ AUTO-PILOT OFF")
        
    st.info(f"Status Terakhir: {execution_bot.bot_state['last_action']}")
    st.button("🔄 Refresh Tampilan Layar", use_container_width=True)
    
    st.markdown("---")
    execution_bot.bot_state["scan_speed"] = st.slider("⚡ Kecepatan Pindai Bot (Detik)", 3, 60, 5, 1)
    execution_bot.bot_state["atr_multiplier"] = st.slider("🛡️ Jarak Trailing Stop (ATR)", 1.0, 5.0, 2.0, 0.1)
        
    st.markdown("---")
    st.markdown("### 🔐 LIVE API CREDENTIALS")
    execution_bot.bot_state["api_key"] = st.text_input("Indodax API Key", type="password")
    execution_bot.bot_state["secret_key"] = st.text_input("Indodax Secret Key", type="password")
    
    mode_trading = "🔴 LIVE TRADING" if execution_bot.bot_state["api_key"] and execution_bot.bot_state["secret_key"] else "🟢 SIMULATION"
    st.markdown(f"**Status Mode:** {mode_trading}")

    st.markdown("---")
    st.markdown("### 🏦 Capital & Sizing Engine")
    
    if st.button("🔄 Reset Portfolio & History"):
        execution_bot.bot_state["cash"] = config.MODAL_AWAL_DEFAULT
        execution_bot.bot_state["positions"] = {}
        execution_bot.bot_state["trade_history"] = []
        st.rerun()

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
    pilihan_koin = st.selectbox("Pilih Aset Kripto untuk Grafik Detail", list(config.CRYPTO_MAP.keys()))
    interval_chart = st.selectbox("Timeframe", ["15m", "1h", "4h", "1D"], index=0)

    ticker_koin = config.CRYPTO_MAP[pilihan_koin]["ticker"]
    tv_koin = config.CRYPTO_MAP[pilihan_koin]["tv"]
    
    data_live = data_engine.tarik_data_live_indodax()
    
    if data_live:
        ticker_data = data_live[ticker_koin]
        # PERBAIKAN 1: Gunakan float() bukan int() untuk grafik utama
        harga_sekarang = float(ticker_data['last']) 
        
        st.markdown("---")
        st.markdown("### 🌐 Radar Pengawasan Multi-Koin (Live Scanner)")
        
        if execution_bot.BOT_IS_RUNNING:
            nama_semua_koin = ", ".join(config.CRYPTO_MAP.keys())
            st.info(f"⚡ **Pemindai Latar Belakang Aktif:** Sedang memantau pergerakan {nama_semua_koin} secara terus-menerus.")
            
            kolom_radar = st.columns(len(config.CRYPTO_MAP))
            
            for i, (koin_nama, data_koin) in enumerate(config.CRYPTO_MAP.items()):
                with kolom_radar[i % len(kolom_radar)]:
                    # PERBAIKAN 2: Gunakan float() dan pastikan koin ada di data API
                    if data_koin['ticker'] in data_live:
                        harga_realtime_koin = float(data_live[data_koin['ticker']]['last'])
                    else:
                        harga_realtime_koin = 0.0
                    
                    status_posisi = "✅ Terisi (Hold)" if koin_nama in execution_bot.bot_state["positions"] else "⏳ Standby (Mencari Sinyal)"
                    warna_teks = "#00FF00" if koin_nama in execution_bot.bot_state["positions"] else "#E0E0E0"
                    
                    # Logika tampilan: Tampilkan desimal jika harga koin sangat murah (Koin Mikro)
                    if harga_realtime_koin < 10:
                        teks_harga = f"Rp {harga_realtime_koin:,.4f}"
                    else:
                        teks_harga = f"Rp {harga_realtime_koin:,.0f}"
                    
                    st.markdown(f"""
                    <div class='portfolio-box' style='text-align:center;'>
                        <h4 style='margin:0;'>{koin_nama}</h4>
                        <p style='margin:5px 0; font-size:1.2em;'>{teks_harga}</p>
                        <span style='color:{warna_teks}; font-size:0.9em;'>{status_posisi}</span>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.warning("⏸️ Bot Multi-Koin Latar Belakang sedang dinonaktifkan.")
            
        st.markdown("---")

        df_chart, status_data = data_engine.tarik_grafik_klines_aman(tv_koin, interval_chart, 120, ticker_data)
        
        if not df_chart.empty:
            df_chart = data_engine.hitung_indikator_teknikal(df_chart)
            c_chart, c_panel = st.columns([7, 3])
            
            with c_chart:
                st.markdown(f"### 📈 Institutional Chart - {tv_koin}")
                if "Synthetic" in status_data:
                    st.warning("⚠️ Indodax memblokir grafik. Menampilkan grafik cadangan (Sintetis).")
                    
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
                narasi_ai, _ = quant_brain.prediksi_ai_market(df_chart, pilihan_koin, harga_sekarang, interval_chart, sentimen_sekarang)
                st.markdown(f"<div class='ai-box'>{narasi_ai}</div>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📋 Portofolio & Saldo")
        
        api_key_aktif = execution_bot.bot_state["api_key"]
        secret_key_aktif = execution_bot.bot_state["secret_key"]

        if api_key_aktif and secret_key_aktif:
            st.markdown("#### 🏦 Saldo Asli Indodax Anda")
            info_wallet = execution_bot.indodax_private_api('getInfo')
            
            if info_wallet.get('success') == 1:
                saldo_asli = info_wallet['return']['balance']
                idr_asli = float(saldo_asli.get('idr', 0))
                
                execution_bot.bot_state["cash"] = idr_asli 
                st.info(f"💵 **Uang Kas (IDR):** Rp {idr_asli:,.0f}")
                
                koin_ditemukan = False
                for koin_nama, data_koin in config.CRYPTO_MAP.items():
                    simbol = data_koin['ticker'].split('_')[0] 
                    jumlah = float(saldo_asli.get(simbol, 0))
                    if jumlah > 0:
                        st.success(f"🪙 **{koin_nama}:** {jumlah:.6f}")
                        koin_ditemukan = True
                
                if not koin_ditemukan:
                    st.caption("Belum ada koin kripto utama di dompet Indodax Anda.")
            else:
                st.error(f"Gagal memuat dompet Indodax: {info_wallet.get('error')}")
        else:
            st.markdown("#### 🏦 Saldo Simulasi (Virtual)")
            uang_kas = execution_bot.bot_state["cash"]
            st.info(f"💵 **Uang Kas Tersedia (Simulasi):** Rp {uang_kas:,.0f}")

        st.markdown("#### 🤖 Posisi Terbuka (Dikelola Bot)")
        if execution_bot.bot_state["positions"]:
            for koin, data in execution_bot.bot_state["positions"].items():
                hrg_koin_ini = float(data_live[config.CRYPTO_MAP[koin]["ticker"]]['last']) # PERBAIKAN 3
                nilai_jual_bersih = (data['amount'] * hrg_koin_ini) * (1 - config.FEE_RATE)
                modal_awal_idr = (data['amount'] * data['avg_price']) / (1 - config.FEE_RATE)
                
                pnl_asli = nilai_jual_bersih - modal_awal_idr
                pnl_persen = (pnl_asli / modal_awal_idr) * 100
                warna = "#00FF00" if pnl_asli >= 0 else "#FF0000"
                
                st.markdown(f"<div class='portfolio-box'><strong>{koin}</strong><br>Koin Diterima: {data['amount']:.5f} | Avg Price: Rp {data['avg_price']:,.4f}<br>Estimasi Jual: Rp {nilai_jual_bersih:,.0f} <span style='color:{warna};'>({pnl_persen:+.2f}%)</span></div>", unsafe_allow_html=True)
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
    st.markdown("### ⏪ Mesin Waktu Backtesting (Simulator AI)")
    st.markdown("Uji performa Jaringan Saraf AI dan ketahanan Trailing Stop Anda menggunakan data masa lalu.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        bt_koin = st.selectbox("Koin untuk diuji", list(config.CRYPTO_MAP.keys()), key="bt_coin")
    with col2:
        bt_durasi = st.selectbox("Durasi Data Historis", [7, 14, 30], format_func=lambda x: f"{x} Hari Terakhir")
    with col3:
        bt_tf = st.selectbox("Timeframe Analisis", ["15m", "1h", "4h"], index=1, key="bt_tf")
        
    bt_modal = st.number_input("Modal Awal Simulasi (IDR)", value=10000000.0, step=1000000.0)
    
    if st.button("▶️ JALANKAN SIMULASI BACKTEST", type="primary", use_container_width=True):
        with st.spinner(f"⏳ Sedang memutar waktu... Mengunduh data {bt_koin} dan melatih AI. Mohon tunggu..."):
            
            # Memanggil fungsi dari file backtest_engine.py
            hasil, jurnal = backtest_engine.jalankan_simulasi_backtest(
                koin=bt_koin, 
                timeframe=bt_tf, 
                durasi_hari=bt_durasi, 
                modal_awal=bt_modal,
                atr_multiplier=execution_bot.bot_state["atr_multiplier"]
            )
            
            if hasil is None:
                st.error(f"❌ Simulasi gagal: {jurnal}")
            else:
                if "Synthetic" in hasil["status_data"]:
                    st.warning("⚠️ Indodax membatasi penarikan data riwayat dalam jumlah besar. Menggunakan Data Sintetis (Tiruan) untuk simulasi.")
                else:
                    st.success("✅ Simulasi masa lalu selesai menggunakan Data Asli Indodax!")
                
                # Menampilkan Papan Skor Hasil Simulasi
                st.markdown("### 📊 Papan Skor Backtest")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Modal Awal", f"Rp {hasil['modal_awal']:,.0f}")
                c2.metric("Saldo Akhir (Estimasi)", f"Rp {hasil['saldo_akhir']:,.0f}", f"{hasil['total_profit']:,.0f} IDR")
                c3.metric("Total Transaksi Selesai", hasil['total_trade'])
                c4.metric("Akurasi Menang (Win Rate)", f"{hasil['win_rate']:.1f}%")
                
                # Menampilkan Jurnal Transaksi
                st.markdown("#### 📓 Jurnal Transaksi Virtual")
                if not jurnal.empty:
                    st.dataframe(jurnal, use_container_width=True)
                else:
                    st.info("Tidak ada transaksi (AI memutuskan untuk HOLD terus selama periode ini).")
