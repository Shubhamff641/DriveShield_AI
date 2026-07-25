from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify
)

import mysql.connector
from config import Config


auth = Blueprint("auth", __name__)


def get_db_connection():
    """
    Creates a fresh MySQL connection for each request.

    This is safer than keeping one global connection and cursor,
    because MySQL connections may expire while Flask is running.
    """
    return mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB
    )


# ---------------------------------------------------------
# HOME PAGE
# ---------------------------------------------------------

@auth.route("/")
def home():
    return render_template("index.html")


# ---------------------------------------------------------
# WEB REGISTRATION
# ---------------------------------------------------------

@auth.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":
        return render_template("register.html")

    fullname = request.form.get("fullname", "").strip()
    email = request.form.get("email", "").strip().lower()
    phone = request.form.get("phone", "").strip()

    # Do not lowercase or strip the password.
    password = request.form.get("password", "")

    if not fullname or not email or not phone or not password:

        flash(
            "All fields are required.",
            "danger"
        )

        return render_template(
            "register.html",
            fullname=fullname,
            email=email,
            phone=phone
        )

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE LOWER(TRIM(email)) = %s
            LIMIT 1
            """,
            (email,)
        )

        existing_user = cursor.fetchone()

        if existing_user:

            flash(
                "Email already exists! Please use another email.",
                "danger"
            )

            return render_template(
                "register.html",
                fullname=fullname,
                email=email,
                phone=phone
            )

        cursor.execute(
            """
            INSERT INTO users (
                full_name,
                email,
                phone,
                password
            )
            VALUES (%s, %s, %s, %s)
            """,
            (
                fullname,
                email,
                phone,
                password
            )
        )

        connection.commit()

        flash(
            "Registration successful! Please login.",
            "success"
        )

        return redirect(
            url_for("auth.login")
        )

    except mysql.connector.Error as error:

        if connection is not None:
            connection.rollback()

        print(
            "Web registration database error:",
            error
        )

        flash(
            "Registration failed because of a database error.",
            "danger"
        )

        return render_template(
            "register.html",
            fullname=fullname,
            email=email,
            phone=phone
        )

    except Exception as error:

        if connection is not None:
            connection.rollback()

        print(
            "Web registration error:",
            error
        )

        flash(
            "An unexpected error occurred during registration.",
            "danger"
        )

        return render_template(
            "register.html",
            fullname=fullname,
            email=email,
            phone=phone
        )

    finally:

        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


# ---------------------------------------------------------
# WEB LOGIN
# ---------------------------------------------------------

@auth.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:

        flash(
            "Email and password are required.",
            "danger"
        )

        return render_template(
            "login.html",
            email=email
        )

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                full_name,
                email,
                password
            FROM users
            WHERE LOWER(TRIM(email)) = %s
            LIMIT 1
            """,
            (email,)
        )

        user = cursor.fetchone()

        if not user or user["password"] != password:

            flash(
                "Invalid email or password.",
                "danger"
            )

            return render_template(
                "login.html",
                email=email
            )

        session.clear()

        session["user_id"] = user["id"]
        session["user_name"] = user["full_name"]
        session["user_email"] = user["email"]

        return redirect(
            url_for("dashboard.dashboard_page")
        )

    except mysql.connector.Error as error:

        print(
            "Web login database error:",
            error
        )

        flash(
            "Login failed because of a database error.",
            "danger"
        )

        return render_template(
            "login.html",
            email=email
        )

    except Exception as error:

        print(
            "Web login error:",
            error
        )

        flash(
            "An unexpected error occurred during login.",
            "danger"
        )

        return render_template(
            "login.html",
            email=email
        )

    finally:

        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


# ---------------------------------------------------------
# WEB LOGOUT
# ---------------------------------------------------------

@auth.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("auth.login")
    )


# ---------------------------------------------------------
# ANDROID REGISTRATION API
# ---------------------------------------------------------

@auth.route("/api/register", methods=["POST"])
def api_register():

    data = request.get_json(silent=True) or {}

    fullname = str(
        data.get("full_name")
        or data.get("fullname")
        or data.get("name")
        or ""
    ).strip()

    email = str(
        data.get("email", "")
    ).strip().lower()

    phone = str(
        data.get("phone", "")
    ).strip()

    password = str(
        data.get("password", "")
    )

    if not fullname or not email or not phone or not password:

        return jsonify({
            "success": False,
            "message": "Full name, email, phone and password are required."
        }), 400

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE LOWER(TRIM(email)) = %s
            LIMIT 1
            """,
            (email,)
        )

        existing_user = cursor.fetchone()

        if existing_user:

            return jsonify({
                "success": False,
                "message": "An account with this email already exists."
            }), 409

        cursor.execute(
            """
            INSERT INTO users (
                full_name,
                email,
                phone,
                password
            )
            VALUES (%s, %s, %s, %s)
            """,
            (
                fullname,
                email,
                phone,
                password
            )
        )

        connection.commit()

        user_id = cursor.lastrowid

        return jsonify({
            "success": True,
            "message": "Registration successful. Please login.",
            "user": {
                "id": user_id,
                "full_name": fullname,
                "email": email,
                "phone": phone
            }
        }), 201

    except mysql.connector.Error as error:

        if connection is not None:
            connection.rollback()

        print(
            "Android registration API error:",
            error
        )

        return jsonify({
            "success": False,
            "message": "Database error occurred during registration."
        }), 500

    except Exception as error:

        if connection is not None:
            connection.rollback()

        print(
            "Android registration error:",
            error
        )

        return jsonify({
            "success": False,
            "message": "An unexpected registration error occurred."
        }), 500

    finally:

        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


# ---------------------------------------------------------
# ANDROID LOGIN API
# ---------------------------------------------------------

@auth.route("/api/login", methods=["POST"])
def api_login():

    data = request.get_json(silent=True) or {}

    email = str(
        data.get("email", "")
    ).strip().lower()

    # Keep the password exactly as entered.
    password = str(
        data.get("password", "")
    )

   
    if not email or not password:

        return jsonify({
            "success": False,
            "message": "Email and password are required."
        }), 400

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        

        cursor.execute(
            """
            SELECT
                id,
                full_name,
                email,
                phone,
                password
            FROM users
            WHERE LOWER(TRIM(email)) = %s
            LIMIT 1
            """,
            (email,)
        )

        user = cursor.fetchone()

        print(
            "User found =",
            user is not None
        )

        if user:

            print(
                "Stored email =",
                repr(user["email"]),
                "stored password length =",
                len(user["password"]),
                "password matches =",
                user["password"] == password
            )

        if not user or user["password"] != password:

            return jsonify({
                "success": False,
                "message": "Invalid email or password."
            }), 401

        session.clear()

        session["user_id"] = user["id"]
        session["user_name"] = user["full_name"]
        session["user_email"] = user["email"]

        return jsonify({
            "success": True,
            "message": "Login successful.",
            "user": {
                "id": user["id"],
                "full_name": user["full_name"],
                "email": user["email"],
                "phone": user["phone"]
            }
        }), 200

    except mysql.connector.Error as error:

        print(
            "Android login API error:",
            error
        )

        return jsonify({
            "success": False,
            "message": "Database error occurred during login."
        }), 500

    except Exception as error:

        print(
            "Android login error:",
            error
        )

        return jsonify({
            "success": False,
            "message": "An unexpected login error occurred."
        }), 500

    finally:

        if cursor is not None:
            cursor.close()

        if (
            connection is not None
            and connection.is_connected()
        ):
            connection.close()