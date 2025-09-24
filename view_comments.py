import sqlite3
import os

db_path = os.path.abspath("chat_archive.db")
print(f"📖 Kommentarer i: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT author, message, timestamp FROM live_chat ORDER BY timestamp DESC")
rows = cursor.fetchall()
conn.close()

print(f"🔢 Totalt: {len(rows)} kommentarer\n")
for r in rows:
    print(f"{r[2]} – {r[0]}: {r[1]}")
