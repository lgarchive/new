from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return "<h1>Loch Garten – testkörning 🦅</h1><p>Appen startar!</p>"

@app.route("/archive")
def archive():
    return "<h2>Arkivet</h2><p>Här kan vi senare lägga in dina tidskapslar och material.</p>"

if __name__ == "__main__":
    app.run(debug=True)


