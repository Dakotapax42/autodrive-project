from database import get_db
from flask import Blueprint, render_template, session, redirect

inventory_bp = Blueprint("inventory", __name__)


# TODO (Abahoor): Implement vehicle inventory view & search (FR-02)
# - Route URL: '/cars'
# - Database Table to query: 'cars' (columns: id, make, model, year, price, status)
@inventory_bp.route("/cars")
def cars():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    car_list = conn.execute("SELECT * FROM cars").fetchall()
    conn.close()

    return render_template("cars.html", cars=car_list)