# AutoDrive Platform (MVP)

AutoDrive is a modular Flask web application designed for vehicle inventory management, user authentication, and test drive appointment scheduling. The project uses Python, Flask Blueprints, and an embedded SQLite database.

---

## Project Architecture and Team Roles

The system uses a modular blueprint structure to maintain separation of concerns across application components:

* **Architecture and System Integration Lead (Dakota Paxton):** Application entry point (`app.py`), database setup (`database.py`), virtual environment configuration, and core system integration.
* **Authentication Lead (Thomas):** User login, session management, and logout logic (`auth.py`).
* **Inventory Lead (Abahoor):** Vehicle inventory browsing and database query management (`inventory.py`).
* **Scheduling Lead (Ting):** Test drive reservation logic and appointment conflict checking (`scheduling.py`).
* **Frontend Lead (Jonathan):** HTML structure, user interfaces, and Jinja2 templates (`templates/`).

---

## Repository Structure

```text
autodrive-project/
├── .venv/                 # Local Python Virtual Environment (git ignored)
├── templates/             # Jinja2 HTML Templates
│   ├── index.html         # Landing page view
│   ├── login.html         # User authentication form
│   ├── cars.html          # Vehicle inventory list
│   └── schedule.html      # Test drive booking form
├── .gitignore             # Git ignore configuration
├── app.py                 # Main Flask application and blueprint registration
├── auth.py                # Authentication blueprint module
├── database.py            # SQLite configuration and schema initializers
├── inventory.py           # Inventory management blueprint module
├── scheduling.py          # Appointment scheduling blueprint module
├── autodrive.db           # SQLite database instance (git ignored)
└── README.md              # Project documentation
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

## Version Control Guidelines

* Do not commit local environment directories (`.venv/`) or database files (`autodrive.db`).
* Verify `.gitignore` rules before pushing changes to remote branches.