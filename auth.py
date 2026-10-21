from database import get_db
from flask import Blueprint, redirect, render_template, request, session, url_for

auth_bp = Blueprint("auth", __name__)


# TODO (Thomas): Implement login logic (FR-01)
# - Route URL: '/login'
# - HTML Form Input Names to read: request.form.get('username'), request.form.get('password')
# - Database Table to query: 'users' (columns: id, username, password, role)
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
  if request.method == "POST":
    # 1. Grab username and password from the form request
    # 2. Query the 'users' table in the database
    # 3. If valid, save user info in session: session['user_id'], session['username'], session['role']
    # 4. Redirect to url_for('inventory.cars')
    pass

  return render_template("login.html")


# TODO (Thomas): Implement logout
@auth_bp.route("/logout")
def logout():
  # Clear the session and redirect back to login
  pass