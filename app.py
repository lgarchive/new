from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return "<h1>Loch Garten – testkörning 🦅</h1><p>Appen startar!</p>"

if __name__ == "__main__":
    app.run(debug=True)
