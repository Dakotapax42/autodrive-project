from database import get_db
from flask import Blueprint, render_template, request, session

scheduling_bp = Blueprint("scheduling", __name__)


# TODO (Ting): Implement test drive booking & time-slot conflict check (FR-03)
# - Route URL: '/schedule/<int:car_id>'
# - HTML Form Input Name to read: request.form.get('appt_date')
# - Database Table to insert/check: 'appointments' (columns: id, user_id, car_id, appointment_date, status)
@scheduling_bp.route("/schedule/<int:car_id>", methods=["GET", "POST"])
def schedule(car_id):
  # 1. Check if user is logged in ('user_id' in session)

  if request.method == "POST":
    # 2. Grab 'appt_date' from the form submission
    # 3. Check 'appointments' table to see if a booking already exists for this car_id and appt_date (Conflict Check)
    # 4. If conflict, return an error message
    # 5. If no conflict, INSERT the new appointment into the 'appointments' table and commit
    pass

  return render_template("schedule.html", car_id=car_id)