"""
================================================================================
FILE: anime_assistant.py
DESKRIPSI: Modul Asisten Anime Interaktif dengan fitur Multi-Ekspresi.
Menggunakan teknik Replace String murni agar aman dari NameError/SyntaxError Python.
================================================================================
"""
import streamlit as st
import streamlit.components.v1 as components
import base64

def get_base64_of_bin_file(bin_file):
    """Membaca file gambar lokal dan mengubahnya menjadi format Base64"""
    try:
        with open(bin_file, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None

def tampilkan_asisten(bot_state):
    """Menampilkan karakter Gadis Anime dengan fitur perubahan ekspresi wajah."""
    
    st.markdown("---")
    st.caption("🌸 **Eagle-Chan (Expressive Mode)**")

    # 1. MEMUAT 3 VARIASI EKSPRESI
    b64_normal = get_base64_of_bin_file("normal.png")
    b64_senyum = get_base64_of_bin_file("senyum.png")
    b64_kaget = get_base64_of_bin_file("kaget.png")

    # Validasi file utama
    if not b64_normal:
        st.warning("⚠️ File 'normal.png' tidak ditemukan! Pastikan nama file benar.")
        img_normal_src = "https://via.placeholder.com/150?text=Normal+Tidak+Ada"
    else:
        img_normal_src = f"data:image/png;base64,{b64_normal}"

    # Sistem Fallback: Jika gambar ekspresi belum dibuat user, gunakan gambar normal
    img_senyum_src = f"data:image/png;base64,{b64_senyum}" if b64_senyum else img_normal_src
    img_kaget_src = f"data:image/png;base64,{b64_kaget}" if b64_kaget else img_normal_src

    # 2. TEMPLATE HTML & JAVASCRIPT (TANPA f-string AWALAN)
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body { 
            margin: 0; display: flex; justify-content: center; align-items: flex-end; 
            height: 380px; overflow: hidden; background-color: transparent; 
            perspective: 1000px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        #tiltWrap {
            transform-style: preserve-3d; transition: transform 0.1s ease-out; position: relative;
        }

        #charWrap {
            display: flex; flex-direction: column; align-items: center; justify-content: flex-end;
            cursor: pointer; animation: float 4s ease-in-out infinite; position: relative;
        }

        @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-12px); }
        }

        .jump-anim { animation: jump 0.4s ease; }

        @keyframes jump {
            0%, 100% { transform: translateY(0px) scale(1); }
            50% { transform: translateY(-40px) scale(1.05); }
        }

        .assistant-image {
            height: 300px; width: auto; object-fit: contain;
            transition: filter 0.3s ease; filter: drop-shadow(0px 5px 10px rgba(0,0,0,0.3));
        }

        #charWrap:hover .assistant-image {
            filter: drop-shadow(0px 0px 15px rgba(255, 105, 180, 0.7));
        }

        #bubble {
            position: absolute; top: -30px; left: 50%; transform: translateX(-50%);
            background: white; padding: 8px 15px; border-radius: 15px;
            border: 2px solid #ff8a80; color: #333; font-weight: bold; font-size: 13px;
            white-space: nowrap; box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            opacity: 0; pointer-events: none; transition: opacity 0.3s ease; z-index: 10;
        }

        #bubble::after {
            content: ''; position: absolute; bottom: -8px; left: 50%; transform: translateX(-50%);
            border-width: 8px 8px 0; border-style: solid; border-color: #ff8a80 transparent transparent transparent;
        }

        #bubble.show { opacity: 1; }
    </style>
    </head>
    <body>

        <div id="tiltWrap">
            <div id="charWrap">
                <div id="bubble">Halo!</div>
                <img id="animeKarakter" src="SRC_NORMAL_PLACEHOLDER" alt="Gadis Anime" class="assistant-image">
            </div>
        </div>

        <script>
            const tiltWrap = document.getElementById('tiltWrap');
            const charWrap = document.getElementById('charWrap');
            const bubble = document.getElementById('bubble');
            const imgKarakter = document.getElementById('animeKarakter');
            
            // Variabel penyimpan sumber gambar ekspresi (Akan diganti oleh Python nanti)
            const srcNormal = "SRC_NORMAL_PLACEHOLDER";
            const srcSenyum = "SRC_SENYUM_PLACEHOLDER";
            const srcKaget = "SRC_KAGET_PLACEHOLDER";

            // 1. Efek 3D Mouse Tracking
            document.addEventListener('mousemove', (e) => {
                let xAxis = (window.innerWidth / 2 - e.pageX) / 40;
                let yAxis = (window.innerHeight / 2 - e.pageY) / 40;
                // JS Asli, aman karena Python tidak lagi memproses string ini secara otomatis
                tiltWrap.style.transform = `rotateY(${-xAxis}deg) rotateX(${yAxis}deg)`;
            });

            // 2. EKSPRESI 1: Tersenyum saat kursor didekatkan (Hover)
            charWrap.addEventListener('mouseenter', () => {
                imgKarakter.src = srcSenyum;
            });

            // Kembali ke ekspresi normal saat kursor menjauh
            charWrap.addEventListener('mouseleave', () => {
                imgKarakter.src = srcNormal;
            });

            const kataKata = [
                "Semangat terus, Fabio!",
                "Jangan lupa disiplin Take Profit ya~",
                "Pasar lagi volatile? Santai saja!",
                "Aku yakin analisamu tajam hari ini!"
            ];

            // 3. EKSPRESI 2: Kaget/Antusias saat diklik
            charWrap.addEventListener('click', () => {
                imgKarakter.src = srcKaget;

                charWrap.classList.remove('jump-anim');
                void charWrap.offsetWidth; 
                charWrap.classList.add('jump-anim');

                let randomTeks = kataKata[Math.floor(Math.random() * kataKata.length)];
                bubble.innerText = randomTeks;
                bubble.classList.add('show');

                setTimeout(() => {
                    bubble.classList.remove('show');
                    if(charWrap.matches(':hover')) {
                        imgKarakter.src = srcSenyum;
                    } else {
                        imgKarakter.src = srcNormal;
                    }
                }, 2000);
            });
        </script>
    </body>
    </html>
    """
    
    # 3. MENGGANTI PLACEHOLDER SECARA MANUAL (100% AMAN DARI ERROR)
    html_final = html_template.replace("SRC_NORMAL_PLACEHOLDER", img_normal_src)
    html_final = html_final.replace("SRC_SENYUM_PLACEHOLDER", img_senyum_src)
    html_final = html_final.replace("SRC_KAGET_PLACEHOLDER", img_kaget_src)
    
    # Merender ke Streamlit
    components.html(html_final, height=400)
    
    # Logika teks responsif berdasarkan PnL
    total_pnl = sum(trade.get("pnl", 0) for trade in bot_state.get("trade_history", []))
    if total_pnl < 0:
        st.info("💡 Tidak apa-apa merah sedikit! Trailing stop menyelamatkan kita dari kerugian lebih dalam.")
    elif total_pnl > 0:
        st.success("🎉 Wow, kita sedang profit! Terus pertahankan!")
    else:
        st.info("☕ Pasar sedang siap-siap. Coba klik karakternya!")
