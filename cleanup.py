import sqlite3
import os

db_path = os.path.abspath("chat_archive.db")
print(f"📦 Rensar databasen: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

deleted = cursor.execute(
    "DELETE FROM live_chat WHERE message NOT LIKE '%Æ%'"
).rowcount

conn.commit()
conn.close()

print(f"🧹 Rensade {deleted} meddelanden utan Æ.")
