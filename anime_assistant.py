"""
================================================================================
FILE: anime_assistant.py
DESKRIPSI: Modul Asisten Anime menggunakan gambar PNG Transparan (Tanpa Latar)
dengan efek interaktif (Melayang & Cahaya Hover).
================================================================================
"""
import streamlit as st
import streamlit.components.v1 as components
import base64

def get_base64_of_bin_file(bin_file):
    """Membaca file gambar lokal dan mengubahnya menjadi format Base64"""
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        return None

def tampilkan_asisten(bot_state):
    """Menampilkan karakter Gadis Anime transparan yang interaktif."""
    
    st.markdown("---")
    st.caption("🌸 **Gadis Anime (Interactive Mode)**")

    # KUNCI UTAMA: Kita memanggil file PNG yang sudah dihapus background-nya
    nama_file_gambar = "karakter.png" 
    b64_image = get_base64_of_bin_file(nama_file_gambar)

    if b64_image:
        # Format diubah menjadi image/png
        img_src = f"data:image/png;base64,{b64_image}"
    else:
        img_src = "https://via.placeholder.com/150?text=PNG+Tidak+Ditemukan"
        st.warning(f"⚠️ File '{nama_file_gambar}' tidak ditemukan di folder!")

    # Kode CSS yang dioptimalkan untuk PNG transparan
    html_animasi = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{ 
            margin: 0; 
            display: flex; 
            justify-content: center; 
            align-items: flex-end; 
            height: 350px; 
            overflow: hidden; 
            background-color: transparent; /* Latar belakang iframe tembus pandang */
        }}
        
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
            50% {{ transform: translateY(-12px); }}
            100% {{ transform: translateY(0px); }}
        }}

        .assistant-image {{
            max-width: 100%;
            height: 330px;
            width: auto;
            object-fit: contain;
            /* drop-shadow pada filter akan mengikuti bentuk tubuh PNG, BUKAN bentuk kotak gambar */
            transition: filter 0.3s ease, transform 0.3s ease;
        }}
        
        .character-container:hover {{
            transform: scale(1.05) translateY(-5px);
        }}

        /* Efek glow yang mengikuti siluet tubuh karakter */
        .character-container:hover .assistant-image {{
            filter: drop-shadow(0px 0px 12px rgba(255, 105, 180, 0.8));
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
    
    components.html(html_animasi, height=350)
    
    # Logika teks responsif
    total_pnl = sum(trade.get("pnl", 0) for trade in bot_state.get("trade_history", []))
    
    if total_pnl < 0:
        st.info("💡 Tidak apa-apa merah sedikit! Aku bantu memantau agar aman. Santai dulu yuk, Fabio!")
    elif total_pnl > 0:
        st.success("🎉 Wow, kita sedang profit! Aku bangga padamu! Pertahankan disiplinnya!")
    else:
        st.info("☕ Pasar sedang bersiap. Siapkan kopimu, biarkan AI yang bekerja keras!")
