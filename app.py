import os
import time
import sys
import socket
import logging
import requests
import sqlite3
import json


from dateutil import tz
from dateutil.parser import parse
from datetime import timezone, datetime, timedelta
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from flask import send_from_directory
from werkzeug.utils import secure_filename
from collections import defaultdict






app = Flask(__name__)  # 🛠️ Skapa Flask–appen först!
app.secret_key = 'något-superhemligt-här'  # 🔐 Session-nyckeln direkt efter




# 📂 Uppladdningar
# 🧭 Konfiguration

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


print("UPLOAD_FOLDER:", app.config['UPLOAD_FOLDER'])
print("Writable?", os.access(app.config['UPLOAD_FOLDER'], os.W_OK))



# 📋 Logginställningar
log_path = os.path.join(os.path.dirname(__file__), "error.log")
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format="%(asctime)s: %(message)s",
    filemode="a"
)

# 🔐 Miljövariabler

YOUTUBE_VIDEO_ID = "abc123xyz"  # ← ersätt med ditt riktiga ID
FILTER_KEYWORD = "Ææ"





# 🗂️ Databas
def init_db():
    conn = sqlite3.connect("chat_archive.db")
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS live_chat (
        id TEXT PRIMARY KEY,
        author TEXT,
        message TEXT,
        timestamp TEXT
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS visitors (
        ip TEXT PRIMARY KEY,
        visit_time TEXT
    )""")
    conn.commit()
    conn.close()

init_db()

# 👥 Besökare
def count_unique_visitors():
    ip = request.remote_addr
    visit_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect("chat_archive.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO visitors VALUES (?, ?)", (ip, visit_time))
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM visitors")
    count = cursor.fetchone()[0]
    conn.close()
    return count





@app.route("/")
def landing():
    return redirect(url_for('index'))  # skickar till /home


last_fetch_time = 0  # måste ligga högt upp i app.py

@app.before_request
def maybe_fetch_chat():
    global last_fetch_time

    # Hämta manuellt om ?refresh=now finns i URL
    force = request.args.get("refresh") == "now"
    now = time.time()

    # Hämta om det gått mer än 30 sekunder eller om man tvingar
    if force or (now - last_fetch_time > 30):
        try:
            fetched = fetch_live_chat()  # ← din funktion som hämtar kommentarer
            last_fetch_time = now
            logging.info(f"Fetched {len(fetched)} comments (forced={force})")
        except Exception as e:
            logging.error(f"Error fetching chat: {e}")








# 🏠 Startsida – live chat + arkiv
@app.route("/home")
def index():
    conn = sqlite3.connect("chat_archive.db")
    cursor = conn.cursor()
    cursor.execute("SELECT author, message, timestamp FROM live_chat ORDER BY timestamp DESC")
    comments = cursor.fetchall()
    conn.close()

    visitors = count_unique_visitors()

    comment_json_path = os.path.join(os.path.dirname(__file__), 'comment_archive.json')
    try: site_comments = json.load(open(comment_json_path))
    except: site_comments = []

    return render_template("index.html",
                           comments=comments,
                           visitor_count=visitors,
                           current_year=datetime.utcnow().year)






@app.route("/chat", methods=["GET", "POST"])
def chat():
    archive_path = os.path.join(os.path.dirname(__file__), "comment_archive.json")

    try:
        with open(archive_path, "r") as f:
            messages = json.load(f)
    except:
        messages = []

    if request.method == "POST":
        name = request.form.get("name", "Anonymous")
        text = request.form.get("text", "").strip()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        if text:
            messages.append({
                "source": "ChatBoard",
                "name": name,
                "text": text,
                "timestamp": timestamp
            })
            with open(archive_path, "w") as f:
                json.dump(messages, f, indent=2)

    messages = sorted(messages, key=lambda x: x["timestamp"], reverse=True)
    return render_template("chat.html", messages=messages)


@app.route('/comment_popup')
def comment_popup():
    archive_path = os.path.join(os.path.dirname(__file__), 'comment_archive.json')
    try:
        with open(archive_path, 'r') as f:
            all_comments = json.load(f)
    except:
        all_comments = []

    # 🔍 FILTRERA ENDAST kommentarer från webben!
    site_comments = [c for c in all_comments if c.get("source") == "Website"]

    site_comments = sorted(site_comments, key=lambda x: x.get("timestamp", ""), reverse=True)
    return render_template('comment_popup.html', site_comments=site_comments)



@app.route('/add_comment', methods=["POST"])
def add_comment():
    name = request.form.get("name")
    text = request.form.get("text")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    entry = {
        "source": "Website",
        "name": name,
        "text": text,
        "timestamp": timestamp
    }

    path = os.path.join(os.path.dirname(__file__), 'comment_archive.json')
    try:
        archive = json.load(open(path))
    except:
        archive = []

    archive.append(entry)
    json.dump(archive, open(path, 'w'), indent=2)

    return "<p>✅ Thank you! Your comment is saved.</p>"

# 📸 Routen för uppladdningssidan

image_metadata = {}


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    print("🧠 Flask route '/upload' called with method:", request.method)
    message = ''
    filename = ''

    # Lista tillåtna filtyper
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'webm'}

    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

    if request.method == 'POST':
        file = request.files.get('file')
        uploader = request.form.get('uploader')
        description = request.form.get('description')
        category = request.form.get('category', 'Uncategorized').strip()
        custom_category = request.form.get('customCategory', '').strip()

        if category == 'Other' and custom_category:
            category = custom_category.strip()

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        session['uploader'] = uploader

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            ext = os.path.splitext(filename)[1].lower()
            is_video = ext in ['.mp4', '.webm']
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            print("🔧 Trying to save to:", save_path)

            try:
                file.save(save_path)

                # Spara metadata
                metadata_path = os.path.join(os.path.dirname(__file__), 'metadata.json')
                try:
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                except (FileNotFoundError, json.decoder.JSONDecodeError):
                    metadata = {}

                metadata[filename] = {
                    "uploader": uploader,
                    "description": description,
                    "timestamp": timestamp,
                    "category": category,
                    "type": "video" if is_video else "image"
                }

                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)

                print("✅ File saved successfully:", filename)
                message = 'File successfully uploaded'
            except Exception as e:
                message = f'Failed to save file: {e}'
                print("❌ Exception during save:", e)
        else:
            message = 'Invalid file type'
            print("❌ File type not allowed:", getattr(file, 'filename', 'unknown'))

    return render_template('upload.html', message=message, filename=filename)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/image/<filename>', methods=['GET', 'POST'])
def image_view(filename):
    metadata_path = os.path.join(os.path.dirname(__file__), 'metadata.json')
    comments_path = os.path.join(os.path.dirname(__file__), 'comments.json')

    # Läs metadata
    try:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
    except:
        metadata = {}

    image_meta = metadata.get(filename, {})

    # Läs kommentarer
    try:
        with open(comments_path, 'r') as f:
            all_comments = json.load(f)
    except:
        all_comments = {}

    image_comments = all_comments.get(filename, [])

    # Om nytt inlägg
    if request.method == 'POST':
        author = request.form.get('author')
        text = request.form.get('comment')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

        new_comment = {"author": author, "text": text, "timestamp": timestamp}
        image_comments.append(new_comment)

        all_comments[filename] = image_comments
        with open(comments_path, 'w') as f:
            json.dump(all_comments, f, indent=2)

    return render_template('image_view.html',
                           filename=filename,
                           meta=image_meta,
                           comments=image_comments,
                           uploader=session.get('uploader'))


@app.route('/folders')
def folder_list():
    metadata_path = os.path.join(os.path.dirname(__file__), 'metadata.json')

    try:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
    except:
        metadata = {}

    # Extrahera unika mappar/kategorier
    folders = sorted(set(
        meta.get('category') for meta in metadata.values()
        if meta.get('category')
    ))

    return render_template('folders.html', folders=folders)



@app.route('/gallery')
def gallery():
    metadata_path = os.path.join(os.path.dirname(__file__), 'metadata.json')
    try:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
    except:
        metadata = {}

    # Gruppad per kategori (ursprunglig struktur)
    grouped = defaultdict(list)
    for filename, meta in metadata.items():
        category = meta.get("category", "Uncategorized").strip()
        grouped[category].append((filename, meta))

    # Flat dict för Jinja-loop
    images = metadata  # {filename: meta}

    return render_template(
        "gallery.html",
        grouped=grouped,
        images=images,
        uploader=session.get("uploader")
    )




@app.route('/gallery/<category>')
def category_gallery(category):
    metadata_path = os.path.join(os.path.dirname(__file__), 'metadata.json')

    try:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
    except:
        metadata = {}

    filtered = [
        (filename, meta) for filename, meta in metadata.items()
        if meta.get('category', '').lower() == category.lower()
    ]

    return render_template('gallery.html', images=filtered)




@app.route('/delete/<filename>', methods=['POST'])
def delete(filename):
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    metadata_path = os.path.join(os.path.dirname(__file__), 'metadata.json')

    try:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)

        # Kontrollera att filen finns i metadata
        if filename not in metadata:
            return "File not found in metadata", 404

        # Kontrollera att användaren är uppladdaren
        current_user = session.get('uploader')  # eller vad du använder
        file_uploader = metadata[filename].get('uploader')

        if current_user != file_uploader:
            return "Unauthorized: You can only delete your own uploads", 403

        # Radera fil och metadata
        os.remove(image_path)
        del metadata[filename]
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        flash(f"🗑️ Deleted file: {filename}")
        print(f"🗑️ Deleted file: {filename}")
        return jsonify({'success': True, 'filename': filename})

    except Exception as e:
        return f"Error deleting file: {e}", 500



@app.route('/delete_category/<category>')
def delete_category(category):
    uploader = session.get('uploader', '')

    if uploader != "Pia":
        return "⛔ Only Pia can delete entire folders."

    metadata_path = os.path.join(os.path.dirname(__file__), 'metadata.json')
    upload_folder = os.path.join(app.config['UPLOAD_FOLDER'])
    log_path = os.path.join(os.path.dirname(__file__), 'deleted_log.json')

    try:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
    except:
        metadata = {}

    # Hitta bilder i denna kategori
    to_delete = [filename for filename, meta in metadata.items()
                 if meta.get('category', '').lower() == category.lower()]

    deleted_entries = []

    for filename in to_delete:
        image_path = os.path.join(upload_folder, filename)
        if os.path.exists(image_path):
            os.remove(image_path)

        deleted_entries.append({
            "filename": filename,
            "category": category,
            "uploader": metadata[filename].get("uploader"),
            "description": metadata[filename].get("description"),
            "timestamp": metadata[filename].get("timestamp"),
            "deleted_by": uploader,
            "deleted_at": datetime.now().strftime('%Y-%m-%d %H:%M')
        })

        metadata.pop(filename, None)

    # Spara ny metadata
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    # Uppdatera deleteloggen
    try:
        with open(log_path, 'r') as f:
            deleted_log = json.load(f)
    except:
        deleted_log = []

    deleted_log.extend(deleted_entries)

    with open(log_path, 'w') as f:
        json.dump(deleted_log, f, indent=2)

    return f"✅ Deleted {len(to_delete)} images and logged the action for category '{category}'."


@app.route('/deleted_log')
def deleted_log():
    log_path = os.path.join(os.path.dirname(__file__), 'deleted_log.json')

    try:
        with open(log_path, 'r') as f:
            log_entries = json.load(f)
    except:
        log_entries = []

    # Sortera senaste först
    sorted_log = sorted(log_entries, key=lambda x: x.get('deleted_at', ''), reverse=True)

    return render_template('deleted_log.html', log=sorted_log)


@app.route('/video_popup/<filename>')
def video_popup(filename):
    with open("video_meta.json") as f:
        meta = json.load(f).get(filename, {})
    return render_template("video_popup.html", filename=filename, title=meta.get("title"), description=meta.get("description"))

@app.route("/api/video_meta/<filename>")
def video_meta(filename):
    with open("video_meta.json", "r") as f:
        data = json.load(f)
    return jsonify(data.get(filename, {"title": "Ingen titel", "description": "Ingen beskrivning"}))



# 💬 Hämtar kommentarer
@app.route("/comments_video/<filename>")
def get_comments(filename):
    filepath = os.path.join("comments", f"{filename}.json")
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            comments = json.load(f)
    else:
        comments = []
    return jsonify(comments)

# 📝 Sparar ny kommentar
@app.route("/comment_video", methods=["POST"])
def post_comment():
    data = request.get_json()
    filepath = os.path.join("comments", f"{data['filename']}.json")
    comments = []
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            comments = json.load(f)
    comments.append({
        "author": data["author"],
        "text": data["text"]
    })
    with open(filepath, "w") as f:
        json.dump(comments, f)
    return jsonify({"success": True})








@app.route("/comments")
def comments():
    conn = sqlite3.connect("chat_archive.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT author, message, timestamp
        FROM live_chat
        WHERE date(timestamp) = date('now', 'localtime')
        ORDER BY timestamp DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    # 🛡 Oavsett om 'rows' är tom eller ej, skicka tillbaka JSON
    return jsonify([
        {"author": r[0], "message": r[1], "timestamp": r[2]} for r in rows
    ])

@app.route('/logout')
def logout():
    session.clear()  # Rensar all sessionsdata
    return redirect(url_for('gallery'))  # Ändra till valfri landningssida



# 📆 Månadsvis arkiv
@app.route("/archive/by_month")
def archive_by_month():
    conn = sqlite3.connect("chat_archive.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT strftime('%Y-%m', timestamp) AS month
        FROM live_chat
        ORDER BY month DESC
    """)
    months = [row[0] for row in cursor.fetchall()]

    selected_month = request.args.get("month")
    if selected_month:
        cursor.execute("""
            SELECT author, message, timestamp
            FROM live_chat
            WHERE strftime('%Y-%m', timestamp) = ?
            ORDER BY timestamp DESC
        """, (selected_month,))
        comments = cursor.fetchall()
    else:
        comments = []

    conn.close()
    return render_template("archive.html",
                           comments=comments,
                           months=months,
                           selected_month=selected_month)

# 📅 Veckovis arkiv
def get_week_range(year, week_number):
    monday = datetime.strptime(f'{year}-W{week_number}-1', "%Y-W%W-%w")
    sunday = monday + timedelta(days=6)
    return monday.strftime("%b %d"), sunday.strftime("%b %d")

@app.route("/archive/by_week")
def archive_by_week():
    conn = sqlite3.connect("chat_archive.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT strftime('%Y-%m', timestamp) AS month
        FROM live_chat
        ORDER BY month DESC
    """)
    months = [row[0] for row in cursor.fetchall()]

    selected_week = request.args.get("week")
    selected_month = request.args.get("month")
    selected_label = None

    if selected_week:
        cursor.execute("""
            SELECT author, message, timestamp
            FROM live_chat
            WHERE strftime('%Y-%W', timestamp) = ?
            ORDER BY timestamp DESC
        """, (selected_week,))
        comments = cursor.fetchall()

        year, week = selected_week.split("-")
        start, end = get_week_range(int(year), int(week))
        selected_label = f"Week {week} ({start}–{end})"
    else:
        comments = []

    conn.close()
    return render_template("archive.html",
                           comments=comments,
                           months=months,
                           selected_month=selected_month,
                           selected_week=selected_week,
                           selected_label=selected_label)

# 🔄 API: hämta veckor från valt månad
@app.route("/get_weeks", methods=["POST"])
def get_weeks():
    selected_month = request.form.get("month")
    conn = sqlite3.connect("chat_archive.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT strftime('%Y-%W', timestamp) AS week
        FROM live_chat
        WHERE strftime('%Y-%m', timestamp) = ?
        ORDER BY week ASC
    """, (selected_month,))
    raw_weeks = [row[0] for row in cursor.fetchall()]

    weeks = []
    for w in raw_weeks:
        year, week = w.split("-")
        start, end = get_week_range(int(year), int(week))
        label = f"Week {week} ({start}–{end})"
        weeks.append({"value": w, "label": label})

    conn.close()
    return jsonify(weeks)


@app.route('/updates')
def updates():
    return render_template('update.html')


@app.route('/old')
def archive_old():
    # Här kan du filtrera metadata eller kommentarer för juli/augusti 2025
    return render_template("archive_old.html")


# 🧹 Nollställ databas
@app.route("/reset")
def reset():
    conn = sqlite3.connect("chat_archive.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM live_chat")
    cursor.execute("DELETE FROM visitors")
    conn.commit()
    conn.close()
    return "Database reset! 🔄"

# 🛜 Ping
@app.route("/ping")
def ping():
    return "pong"



# 🚀 Starta app
def find_open_port(start=5000, end=5100):
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', port)) != 0:
                return port
    raise RuntimeError("No open")
