import sqlite3

DB_NAME = "autodrive.db"


def get_db():
  conn = sqlite3.connect(DB_NAME)
  conn.row_factory = sqlite3.Row  # Allows accessing table columns by name
  return conn


def init_db():
  conn = get_db()
  cursor = conn.cursor()

  # Enable foreign key enforcement in SQLite
  cursor.execute("PRAGMA foreign_keys = ON;")

  # 1. USERS TABLE (Handles both Customers/Buyers and Employees via 'role')
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            userID INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            firstName TEXT NOT NULL,
            lastName TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            licenseID TEXT,
            dob TEXT,
            role TEXT NOT NULL -- 'Customer' or 'Employee'
        )
    """)

  # 2. CARS TABLE (Car Inventory)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS cars (
            carID INTEGER PRIMARY KEY AUTOINCREMENT,
            modelName TEXT NOT NULL,
            category TEXT NOT NULL,
            image TEXT,
            status TEXT DEFAULT 'Available'
        )
    """)

  # 3. APPOINTMENTS TABLE
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            apptID INTEGER PRIMARY KEY AUTOINCREMENT,
            customerID INTEGER NOT NULL,
            employeeID INTEGER,
            carID INTEGER NOT NULL,
            date TEXT NOT NULL,
            timeslot TEXT NOT NULL,
            testDrive BOOLEAN DEFAULT 1,
            status TEXT DEFAULT 'Confirmed',
            FOREIGN KEY (customerID) REFERENCES users(userID),
            FOREIGN KEY (employeeID) REFERENCES users(userID),
            FOREIGN KEY (carID) REFERENCES cars(carID)
        )
    """)

  # 4. PAY_INFO TABLE
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS pay_info (
            payID INTEGER PRIMARY KEY AUTOINCREMENT,
            customerID INTEGER NOT NULL,
            apptID INTEGER,
            cardType TEXT NOT NULL,
            cardNum TEXT NOT NULL,
            expDate TEXT NOT NULL,
            amount REAL NOT NULL,
            FOREIGN KEY (customerID) REFERENCES users(userID),
            FOREIGN KEY (apptID) REFERENCES appointments(apptID)
        )
    """)

  # Seed initial sample data if the tables are empty
  cursor.execute("SELECT COUNT(*) FROM users")
  if cursor.fetchone()[0] == 0:
    # Insert sample Customer and Employee profiles
    cursor.execute("""
            INSERT INTO users (username, firstName, lastName, email, password, licenseID, dob, role) 
            VALUES ('buyer1', 'John', 'Doe', 'john@buyer.com', 'password', 'NY-987654', '1995-04-12', 'Customer')
        """)
    cursor.execute("""
            INSERT INTO users (username, firstName, lastName, email, password, licenseID, dob, role) 
            VALUES ('employee1', 'Jane', 'Smith', 'jane@employee.com', 'password', 'NY-123456', '1988-09-20', 'Employee')
        """)

    # Seed 20 Pre-Loaded Cars for Inventory
    cars_data = [
        ("Tesla Model 3", "Electric", "tesla_model3.jpg", "Available"),
        ("Ford Mustang Mach-E", "SUV", "mache.jpg", "Available"),
        ("Chevrolet Bolt EV", "Electric", "bolt_ev.jpg", "Available"),
        ("Hyundai Ioniq 5", "Electric", "ioniq5.jpg", "Available"),
        ("Kia EV6", "Electric", "ev6.jpg", "Available"),
        ("Toyota Prius", "Hybrid", "prius.jpg", "Available"),
        ("Honda CR-V", "SUV", "crv.jpg", "Available"),
        ("Toyota Camry", "Sedan", "camry.jpg", "Available"),
        ("Ford F-150 Lightning", "Truck", "f150_lightning.jpg", "Available"),
        ("Rivian R1T", "Truck", "rivian_r1t.jpg", "Available"),
        ("Audi e-tron", "Electric", "etron.jpg", "Available"),
        ("BMW i4", "Electric", "bmw_i4.jpg", "Available"),
        ("Mercedes-Benz EQS", "Electric", "eqs.jpg", "Available"),
        ("Lexus RX", "SUV", "lexus_rx.jpg", "Available"),
        ("Subaru Outback", "SUV", "outback.jpg", "Available"),
        ("Mazda CX-5", "SUV", "cx5.jpg", "Available"),
        ("Volkswagen ID.4", "Electric", "id4.jpg", "Available"),
        ("Nissan Leaf", "Electric", "nissan_leaf.jpg", "Available"),
        ("Volvo XC40 Recharge", "SUV", "xc40.jpg", "Available"),
        ("Lucid Air", "Electric", "lucid_air.jpg", "Available"),
    ]

    cursor.executemany(
        """
            INSERT INTO cars (modelName, category, image, status) 
            VALUES (?, ?, ?, ?)
        """,
        cars_data,
    )

    conn.commit()

  conn.close()


if __name__ == "__main__":
  init_db()
  print(
      "Database 'autodrive.db' initialized with Users, Employees, and 20 cars!"
  )