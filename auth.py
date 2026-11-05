import time
from functools import wraps

from database import get_db
from flask import (
    Blueprint,
    abort,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

auth_bp = Blueprint("auth", __name__)

# Session contract (other modules can rely on these keys after login):
#   session["user_id"]  -> users.userID (int)
#   session["username"] -> users.username (str)
#   session["role"]     -> "Customer" or "Employee"

# Brute-force prot (in memory, so it resets when the server restarts)
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 300
_failed_logins = {}  # username -> (failure count, time of last failure)


def _is_locked_out(username):
  count, last_failure = _failed_logins.get(username, (0, 0))
  if count >= MAX_FAILED_ATTEMPTS:
    if time.time() - last_failure < LOCKOUT_SECONDS:
      return True
    _failed_logins.pop(username, None)  # lockout expired, start fresh
  return False


def _record_failure(username):
  count, _ = _failed_logins.get(username, (0, 0))
  _failed_logins[username] = (count + 1, time.time())


# Password hashing
def hash_legacy_passwords():
  conn = get_db()
  rows = conn.execute("SELECT userID, password FROM users").fetchall()
  for row in rows:
    if not row["password"].startswith(("scrypt:", "pbkdf2:")):
      conn.execute(
          "UPDATE users SET password = ? WHERE userID = ?",
          (generate_password_hash(row["password"]), row["userID"]),
      )
  conn.commit()
  conn.close()


@auth_bp.record_once
def _on_register(state):
  # Runs once, when app.register_blueprint(auth_bp) is called
  state.app.config.update(
      SESSION_COOKIE_HTTPONLY=True,  # JavaScript cannot read the session cookie
      SESSION_COOKIE_SAMESITE="Lax",  # limits cross-site request abuse
  )
  hash_legacy_passwords()


# Access-control decorators (for use by every other module
def login_required(view):
  @wraps(view)
  def wrapped(*args, **kwargs):
    if "user_id" not in session:
      return redirect(url_for("auth.login"))
    return view(*args, **kwargs)

  return wrapped


def role_required(role):
  """Only allow users with the given role ("Customer" or "Employee")."""

  def decorator(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
      if "user_id" not in session:
        return redirect(url_for("auth.login"))
      if session.get("role") != role:
        abort(403)
      return view(*args, **kwargs)

    return wrapped

  return decorator


# Routes (FReq-01)
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
  error = None
  status = 200

  if request.method == "POST":
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if _is_locked_out(username):
      error = "Too many failed attempts. Please try again in a few minutes."
      status = 429
    else:
      conn = get_db()
      user = conn.execute(
          "SELECT userID, username, password, role FROM users WHERE username = ?",
          (username,),
      ).fetchone()
      conn.close()

      if user and check_password_hash(user["password"], password):
        _failed_logins.pop(username, None)
        session.clear()  # drop any old session data before logging in
        session["user_id"] = user["userID"]
        session["username"] = user["username"]
        session["role"] = user["role"]
        return redirect(url_for("inventory.cars"))

      # Same message for "no such user" and "wrong password" on purpose
      _record_failure(username)
      error = "Invalid username or password."
      status = 401

  return render_template("login.html", error=error), status


@auth_bp.route("/logout")
def logout():
  session.clear()
  return redirect(url_for("auth.login"))
