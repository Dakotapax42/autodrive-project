# AutoDrive Platform (MVP)

## Overview & Design Philosophy

Traditional dealerships often run digital car listings and physical lot schedules in silos, leading to double-bookings and a frustrating experience for buyers and employees alike. **AutoDrive** unifies online inventory browsing with real-time test drive scheduling in a modular Flask and SQLite application.

* **3-Tier Modularity:** Separates frontend templates, Flask Blueprint controllers, and SQLite data management so team members can build and test independently.
* **Database-Enforced Integrity:** Relies on foreign key constraints, unique time-slot validations, and SQL-injection-resistant queries rather than frontend checks alone.
* **Security by Design:** Uses salted and hashed credentials alongside role-based access (customers vs. employees) and isolates payment records in a dedicated `pay_info` table.
* **Core Capabilities:** Includes user profile management, 20 pre-seeded vehicle models, conflict-validated bookings, and support for customer inquiries, availability management, and notification system.
---
## Project Architecture & Team Roles

Using a 3-Tier layered structure with Flask Blueprints keeps frontend views, backend routes/logic, and SQLite data persistence isolated so the team can build and integrate cleanly:

- **Project Manager, Architecture & Database Lead (Dakota Paxton):** Application entry point (`app.py`), database initialization and local SQLite setup (`database.py` / `autodrive.db`), repository coordination, documentation, and system integration.
- **Authentication & Inquiries Lead (Thomas):** User authentication, session management, password reset (`auth.py`), and customer inquiry messaging (`inquiries.py`).
- **Inventory Lead (Abahoor):** Vehicle catalog browsing, search/filtering, and inventory logic (`inventory.py`).
- **Scheduling & Notifications Lead (Ting):** Test drive appointment booking, time-slot conflict validation (`scheduling.py`), and booking notifications (`notifications.py`).
- **Frontend Lead (Jonathan):** HTML structure, styling, and Jinja2 templates (`templates/`).

---
## Repository Structure

```text
autodrive-project/
├── .venv/                      # Local Python Virtual Environment (git ignored)
├── static/                     # Static assets directory
│   ├── css/
│   │   └── style.css           # Global CSS stylesheet for UI styling & layouts
│   └── images/                 # Vehicle and UI image assets
├── templates/                  # Jinja2 HTML Templates
│   ├── appointments.html       # Appointment management & master calendar view
│   ├── base.html               # Master layout template (navigation & footer)
│   ├── cars.html               # Vehicle inventory list
│   ├── forgot_password.html    # Password recovery request view
│   ├── index.html              # Landing page view
│   ├── inquiries.html          # Customer inquiries overview
│   ├── inquiry_form.html       # Inquiry submission form
│   ├── login.html              # User authentication form
│   ├── reset_password.html     # Password reset view
│   ├── schedule.html           # Test drive booking form
│   └── vehicle_form.html       # Vehicle form view
├── .gitattributes              # Git attributes configuration
├── .gitignore                  # Configured to ignore .venv/ and local DBs
├── app.py                      # Main Flask driver script & Blueprint registration
├── auth.py                     # Authentication blueprint module
├── database.py                 # SQLite configuration and schema initializers
├── inquiries.py                # Inquiries module
├── inventory.py                # Inventory management blueprint module
├── notifications.py            # Notifications module
├── scheduling.py               # Appointment scheduling blueprint module
├── test_auth.py                # Authentication tests
├── test_inquiries_reset.py     # Inquiries and password reset tests
├── autodrive.db                # SQLite local database instance (git ignored)
└── README.md                   # Project documentation
```

---
## Setup and Installation

### 1. Prerequisites
* Python 3.10 or higher
* Git

### 2. Environment Setup

Clone the repository and navigate into the project directory:

```bash
git clone <repository-url>
cd autodrive-project
```

Create and activate a local virtual environment:

* **Windows (PowerShell/CMD):**
  ```powershell
  py -m venv .venv
  .\.venv\Scripts\activate
  ```

* **macOS/Linux:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

Install necessary project dependencies:

```bash
pip install flask
```
Initialize the local SQLite database and pre-seeded test data:

```bash
python database.py
```
### 3. Execution

Run the local development server:

```bash
python app.py
```

Access the application in a web browser at `http://127.0.0.1:5000/`.

---
## Pre-seeded Test Credentials

The database script automatically initializes standard test accounts on launch:

| Role | Username | Password |
| :--- | :--- | :--- |
| Customer | buyer1 | password123 |
| Employee | employee1 | admin123 |
---
## Notes & Troubleshooting

* Virtual Environment Required: Always ensure your `.venv` is activated before running scripts or installing packages. If your terminal prompt doesn't start with `(.venv)`, run `.\.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (Mac/Linux).
* Database Reset ("Hard Reset"): If you ever need to wipe your test bookings and restore the database to its pristine default state, simply delete the local `autodrive.db` file and re-run `python database.py`.
---
## Version Control Guidelines

* Do not commit local environment directories (`.venv/`) or database files (`autodrive.db`).
* Verify `.gitignore` rules before pushing changes to remote branches.
