from database import get_db
from flask import Blueprint, render_template, session

inventory_bp = Blueprint("inventory", __name__)


# TODO (Abahoor): Implement vehicle inventory view & search (FR-02)
# - Route URL: '/cars'
# - Database Table to query: 'cars' (columns: id, make, model, year, price, status)
@inventory_bp.route("/cars")
def cars():
  # 1. Check if user is logged in ('user_id' in session), else redirect to login
  # 2. Query all rows from the 'cars' table
  # 3. Render 'cars.html' and pass the car list into it: render_template('cars.html', cars=car_list)
  pass