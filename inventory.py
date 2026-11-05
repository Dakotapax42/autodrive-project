from contextlib import closing

from flask import Blueprint, redirect, render_template, request, session, url_for
from database import get_db

inventory_bp = Blueprint("inventory", __name__)


@inventory_bp.route("/cars")
def cars():
    # Only logged-in users can view the inventory.
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()
    status = request.args.get("status", "").strip()

    query = """
        SELECT carID, modelName, category, image, status
        FROM cars
        WHERE 1=1
    """
    parameters = []

    if search:
        escaped = search.replace("!", "!!").replace("%", "!%").replace("_", "!_")
        query += " AND modelName LIKE ? ESCAPE '!'"
        parameters.append(f"%{escaped}%")

    if category:
        query += " AND category = ?"
        parameters.append(category)

    if status:
        query += " AND status = ?"
        parameters.append(status)

    query += " ORDER BY modelName COLLATE NOCASE, carID"

    with closing(get_db()) as conn:
        car_list = conn.execute(query, parameters).fetchall()

        categories = [
            row[0]
            for row in conn.execute(
                "SELECT DISTINCT category FROM cars ORDER BY category"
            )
        ]

        statuses = [
            row[0]
            for row in conn.execute(
                """
                SELECT DISTINCT status
                FROM cars
                WHERE status IS NOT NULL
                ORDER BY status
                """
            )
        ]

    return render_template(
        "cars.html",
        cars=car_list,
        search=search,
        category=category,
        status=status,
        categories=categories,
        statuses=statuses,
    )