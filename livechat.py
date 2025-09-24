# livechat.py
import pytchat
import asyncio
import threading
import sqlite3
import re

FILTER_PATTERN = r"Ææ|ae|AE"  # Du kan justera detta efter behov

def save_comment_to_db(author, message, timestamp):
    conn = sqlite3.connect("chat_archive.db")
    cursor = conn.cursor()
    comment_id = f"{author}_{timestamp}_{hash(message)}"
    cursor.execute("""
        INSERT OR IGNORE INTO live_chat (id, author, message, timestamp)
        VALUES (?, ?, ?, ?)
    """, (comment_id, author, message, timestamp))
    conn.commit()
    conn.close()

async def fetch_comments_async(video_id):
    chat = pytchat.LiveChatAsync(video_id=video_id)
    while chat.is_alive():
        data = await chat.get()
        for c in data.items:
            if re.search(FILTER_PATTERN, c.message, re.IGNORECASE):
                save_comment_to_db(c.author.name, c.message, c.timestamp)
        await asyncio.sleep(1)

def start_comment_thread(video_id):
    def runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(fetch_comments_async(video_id))
    threading.Thread(target=runner, daemon=True).start()
