"""
================================================================================
FILE: anime_assistant.py
DESKRIPSI: Modul khusus untuk mengurus tampilan dan interaksi Asisten Anime.
Ini menjaga file utama (app.py) tetap bersih.
================================================================================
"""
import streamlit as st
import requests
from streamlit_lottie import st_lottie

@st.cache_data
def muat_animasi_lottie(url: str):
    """Fungsi ringan untuk menarik data animasi JSON dari internet."""
    try:
        r = requests.get(url)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None

def tampilkan_asisten(bot_state):
    """
    Fungsi ini akan dipanggil oleh app.py untuk menggambar karakter anime
    di layar beserta teks penyemangatnya.
    """
    # Tautan ke animasi Lottie
    lottie_url = "https://assets9.lottiefiles.com/packages/lf20_bhebjzpu.json" 
    animasi_asisten = muat_animasi_lottie(lottie_url)
    
    st.markdown("---")
    if animasi_asisten:
        st.caption("🌸 **Eagle-Chan siap menemanimu!**")
        st_lottie(animasi_asisten, height=180, key="anime_assistant")
        
        # Logika teks penyemangat adaptif membaca dari bot_state
        total_pnl = sum(trade.get("pnl", 0) for trade in bot_state.get("trade_history", []))
        
        if total_pnl < 0:
            st.info("💡 Tidak apa-apa merah sedikit! Trailing stop menyelamatkan kita dari kerugian yang lebih dalam. Santai dulu yuk!")
        elif total_pnl > 0:
            st.success("🎉 Wow, kita sedang profit! Eagle-Chan bangga padamu!")
        else:
            st.info("☕ Pasar sedang dipantau. Siapkan kopimu, biarkan AI yang bekerja keras!")
