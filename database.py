from datetime import datetime
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

  # 2. CARS TABLE (Car Inventory, seperating body type and fuel type)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS cars (
            carID INTEGER PRIMARY KEY AUTOINCREMENT,
            modelName TEXT NOT NULL,
            category TEXT NOT NULL,     -- e.g., Sedan, SUV, Truck, Hatchback
            fuelType TEXT NOT NULL,     -- e.g., Electric, Hybrid, Gas
            image TEXT,
            status TEXT DEFAULT 'Available',
            price REAL NOT NULL,
            year INTEGER NOT NULL,
            mileage INTEGER NOT NULL
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

  # 4. INQUIRIES TABLE (Customer Messaging & Employee Response for FR-04)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS inquiries (
            inquiryID INTEGER PRIMARY KEY AUTOINCREMENT,
            customerID INTEGER NOT NULL,
            carID INTEGER NOT NULL,
            message TEXT NOT NULL,
            response TEXT,
            status TEXT DEFAULT 'Pending',
            dateSubmitted TEXT NOT NULL,
            FOREIGN KEY (customerID) REFERENCES users(userID),
            FOREIGN KEY (carID) REFERENCES cars(carID)
        )
    """)

  # 5. PAY_INFO TABLE
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
  # Seed 20 Pre-Loaded Cars with Body Style, Fuel Type, Price, Year, and Mileage attributes
  cars_data = [
        ("Tesla Model 3", "Sedan", "Electric", "images/tesla_model3.png", "Available", 38990.0, 2023, 12500),
        ("Ford Mustang Mach-E", "SUV", "Electric", "images/mache.png", "Available", 42995.0, 2023, 8400),
        ("Chevrolet Bolt EV", "Hatchback", "Electric", "images/bolt_ev.png", "Available", 26500.0, 2022, 19200),
        ("Hyundai Ioniq 5", "SUV", "Electric", "images/ioniq5.png", "Available", 41650.0, 2023, 5100),
        ("Kia EV6", "SUV", "Electric", "images/ev6.png", "Available", 48700.0, 2023, 7300),
        ("Toyota Prius", "Sedan", "Hybrid", "images/prius.png", "Available", 27950.0, 2023, 3100),
        ("Honda CR-V", "SUV", "Hybrid", "images/crv.png", "Available", 29500.0, 2022, 24000),
        ("Toyota Camry", "Sedan", "Hybrid", "images/camry.png", "Available", 26320.0, 2022, 21500),
        ("Ford F-150 Lightning", "Truck", "Electric", "images/f150_lightning.png", "Available", 55990.0, 2023, 11000),
        ("Rivian R1T", "Truck", "Electric", "images/rivian_r1t.png", "Available", 73000.0, 2023, 9500),
        ("Audi e-tron", "SUV", "Electric", "images/etron.png", "Available", 65900.0, 2022, 18000),
        ("BMW i4", "Sedan", "Electric", "images/bmw_i4.png", "Available", 52200.0, 2023, 6200),
        ("Mercedes-Benz EQS", "Sedan", "Electric", "images/eqs.png", "Available", 104400.0, 2023, 4000),
        ("Lexus RX", "SUV", "Hybrid", "images/lexus_rx.png", "Available", 48600.0, 2022, 28000),
        ("Subaru Outback", "SUV", "Gas", "images/outback.png", "Available", 28395.0, 2022, 31000),
        ("Mazda CX-5", "SUV", "Gas", "images/cx5.png", "Available", 29300.0, 2023, 14200),
        ("Volkswagen ID.4", "SUV", "Electric", "images/id4.png", "Available", 38995.0, 2023, 10800),
        ("Nissan Leaf", "Hatchback", "Electric", "images/nissan_leaf.png", "Available", 28040.0, 2022, 22000),
        ("Volvo XC40 Recharge", "SUV", "Electric", "images/xc40.png", "Available", 53500.0, 2023, 8900),
        ("Lucid Air", "Sedan", "Electric", "images/lucid_air.png", "Available", 82400.0, 2023, 3500),
    ]

    # Upgrade older databases while preserving vehicle IDs and related records.
  existing = {
      row["name"]
      for row in cursor.execute("PRAGMA table_info(cars)")
  }

  new_fields = {
      "fuelType": "TEXT",
      "price": "REAL",
      "year": "INTEGER",
      "mileage": "INTEGER",
  }

  missing = [
      field
      for field in new_fields
      if field not in existing
  ]

  if missing:
    cursor.execute("BEGIN")

    for field in missing:
      cursor.execute(
          f"ALTER TABLE cars ADD COLUMN {field} {new_fields[field]}"
      )

    for (
        model,
        category,
        fuel,
        image,
        status,
        price,
        year,
        mileage,
    ) in cars_data:
      specs = {
          "fuelType": fuel,
          "price": price,
          "year": year,
          "mileage": mileage,
      }

      updates = {
          field: specs[field]
          for field in missing
      }

      if "fuelType" in missing:
        # Original sample vehicles used fuel labels as categories.
        cursor.execute(
            """
            UPDATE cars
            SET category = ?
            WHERE modelName = ?
              AND category IN ('Electric', 'Hybrid')
            """,
            (category, model),
        )

        old_image = (
            image.split("/")[-1].replace(".png", ".jpg")
        )

        cursor.execute(
            """
            UPDATE cars
            SET image = ?
            WHERE modelName = ? AND image = ?
            """,
            (image, model, old_image),
        )

      assignments = ", ".join(
          f"{field} = ?"
          for field in updates
      )

      cursor.execute(
          f"""
          UPDATE cars
          SET {assignments}
          WHERE modelName = ?
          """,
          (*updates.values(), model),
      )

    conn.commit()
  # Seed initial sample data if the tables are empty
  cursor.execute("SELECT COUNT(*) FROM users")
  if cursor.fetchone()[0] == 0:
    # Insert sample Customer and Employee profiles
    cursor.execute("""
            INSERT INTO users (username, firstName, lastName, email, password, licenseID, dob, role) 
            VALUES ('buyer1', 'John', 'Doe', 'john@buyer.com', 'password123', 'NY-987654', '1995-04-12', 'Customer')
        """)
    cursor.execute("""
            INSERT INTO users (username, firstName, lastName, email, password, licenseID, dob, role) 
            VALUES ('employee1', 'Jane', 'Smith', 'jane@employee.com', 'admin123', 'NY-123456', '1988-09-20', 'Employee')
        """)



    cursor.executemany(
        """
            INSERT INTO cars (modelName, category, fuelType, image, status, price, year, mileage) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        cars_data,
    )

    # Seed a sample Customer Inquiry for testing FR-04
    cursor.execute("""
            INSERT INTO inquiries (customerID, carID, message, response, status, dateSubmitted)
            VALUES (1, 1, 'Is this Tesla equipped with Enhanced Autopilot?', 'Yes, it includes standard Autopilot capabilities.', 'Resolved', '2026-03-01')
        """)

    conn.commit()

  conn.close()


if __name__ == "__main__":
  init_db()
  print(
      "Database 'autodrive.db' successfully initialized with Users, Cars, Appointments,"
      " Inquiries, and Pay Info tables!"
  )