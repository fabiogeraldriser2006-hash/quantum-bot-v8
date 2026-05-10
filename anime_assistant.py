"""
================================================================================
FILE: anime_assistant.py
DESKRIPSI: Modul Asisten Anime menggunakan PNG Transparan dengan interaksi canggih:
3D Mouse Tracking (Parallax), Animasi Melompat, dan Balon Percakapan via JavaScript.
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
    """Menampilkan karakter Gadis Anime transparan yang hidup dan interaktif."""
    
    st.markdown("---")
    st.caption("🌸 **Eagle-Chan (Click me!)**")

    # Membaca gambar PNG transparan
    nama_file_gambar = "karakter.png" 
    b64_image = get_base64_of_bin_file(nama_file_gambar)

    if b64_image:
        img_src = f"data:image/png;base64,{b64_image}"
    else:
        img_src = "https://via.placeholder.com/150?text=PNG+Tidak+Ditemukan"
        st.warning(f"⚠️ File '{nama_file_gambar}' tidak ditemukan di folder!")

    # TEMPLATE HTML, CSS, dan JAVASCRIPT (Ditulis utuh tanpa f-string agar aman dari SyntaxError)
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body { 
            margin: 0; display: flex; justify-content: center; align-items: flex-end; 
            height: 380px; overflow: hidden; background-color: transparent; 
            perspective: 1000px; /* Efek kedalaman 3D */
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        /* Pembungkus untuk efek 3D Tilt (Mouse Tracking) */
        #tiltWrap {
            transform-style: preserve-3d;
            transition: transform 0.1s ease-out;
            position: relative;
        }

        /* Pembungkus untuk animasi melayang dan klik */
        #charWrap {
            display: flex; flex-direction: column; align-items: center; justify-content: flex-end;
            cursor: pointer;
            animation: float 4s ease-in-out infinite;
            position: relative;
        }

        @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-12px); }
        }

        /* Kelas untuk animasi melompat saat diklik */
        .jump-anim {
            animation: jump 0.4s ease;
        }

        @keyframes jump {
            0%, 100% { transform: translateY(0px) scale(1); }
            50% { transform: translateY(-40px) scale(1.05); }
        }

        .assistant-image {
            height: 300px; width: auto; object-fit: contain;
            transition: filter 0.3s ease;
            filter: drop-shadow(0px 5px 10px rgba(0,0,0,0.3));
        }

        #charWrap:hover .assistant-image {
            filter: drop-shadow(0px 0px 15px rgba(255, 105, 180, 0.7));
        }

        /* Balon Percakapan (Speech Bubble) */
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
                <img src="IMAGE_SRC_PLACEHOLDER" alt="Gadis Anime" class="assistant-image">
            </div>
        </div>

        <script>
            const tiltWrap = document.getElementById('tiltWrap');
            const charWrap = document.getElementById('charWrap');
            const bubble = document.getElementById('bubble');
            
            // 1. Efek 3D Mouse Tracking
            document.addEventListener('mousemove', (e) => {
                let xAxis = (window.innerWidth / 2 - e.pageX) / 40;
                let yAxis = (window.innerHeight / 2 - e.pageY) / 40;
                tiltWrap.style.transform = `rotateY(${-xAxis}deg) rotateX(${yAxis}deg)`;
            });

            // Daftar kata-kata penyemangat
            const kataKata = [
                "Semangat terus, Fabio!",
                "Jangan lupa disiplin Take Profit ya~",
                "Pasar lagi volatile? Santai saja!",
                "Aku yakin analisamu tajam hari ini!",
                "Wah, kamu keren banget!",
                "Kopinya jangan lupa diminum ☕"
            ];

            // 2. Efek Melompat & Berbicara saat diklik
            charWrap.addEventListener('click', () => {
                // Reset animasi agar bisa diklik berulang kali
                charWrap.classList.remove('jump-anim');
                void charWrap.offsetWidth; // Trigger reflow browser
                charWrap.classList.add('jump-anim');

                // Munculkan teks acak
                let randomTeks = kataKata[Math.floor(Math.random() * kataKata.length)];
                bubble.innerText = randomTeks;
                bubble.classList.add('show');

                // Sembunyikan teks setelah 2.5 detik
                setTimeout(() => {
                    bubble.classList.remove('show');
                }, 2500);
            });
        </script>
    </body>
    </html>
    """
    
    # Memasukkan gambar base64 ke dalam template HTML dengan sangat aman
    html_animasi_final = html_template.replace("IMAGE_SRC_PLACEHOLDER", img_src)
    
    # Render komponen HTML dengan tinggi ekstra agar lompatannya tidak terpotong
    components.html(html_animasi_final, height=400)
    
    # Logika teks responsif berdasarkan PnL (Tetap ada di bawah gambar)
    total_pnl = sum(trade.get("pnl", 0) for trade in bot_state.get("trade_history", []))
    
    if total_pnl < 0:
        st.info("💡 Tidak apa-apa merah sedikit! Trailing stop menyelamatkan kita dari kerugian lebih dalam.")
    elif total_pnl > 0:
        st.success("🎉 Wow, kita sedang profit! Eagle-Chan bangga padamu!")
    else:
        st.info("☕ Pasar sedang siap-siap. Coba klik karakternya kalau kamu bosan!")
