import io
import uuid

import mysql.connector
from flask import Blueprint, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.utils import secure_filename

from config import Config
from database.db import get_db_connection


profile = Blueprint("profile", __name__)


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS
    )


def prepare_profile_image(uploaded_file, user_id):
    if uploaded_file is None or not uploaded_file.filename:
        raise ValueError("Please select a profile image.")

    if not allowed_file(uploaded_file.filename):
        raise ValueError("Please upload a PNG, JPG or JPEG image.")

    original_data = uploaded_file.read()

    if not original_data:
        raise ValueError("The selected image is empty.")

    if len(original_data) > Config.MAX_CONTENT_LENGTH:
        raise ValueError("The selected image is too large.")

    try:
        image = Image.open(io.BytesIO(original_data))
        image = ImageOps.exif_transpose(image)
        image.thumbnail((1200, 1200))

        if image.mode in {"RGBA", "LA"}:
            background = Image.new("RGB", image.size, "white")
            alpha = image.getchannel("A")
            background.paste(image.convert("RGB"), mask=alpha)
            image = background
        else:
            image = image.convert("RGB")

        output = io.BytesIO()
        image.save(output, format="JPEG", quality=85, optimize=True)
        image_data = output.getvalue()

    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise ValueError("The selected file is not a valid image.") from error

    safe_name = secure_filename(uploaded_file.filename)
    base_name = safe_name.rsplit(".", 1)[0] or "profile"
    image_name = f"user_{user_id}_{uuid.uuid4().hex}_{base_name}.jpg"

    return image_name, image_data, "image/jpeg"


def user_to_json(user):
    image_name = user.get("profile_image") or "default.png"

    return {
        "id": user["id"],
        "full_name": user["full_name"],
        "email": user["email"],
        "phone": user["phone"],
        "profile_image": image_name,
        "profile_image_url": url_for(
            "profile.profile_image_file",
            user_id=user["id"],
            v=image_name
        )
    }


@profile.route("/profile/image/<int:user_id>", methods=["GET"])
def profile_image_file(user_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT profile_image_data, profile_image_mime
            FROM users
            WHERE id = %s
            LIMIT 1
            """,
            (user_id,)
        )
        image_record = cursor.fetchone()

        if image_record and image_record.get("profile_image_data"):
            image_data = bytes(image_record["profile_image_data"])
            response = send_file(
                io.BytesIO(image_data),
                mimetype=image_record.get("profile_image_mime") or "image/jpeg",
                download_name=f"profile_{user_id}.jpg",
                max_age=86400
            )
            response.headers["Cache-Control"] = "public, max-age=86400"
            return response

        return redirect(url_for("static", filename="uploads/default.png"))

    except mysql.connector.Error as error:
        print("Profile image retrieval error:", error)
        return redirect(url_for("static", filename="uploads/default.png"))

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@profile.route("/profile", methods=["GET", "POST"])
def profile_page():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    connection = None
    cursor = None
    user_id = session["user_id"]

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, full_name, email, phone, profile_image
            FROM users
            WHERE id = %s
            LIMIT 1
            """,
            (user_id,)
        )
        user = cursor.fetchone()

        if not user:
            session.clear()
            flash("User account was not found.", "danger")
            return redirect(url_for("auth.login"))

        if request.method == "POST":
            fullname = request.form.get("fullname", "").strip()
            email = request.form.get("email", "").strip().lower()
            phone = request.form.get("phone", "").strip()

            if not fullname or not email or not phone:
                flash("Full name, email and phone are required.", "danger")
                return redirect(url_for("profile.profile_page"))

            cursor.execute(
                """
                SELECT id
                FROM users
                WHERE LOWER(TRIM(email)) = %s
                AND id != %s
                LIMIT 1
                """,
                (email, user_id)
            )

            if cursor.fetchone():
                flash("This email is already used by another account.", "danger")
                return redirect(url_for("profile.profile_page"))

            uploaded_file = request.files.get("profile_image")

            if uploaded_file is not None and uploaded_file.filename:
                image_name, image_data, image_mime = prepare_profile_image(
                    uploaded_file,
                    user_id
                )
                cursor.execute(
                    """
                    UPDATE users
                    SET full_name = %s,
                        email = %s,
                        phone = %s,
                        profile_image = %s,
                        profile_image_data = %s,
                        profile_image_mime = %s
                    WHERE id = %s
                    """,
                    (
                        fullname,
                        email,
                        phone,
                        image_name,
                        image_data,
                        image_mime,
                        user_id
                    )
                )
            else:
                cursor.execute(
                    """
                    UPDATE users
                    SET full_name = %s,
                        email = %s,
                        phone = %s
                    WHERE id = %s
                    """,
                    (fullname, email, phone, user_id)
                )

            connection.commit()
            session["user_name"] = fullname
            session["user_email"] = email
            flash("Profile updated successfully!", "success")
            return redirect(url_for("profile.profile_page"))

        return render_template("profile.html", user=user)

    except ValueError as error:
        if connection is not None:
            connection.rollback()
        flash(str(error), "danger")
        return redirect(url_for("profile.profile_page"))

    except mysql.connector.Error as error:
        if connection is not None:
            connection.rollback()
        print("Web profile database error:", error)
        flash("A database error occurred.", "danger")
        return redirect(url_for("dashboard.dashboard_page"))

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@profile.route("/api/profile", methods=["GET", "PUT"])
def api_profile():
    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "Please log in before accessing your profile."
        }), 401

    connection = None
    cursor = None
    user_id = session["user_id"]

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        if request.method == "GET":
            cursor.execute(
                """
                SELECT id, full_name, email, phone, profile_image
                FROM users
                WHERE id = %s
                LIMIT 1
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

        data = request.get_json(silent=True) or {}
        fullname = str(data.get("full_name") or "").strip()
        email = str(data.get("email") or "").strip().lower()
        phone = str(data.get("phone") or "").strip()

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
            (email, user_id)
        )

        if cursor.fetchone():
            return jsonify({
                "success": False,
                "message": "This email is already used by another account."
            }), 409

        cursor.execute(
            """
            UPDATE users
            SET full_name = %s,
                email = %s,
                phone = %s
            WHERE id = %s
            """,
            (fullname, email, phone, user_id)
        )
        connection.commit()
        session["user_name"] = fullname
        session["user_email"] = email

        cursor.execute(
            """
            SELECT id, full_name, email, phone, profile_image
            FROM users
            WHERE id = %s
            LIMIT 1
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
        if connection is not None:
            connection.rollback()
        print("Android profile database error:", error)
        return jsonify({
            "success": False,
            "message": "A database error occurred."
        }), 500

    except Exception as error:
        if connection is not None:
            connection.rollback()
        print("Android profile error:", error)
        return jsonify({
            "success": False,
            "message": "An unexpected profile error occurred."
        }), 500

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@profile.route("/api/profile/image", methods=["POST"])
def api_profile_image():
    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "Please log in before updating your photo."
        }), 401

    uploaded_file = request.files.get("profile_image")
    connection = None
    cursor = None
    user_id = session["user_id"]

    try:
        image_name, image_data, image_mime = prepare_profile_image(
            uploaded_file,
            user_id
        )
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            UPDATE users
            SET profile_image = %s,
                profile_image_data = %s,
                profile_image_mime = %s
            WHERE id = %s
            """,
            (image_name, image_data, image_mime, user_id)
        )
        connection.commit()

        cursor.execute(
            """
            SELECT id, full_name, email, phone, profile_image
            FROM users
            WHERE id = %s
            LIMIT 1
            """,
            (user_id,)
        )
        updated_user = cursor.fetchone()

        return jsonify({
            "success": True,
            "message": "Profile picture updated successfully.",
            "user": user_to_json(updated_user)
        }), 200

    except ValueError as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 400

    except mysql.connector.Error as error:
        if connection is not None:
            connection.rollback()
        print("Profile image database error:", error)
        return jsonify({
            "success": False,
            "message": "A database error occurred."
        }), 500

    except Exception as error:
        if connection is not None:
            connection.rollback()
        print("Profile image upload error:", error)
        return jsonify({
            "success": False,
            "message": "Unable to upload profile picture."
        }), 500

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()