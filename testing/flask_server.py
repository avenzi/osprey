from flask import Flask
app = Flask(__name__)

@app.route("/")
def display():
    return "<h1 style='color:blue'>Testing flask</h1>"

if __name__ == "__main__":
    app.run(host = '0.0.0.0')
