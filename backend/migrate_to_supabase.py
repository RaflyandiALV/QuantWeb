import json
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def migrate():
    # 1. Baca data dari JSON lama
    if not os.path.exists('watchlist.json'):
        print("❌ File watchlist.json tidak ditemukan.")
        return

    with open('watchlist.json', 'r') as f:
        data = json.load(f)

    # 2. Hubungkan ke Supabase
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()

    print(f"🔄 Memulai migrasi {len(data)} data...")

    for item in data:
        # Handle format lama (string) atau format baru (dict)
        symbol = item if isinstance(item, str) else item.get('symbol')
        mode = 'AUTO' if isinstance(item, str) else item.get('mode', 'AUTO')

        try:
            cur.execute(
                "INSERT INTO watchlist (symbol, mode) VALUES (%s, %s) ON CONFLICT (symbol) DO NOTHING",
                (symbol, mode)
            )
        except Exception as e:
            print(f"⚠️ Gagal migrasi {symbol}: {e}")

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Migrasi selesai! Data sekarang aman di Cloud.")

if __name__ == "__main__":
    migrate()