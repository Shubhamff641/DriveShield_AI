from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify
)

from config import Config

import mysql.connector
import os
import uuid

from werkzeug.utils import secure_filename


profile = Blueprint("profile", __name__)


# ---------------------------------------------------------
# DATABASE CONNECTION
# ---------------------------------------------------------

def get_db_connection():

    return mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB
    )


# ---------------------------------------------------------
# CHECK ALLOWED PROFILE IMAGE
# ---------------------------------------------------------

def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in Config.ALLOWED_EXTENSIONS
    )


# ---------------------------------------------------------
# CREATE USER JSON RESPONSE
# ---------------------------------------------------------

def user_to_json(user):

    image_name = (
        user.get("profile_image")
        or "default.png"
    )

    return {
        "id": user["id"],
        "full_name": user["full_name"],
        "email": user["email"],
        "phone": user["phone"],
        "profile_image": image_name,

        # Android will combine this path with BASE_URL.
        "profile_image_url": (
            f"/static/uploads/{image_name}"
        )
    }


# =========================================================
# WEB PROFILE
# =========================================================

@profile.route("/profile", methods=["GET", "POST"])
def profile_page():

    if "user_id" not in session:

        return redirect(
            url_for("auth.login")
        )

    connection = None
    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        user_id = session["user_id"]

        cursor.execute(
            """
            SELECT
                id,
                full_name,
                email,
                phone,
                profile_image
            FROM users
            WHERE id = %s
            """,
            (user_id,)
        )

        user = cursor.fetchone()

        if not user:

            session.clear()

            flash(
                "User account was not found.",
                "danger"
            )

            return redirect(
                url_for("auth.login")
            )

        if request.method == "POST":

            fullname = request.form.get(
                "fullname",
                ""
            ).strip()

            email = request.form.get(
                "email",
                ""
            ).strip().lower()

            phone = request.form.get(
                "phone",
                ""
            ).strip()

            if not fullname or not email or not phone:

                flash(
                    "Full name, email and phone are required.",
                    "danger"
                )

                return redirect(
                    url_for("profile.profile_page")
                )

            # Check whether another account uses this email.
            cursor.execute(
                """
                SELECT id
                FROM users
                WHERE LOWER(TRIM(email)) = %s
                AND id != %s
                LIMIT 1
                """,
                (
                    email,
                    user_id
                )
            )

            duplicate_user = cursor.fetchone()

            if duplicate_user:

                flash(
                    "This email is already used by another account.",
                    "danger"
                )

                return redirect(
                    url_for("profile.profile_page")
                )

            image_name = (
                user.get("profile_image")
                or "default.png"
            )

            uploaded_file = request.files.get(
                "profile_image"
            )

            if (
                uploaded_file
                and uploaded_file.filename
            ):

                if not allowed_file(
                    uploaded_file.filename
                ):

                    flash(
                        "Please upload a valid image file.",
                        "danger"
                    )

                    return redirect(
                        url_for("profile.profile_page")
                    )

                safe_name = secure_filename(
                    uploaded_file.filename
                )

                unique_name = (
                    f"user_{user_id}_"
                    f"{uuid.uuid4().hex}_"
                    f"{safe_name}"
                )

                os.makedirs(
                    Config.UPLOAD_FOLDER,
                    exist_ok=True
                )

                uploaded_file.save(
                    os.path.join(
                        Config.UPLOAD_FOLDER,
                        unique_name
                    )
                )

                image_name = unique_name

            cursor.execute(
                """
                UPDATE users
                SET
                    full_name = %s,
                    email = %s,
                    phone = %s,
                    profile_image = %s
                WHERE id = %s
                """,
                (
                    fullname,
                    email,
                    phone,
                    image_name,
                    user_id
                )
            )

            connection.commit()

            session["user_name"] = fullname
            session["user_email"] = email

            flash(
                "Profile updated successfully!",
                "success"
            )

            return redirect(
                url_for("profile.profile_page")
            )

        return render_template(
            "profile.html",
            user=user
        )

    except mysql.connector.Error as error:

        print(
            "Web profile database error:",
            error
        )

        flash(
            "A database error occurred.",
            "danger"
        )

        return redirect(
            url_for("dashboard.dashboard_page")
        )

    finally:

        if cursor is not None:
            cursor.close()

        if (
            connection is not None
            and connection.is_connected()
        ):
            connection.close()


# =========================================================
# ANDROID PROFILE API
# GET  /api/profile
# PUT  /api/profile
# =========================================================

@profile.route(
    "/api/profile",
    methods=["GET", "PUT"]
)
def api_profile():

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Please log in before accessing your profile."
        }), 401

    connection = None
    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        user_id = session["user_id"]

        # -------------------------------------------------
        # GET PROFILE
        # -------------------------------------------------

        if request.method == "GET":

            cursor.execute(
                """
                SELECT
                    id,
                    full_name,
                    email,
                    phone,
                    profile_image
                FROM users
                WHERE id = %s
                """,
                (user_id,)
            )

            user = cursor.fetchone()

            if not user:

                return jsonify({
                    "success": False,
                    "message": "User account was not found."
                }), 404

            return jsonify({
                "success": True,
                "message": "Profile loaded successfully.",
                "user": user_to_json(user)
            }), 200

        # -------------------------------------------------
        # UPDATE PROFILE
        # -------------------------------------------------

        data = request.get_json(
            silent=True
        ) or {}

        fullname = str(
            data.get("full_name") or ""
        ).strip()

        email = str(
            data.get("email") or ""
        ).strip().lower()

        phone = str(
            data.get("phone") or ""
        ).strip()

        if not fullname or not email or not phone:

            return jsonify({
                "success": False,
                "message": "Full name, email and phone are required."
            }), 400

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE LOWER(TRIM(email)) = %s
            AND id != %s
            LIMIT 1
            """,
            (
                email,
                user_id
            )
        )

        duplicate_user = cursor.fetchone()

        if duplicate_user:

            return jsonify({
                "success": False,
                "message": "This email is already used by another account."
            }), 409

        cursor.execute(
            """
            UPDATE users
            SET
                full_name = %s,
                email = %s,
                phone = %s
            WHERE id = %s
            """,
            (
                fullname,
                email,
                phone,
                user_id
            )
        )

        connection.commit()

        session["user_name"] = fullname
        session["user_email"] = email

        cursor.execute(
            """
            SELECT
                id,
                full_name,
                email,
                phone,
                profile_image
            FROM users
            WHERE id = %s
            """,
            (user_id,)
        )

        updated_user = cursor.fetchone()

        return jsonify({
            "success": True,
            "message": "Profile updated successfully.",
            "user": user_to_json(updated_user)
        }), 200

    except mysql.connector.Error as error:

        print(
            "Android profile database error:",
            error
        )

        return jsonify({
            "success": False,
            "message": "A database error occurred."
        }), 500

    except Exception as error:

        print(
            "Android profile error:",
            error
        )

        return jsonify({
            "success": False,
            "message": "An unexpected profile error occurred."
        }), 500

    finally:

        if cursor is not None:
            cursor.close()

        if (
            connection is not None
            and connection.is_connected()
        ):
            connection.close()


# =========================================================
# ANDROID PROFILE IMAGE API
# POST /api/profile/image
# =========================================================

@profile.route(
    "/api/profile/image",
    methods=["POST"]
)
def api_profile_image():

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Please log in before updating your photo."
        }), 401

    uploaded_file = request.files.get(
        "profile_image"
    )

    if (
        uploaded_file is None
        or uploaded_file.filename == ""
    ):

        return jsonify({
            "success": False,
            "message": "Please select a profile image."
        }), 400

    if not allowed_file(
        uploaded_file.filename
    ):

        return jsonify({
            "success": False,
            "message": "Invalid image format."
        }), 400

    connection = None
    cursor = None

    try:

        user_id = session["user_id"]

        safe_name = secure_filename(
            uploaded_file.filename
        )

        unique_name = (
            f"user_{user_id}_"
            f"{uuid.uuid4().hex}_"
            f"{safe_name}"
        )

        os.makedirs(
            Config.UPLOAD_FOLDER,
            exist_ok=True
        )

        uploaded_file.save(
            os.path.join(
                Config.UPLOAD_FOLDER,
                unique_name
            )
        )

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            UPDATE users
            SET profile_image = %s
            WHERE id = %s
            """,
            (
                unique_name,
                user_id
            )
        )

        connection.commit()

        cursor.execute(
            """
            SELECT
                id,
                full_name,
                email,
                phone,
                profile_image
            FROM users
            WHERE id = %s
            """,
            (user_id,)
        )

        updated_user = cursor.fetchone()

        return jsonify({
            "success": True,
            "message": "Profile picture updated successfully.",
            "user": user_to_json(updated_user)
        }), 200

    except mysql.connector.Error as error:

        print(
            "Profile image database error:",
            error
        )

        return jsonify({
            "success": False,
            "message": "A database error occurred."
        }), 500

    except Exception as error:

        print(
            "Profile image upload error:",
            error
        )

        return jsonify({
            "success": False,
            "message": "Unable to upload profile picture."
        }), 500

    finally:

        if cursor is not None:
            cursor.close()

        if (
            connection is not None
            and connection.is_connected()
        ):
            connection.close()