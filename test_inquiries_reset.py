import os
import re
import tempfile
import time
import unittest

import auth
import database
from test_auth import make_app


class Base(unittest.TestCase):
  def setUp(self):
    fd, self.db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database.DB_NAME = self.db_path
    database.init_db()
    auth._failed_logins.clear()
    auth._reset_requests.clear()
    self.app = make_app()
    self.client = self.app.test_client()
    self.sent = []
    self._orig = auth.deliver_reset_link
    auth.deliver_reset_link = lambda email, link: self.sent.append((email, link))

  def tearDown(self):
    auth.deliver_reset_link = self._orig
    os.remove(self.db_path)

  def token(self, path):
    self.client.get(path)
    with self.client.session_transaction() as s:
      return s["csrf_token"]

  def login(self, u, p):
    return self.client.post("/login", data={"username": u, "password": p})

  def send_inquiry(self, msg="Is it available?", car=1):
    t = self.token(f"/inquiries/new/{car}")
    return self.client.post(
        f"/inquiries/new/{car}", data={"message": msg, "csrf_token": t}
    )


class InquiryTests(Base):
  def test_anonymous_redirected(self):
    self.assertEqual(self.client.get("/inquiries").status_code, 302)
    self.assertEqual(self.client.get("/inquiries/new/1").status_code, 302)

  def test_employee_cannot_send(self):
    self.login("employee1", "admin123")
    self.assertEqual(self.client.get("/inquiries/new/1").status_code, 403)

  def test_customer_sends_and_sees_own(self):
    self.login("buyer1", "password123")
    resp = self.send_inquiry("Any scratches?")
    self.assertEqual(resp.status_code, 302)
    self.assertIn(b"Any scratches?", self.client.get("/inquiries").data)

  def test_missing_csrf_rejected(self):
    self.login("buyer1", "password123")
    resp = self.client.post("/inquiries/new/1", data={"message": "hi"})
    self.assertEqual(resp.status_code, 400)

  def test_empty_and_too_long_rejected(self):
    self.login("buyer1", "password123")
    self.assertEqual(self.send_inquiry("   ").status_code, 400)
    self.assertEqual(self.send_inquiry("x" * 1001).status_code, 400)

  def test_unknown_car_404(self):
    self.login("buyer1", "password123")
    self.assertEqual(self.client.get("/inquiries/new/9999").status_code, 404)

  def test_pending_limit(self):
    self.login("buyer1", "password123")
    for _ in range(5):
      self.assertEqual(self.send_inquiry().status_code, 302)
    self.assertEqual(self.send_inquiry().status_code, 400)

  def test_customer_cannot_respond(self):
    self.login("buyer1", "password123")
    t = self.token("/inquiries/new/1")
    resp = self.client.post("/inquiries/1/respond", data={"response": "x", "csrf_token": t})
    self.assertEqual(resp.status_code, 403)

  def test_customers_cannot_see_each_others_inquiries(self):
    conn = database.get_db()
    conn.execute(
        "INSERT INTO users (username, firstName, lastName, email, password, role) "
        "VALUES ('buyer2','B','Two','b2@example.com','x','Customer')"
    )
    conn.commit()
    conn.close()
    self.login("buyer1", "password123")
    self.send_inquiry("private question")
    self.client.get("/logout")
    # buyer2's password gets hashed on register, so set it directly
    conn = database.get_db()
    conn.execute(
        "UPDATE users SET password = ? WHERE username = 'buyer2'",
        (auth.generate_password_hash("pw123456"),),
    )
    conn.commit()
    conn.close()
    self.login("buyer2", "pw123456")
    self.assertNotIn(b"private question", self.client.get("/inquiries").data)

  def test_employee_sees_all_and_replies(self):
    self.login("buyer1", "password123")
    self.send_inquiry("Colour options?")
    self.client.get("/logout")
    self.login("employee1", "admin123")
    self.assertIn(b"Colour options?", self.client.get("/inquiries").data)
    t = self.token("/inquiries")
    resp = self.client.post(
        "/inquiries/2/respond", data={"response": "Red or blue.", "csrf_token": t}
    )
    self.assertEqual(resp.status_code, 302)
    conn = database.get_db()
    row = conn.execute("SELECT status, response FROM inquiries WHERE inquiryID = 2").fetchone()
    conn.close()
    self.assertEqual((row["status"], row["response"]), ("Resolved", "Red or blue."))

  def test_respond_unknown_inquiry_404(self):
    self.login("employee1", "admin123")
    t = self.token("/inquiries")
    resp = self.client.post("/inquiries/999/respond", data={"response": "x", "csrf_token": t})
    self.assertEqual(resp.status_code, 404)

  def test_xss_is_escaped(self):
    self.login("buyer1", "password123")
    self.send_inquiry("<script>alert(1)</script>")
    page = self.client.get("/inquiries").data
    self.assertNotIn(b"<script>alert(1)</script>", page)


class ResetTests(Base):
  def request_reset(self, email="buyer1@example.com"):
    t = self.token("/forgot-password")
    return self.client.post("/forgot-password", data={"email": email, "csrf_token": t})

  def buyer_email(self):
    conn = database.get_db()
    e = conn.execute("SELECT email FROM users WHERE username='buyer1'").fetchone()[0]
    conn.close()
    return e

  def link_token(self):
    return re.search(r"/reset-password/(.+)$", self.sent[-1][1]).group(1)

  def test_same_response_for_known_and_unknown_email(self):
    a = self.request_reset(self.buyer_email())
    b = self.request_reset("nobody@example.com")
    self.assertEqual(a.status_code, b.status_code)
    self.assertEqual(len(self.sent), 1)

  def test_csrf_required(self):
    resp = self.client.post("/forgot-password", data={"email": "x@y.z"})
    self.assertEqual(resp.status_code, 400)

  def test_token_stored_hashed(self):
    self.request_reset(self.buyer_email())
    tok = self.link_token()
    conn = database.get_db()
    hashes = [r[0] for r in conn.execute("SELECT tokenHash FROM password_resets")]
    conn.close()
    self.assertNotIn(tok, hashes)
    self.assertIn(auth._hash_token(tok), hashes)

  def full_reset(self, new="newpass123"):
    self.request_reset(self.buyer_email())
    tok = self.link_token()
    path = f"/reset-password/{tok}"
    t = self.token(path)
    resp = self.client.post(path, data={"password": new, "confirm": new, "csrf_token": t})
    return tok, resp

  def test_reset_changes_password(self):
    _, resp = self.full_reset()
    self.assertEqual(resp.status_code, 302)
    self.client.get("/logout")
    self.assertEqual(self.login("buyer1", "password123").status_code, 401)
    self.assertEqual(self.login("buyer1", "newpass123").status_code, 302)

  def test_token_single_use(self):
    tok, _ = self.full_reset()
    self.assertEqual(self.client.get(f"/reset-password/{tok}").status_code, 400)

  def test_new_request_invalidates_old_token(self):
    self.request_reset(self.buyer_email())
    old = self.link_token()
    self.request_reset(self.buyer_email())
    self.assertEqual(self.client.get(f"/reset-password/{old}").status_code, 400)
    self.assertEqual(self.client.get(f"/reset-password/{self.link_token()}").status_code, 200)

  def test_expired_token_rejected(self):
    self.request_reset(self.buyer_email())
    tok = self.link_token()
    conn = database.get_db()
    conn.execute("UPDATE password_resets SET expiresAt = ?", (time.time() - 1,))
    conn.commit()
    conn.close()
    self.assertEqual(self.client.get(f"/reset-password/{tok}").status_code, 400)

  def test_bogus_token_rejected(self):
    self.assertEqual(self.client.get("/reset-password/not-a-real-token").status_code, 400)

  def test_weak_or_mismatched_password_rejected(self):
    self.request_reset(self.buyer_email())
    path = f"/reset-password/{self.link_token()}"
    t = self.token(path)
    short = self.client.post(path, data={"password": "abc", "confirm": "abc", "csrf_token": t})
    mismatch = self.client.post(path, data={"password": "longenough1", "confirm": "different1", "csrf_token": t})
    self.assertEqual((short.status_code, mismatch.status_code), (400, 400))
    self.assertEqual(self.login("buyer1", "password123").status_code, 302)

  def test_reset_post_needs_csrf(self):
    self.request_reset(self.buyer_email())
    path = f"/reset-password/{self.link_token()}"
    resp = self.client.post(path, data={"password": "newpass123", "confirm": "newpass123"})
    self.assertEqual(resp.status_code, 400)

  def test_reset_clears_lockout(self):
    for _ in range(auth.MAX_FAILED_ATTEMPTS):
      self.login("buyer1", "wrong")
    self.full_reset()
    self.assertEqual(self.login("buyer1", "newpass123").status_code, 302)

  def test_rate_limit(self):
    for _ in range(auth.MAX_RESET_REQUESTS):
      self.request_reset("nobody@example.com")
    self.assertEqual(self.request_reset("nobody@example.com").status_code, 429)


if __name__ == "__main__":
  unittest.main()
