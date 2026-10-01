from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
import os
from datetime import datetime


# =========================================================
# FLASK APPLICATION
# =========================================================

app = Flask(__name__)

app.secret_key = "smart-emergency-secret-key"


# =========================================================
# DATABASE PATH
# =========================================================

DB_PATH = os.path.join(app.root_path, "users.db")


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db():

    conn = sqlite3.connect(DB_PATH)

    # Enable foreign key support
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


# =========================================================
# INITIALIZE DATABASE
# =========================================================

def init_db():

    conn = get_db()
    cursor = conn.cursor()


    # =====================================================
    # USERS TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL

        )
    """)


    # =====================================================
    # EMERGENCY REPORTS TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emergency_reports (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            emergency_type TEXT NOT NULL,

            injured TEXT NOT NULL,

            bleeding TEXT NOT NULL,

            breathing TEXT NOT NULL,

            people INTEGER NOT NULL,

            risk_score INTEGER NOT NULL,

            severity TEXT NOT NULL,

            latitude REAL,

            longitude REAL,

            created_at TEXT NOT NULL,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE

        )
    """)


    # =====================================================
    # EMERGENCY CONTACTS TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emergency_contacts (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            name TEXT NOT NULL,

            phone TEXT NOT NULL,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE

        )
    """)


    # =====================================================
    # DATABASE MIGRATION
    # Add latitude and longitude if old database
    # does not contain these columns
    # =====================================================

    cursor.execute("""
        PRAGMA table_info(emergency_reports)
    """)

    columns = [
        column[1]
        for column in cursor.fetchall()
    ]


    if "latitude" not in columns:

        cursor.execute("""
            ALTER TABLE emergency_reports
            ADD COLUMN latitude REAL
        """)


    if "longitude" not in columns:

        cursor.execute("""
            ALTER TABLE emergency_reports
            ADD COLUMN longitude REAL
        """)


    conn.commit()
    conn.close()


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    if "user_id" not in session:

        return redirect("/login")

    return render_template("index.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )


        # -------------------------------------------------
        # Validate input
        # -------------------------------------------------

        if not email or not password:

            return "Email and password are required."


        conn = get_db()
        cursor = conn.cursor()


        cursor.execute("""
            SELECT
                id,
                name
            FROM users
            WHERE email = ?
            AND password = ?
        """, (
            email,
            password
        ))


        user = cursor.fetchone()

        conn.close()


        if user:

            session["user_id"] = user[0]

            session["user_name"] = user[1]

            return redirect("/")


        return "Invalid email or password."


    return render_template("login.html")


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )


        # -------------------------------------------------
        # Validate registration
        # -------------------------------------------------

        if not name or not email or not password:

            return "All fields are required."


        if password != confirm_password:

            return "Passwords do not match."


        conn = get_db()
        cursor = conn.cursor()


        try:

            cursor.execute("""
                INSERT INTO users
                (
                    name,
                    email,
                    password
                )

                VALUES
                (
                    ?,
                    ?,
                    ?
                )
            """, (
                name,
                email,
                password
            ))


            conn.commit()


        except sqlite3.IntegrityError:

            conn.close()

            return "Email already registered."


        conn.close()


        return redirect("/login")


    return render_template("register.html")


# =========================================================
# FIRST AID
# =========================================================

@app.route("/first-aid")
def first_aid():

    if "user_id" not in session:

        return redirect("/login")

    return render_template("first-aid.html")


# =========================================================
# SAVE EMERGENCY REPORT
# =========================================================

@app.route("/save-emergency", methods=["POST"])
def save_emergency():

    # -----------------------------------------------------
    # Check login
    # -----------------------------------------------------

    if "user_id" not in session:

        return jsonify({

            "success": False,

            "message": "Please login first."

        }), 401


    # -----------------------------------------------------
    # Read JSON
    # -----------------------------------------------------

    data = request.get_json(silent=True)


    if not data:

        return jsonify({

            "success": False,

            "message": "Invalid emergency data."

        }), 400


    # =====================================================
    # GET EMERGENCY DETAILS
    # =====================================================

    emergency_type = data.get(
        "emergency_type"
    )

    injured = data.get(
        "injured"
    )

    bleeding = data.get(
        "bleeding"
    )

    breathing = data.get(
        "breathing"
    )

    people = data.get(
        "people"
    )

    risk_score = data.get(
        "risk_score"
    )

    severity = data.get(
        "severity"
    )


    # =====================================================
    # GET LOCATION
    # =====================================================

    latitude = data.get(
        "latitude"
    )

    longitude = data.get(
        "longitude"
    )


    # =====================================================
    # BASIC VALIDATION
    # =====================================================

    required_values = [

        emergency_type,
        injured,
        bleeding,
        breathing,
        people,
        risk_score,
        severity

    ]


    if any(
        value is None
        for value in required_values
    ):

        return jsonify({

            "success": False,

            "message": "Incomplete emergency information."

        }), 400


    # =====================================================
    # VALIDATE NUMBERS
    # =====================================================

    try:

        people = int(people)

        risk_score = int(risk_score)

    except (ValueError, TypeError):

        return jsonify({

            "success": False,

            "message": "Invalid numeric emergency data."

        }), 400


    # -----------------------------------------------------
    # Keep risk score within 0-100
    # -----------------------------------------------------

    risk_score = max(
        0,
        min(risk_score, 100)
    )


    # -----------------------------------------------------
    # Keep people count valid
    # -----------------------------------------------------

    people = max(
        1,
        people
    )


    # =====================================================
    # CREATED TIME
    # =====================================================

    created_at = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


    # =====================================================
    # DATABASE CONNECTION
    # =====================================================

    conn = get_db()
    cursor = conn.cursor()


    # =====================================================
    # SAVE EMERGENCY REPORT
    # =====================================================

    cursor.execute("""
        INSERT INTO emergency_reports
        (
            user_id,

            emergency_type,

            injured,

            bleeding,

            breathing,

            people,

            risk_score,

            severity,

            latitude,

            longitude,

            created_at
        )

        VALUES
        (
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?
        )
    """, (

        session["user_id"],

        emergency_type,

        injured,

        bleeding,

        breathing,

        people,

        risk_score,

        severity,

        latitude,

        longitude,

        created_at

    ))


    conn.commit()
    conn.close()


    # =====================================================
    # RESPONSE
    # =====================================================

    return jsonify({

        "success": True,

        "message": "Emergency report saved successfully."

    })


# =========================================================
# ADD EMERGENCY CONTACT
# =========================================================

@app.route("/add-contact", methods=["POST"])
def add_contact():

    # -----------------------------------------------------
    # Check login
    # -----------------------------------------------------

    if "user_id" not in session:

        return jsonify({

            "success": False,

            "message": "Please login first."

        }), 401


    data = request.get_json(
        silent=True
    )


    if not data:

        return jsonify({

            "success": False,

            "message": "Invalid contact data."

        }), 400


    name = data.get(
        "name",
        ""
    ).strip()

    phone = data.get(
        "phone",
        ""
    ).strip()


    # -----------------------------------------------------
    # Validate
    # -----------------------------------------------------

    if not name or not phone:

        return jsonify({

            "success": False,

            "message": "Name and phone number are required."

        }), 400


    conn = get_db()
    cursor = conn.cursor()


    cursor.execute("""
        INSERT INTO emergency_contacts
        (
            user_id,
            name,
            phone
        )

        VALUES
        (
            ?,
            ?,
            ?
        )
    """, (

        session["user_id"],

        name,

        phone

    ))


    conn.commit()
    conn.close()


    return jsonify({

        "success": True,

        "message": "Emergency contact added successfully."

    })


# =========================================================
# GET EMERGENCY CONTACTS
# =========================================================

@app.route("/get-contacts", methods=["GET"])
def get_contacts():

    # -----------------------------------------------------
    # Check login
    # -----------------------------------------------------

    if "user_id" not in session:

        return jsonify({

            "success": False,

            "message": "Please login first."

        }), 401


    conn = get_db()
    cursor = conn.cursor()


    cursor.execute("""
        SELECT
            id,
            name,
            phone

        FROM emergency_contacts

        WHERE user_id = ?

        ORDER BY id DESC
    """, (
        session["user_id"],
    ))


    contacts = cursor.fetchall()

    conn.close()


    # -----------------------------------------------------
    # Convert database rows to JSON
    # -----------------------------------------------------

    contact_list = []


    for contact in contacts:

        contact_list.append({

            "id": contact[0],

            "name": contact[1],

            "phone": contact[2]

        })


    return jsonify({

        "success": True,

        "contacts": contact_list

    })


# =========================================================
# DELETE EMERGENCY CONTACT
# =========================================================

@app.route(
    "/delete-contact/<int:contact_id>",
    methods=["DELETE"]
)
def delete_contact(contact_id):

    # -----------------------------------------------------
    # Check login
    # -----------------------------------------------------

    if "user_id" not in session:

        return jsonify({

            "success": False,

            "message": "Please login first."

        }), 401


    conn = get_db()
    cursor = conn.cursor()


    # -----------------------------------------------------
    # Delete only current user's contact
    # -----------------------------------------------------

    cursor.execute("""
        DELETE FROM emergency_contacts

        WHERE id = ?

        AND user_id = ?
    """, (
        contact_id,

        session["user_id"]
    ))


    conn.commit()


    deleted_rows = cursor.rowcount


    conn.close()


    if deleted_rows == 0:

        return jsonify({

            "success": False,

            "message": "Contact not found."

        }), 404


    return jsonify({

        "success": True,

        "message": "Emergency contact deleted successfully."

    })


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    # -----------------------------------------------------
    # Check login
    # -----------------------------------------------------

    if "user_id" not in session:

        return redirect("/login")


    conn = get_db()
    cursor = conn.cursor()


    # =====================================================
    # TOTAL REPORTS
    # =====================================================

    cursor.execute("""
        SELECT COUNT(*)

        FROM emergency_reports

        WHERE user_id = ?
    """, (
        session["user_id"],
    ))


    total_reports = cursor.fetchone()[0]


    # =====================================================
    # LOW COUNT
    # =====================================================

    cursor.execute("""
        SELECT COUNT(*)

        FROM emergency_reports

        WHERE user_id = ?

        AND severity = 'LOW'
    """, (
        session["user_id"],
    ))


    low_count = cursor.fetchone()[0]


    # =====================================================
    # MEDIUM COUNT
    # =====================================================

    cursor.execute("""
        SELECT COUNT(*)

        FROM emergency_reports

        WHERE user_id = ?

        AND severity = 'MEDIUM'
    """, (
        session["user_id"],
    ))


    medium_count = cursor.fetchone()[0]


    # =====================================================
    # HIGH COUNT
    # =====================================================

    cursor.execute("""
        SELECT COUNT(*)

        FROM emergency_reports

        WHERE user_id = ?

        AND severity = 'HIGH'
    """, (
        session["user_id"],
    ))


    high_count = cursor.fetchone()[0]


    # =====================================================
    # CRITICAL COUNT
    # =====================================================

    cursor.execute("""
        SELECT COUNT(*)

        FROM emergency_reports

        WHERE user_id = ?

        AND severity = 'CRITICAL'
    """, (
        session["user_id"],
    ))


    critical_count = cursor.fetchone()[0]


    # =====================================================
    # RISK PERCENTAGES
    # =====================================================

    if total_reports > 0:

        low_percentage = round(
            (low_count / total_reports) * 100
        )

        medium_percentage = round(
            (medium_count / total_reports) * 100
        )

        high_percentage = round(
            (high_count / total_reports) * 100
        )

        critical_percentage = round(
            (critical_count / total_reports) * 100
        )

    else:

        low_percentage = 0

        medium_percentage = 0

        high_percentage = 0

        critical_percentage = 0


    # =====================================================
    # EMERGENCY CATEGORY COUNTS
    # =====================================================

    cursor.execute("""
        SELECT
            emergency_type,
            COUNT(*)

        FROM emergency_reports

        WHERE user_id = ?

        GROUP BY emergency_type

        ORDER BY COUNT(*) DESC
    """, (
        session["user_id"],
    ))


    category_counts = cursor.fetchall()


    # =====================================================
    # RECENT REPORTS
    # =====================================================

    cursor.execute("""
        SELECT

            emergency_type,

            risk_score,

            severity,

            created_at

        FROM emergency_reports

        WHERE user_id = ?

        ORDER BY id DESC

        LIMIT 5
    """, (
        session["user_id"],
    ))


    recent_reports = cursor.fetchall()


    conn.close()


    # =====================================================
    # SEND DATA TO DASHBOARD
    # =====================================================

    return render_template(

        "dashboard.html",

        total_reports=total_reports,

        low_count=low_count,

        medium_count=medium_count,

        high_count=high_count,

        critical_count=critical_count,

        low_percentage=low_percentage,

        medium_percentage=medium_percentage,

        high_percentage=high_percentage,

        critical_percentage=critical_percentage,

        category_counts=category_counts,

        recent_reports=recent_reports

    )


# =========================================================
# EMERGENCY HISTORY
# =========================================================

@app.route("/emergency-history")
def emergency_history():

    # -----------------------------------------------------
    # Check login
    # -----------------------------------------------------

    if "user_id" not in session:

        return redirect("/login")


    conn = get_db()
    cursor = conn.cursor()


    # =====================================================
    # GET EMERGENCY REPORTS
    # =====================================================

    cursor.execute("""
        SELECT

            emergency_type,

            injured,

            bleeding,

            breathing,

            people,

            risk_score,

            severity,

            created_at

        FROM emergency_reports

        WHERE user_id = ?

        ORDER BY id DESC
    """, (
        session["user_id"],
    ))


    reports = cursor.fetchall()


    conn.close()


    # =====================================================
    # SEND DATA TO HISTORY PAGE
    # =====================================================

    return render_template(

        "history.html",

        reports=reports

    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# =========================================================
# START APPLICATION
# =========================================================

if __name__ == "__main__":

    init_db()

    app.run(
        debug=True
    )