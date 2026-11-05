from flask import Flask, render_template
from database import init_db
from auth import auth_bp
from inventory import inventory_bp
from scheduling import scheduling_bp
app = Flask(__name__)
app.secret_key = "autodrive_secret_key_change_in_production"

app.register_blueprint(auth_bp)
app.register_blueprint(inventory_bp)
app.register_blueprint(scheduling_bp)
# Automatically ensure tables and 20 cars exist on startup
init_db()


@app.route("/")
def index():
  # Basic landing page route
  return render_template("index.html")


if __name__ == "__main__":
  app.run(debug=True)