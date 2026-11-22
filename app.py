import os
import secrets

from flask import Flask, render_template

from auth import auth_bp
from database import init_db
from inquiries import inquiries_bp
from inventory import get_featured_cars, inventory_bp
from scheduling import scheduling_bp

app = Flask(__name__)
app.secret_key = (
    os.environ.get("AUTODRIVE_SECRET_KEY") or secrets.token_hex(32)
)

# Create the tables before authentication reads the users table.
init_db()

app.register_blueprint(auth_bp)
app.register_blueprint(inventory_bp)
app.register_blueprint(scheduling_bp)
app.register_blueprint(inquiries_bp)


@app.route("/")
def index():
  # Basic landing page route
  featured_cars = get_featured_cars(limit=1)
  return render_template("index.html", featured_cars=featured_cars)


if __name__ == "__main__":
  app.run(debug=True)