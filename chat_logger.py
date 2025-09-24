import os
import pytchat
import sqlite3
from datetime import datetime

video_id = os.getenv("YOUTUBE_VIDEO_ID")
filter_keyword = os.getenv("FILTER_KEYWORD", "Ææ")

chat = pytchat.create(video_id=video_id)

conn = sqlite3.connect("chat_archive.db")
cursor = conn.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS live_chat (
    id TEXT PRIMARY KEY,
    author TEXT,
    message TEXT,
    timestamp TEXT
)""")

while chat.is_alive():
    for c in chat.get().sync_items():
        if filter_keyword.lower() in c.message.lower():
            chat_id = c.id
            author = c.author.name
            message = c.message
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("INSERT OR IGNORE INTO live_chat VALUES (?, ?, ?, ?)",
                           (chat_id, author, message, timestamp))
            conn.commit()
