"""
================================================================================
FILE: anime_assistant.py
DESKRIPSI: Modul Asisten Anime Full Body yang wujudnya identik dengan referensi,
menggunakan Base64 image dan interaksi hover CSS.
================================================================================
"""
import streamlit as st
import streamlit.components.v1 as components

# --- STRING BASE64 DARI GAMBAR REFERENSI USER ---
# String ini mewakili file gambar Anda secara utuh di dalam kode Python.
assistant_reference_b64 = "iVBORw0KGgoAAAANSUhEUgAABLAAAAXvCAYAAAC0I8K/AAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAOxAAADsQBlSsOGwAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAACAASUVORK5CYII="

def tampilkan_asisten(bot_state):
    """
    Fungsi ini menampilkan karakter 'Gadis Anime' (sesuai referensi user)
    secara identik dan interaktif di Sidebar.
    """
    st.markdown("---")
    st.caption("🌸 **Gadis Anime (Interactive Mode)**")

    # Kode HTML dan CSS untuk meng-embed gambar referensi dan interaksi hover
    html_animasi = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        /* Mengatur posisi di tengah, pinggir bawah container */
        body {{ margin: 0; display: flex; justify-content: center; align-items: flex-end; height: 350px; overflow: hidden; background-color: transparent;}}
        
        /* Container utama karakter dengan animasi melayang (floating) */
        .character-container {{
            display: flex;
            justify-content: center;
            align-items: flex-end;
            height: 100%;
            cursor: pointer;
            
            /* Animasi Melayang (Floating/Breathing Effect) */
            animation: float 4s ease-in-out infinite;
            transition: transform 0.3s ease-out; /* Transisi halus saat hover */
        }

        /* Definisi keyframes untuk animasi melayang */
        @keyframes float {{
            0% {{ transform: translateY(0px); }}
            50% {{ transform: translateY(-10px); }}
            100% {{ transform: translateY(0px); }}
        }

        /* Mengatur tampilan gambar karakter (full-body) */
        .assistant-image {{
            max-width: 100%;
            height: 330px; /* Menyesuaikan tinggi container */
            width: auto;   /* Mempertahankan aspek rasio */
            object-fit: contain;
            transition: filter 0.3s ease; /* Transisi efek cahaya */
        }

        /* --- FITUR INTERAKTIF (Hover) --- */
        
        /* 1. Efek membesar (scale up) halus saat kursor menyentuh container */
        .character-container:hover {{
            transform: scale(1.03) translateY(-10px); /* Sedikit membesar dan naik sedikit */
        }

        /* 2. Efek cahaya (glow) pada gambar saat di-hover */
        .character-container:hover .assistant-image {{
            filter: drop-shadow(0 0 10px rgba(255, 138, 128, 0.7)); /* Glow merah muda halus */
        }
    </style>
    </head>
    <body>
        <div class="character-container">
            <img src="data:image/jpeg;base64,{assistant_reference_b64}" alt="Gadis Anime" class="assistant-image">
        </div>
    </body>
    </html>
    """
    
    # Render komponen HTML dengan tinggi penuh untuk karakter full body
    components.html(html_animasi, height=350)
    
    # Logika teks responsif berdasarkan PnL (pertahankan fitur lama)
    total_pnl = sum(trade.get("pnl", 0) for trade in bot_state.get("trade_history", []))
    
    if total_pnl < 0:
        st.info("💡 Tidak apa-apa merah sedikit! Aku bantu memantau Trailing Stop agar aman. Santai dulu yuk, Fabio!")
    elif total_pnl > 0:
        st.success("🎉 Wow, kita sedang profit! Eagle-Chan... eh, aku bangga padamu! Pertahankan disiplinnya!")
    else:
        st.info("☕ Pasar sedang siap-siap. Siapkan kopimu, biarkan AI yang bekerja keras! Arahkan kursor ke arahku kalau kamu bosan!")
