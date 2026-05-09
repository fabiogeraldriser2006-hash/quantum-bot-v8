"""
================================================================================
FILE: anime_assistant.py
DESKRIPSI: Modul Asisten Anime menggunakan SVG murni yang dirender via st.components
agar dijamin muncul sebagai gambar, bukan teks.
================================================================================
"""
import streamlit as st
import streamlit.components.v1 as components # <--- TAMBAHAN: Modul khusus untuk gambar/HTML

def tampilkan_asisten(bot_state):
    """
    Fungsi ini menggambar karakter 'Eagle-Chan' menggunakan komponen HTML Streamlit.
    """
    st.markdown("---")
    st.caption("🌸 **Eagle-Chan siap menemanimu!**")

    # Kode SVG karakter anime
    svg_karakter = """
    <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
        <svg width="150" height="150" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
            <!-- Wajah -->
            <circle cx="50" cy="50" r="40" fill="#ffe0bd" /> 
            
            <!-- Rambut (Poni) -->
            <path d="M 10 50 Q 50 -10 90 50 Q 50 20 10 50" fill="#4a148c" />
            <path d="M 10 50 Q 30 100 20 90 Q 20 40 10 50" fill="#4a148c" />
            <path d="M 90 50 Q 70 100 80 90 Q 80 40 90 50" fill="#4a148c" />
            
            <!-- Mata Kiri -->
            <ellipse cx="33" cy="55" rx="7" ry="12" fill="#283593" /> 
            <circle cx="31" cy="51" r="3" fill="white" /> 
            <path d="M 23 45 Q 33 40 42 46" stroke="#1a237e" stroke-width="2" fill="transparent"/> 
            
            <!-- Mata Kanan -->
            <ellipse cx="67" cy="55" rx="7" ry="12" fill="#283593" /> 
            <circle cx="65" cy="51" r="3" fill="white" /> 
            <path d="M 58 46 Q 67 40 77 45" stroke="#1a237e" stroke-width="2" fill="transparent"/> 
            
            <!-- Pipi Merona -->
            <ellipse cx="25" cy="65" rx="5" ry="3" fill="#ff8a80" opacity="0.6"/>
            <ellipse cx="75" cy="65" rx="5" ry="3" fill="#ff8a80" opacity="0.6"/>
            
            <!-- Mulut Senyum -->
            <path d="M 45 72 Q 50 78 55 72" stroke="#d32f2f" stroke-width="2" fill="transparent"/>
        </svg>
    </div>
    """
    
    # KUNCI PERBAIKAN: Menggunakan components.html untuk merender gambar SVG
    components.html(svg_karakter, height=160)
    
    # Logika teks penyemangat
    total_pnl = sum(trade.get("pnl", 0) for trade in bot_state.get("trade_history", []))
    
    if total_pnl < 0:
        st.info("💡 Tidak apa-apa merah sedikit! Trailing stop menyelamatkan kita dari kerugian yang lebih dalam. Santai dulu yuk!")
    elif total_pnl > 0:
        st.success("🎉 Wow, kita sedang profit! Eagle-Chan bangga padamu!")
    else:
        st.info("☕ Pasar sedang dipantau. Siapkan kopimu, biarkan AI yang bekerja keras!")
