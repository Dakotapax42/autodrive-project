import os
import secrets

from flask import Flask, render_template

from database import init_db
from auth import auth_bp
from inventory import inventory_bp
from scheduling import scheduling_bp

app = Flask(__name__)
app.secret_key = (os.environ.get("AUTODRIVE_SECRET_KEY") or secrets.token_hex(32))

# Create the tables before authentication reads the users table.
init_db()

app.register_blueprint(auth_bp)
app.register_blueprint(inventory_bp)
app.register_blueprint(scheduling_bp)



@app.route("/")
def index():
  # Basic landing page route
  return render_template("index.html")


if __name__ == "__main__":
  app.run(debug=True)

# comment meow
