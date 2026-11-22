import hashlib
import secrets
import time
from functools import wraps

from database import get_db
from flask import (
    Blueprint,
    abort,
    flash,
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
  state.app.jinja_env.globals["csrf_token"] = csrf_token
  hash_legacy_passwords()
  ensure_reset_table()


# CSRF protection for forms (FR-04 and password reset use these)
def csrf_token():
  if "csrf_token" not in session:
    session["csrf_token"] = secrets.token_urlsafe(32)
  return session["csrf_token"]


def verify_csrf():
  sent = request.form.get("csrf_token", "")
  expected = session.get("csrf_token", "")
  if not expected or not secrets.compare_digest(sent, expected):
    abort(400)


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


# Password reset
RESET_TOKEN_MINUTES = 30
MIN_PASSWORD_LENGTH = 8
MAX_RESET_REQUESTS = 5  # per client address, per RESET_WINDOW_SECONDS
RESET_WINDOW_SECONDS = 900
_reset_requests = {}  # client address -> list of request times


def ensure_reset_table():
  conn = get_db()
  conn.execute(
      """
      CREATE TABLE IF NOT EXISTS password_resets (
          resetID INTEGER PRIMARY KEY AUTOINCREMENT,
          userID INTEGER NOT NULL,
          tokenHash TEXT NOT NULL UNIQUE,
          expiresAt REAL NOT NULL,
          used INTEGER NOT NULL DEFAULT 0,
          FOREIGN KEY (userID) REFERENCES users(userID)
      )
      """
  )
  conn.commit()
  conn.close()


def _hash_token(token):
  # Only the hash is stored, so a leaked database cannot be used to reset
  return hashlib.sha256(token.encode()).hexdigest()


def _rate_limited(client):
  now = time.time()
  recent = [t for t in _reset_requests.get(client, []) if now - t < RESET_WINDOW_SECONDS]
  limited = len(recent) >= MAX_RESET_REQUESTS
  if not limited:
    recent.append(now)
  _reset_requests[client] = recent
  return limited


def deliver_reset_link(email, link):
  """Seam for Ting's notification work (FR-06). For now it prints to the
  server console; replace the body with a real email send later."""
  print(f"[password reset] for {email}: {link}")


def _find_valid_reset(token):
  conn = get_db()
  row = conn.execute(
      "SELECT resetID, userID FROM password_resets "
      "WHERE tokenHash = ? AND used = 0 AND expiresAt > ?",
      (_hash_token(token), time.time()),
  ).fetchone()
  conn.close()
  return row


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
  if request.method == "POST":
    verify_csrf()
    if _rate_limited(request.remote_addr or "unknown"):
      flash("Too many reset requests. Please try again later.", "error")
      return render_template("forgot_password.html"), 429

    email = request.form.get("email", "").strip()
    conn = get_db()
    user = conn.execute(
        "SELECT userID, email FROM users WHERE email = ?", (email,)
    ).fetchone()
    if user:
      token = secrets.token_urlsafe(32)
      # Only the newest link works
      conn.execute(
          "UPDATE password_resets SET used = 1 WHERE userID = ? AND used = 0",
          (user["userID"],),
      )
      conn.execute(
          "INSERT INTO password_resets (userID, tokenHash, expiresAt) "
          "VALUES (?, ?, ?)",
          (user["userID"], _hash_token(token),
           time.time() + RESET_TOKEN_MINUTES * 60),
      )
      conn.commit()
      link = url_for("auth.reset_password", token=token, _external=True)
      deliver_reset_link(user["email"], link)
    conn.close()

    # Same response whether or not the email exists (no account enumeration)
    flash(
        "If that email is registered, a reset link has been sent. "
        f"It expires in {RESET_TOKEN_MINUTES} minutes.",
        "success",
    )
    return redirect(url_for("auth.login"))

  return render_template("forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
  reset = _find_valid_reset(token)
  if not reset:
    flash("This reset link is invalid or has expired.", "error")
    return render_template("forgot_password.html"), 400

  if request.method == "POST":
    verify_csrf()
    password = request.form.get("password", "")
    confirm = request.form.get("confirm", "")
    error = None
    if len(password) < MIN_PASSWORD_LENGTH:
      error = f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    elif password != confirm:
      error = "Passwords do not match."
    if error:
      flash(error, "error")
      return render_template("reset_password.html", token=token), 400

    conn = get_db()
    user = conn.execute(
        "SELECT username FROM users WHERE userID = ?", (reset["userID"],)
    ).fetchone()
    conn.execute(
        "UPDATE users SET password = ? WHERE userID = ?",
        (generate_password_hash(password), reset["userID"]),
    )
    conn.execute(
        "UPDATE password_resets SET used = 1 WHERE userID = ?",
        (reset["userID"],),
    )
    conn.commit()
    conn.close()

    _failed_logins.pop(user["username"], None)  # clear any lockout
    session.clear()
    flash("Password updated. Please log in.", "success")
    return redirect(url_for("auth.login"))

  return render_template("reset_password.html", token=token)
