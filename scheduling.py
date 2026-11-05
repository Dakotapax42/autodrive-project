from database import get_db
from flask import Blueprint, redirect, render_template, request, session, url_for

scheduling_bp = Blueprint("scheduling", __name__)


@scheduling_bp.route("/schedule/<int:car_id>", methods=["GET", "POST"])
def schedule(car_id):
  # 1. Check if user is logged in ('user_id' in session)
  if "user_id" not in session:
    return redirect(url_for("auth.login"))

  conn = get_db()
  # Fetch car details to display the modelName in the popup
  car = conn.execute("SELECT * FROM cars WHERE carID = ?", (car_id,)).fetchone()

  error = None
  success_data = None

  if request.method == "POST":
    # 2. Grab 'appt_date' and 'timeslot' from the form submission
    appt_date = request.form.get("appt_date")
    timeslot = request.form.get("timeslot")
    user_id = session["user_id"]

    if not appt_date or not timeslot:
      error = "Please select both an appointment date and a timeslot."
    else:
      # 3. Check 'appointments' table to see if a booking already exists (Conflict Check)
      existing_booking = conn.execute(
          """
              SELECT apptID FROM appointments 
              WHERE carID = ? AND date = ? AND timeslot = ? AND status != 'Cancelled'
          """,
          (car_id, appt_date, timeslot),
      ).fetchone()

      # 4. If conflict, return an error message
      if existing_booking:
        error = (
            "This time slot is already booked for this vehicle. Please select"
            " a different time."
        )
      else:
        # 5. If no conflict, INSERT the new appointment into the 'appointments' table and commit
        conn.execute(
            """
                INSERT INTO appointments (customerID, carID, date, timeslot, testDrive, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, car_id, appt_date, timeslot, 1, "Confirmed"),
        )
        conn.commit()

        # Package success details for the popup bubble
        success_data = {
            "date": appt_date,
            "timeslot": timeslot,
            "car_name": car["modelName"] if car else "Selected Vehicle",
        }

  conn.close()
  return render_template(
      "schedule.html",
      car_id=car_id,
      error=error,
      success_data=success_data,
  )


@scheduling_bp.route("/appointments")
def view_appointments():
  if "user_id" not in session:
    return redirect(url_for("auth.login"))

  user_id = session["user_id"]
  role = session.get("role", "Customer")
  conn = get_db()

  if role == "Employee":
    # Employees see ALL appointments across all customers (Master Calendar)
    query = """
            SELECT a.apptID, u.username AS customerName, c.modelName, a.date, a.timeslot, a.status
            FROM appointments a
            JOIN users u ON a.customerID = u.userID
            JOIN cars c ON a.carID = c.carID
            ORDER BY a.date, a.timeslot
        """
    appointments = conn.execute(query).fetchall()
  else:
    # Customers see ONLY their own appointments
    query = """
            SELECT a.apptID, c.modelName, a.date, a.timeslot, a.status
            FROM appointments a
            JOIN cars c ON a.carID = c.carID
            WHERE a.customerID = ?
            ORDER BY a.date, a.timeslot
        """
    appointments = conn.execute(query, (user_id,)).fetchall()

  conn.close()
  return render_template(
      "appointments.html", appointments=appointments, role=role
  )


@scheduling_bp.route("/appointments/cancel/<int:appt_id>", methods=["POST"])
def cancel_appointment(appt_id):
  if "user_id" not in session:
    return redirect(url_for("auth.login"))

  user_id = session["user_id"]
  role = session.get("role", "Customer")
  conn = get_db()

  if role == "Employee":
    conn.execute(
        "UPDATE appointments SET status = 'Cancelled' WHERE apptID = ?",
        (appt_id,),
    )
  else:
    conn.execute(
        "UPDATE appointments SET status = 'Cancelled' WHERE apptID = ? AND"
        " customerID = ?",
        (appt_id, user_id),
    )

  conn.commit()
  conn.close()
  return redirect(url_for("scheduling.view_appointments"))