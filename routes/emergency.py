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


emergency = Blueprint(
    "emergency",
    __name__
)


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db():

    return mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB
    )


# =========================================================
# CONVERT CONTACT TO JSON
# =========================================================

def contact_to_json(contact):

    return {
        "id": contact["id"],
        "user_id": contact["user_id"],
        "contact_name": contact["contact_name"],
        "relationship": contact["relationship"],
        "contact_phone": contact["contact_phone"],
        "contact_email": contact.get("contact_email") or ""
    }


# =========================================================
# WEB PAGE — VIEW AND ADD CONTACTS
# =========================================================

@emergency.route(
    "/emergency",
    methods=["GET", "POST"]
)
def emergency_page():

    if "user_id" not in session:

        return redirect(
            url_for("auth.login")
        )

    db = None
    cursor = None

    try:

        db = get_db()

        cursor = db.cursor(
            dictionary=True
        )

        user_id = session["user_id"]

        if request.method == "POST":

            contact_name = (
                request.form
                .get("contact_name", "")
                .strip()
            )

            relationship = (
                request.form
                .get("relationship", "")
                .strip()
            )

            contact_phone = (
                request.form
                .get("phone", "")
                .strip()
            )

            contact_email = (
                request.form
                .get("contact_email", "")
                .strip()
                .lower()
            )

            if (
                not contact_name or
                not relationship or
                not contact_phone
            ):

                flash(
                    "Name, relationship and phone are required.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "emergency.emergency_page"
                    )
                )

            cursor.execute(
                """
                INSERT INTO emergency_contacts
                (
                    user_id,
                    contact_name,
                    relationship,
                    contact_phone,
                    contact_email
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    contact_name,
                    relationship,
                    contact_phone,
                    contact_email
                )
            )

            db.commit()

            flash(
                "Emergency Contact Added Successfully!",
                "success"
            )

            return redirect(
                url_for(
                    "emergency.emergency_page"
                )
            )

        cursor.execute(
            """
            SELECT
                id,
                user_id,
                contact_name,
                relationship,
                contact_phone,
                contact_email
            FROM emergency_contacts
            WHERE user_id = %s
            ORDER BY id DESC
            """,
            (user_id,)
        )

        contacts = cursor.fetchall()

        return render_template(
            "emergency.html",
            contacts=contacts
        )

    except mysql.connector.Error as error:

        if db is not None:
            db.rollback()

        flash(
            f"Database error: {error}",
            "danger"
        )

        return redirect(
            url_for(
                "dashboard.dashboard_page"
            )
        )

    finally:

        if cursor is not None:
            cursor.close()

        if db is not None and db.is_connected():
            db.close()


# =========================================================
# WEB PAGE — EDIT CONTACT
# =========================================================

@emergency.route(
    "/edit_contact/<int:id>",
    methods=["GET", "POST"]
)
def edit_contact(id):

    if "user_id" not in session:

        return redirect(
            url_for("auth.login")
        )

    db = None
    cursor = None

    try:

        db = get_db()

        cursor = db.cursor(
            dictionary=True
        )

        user_id = session["user_id"]

        if request.method == "POST":

            contact_name = (
                request.form
                .get("contact_name", "")
                .strip()
            )

            relationship = (
                request.form
                .get("relationship", "")
                .strip()
            )

            contact_phone = (
                request.form
                .get("phone", "")
                .strip()
            )

            contact_email = (
                request.form
                .get("contact_email", "")
                .strip()
                .lower()
            )

            if (
                not contact_name or
                not relationship or
                not contact_phone
            ):

                flash(
                    "Name, relationship and phone are required.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "emergency.edit_contact",
                        id=id
                    )
                )

            cursor.execute(
                """
                UPDATE emergency_contacts
                SET
                    contact_name = %s,
                    relationship = %s,
                    contact_phone = %s,
                    contact_email = %s
                WHERE id = %s
                AND user_id = %s
                """,
                (
                    contact_name,
                    relationship,
                    contact_phone,
                    contact_email,
                    id,
                    user_id
                )
            )

            if cursor.rowcount == 0:

                flash(
                    "Contact not found.",
                    "danger"
                )

            else:

                db.commit()

                flash(
                    "Contact Updated Successfully!",
                    "success"
                )

            return redirect(
                url_for(
                    "emergency.emergency_page"
                )
            )

        cursor.execute(
            """
            SELECT
                id,
                user_id,
                contact_name,
                relationship,
                contact_phone,
                contact_email
            FROM emergency_contacts
            WHERE id = %s
            AND user_id = %s
            """,
            (
                id,
                user_id
            )
        )

        contact = cursor.fetchone()

        if contact is None:

            flash(
                "Contact not found.",
                "danger"
            )

            return redirect(
                url_for(
                    "emergency.emergency_page"
                )
            )

        return render_template(
            "edit_contact.html",
            contact=contact
        )

    except mysql.connector.Error as error:

        if db is not None:
            db.rollback()

        flash(
            f"Database error: {error}",
            "danger"
        )

        return redirect(
            url_for(
                "emergency.emergency_page"
            )
        )

    finally:

        if cursor is not None:
            cursor.close()

        if db is not None and db.is_connected():
            db.close()


# =========================================================
# WEB PAGE — DELETE CONTACT
# =========================================================

@emergency.route(
    "/delete_contact/<int:id>",
    methods=["GET", "POST"]
)
def delete_contact(id):

    if "user_id" not in session:

        return redirect(
            url_for("auth.login")
        )

    db = None
    cursor = None

    try:

        db = get_db()

        cursor = db.cursor()

        user_id = session["user_id"]

        cursor.execute(
            """
            DELETE FROM emergency_contacts
            WHERE id = %s
            AND user_id = %s
            """,
            (
                id,
                user_id
            )
        )

        if cursor.rowcount == 0:

            flash(
                "Contact not found.",
                "danger"
            )

        else:

            db.commit()

            flash(
                "Contact Deleted Successfully!",
                "success"
            )

        return redirect(
            url_for(
                "emergency.emergency_page"
            )
        )

    except mysql.connector.Error as error:

        if db is not None:
            db.rollback()

        flash(
            f"Database error: {error}",
            "danger"
        )

        return redirect(
            url_for(
                "emergency.emergency_page"
            )
        )

    finally:

        if cursor is not None:
            cursor.close()

        if db is not None and db.is_connected():
            db.close()


# =========================================================
# API — GET ALL EMERGENCY CONTACTS
# =========================================================

@emergency.route(
    "/api/emergency-contacts",
    methods=["GET"]
)
def api_get_emergency_contacts():

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Please login first.",
            "contacts": []
        }), 401

    db = None
    cursor = None

    try:

        db = get_db()

        cursor = db.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT
                id,
                user_id,
                contact_name,
                relationship,
                contact_phone,
                contact_email
            FROM emergency_contacts
            WHERE user_id = %s
            ORDER BY id DESC
            """,
            (
                session["user_id"],
            )
        )

        contacts = cursor.fetchall()

        return jsonify({
            "success": True,
            "message": "Emergency contacts loaded successfully.",
            "contacts": [
                contact_to_json(contact)
                for contact in contacts
            ]
        }), 200

    except mysql.connector.Error as error:

        return jsonify({
            "success": False,
            "message": f"Database error: {error}",
            "contacts": []
        }), 500

    finally:

        if cursor is not None:
            cursor.close()

        if db is not None and db.is_connected():
            db.close()


# =========================================================
# API — ADD EMERGENCY CONTACT
# =========================================================

@emergency.route(
    "/api/emergency-contacts",
    methods=["POST"]
)
def api_add_emergency_contact():

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    data = request.get_json(
        silent=True
    ) or {}

    contact_name = (
        str(
            data.get(
                "contact_name",
                ""
            )
        )
        .strip()
    )

    relationship = (
        str(
            data.get(
                "relationship",
                ""
            )
        )
        .strip()
    )

    contact_phone = (
        str(
            data.get(
                "contact_phone",
                ""
            )
        )
        .strip()
    )

    contact_email = (
        str(
            data.get(
                "contact_email",
                ""
            )
        )
        .strip()
        .lower()
    )

    if not contact_name:

        return jsonify({
            "success": False,
            "message": "Contact name is required."
        }), 400

    if not relationship:

        return jsonify({
            "success": False,
            "message": "Relationship is required."
        }), 400

    if not contact_phone:

        return jsonify({
            "success": False,
            "message": "Contact phone is required."
        }), 400

    db = None
    cursor = None

    try:

        db = get_db()

        cursor = db.cursor(
            dictionary=True
        )

        user_id = session["user_id"]

        cursor.execute(
            """
            INSERT INTO emergency_contacts
            (
                user_id,
                contact_name,
                relationship,
                contact_phone,
                contact_email
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                user_id,
                contact_name,
                relationship,
                contact_phone,
                contact_email
            )
        )

        contact_id = cursor.lastrowid

        db.commit()

        cursor.execute(
            """
            SELECT
                id,
                user_id,
                contact_name,
                relationship,
                contact_phone,
                contact_email
            FROM emergency_contacts
            WHERE id = %s
            AND user_id = %s
            """,
            (
                contact_id,
                user_id
            )
        )

        contact = cursor.fetchone()

        return jsonify({
            "success": True,
            "message": "Emergency contact added successfully.",
            "contact": contact_to_json(contact)
        }), 201

    except mysql.connector.Error as error:

        if db is not None:
            db.rollback()

        return jsonify({
            "success": False,
            "message": f"Database error: {error}"
        }), 500

    finally:

        if cursor is not None:
            cursor.close()

        if db is not None and db.is_connected():
            db.close()


# =========================================================
# API — UPDATE EMERGENCY CONTACT
# =========================================================

@emergency.route(
    "/api/emergency-contacts/<int:contact_id>",
    methods=["PUT"]
)
def api_update_emergency_contact(contact_id):

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    data = request.get_json(
        silent=True
    ) or {}

    contact_name = (
        str(
            data.get(
                "contact_name",
                ""
            )
        )
        .strip()
    )

    relationship = (
        str(
            data.get(
                "relationship",
                ""
            )
        )
        .strip()
    )

    contact_phone = (
        str(
            data.get(
                "contact_phone",
                ""
            )
        )
        .strip()
    )

    contact_email = (
        str(
            data.get(
                "contact_email",
                ""
            )
        )
        .strip()
        .lower()
    )

    if not contact_name:

        return jsonify({
            "success": False,
            "message": "Contact name is required."
        }), 400

    if not relationship:

        return jsonify({
            "success": False,
            "message": "Relationship is required."
        }), 400

    if not contact_phone:

        return jsonify({
            "success": False,
            "message": "Contact phone is required."
        }), 400

    db = None
    cursor = None

    try:

        db = get_db()

        cursor = db.cursor(
            dictionary=True
        )

        user_id = session["user_id"]

        cursor.execute(
            """
            UPDATE emergency_contacts
            SET
                contact_name = %s,
                relationship = %s,
                contact_phone = %s,
                contact_email = %s
            WHERE id = %s
            AND user_id = %s
            """,
            (
                contact_name,
                relationship,
                contact_phone,
                contact_email,
                contact_id,
                user_id
            )
        )

        if cursor.rowcount == 0:

            cursor.execute(
                """
                SELECT id
                FROM emergency_contacts
                WHERE id = %s
                AND user_id = %s
                """,
                (
                    contact_id,
                    user_id
                )
            )

            existing_contact = cursor.fetchone()

            if existing_contact is None:

                return jsonify({
                    "success": False,
                    "message": "Emergency contact not found."
                }), 404

        db.commit()

        cursor.execute(
            """
            SELECT
                id,
                user_id,
                contact_name,
                relationship,
                contact_phone,
                contact_email
            FROM emergency_contacts
            WHERE id = %s
            AND user_id = %s
            """,
            (
                contact_id,
                user_id
            )
        )

        contact = cursor.fetchone()

        return jsonify({
            "success": True,
            "message": "Emergency contact updated successfully.",
            "contact": contact_to_json(contact)
        }), 200

    except mysql.connector.Error as error:

        if db is not None:
            db.rollback()

        return jsonify({
            "success": False,
            "message": f"Database error: {error}"
        }), 500

    finally:

        if cursor is not None:
            cursor.close()

        if db is not None and db.is_connected():
            db.close()


# =========================================================
# API — DELETE EMERGENCY CONTACT
# =========================================================

@emergency.route(
    "/api/emergency-contacts/<int:contact_id>",
    methods=["DELETE"]
)
def api_delete_emergency_contact(contact_id):

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    db = None
    cursor = None

    try:

        db = get_db()

        cursor = db.cursor()

        cursor.execute(
            """
            DELETE FROM emergency_contacts
            WHERE id = %s
            AND user_id = %s
            """,
            (
                contact_id,
                session["user_id"]
            )
        )

        if cursor.rowcount == 0:

            return jsonify({
                "success": False,
                "message": "Emergency contact not found."
            }), 404

        db.commit()

        return jsonify({
            "success": True,
            "message": "Emergency contact deleted successfully."
        }), 200

    except mysql.connector.Error as error:

        if db is not None:
            db.rollback()

        return jsonify({
            "success": False,
            "message": f"Database error: {error}"
        }), 500

    finally:

        if cursor is not None:
            cursor.close()

        if db is not None and db.is_connected():
            db.close()