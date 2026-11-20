import os
import tempfile
import unittest

import auth
import database
from flask import Flask


def make_app():
  app = Flask(__name__)
  app.secret_key = "test-key"

  from inventory import inventory_bp
  from scheduling import scheduling_bp

  app.register_blueprint(auth.auth_bp)
  app.register_blueprint(inventory_bp)
  app.register_blueprint(scheduling_bp)

  # Throwaway routes to exercise the access-control decorators
  @app.route("/_any_user")
  @auth.login_required
  def any_user():
    return "ok"

  @app.route("/_employee_only")
  @auth.role_required("Employee")
  def employee_only():
    return "ok"

  return app


class AuthTests(unittest.TestCase):
  def setUp(self):
    fd, self.db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database.DB_NAME = self.db_path
    database.init_db()  # creates tables + seed users (plain-text passwords)
    auth._failed_logins.clear()
    self.app = make_app()  # registering auth_bp hashes the seed passwords
    self.client = self.app.test_client()

  def tearDown(self):
    os.remove(self.db_path)

  def login(self, username, password):
    return self.client.post(
        "/login", data={"username": username, "password": password}
    )

  def test_seed_passwords_are_hashed(self):
    conn = database.get_db()
    for row in conn.execute("SELECT password FROM users"):
      self.assertNotEqual(row["password"], "password")
      self.assertTrue(row["password"].startswith(("scrypt:", "pbkdf2:")))
    conn.close()

  def test_valid_login_sets_session_and_redirects(self):
    resp = self.login("buyer1", "password")
    self.assertEqual(resp.status_code, 302)
    self.assertTrue(resp.headers["Location"].endswith("/cars"))
    with self.client.session_transaction() as sess:
      self.assertEqual(sess["username"], "buyer1")
      self.assertEqual(sess["role"], "Customer")
      self.assertIn("user_id", sess)

  def test_wrong_password_rejected(self):
    resp = self.login("buyer1", "wrong")
    self.assertEqual(resp.status_code, 401)
    with self.client.session_transaction() as sess:
      self.assertNotIn("user_id", sess)

  def test_unknown_user_gets_same_error(self):
    bad_pw = self.login("buyer1", "wrong")
    no_user = self.login("nobody", "wrong")
    self.assertEqual(bad_pw.status_code, no_user.status_code)

  def test_sql_injection_attempt_fails(self):
    resp = self.login("' OR '1'='1' --", "anything")
    self.assertEqual(resp.status_code, 401)

  def test_lockout_after_repeated_failures(self):
    for _ in range(auth.MAX_FAILED_ATTEMPTS):
      self.login("buyer1", "wrong")
    # Even the correct password is refused while locked out
    resp = self.login("buyer1", "password")
    self.assertEqual(resp.status_code, 429)

  def test_logout_clears_session(self):
    self.login("buyer1", "password")
    resp = self.client.get("/logout")
    self.assertEqual(resp.status_code, 302)
    with self.client.session_transaction() as sess:
      self.assertNotIn("user_id", sess)

  def test_login_required_redirects_when_logged_out(self):
    resp = self.client.get("/_any_user")
    self.assertEqual(resp.status_code, 302)
    self.assertTrue(resp.headers["Location"].endswith("/login"))

  def test_customer_blocked_from_employee_route(self):
    self.login("buyer1", "password")
    self.assertEqual(self.client.get("/_employee_only").status_code, 403)

  def test_employee_allowed_on_employee_route(self):
    self.login("employee1", "password")
    self.assertEqual(self.client.get("/_employee_only").status_code, 200)

  def test_session_cookie_hardening(self):
    self.assertTrue(self.app.config["SESSION_COOKIE_HTTPONLY"])
    self.assertEqual(self.app.config["SESSION_COOKIE_SAMESITE"], "Lax")


if __name__ == "__main__":
  unittest.main()
