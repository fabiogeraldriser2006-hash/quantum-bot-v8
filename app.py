import streamlit as st
import config
import execution_bot

st.set_page_config(page_title="Eagle Focus Bot", layout="wide")

st.title("🦅 Eagle Focus - Koin Tunggal & Survival 24 Jam")

# SIDEBAR UNTUK KENDALI
with st.sidebar:
    st.header("⚙️ Kontrol Bot")
    
    # Pilih Koin (Sinkron ke bot_state)
    target = st.selectbox("Pilih Koin Target", list(config.CRYPTO_MAP.keys()))
    execution_bot.bot_state["selected_coin"] = target
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("MULAI", use_container_width=True):
            execution_bot.start_bot()
    with col2:
        if st.button("STOP", use_container_width=True):
            execution_bot.stop_bot()

# DASHBOARD UTAMA
col_info1, col_info2 = st.columns(2)

with col_info1:
    st.metric("Koin Aktif", execution_bot.bot_state["selected_coin"])
    st.info(f"Log: {execution_bot.bot_state['last_action']}")

with col_info2:
    st.metric("Modal (Simulasi)", f"Rp {execution_bot.bot_state['cash']:,.0f}")
    if execution_bot.bot_state["positions"]:
        st.warning("Status: Memiliki Posisi Terbuka")
    else:
        st.success("Status: Menunggu Sinyal Beli")

st.write("---")
st.caption("Catatan: Analisis AI diperbarui setiap 72 menit untuk memastikan bot bertahan 24 jam dengan jatah 20 kuota Gemini.")
