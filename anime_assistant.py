"""
================================================================================
FILE: anime_assistant.py
DESKRIPSI: Modul Asisten Anime Full Body dengan Animasi CSS dan Interaksi Hover.
================================================================================
"""
import streamlit as st
import streamlit.components.v1 as components

def tampilkan_asisten(bot_state):
    """
    Fungsi ini menggambar karakter 'Eagle-Chan' Full Body yang interaktif.
    """
    st.markdown("---")
    st.caption("🌸 **Eagle-Chan (Interactive Mode)**")

    # Kode HTML, CSS, dan SVG dicampur untuk menciptakan interaktivitas
    html_animasi = """
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        /* Mengatur posisi di tengah */
        body { margin: 0; display: flex; justify-content: center; align-items: flex-end; height: 320px; overflow: hidden; background-color: transparent;}
        
        /* Animasi Melayang (Bernapas) */
        @keyframes float {
            0% { transform: translateY(0px); }
            50% { transform: translateY(-8px); }
            100% { transform: translateY(0px); }
        }

        /* Container utama karakter dengan animasi melayang */
        .character-box {
            animation: float 3s ease-in-out infinite;
            transition: transform 0.3s ease;
            cursor: pointer;
        }

        /* Efek Interaktif saat kursor menyentuh karakter (Hover) */
        .character-box:hover {
            transform: scale(1.05); /* Sedikit membesar */
        }

        /* Transisi pergerakan lengan */
        .arm {
            transform-origin: 50% 120px; /* Titik putar bahu */
            transition: transform 0.4s ease;
        }

        /* Lengan bergerak menyapa saat di-hover */
        .character-box:hover .arm-left {
            transform: rotate(30deg);
        }
        .character-box:hover .arm-right {
            transform: rotate(-30deg);
        }
    </style>
    </head>
    <body>
        <div class="character-box">
            <!-- Kanvas Full Body -->
            <svg width="180" height="300" viewBox="0 0 100 200" xmlns="http://www.w3.org/2000/svg">
                
                <!-- Kaki Kiri & Kanan -->
                <rect x="40" y="150" width="6" height="40" fill="#ffe0bd" rx="3" />
                <rect x="54" y="150" width="6" height="40" fill="#ffe0bd" rx="3" />
                
                <!-- Sepatu -->
                <ellipse cx="43" cy="190" rx="6" ry="4" fill="#1a1a1a" />
                <ellipse cx="57" cy="190" rx="6" ry="4" fill="#1a1a1a" />

                <!-- Badan (Pakaian/Gaun) -->
                <path d="M 40 100 L 30 160 Q 50 165 70 160 L 60 100 Z" fill="#283593" />
                <!-- Sabuk / Pita -->
                <rect x="38" y="115" width="24" height="5" fill="#ff8a80" />

                <!-- Lengan Kiri (Class arm-left untuk interaksi) -->
                <g class="arm arm-left">
                    <rect x="25" y="100" width="8" height="40" fill="#ffe0bd" rx="4" />
                    <!-- Lengan Baju Kiri -->
                    <path d="M 23 100 L 25 120 L 33 120 L 35 100 Z" fill="#1a237e" />
                </g>

                <!-- Lengan Kanan (Class arm-right untuk interaksi) -->
                <g class="arm arm-right">
                    <rect x="67" y="100" width="8" height="40" fill="#ffe0bd" rx="4" />
                    <!-- Lengan Baju Kanan -->
                    <path d="M 65 100 L 67 120 L 75 120 L 77 100 Z" fill="#1a237e" />
                </g>

                <!-- Leher -->
                <rect x="46" y="90" width="8" height="15" fill="#ffe0bd" />

                <!-- AREA WAJAH (Dari kode sebelumnya, digeser ke koordinat atas) -->
                <g transform="translate(0, 10)">
                    <!-- Kepala -->
                    <circle cx="50" cy="50" r="30" fill="#ffe0bd" /> 
                    
                    <!-- Rambut Belakang -->
                    <circle cx="50" cy="50" r="32" fill="#4a148c" clip-path="url(#cut-off-bottom)" />
                    
                    <!-- Rambut Poni -->
                    <path d="M 20 50 Q 50 10 80 50 Q 50 30 20 50" fill="#4a148c" />
                    <path d="M 20 50 Q 30 90 25 80 Q 25 40 20 50" fill="#4a148c" />
                    <path d="M 80 50 Q 70 90 75 80 Q 75 40 80 50" fill="#4a148c" />
                    
                    <!-- Mata -->
                    <ellipse cx="38" cy="55" rx="4" ry="7" fill="#283593" /> 
                    <circle cx="37" cy="53" r="1.5" fill="white" /> 
                    <ellipse cx="62" cy="55" rx="4" ry="7" fill="#283593" /> 
                    <circle cx="61" cy="53" r="1.5" fill="white" /> 
                    
                    <!-- Pipi Merona -->
                    <ellipse cx="32" cy="62" rx="4" ry="2" fill="#ff8a80" opacity="0.6"/>
                    <ellipse cx="68" cy="62" rx="4" ry="2" fill="#ff8a80" opacity="0.6"/>
                    
                    <!-- Mulut -->
                    <path d="M 47 66 Q 50 70 53 66" stroke="#d32f2f" stroke-width="1.5" fill="transparent"/>
                </g>
            </svg>
        </div>
    </body>
    </html>
    """
    
    # Render komponen HTML dengan tinggi yang cukup untuk full body
    components.html(html_animasi, height=330)
    
    # Logika teks responsif berdasarkan PnL
    total_pnl = sum(trade.get("pnl", 0) for trade in bot_state.get("trade_history", []))
    
    if total_pnl < 0:
        st.info("💡 Ayo Fabio! Aku bantu memantau Trailing Stop agar aman.")
    elif total_pnl > 0:
        st.success("🎉 Hebat! Profit kita bertambah, tetap pertahankan disiplinnya!")
    else:
        st.info("☕ Pasar sedang siap-siap. Arahkan kursor ke arahku kalau kamu bosan!")
