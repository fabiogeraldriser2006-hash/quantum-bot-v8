"""
================================================================================
FILE: anime_assistant.py
DESKRIPSI: Modul Asisten Anime Full Body yang membaca gambar langsung dari folder
dengan interaksi hover CSS yang aman dari SyntaxError.
================================================================================
"""
import streamlit as st
import streamlit.components.v1 as components
import base64
import os

def get_base64_of_bin_file(bin_file):
    """Membaca file gambar lokal dan mengubahnya menjadi format Base64"""
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        return None

def tampilkan_asisten(bot_state):
    """
    Fungsi ini menampilkan karakter 'Gadis Anime' (sesuai referensi user)
    secara interaktif di Sidebar.
    """
    st.markdown("---")
    st.caption("🌸 **Gadis Anime (Interactive Mode)**")

    # 1. Membaca gambar karakter dari folder project
    # Ganti "karakter.jpg" dengan nama file gambar anime Anda
    nama_file_gambar = "karakter.jpg" 
    b64_image = get_base64_of_bin_file(nama_file_gambar)

    if b64_image:
        img_src = f"data:image/jpeg;base64,{b64_image}"
    else:
        # Fallback jika gambar tidak ditemukan di folder
        img_src = "https://via.placeholder.com/150?text=Gambar+Tidak+Ditemukan"
        st.warning(f"⚠️ File '{nama_file_gambar}' tidak ditemukan di folder!")

    # 2. Kode HTML dan CSS (Semua tanda kurung kurawal sudah digandakan {{ }} agar aman)
    html_animasi = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{ margin: 0; display: flex; justify-content: center; align-items: flex-end; height: 350px; overflow: hidden; background-color: transparent; }}
        
        .character-container {{
            display: flex;
            justify-content: center;
            align-items: flex-end;
            height: 100%;
            cursor: pointer;
            animation: float 4s ease-in-out infinite;
            transition: transform 0.3s ease-out;
        }}

        @keyframes float {{
            0% {{ transform: translateY(0px); }}
            50% {{ transform: translateY(-10px); }}
            100% {{ transform: translateY(0px); }}
        }}

        .assistant-image {{
            max-width: 100%;
            height: 330px;
            width: auto;
            object-fit: contain;
            transition: filter 0.3s ease;
        }}
        
        .character-container:hover {{
            transform: scale(1.03) translateY(-10px);
        }}

        .character-container:hover .assistant-image {{
            filter: drop-shadow(0 0 10px rgba(255, 138, 128, 0.7));
        }}
    </style>
    </head>
    <body>
        <div class="character-container">
            <img src="{img_src}" alt="Gadis Anime" class="assistant-image">
        </div>
    </body>
    </html>
    """
    
    # Render komponen HTML
    components.html(html_animasi, height=350)
    
    # 3. Logika teks responsif berdasarkan PnL
    total_pnl = sum(trade.get("pnl", 0) for trade in bot_state.get("trade_history", []))
    
    if total_pnl < 0:
        st.info("💡 Tidak apa-apa merah sedikit! Aku bantu memantau agar aman. Santai dulu yuk, Fabio!")
    elif total_pnl > 0:
        st.success("🎉 Wow, kita sedang profit! Aku bangga padamu! Pertahankan disiplinnya!")
    else:
        st.info("☕ Pasar sedang bersiap. Siapkan kopimu, biarkan AI yang bekerja keras!")
