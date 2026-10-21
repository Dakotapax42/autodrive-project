from flask import Flask, render_template
from database import init_db

app = Flask(__name__)
app.secret_key = "autodrive_secret_key_change_in_production"

# Automatically ensure tables and 20 cars exist on startup
init_db()


@app.route("/")
def index():
  # Basic landing page route
  return render_template("index.html")


if __name__ == "__main__":
  app.run(debug=True)