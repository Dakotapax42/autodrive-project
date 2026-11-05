from database import get_db
from flask import Blueprint, redirect, render_template, request, session, url_for

scheduling_bp = Blueprint("scheduling", __name__)


@scheduling_bp.route("/schedule/<int:car_id>", methods=["GET", "POST"])
def schedule(car_id):
  # 1. Check if user is logged in ('user_id' in session)
  if "user_id" not in session:
    return redirect(url_for("auth.login"))

  if request.method == "POST":
    # 2. Grab 'appt_date' from the form submission
    appt_date = request.form.get("appt_date")

    if not appt_date:
      return render_template(
          "schedule.html",
          car_id=car_id,
          error="Please select a valid appointment date and time.",
      )

    db = get_db()
    cursor = db.cursor()

    # 3. Check 'appointments' table to see if a booking already exists for this car_id and appt_date
    cursor.execute(
        """
            SELECT id FROM appointments 
            WHERE car_id = ? AND appointment_date = ? AND status != 'cancelled'
        """,
        (car_id, appt_date),
    )
    existing_booking = cursor.fetchone()

    # 4. If conflict, return an error message rendered on the template
    if existing_booking:
      return render_template(
          "schedule.html",
          car_id=car_id,
          error=(
              "This time slot is already booked for this vehicle. Please select"
              " a different time."
          ),
      )

    # 5. If no conflict, INSERT the new appointment into the 'appointments' table and commit
    user_id = session["user_id"]
    cursor.execute(
        """
            INSERT INTO appointments (user_id, car_id, appointment_date, status)
            VALUES (?, ?, ?, ?)
        """,
        (user_id, car_id, appt_date, "confirmed"),
    )
    db.commit()

    # Redirect to a success page or confirmation view (adjust route name as needed)
    return redirect(url_for("scheduling.schedule_success", car_id=car_id))

  return render_template("schedule.html", car_id=car_id)