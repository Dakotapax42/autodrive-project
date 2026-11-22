import calendar
from datetime import date, datetime

from database import get_db
from flask import (
    Blueprint, flash, redirect, render_template,
    request, session, url_for, abort
)

scheduling_bp = Blueprint("scheduling", __name__)

TIMESLOTS = [
    "9:00 AM",
    "10:00 AM",
    "11:00 AM",
    "1:00 PM",
    "2:00 PM",
    "3:00 PM",
]


@scheduling_bp.route("/schedule/<int:car_id>", methods=["GET", "POST"])
def schedule(car_id):

    if "user_id" not in session:
        flash("Please log in as a customer to book a test drive.", "warning")
        return redirect(url_for("auth.login"))

    if session.get("role") == "Employee":
        flash("Employees cannot schedule test drives.", "danger")
        return redirect(url_for("scheduling.view_appointments"))

    conn = get_db()

    car = conn.execute(
        "SELECT * FROM cars WHERE carID = ?", (car_id,)
    ).fetchone()

    if not car:
        conn.close()
        abort(404)

    if car["status"] != "Available":
        conn.close()
        flash("This vehicle is currently unavailable.", "warning")
        return redirect(url_for("inventory.cars"))

    today = date.today()

    # Allowed booking window: current month and one month ahead.
    min_month = today.replace(day=1)
    max_month = min_month.replace(
        year=min_month.year + 1 if min_month.month == 12 else min_month.year,
        month=1 if min_month.month == 12 else min_month.month + 1,
    )
    max_booking_day = calendar.monthrange(max_month.year, max_month.month)[1]
    max_booking_date = date(max_month.year, max_month.month, max_booking_day)

    # Determine which month to display, clamped to [min_month, max_month].
    month_value = request.values.get("month", today.strftime("%Y-%m"))

    try:
        current_month = datetime.strptime(
            month_value, "%Y-%m"
        ).date().replace(day=1)
    except ValueError:
        current_month = today.replace(day=1)

    if current_month < min_month:
        current_month = min_month
    elif current_month > max_month:
        current_month = max_month

    selected_date = (
        request.form.get("appt_date")
        or request.args.get("date", "")
    )

    if selected_date:
        try:
            parsed_selected = datetime.strptime(
                selected_date, "%Y-%m-%d"
            ).date()
            if parsed_selected < today or parsed_selected > max_booking_date:
                selected_date = ""
        except ValueError:
            selected_date = ""

    error = None
    success_data = None
    selected_timeslot = request.form.get("timeslot", "")

    # Process booking submission.
    if request.method == "POST":

        timeslot = request.form.get("timeslot", "")

        try:
            booking_date = datetime.strptime(
                selected_date, "%Y-%m-%d"
            ).date()
        except ValueError:
            booking_date = None

        if (
            not booking_date
            or booking_date < today
            or booking_date > max_booking_date
        ):
            error = (
                f"Please select a valid date between {today.isoformat()} "
                f"and {max_booking_date.isoformat()}."
            )

        elif timeslot not in TIMESLOTS:
            error = "Please select a valid timeslot."

        else:
            existing_booking = conn.execute(
                """
                SELECT apptID
                FROM appointments
                WHERE carID = ?
                AND date = ?
                AND timeslot = ?
                AND status != 'Cancelled'
                """,
                (car_id, selected_date, timeslot),
            ).fetchone()

            if existing_booking:
                error = (
                    "This time slot is already booked for this vehicle. "
                    "Please select a different time."
                )
            else:
                conn.execute(
                    """
                    INSERT INTO appointments
                    (customerID, carID, date, timeslot, testDrive, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session["user_id"],
                        car_id,
                        selected_date,
                        timeslot,
                        1,
                        "Confirmed",
                    ),
                )
                conn.commit()

                success_data = {
                    "date": selected_date,
                    "timeslot": timeslot,
                    "car_name": car["modelName"],
                }

    # Get all active bookings for this vehicle in the displayed month.
    year = current_month.year
    month = current_month.month

    last_day = calendar.monthrange(year, month)[1]
    month_start = f"{year}-{month:02d}-01"
    month_end = f"{year}-{month:02d}-{last_day:02d}"

    bookings = conn.execute(
        """
        SELECT date, timeslot
        FROM appointments
        WHERE carID = ?
        AND date BETWEEN ? AND ?
        AND status != 'Cancelled'
        """,
        (car_id, month_start, month_end),
    ).fetchall()

    conn.close()

    # Group booked times by date.
    booked_by_date = {}

    for booking in bookings:
        booked_by_date.setdefault(booking["date"], set()).add(
            booking["timeslot"]
        )

    # Build the calendar.
    calendar_rows = []

    for week in calendar.Calendar(firstweekday=6).monthdayscalendar(
        year, month
    ):
        calendar_week = []

        for day in week:
            if day == 0:
                calendar_week.append(None)
                continue

            day_date = date(year, month, day)
            date_string = day_date.isoformat()

            booked_count = len(
                booked_by_date.get(date_string, set())
            )

            if day_date < today:
                availability = "past"
            elif day_date > max_booking_date:
                availability = "unavailable"
            elif booked_count >= len(TIMESLOTS):
                availability = "full"
            else:
                availability = "available"

            calendar_week.append({
                "day": day,
                "date": date_string,
                "availability": availability,
                "selected": date_string == selected_date,
            })

        calendar_rows.append(calendar_week)

    # Build time slot availability for the selected date.
    slot_options = []

    if selected_date:
        booked_slots = booked_by_date.get(selected_date, set())

        slot_options = [
            {
                "time": slot,
                "booked": slot in booked_slots,
                "selected": slot == selected_timeslot,
            }
            for slot in TIMESLOTS
        ]

    previous_month = (
        None
        if current_month <= min_month
        else current_month.replace(
            year=year - 1 if month == 1 else year,
            month=12 if month == 1 else month - 1,
        ).strftime("%Y-%m")
    )

    next_month = (
        None
        if current_month >= max_month
        else current_month.replace(
            year=year + 1 if month == 12 else year,
            month=1 if month == 12 else month + 1,
        ).strftime("%Y-%m")
    )

    return render_template(
        "schedule.html",
        car_id=car_id,
        car=car,
        error=error,
        success_data=success_data,
        selected_date=selected_date,
        selected_timeslot=selected_timeslot,
        slot_options=slot_options,
        calendar_rows=calendar_rows,
        month_name=current_month.strftime("%B %Y"),
        previous_month=previous_month,
        next_month=next_month,
        current_month=current_month.strftime("%Y-%m"),
    )


@scheduling_bp.route("/appointments")
def view_appointments():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    role = session.get("role", "Customer")
    conn = get_db()

    if role == "Employee":
        query = """
            SELECT a.apptID, u.username AS customerName,
                   c.modelName, a.date, a.timeslot, a.status
            FROM appointments a
            JOIN users u ON a.customerID = u.userID
            JOIN cars c ON a.carID = c.carID
            ORDER BY a.date, a.timeslot
        """
        appointments = conn.execute(query).fetchall()

    else:
        query = """
            SELECT a.apptID, c.modelName, a.date,
                   a.timeslot, a.status
            FROM appointments a
            JOIN cars c ON a.carID = c.carID
            WHERE a.customerID = ?
            ORDER BY a.date, a.timeslot
        """
        appointments = conn.execute(query, (user_id,)).fetchall()

    conn.close()

    return render_template(
        "appointments.html",
        appointments=appointments,
        role=role
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
            """
            UPDATE appointments
            SET status = 'Cancelled'
            WHERE apptID = ? AND customerID = ?
            """,
            (appt_id, user_id),
        )

    conn.commit()
    conn.close()

    return redirect(url_for("scheduling.view_appointments"))