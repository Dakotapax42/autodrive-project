import logging
from database import get_db

logger = logging.getLogger(__name__)


def deliver_notification(to_email: str, subject: str, body: str) -> None:
    if not to_email:
        return
    logger.info("[EMAIL -> %s] %s\n%s", to_email, subject, body)
    print(f"[EMAIL -> {to_email}] {subject}: {body}")


def _get_customer_email(conn, customer_id: int) -> str | None:
    row = conn.execute(
        "SELECT email FROM users WHERE userID = ?",
        (customer_id,),
    ).fetchone()
    return row["email"] if row and row["email"] else None


def _get_employee_emails(conn) -> list[str]:
    rows = conn.execute(
        "SELECT email FROM users WHERE role = 'Employee'"
    ).fetchall()
    return [row["email"] for row in rows if row["email"]]


def notify_booking_confirmed(
    appt_id: int,
    customer_id: int,
    car_name: str,
    appt_date: str,
    timeslot: str,
) -> None:
    conn = get_db()
    try:
        customer_email = _get_customer_email(conn, customer_id)
        employee_emails = _get_employee_emails(conn)
    finally:
        conn.close()

    customer_label = customer_email or f"Customer #{customer_id}"

    if customer_email:
        deliver_notification(
            customer_email,
            f"Test Drive Confirmed: {car_name}",
            (
                f"Your test drive for {car_name} on {appt_date} at {timeslot} "
                f"is confirmed (Appointment #{appt_id})."
            ),
        )

    for emp_email in employee_emails:
        deliver_notification(
            emp_email,
            f"New Test Drive Booking: {car_name} ({appt_date})",
            (
                f"Customer ({customer_label}) booked a test drive for {car_name} "
                f"on {appt_date} at {timeslot} (Appointment #{appt_id})."
            ),
        )


def notify_booking_cancelled(
    appt_id: int,
    customer_id: int,
    car_name: str,
    appt_date: str,
    timeslot: str,
) -> None:
    conn = get_db()
    try:
        customer_email = _get_customer_email(conn, customer_id)
        employee_emails = _get_employee_emails(conn)
    finally:
        conn.close()

    customer_label = customer_email or f"Customer #{customer_id}"

    if customer_email:
        deliver_notification(
            customer_email,
            f"Test Drive Cancelled: {car_name}",
            (
                f"Your test drive for {car_name} on {appt_date} at {timeslot} "
                f"has been cancelled (Appointment #{appt_id})."
            ),
        )

    for emp_email in employee_emails:
        deliver_notification(
            emp_email,
            f"Test Drive Cancelled: {car_name} ({appt_date})",
            (
                f"Appointment #{appt_id} for {car_name} on {appt_date} "
                f"at {timeslot} by {customer_label} was cancelled."
            ),
        )
