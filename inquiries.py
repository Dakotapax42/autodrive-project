from datetime import date

from auth import login_required, role_required, verify_csrf
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

inquiries_bp = Blueprint("inquiries", __name__)

# Customer Inquiry Messaging (FReq-04)
#   Customers: send a question about a car, see only their own inquiries.
#   Employees: see all inquiries, reply to them.
MAX_MESSAGE_LENGTH = 1000
MAX_RESPONSE_LENGTH = 2000
MAX_PENDING_PER_CUSTOMER = 5  # simple spam limit


def _validate_text(text, limit, label):
  if not text:
    return f"{label} cannot be empty."
  if len(text) > limit:
    return f"{label} must be {limit} characters or fewer."
  return None


@inquiries_bp.route("/inquiries/new/<int:car_id>", methods=["GET", "POST"])
@role_required("Customer")
def new_inquiry(car_id):
  conn = get_db()
  car = conn.execute(
      "SELECT carID, modelName, year FROM cars WHERE carID = ?", (car_id,)
  ).fetchone()
  if car is None:
    conn.close()
    abort(404)

  if request.method == "POST":
    verify_csrf()
    message = request.form.get("message", "").strip()
    error = _validate_text(message, MAX_MESSAGE_LENGTH, "Message")

    if not error:
      pending = conn.execute(
          "SELECT COUNT(*) FROM inquiries "
          "WHERE customerID = ? AND status = 'Pending'",
          (session["user_id"],),
      ).fetchone()[0]
      if pending >= MAX_PENDING_PER_CUSTOMER:
        error = "You have too many unanswered inquiries. Please wait for a reply."

    if error:
      conn.close()
      flash(error, "error")
      return render_template("inquiry_form.html", car=car, message=message), 400

    conn.execute(
        "INSERT INTO inquiries (customerID, carID, message, status, dateSubmitted) "
        "VALUES (?, ?, ?, 'Pending', ?)",
        (session["user_id"], car_id, message, date.today().isoformat()),
    )
    conn.commit()
    conn.close()
    flash("Your inquiry was sent.", "success")
    return redirect(url_for("inquiries.list_inquiries"))

  conn.close()
  return render_template("inquiry_form.html", car=car, message="")


@inquiries_bp.route("/inquiries")
@login_required
def list_inquiries():
  conn = get_db()
  sql = (
      "SELECT i.inquiryID, i.message, i.response, i.status, i.dateSubmitted, "
      "c.modelName, c.year, u.username "
      "FROM inquiries i "
      "JOIN cars c ON c.carID = i.carID "
      "JOIN users u ON u.userID = i.customerID "
  )
  if session["role"] == "Employee":
    rows = conn.execute(sql + "ORDER BY i.status = 'Pending' DESC, i.inquiryID DESC")
  else:
    rows = conn.execute(
        sql + "WHERE i.customerID = ? ORDER BY i.inquiryID DESC",
        (session["user_id"],),
    )
  inquiries = rows.fetchall()
  conn.close()
  return render_template("inquiries.html", inquiries=inquiries)


@inquiries_bp.route("/inquiries/<int:inquiry_id>/respond", methods=["POST"])
@role_required("Employee")
def respond(inquiry_id):
  verify_csrf()
  response = request.form.get("response", "").strip()
  error = _validate_text(response, MAX_RESPONSE_LENGTH, "Response")
  if error:
    flash(error, "error")
    return redirect(url_for("inquiries.list_inquiries"))

  conn = get_db()
  cur = conn.execute(
      "UPDATE inquiries SET response = ?, status = 'Resolved' WHERE inquiryID = ?",
      (response, inquiry_id),
  )
  conn.commit()
  conn.close()
  if cur.rowcount == 0:
    abort(404)
  flash("Reply sent.", "success")
  return redirect(url_for("inquiries.list_inquiries"))
