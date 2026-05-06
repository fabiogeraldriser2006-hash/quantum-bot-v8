"""
================================================================================
FILE: database.py
DESKRIPSI: Modul Database SQLite.
Bertugas menyimpan dan memuat riwayat trading serta status bot secara permanen.
================================================================================
"""

import sqlite3
import json
from datetime import datetime

DB_NAME = "quant_bot.db"

def inisialisasi_db():
    """Membuat file database dan tabel jika belum ada."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tabel untuk riwayat transaksi yang sudah selesai (Scoreboard)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trade_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            waktu TEXT,
            koin TEXT,
            harga_beli REAL,
            harga_jual REAL,
            pnl REAL,
            alasan TEXT
        )
    ''')
    
    # Tabel untuk menyimpan status terakhir (Saldo, Posisi Aktif)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_status (
            kunci TEXT PRIMARY KEY,
            nilai TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def simpan_trade(trade_data):
    """Mencatat transaksi jual ke riwayat permanen."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO trade_history (waktu, koin, harga_beli, harga_jual, pnl, alasan)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (trade_data['waktu'], trade_data['koin'], trade_data['harga_beli'], 
          trade_data['harga_jual'], trade_data['pnl'], trade_data['alasan']))
    conn.commit()
    conn.close()

def ambil_riwayat():
    """Mengambil semua riwayat transaksi untuk ditampilkan di Dashboard."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT waktu, koin, harga_beli, harga_jual, pnl, alasan FROM trade_history ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    
    # Mengubah hasil database menjadi format list dictionary agar dipahami bot_state
    history = []
    for r in rows:
        history.append({
            "waktu": r[0], "koin": r[1], "harga_beli": r[2], 
            "harga_jual": r[3], "pnl": r[4], "alasan": r[5]
        })
    return history

def simpan_status_bot(cash, positions, live_positions):
    """Menyimpan saldo dan posisi aktif agar tidak hilang saat restart."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Simpan Cash (Uang)
    cursor.execute('INSERT OR REPLACE INTO bot_status (kunci, nilai) VALUES (?, ?)', ("cash", str(cash)))
    
    # Simpan Posisi (Dikonversi ke JSON agar bisa disimpan dalam teks)
    cursor.execute('INSERT OR REPLACE INTO bot_status (kunci, nilai) VALUES (?, ?)', ("positions", json.dumps(positions)))
    cursor.execute('INSERT OR REPLACE INTO bot_status (kunci, nilai) VALUES (?, ?)', ("live_positions", json.dumps(live_positions)))
    
    conn.commit()
    conn.close()

def muat_status_bot():
    """Mengambil kembali saldo dan posisi terakhir saat bot dinyalakan."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    data = {"cash": 10000000.0, "positions": {}, "live_positions": {}}
    
    try:
        cursor.execute('SELECT kunci, nilai FROM bot_status')
        rows = cursor.fetchall()
        for kunci, nilai in rows:
            if kunci == "cash":
                data["cash"] = float(nilai)
            elif kunci == "positions":
                data["positions"] = json.loads(nilai)
            elif kunci == "live_positions":
                data["live_positions"] = json.loads(nilai)
    except Exception:
        pass
        
    conn.close()
    return data
