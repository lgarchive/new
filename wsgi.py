import sys
import os

# Lägg till din app-mapp i sökvägen
path = '/home/AEapp'  # ← justera om din app ligger i en undermapp
if path not in sys.path:
    sys.path.append(path)

# Sätt arbetskatalogen
os.chdir(path)

# Importera Flask-appen
from app import app as application  # ← OBS: app.py måste innehålla app = Flask(__name__)
