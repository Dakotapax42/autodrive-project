import os
import secrets

from flask import Flask, render_template

from database import get_db, init_db
from auth import auth_bp
from inventory import inventory_bp
from scheduling import scheduling_bp

app = Flask(__name__)
app.secret_key = (os.environ.get("AUTODRIVE_SECRET_KEY") or secrets.token_hex(32))

# Create the tables before authentication reads the users table.
init_db()

# Automatically ensure tables and 20 cars exist on startup
init_db()

app.register_blueprint(auth_bp)
app.register_blueprint(inventory_bp)
app.register_blueprint(scheduling_bp)



@app.route("/")
def home():
    conn = get_db()

    featured_cars = conn.execute("""
        SELECT carID, modelName, image, price, year, category
        FROM cars
        WHERE status = 'Available'
        ORDER BY carID
        LIMIT 3
    """).fetchall()

    conn.close()

    return render_template(
        "index.html",
        featured_cars=featured_cars
    )


if __name__ == "__main__":
  app.run(debug=True)

# comment meow
