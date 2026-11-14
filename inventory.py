from contextlib import closing
from flask import Blueprint, render_template, request, url_for
from database import get_db

inventory_bp = Blueprint("inventory", __name__)


@inventory_bp.route("/cars")
def cars():
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()

    query = """
        SELECT carID, modelName, category, fuelType, image, status, price, year, mileage
        FROM cars
        WHERE 1=1
    """
    parameters = []

    if search:
        escaped = search.replace("!", "!!").replace("%", "!%").replace("_", "!_")
        query += " AND modelName LIKE ? ESCAPE '!'"
        parameters.append(f"%{escaped}%")

    if status:
        query += " AND status = ?"
        parameters.append(status)

    query += " ORDER BY modelName COLLATE NOCASE, carID"

    with closing(get_db()) as conn:
        car_list = conn.execute(query, parameters).fetchall()

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
        status=status,
        statuses=statuses,
    )