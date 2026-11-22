from contextlib import closing
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
import secrets
import sqlite3

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from auth import role_required
from database import get_db


inventory_bp = Blueprint("inventory", __name__)

FIELDS = (
    "modelName",
    "category",
    "fuelType",
    "image",
    "status",
    "price",
    "year",
    "mileage",
)

COLUMNS = "carID, " + ", ".join(FIELDS)
FILTERS = ("category", "fuelType", "status")


# Browse and search the vehicle catalog.
@inventory_bp.get("/cars")
def cars():
    search = request.args.get("search", "").strip()

    filters = {
        key: request.args.get(key, "").strip()
        for key in FILTERS
    }

    query = f"SELECT {COLUMNS} FROM cars WHERE 1=1"
    parameters = []

    if search:
        escaped = (
            search.replace("!", "!!")
            .replace("%", "!%")
            .replace("_", "!_")
        )

        query += " AND modelName LIKE ? ESCAPE '!'"
        parameters.append(f"%{escaped}%")

    # Column names come from FILTERS above.
    # User-entered values are passed through placeholders.
    for column, value in filters.items():
        if value:
            query += f" AND {column} = ?"
            parameters.append(value)

        # Only allow these predefined sorting options.
    sort_options = {
        "name_asc": "modelName COLLATE NOCASE ASC, carID",
        "name_desc": "modelName COLLATE NOCASE DESC, carID",
        "price_asc": "price IS NULL, price ASC, carID",
        "price_desc": "price IS NULL, price DESC, carID",
        "mileage_asc": "mileage IS NULL, mileage ASC, carID",
        "mileage_desc": "mileage IS NULL, mileage DESC, carID",
        "year_desc": "year IS NULL, year DESC, carID",
        "year_asc": "year IS NULL, year ASC, carID",
    }

    sort = request.args.get("sort", "name_asc")

    # Fall back to alphabetical order for an invalid option.
    if sort not in sort_options:
        sort = "name_asc"

    query += " ORDER BY " + sort_options[sort]

    with closing(get_db()) as conn:
        car_list = conn.execute(query, parameters).fetchall()

        choices = {}

        for column in FILTERS:
            values = {
                row[0]
                for row in conn.execute(
                    f"""
                    SELECT DISTINCT {column}
                    FROM cars
                    WHERE {column} IS NOT NULL
                    """
                )
            }

            # Keep an active filter visible even if it has no matches.
            if filters[column]:
                values.add(filters[column])

            choices[column] = sorted(values)

    return render_template(
        "cars.html",
        cars=car_list,
        search=search,
        filters=filters,
        choices=choices,
        sort=sort,
    )


# Give inventory forms a token tied to the user's session.
def form_token():
    if "inventory_token" not in session:
        session["inventory_token"] = secrets.token_hex(32)

    return session["inventory_token"]


# Check the token before changing inventory data.
def verify_form():
    submitted_token = request.form.get("token", "")

    if not secrets.compare_digest(
        submitted_token.encode(),
        form_token().encode(),
    ):
        abort(400, "Please reload the form and try again.")


# Validate the employee's form input.
def validate_vehicle(values, images):
    required_fields = (
        "modelName",
        "category",
        "fuelType",
        "status",
    )

    if not all(values[key] for key in required_fields):
        return "Enter a vehicle name, category, fuel type, and status."

    if values["image"] and values["image"] not in images:
        return "Choose an image from the list."

    try:
        price = Decimal(values["price"])

        if (
            not price.is_finite()
            or not 0 <= price <= 9999999999
            or price != price.quantize(Decimal(".01"))
        ):
            raise ValueError

        values["price"] = float(price)

    except (InvalidOperation, ValueError):
        return (
            "Enter a nonnegative price up to 9,999,999,999 "
            "with at most two decimal places."
        )

    try:
        year = int(values["year"])
        mileage = int(values["mileage"])

        if (
            not 1886 <= year <= date.today().year + 1
            or not 0 <= mileage <= 2147483647
        ):
            raise ValueError

    except ValueError:
        return (
            "Check the model year and enter nonnegative whole miles."
        )


# Employees use the same form to add or edit a vehicle.
@inventory_bp.route("/cars/new", methods=["GET", "POST"])
@inventory_bp.route(
    "/cars/<int:car_id>/edit",
    methods=["GET", "POST"],
)
@role_required("Employee")
def vehicle_form(car_id=None):
    with closing(get_db()) as conn:
        values = {"status": "Available"}

        # An existing ID means we are editing a vehicle.
        if car_id is not None:
            car = conn.execute(
                f"SELECT {COLUMNS} FROM cars WHERE carID = ?",
                (car_id,),
            ).fetchone()

            if car is None:
                abort(404)

            values = dict(car)

        image_folder = Path(current_app.static_folder) / "images"

        images = sorted(
            "images/" + path.name
            for path in image_folder.glob("*")
            if path.is_file()
            and path.suffix.lower() in {
                ".png",
                ".jpg",
                ".jpeg",
                ".webp",
            }
        )

        # Preserve an existing image value when editing older records.
        if values.get("image") and values["image"] not in images:
            images.append(values["image"])

        error = None

        if request.method == "POST":
            verify_form()

            values = {
                name: request.form.get(name, "").strip()
                for name in FIELDS
            }

            error = validate_vehicle(values, images)

            if not error:
                parameters = [values[key] for key in FIELDS]

                # Commit on success and roll back if an operation fails.
                with conn:
                    if car_id is None:
                        conn.execute(
                            f"""
                            INSERT INTO cars ({", ".join(FIELDS)})
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            parameters,
                        )
                    else:
                        assignments = ", ".join(
                            f"{key} = ?" for key in FIELDS
                        )

                        result = conn.execute(
                            f"""
                            UPDATE cars
                            SET {assignments}
                            WHERE carID = ?
                            """,
                            parameters + [car_id],
                        )

                        if not result.rowcount:
                            abort(404)

                flash("Vehicle saved.")
                return redirect(url_for("inventory.cars"))

        return render_template(
            "vehicle_form.html",
            values=values,
            images=images,
            error=error,
            car_id=car_id,
            token=form_token(),
        ), 400 if error else 200


# Remove a listing after an employee confirms.
@inventory_bp.post("/cars/<int:car_id>/remove")
@role_required("Employee")
def remove_vehicle(car_id):
    verify_form()

    with closing(get_db()) as conn:
        # Prevent deletion of cars referenced by other records.
        conn.execute("PRAGMA foreign_keys = ON")

        try:
            with conn:
                result = conn.execute(
                    "DELETE FROM cars WHERE carID = ?",
                    (car_id,),
                )

                if not result.rowcount:
                    abort(404)

        except sqlite3.IntegrityError:
            flash(
                "This vehicle has appointments or inquiries. "
                "Edit its status to Unavailable to keep its history."
            )
        else:
            flash("Vehicle removed.")

    return redirect(url_for("inventory.cars"))