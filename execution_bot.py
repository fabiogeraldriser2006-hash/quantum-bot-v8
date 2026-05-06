import time
import threading
from datetime import datetime
import config
import data_engine
import quant_brain

# State Bot: Menyimpan data aktif saat ini
bot_state = {
    "selected_coin": "Bitcoin", 
    "last_action": "Menunggu Start...",
    "cash": 1000000.0, # Modal simulasi (1 Juta IDR)
    "positions": {},   # Tempat menyimpan koin yang sudah dibeli
    "scan_speed": 60   # Cek data pasar setiap 60 detik
}

BOT_IS_RUNNING = False

def jalankan_bot():
    global BOT_IS_RUNNING, bot_state
    
    while BOT_IS_RUNNING:
        try:
            koin_nama = bot_state["selected_coin"]
            conf = config.CRYPTO_MAP.get(koin_nama)
            
            bot_state["last_action"] = f"Memeriksa {koin_nama}..."
            
            # 1. Ambil Data Pasar
            data_live = data_engine.tarik_data_live_indodax()
            ticker = conf['ticker']
            
            if ticker in data_live:
                harga_skrg = float(data_live[ticker]['last'])
                df, _ = data_engine.tarik_grafik_klines_aman(conf['tv'], "15m", 50, data_live[ticker])
                
                if not df.empty:
                    df = data_engine.hitung_indikator_teknikal(df)
                    atr_value = float(df.iloc[-1]['ATR'])
                    
                    # 2. Panggil AI (Otomatis termanajemen 72 menit)
                    narasi, keputusan = quant_brain.prediksi_ai_market(df, koin_nama, harga_skrg, "15m", 50)
                    bot_state["last_action"] = f"AI: {keputusan} | Harga: {harga_skrg}"

                    # 3. Logika Trailing Stop (Jika sudah punya koin)
                    if koin_nama in bot_state["positions"]:
                        pos = bot_state["positions"][koin_nama]
                        
                        # Update harga tertinggi untuk trailing
                        if harga_skrg > pos['high_price']:
                            pos['high_price'] = harga_skrg
                        
                        # Batas jual = Harga Tertinggi - (ATR * 2)
                        batas_cut_loss = pos['high_price'] - (atr_value * 2)
                        
                        if harga_skrg < batas_cut_loss or keputusan == "SELL":
                            # Eksekusi Jual
                            profit = (harga_skrg - pos['buy_price']) / pos['buy_price'] * 100
                            bot_state["cash"] += pos['amount'] * harga_skrg
                            del bot_state["positions"][koin_nama]
                            bot_state["last_action"] = f"JUAL {koin_nama} | Profit: {profit:.2f}%"

                    # 4. Logika Beli
                    elif keputusan == "BUY" and bot_state["cash"] > 100000:
                        amount_to_buy = bot_state["cash"] / harga_skrg
                        bot_state["positions"][koin_nama] = {
                            "buy_price": harga_skrg,
                            "high_price": harga_skrg,
                            "amount": amount_to_buy
                        }
                        bot_state["cash"] = 0
                        bot_state["last_action"] = f"BELI {koin_nama} di {harga_skrg}"

            time.sleep(bot_state["scan_speed"])
            
        except Exception as e:
            bot_state["last_action"] = f"Sistem Jeda: {str(e)}"
            time.sleep(10)

def start_bot():
    global BOT_IS_RUNNING
    if not BOT_IS_RUNNING:
        BOT_IS_RUNNING = True
        threading.Thread(target=jalankan_bot, daemon=True).start()

def stop_bot():
    global BOT_IS_RUNNING
    BOT_IS_RUNNING = False
