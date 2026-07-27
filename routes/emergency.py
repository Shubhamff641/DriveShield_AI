from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for
)

import mysql.connector

from config import Config


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
        port=getattr(
            Config,
            "MYSQL_PORT",
            3306
        ),
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB
    )


# =========================================================
# COMMON HELPERS
# =========================================================

def value_to_boolean(
    value,
    default=False
):

    if value is None:
        return default

    if isinstance(
        value,
        bool
    ):
        return value

    if isinstance(
        value,
        (int, float)
    ):
        return value != 0

    return str(value).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
        "primary"
    }


def contact_to_json(
    contact
):

    return {
        "id": int(
            contact["id"]
        ),

        "user_id": int(
            contact["user_id"]
        ),

        "contact_name": (
            contact.get(
                "contact_name"
            )
            or ""
        ),

        "relationship": (
            contact.get(
                "relationship"
            )
            or ""
        ),

        "contact_phone": (
            contact.get(
                "contact_phone"
            )
            or ""
        ),

        "contact_email": (
            contact.get(
                "contact_email"
            )
            or ""
        ),

        "is_primary": bool(
            contact.get(
                "is_primary",
                0
            )
        )
    }


def select_contact(
    cursor,
    contact_id,
    user_id
):

    cursor.execute(
        """
        SELECT
            id,
            user_id,
            contact_name,
            relationship,
            contact_phone,
            contact_email,
            is_primary
        FROM emergency_contacts
        WHERE id = %s
          AND user_id = %s
        LIMIT 1
        """,
        (
            contact_id,
            user_id
        )
    )

    return cursor.fetchone()


def clear_primary_contacts(
    cursor,
    user_id
):

    cursor.execute(
        """
        UPDATE emergency_contacts
        SET is_primary = 0
        WHERE user_id = %s
        """,
        (
            user_id,
        )
    )


def make_contact_primary(
    cursor,
    user_id,
    contact_id
):

    contact = select_contact(
        cursor,
        contact_id,
        user_id
    )

    if contact is None:
        return False

    clear_primary_contacts(
        cursor,
        user_id
    )

    cursor.execute(
        """
        UPDATE emergency_contacts
        SET is_primary = 1
        WHERE id = %s
          AND user_id = %s
        """,
        (
            contact_id,
            user_id
        )
    )

    return True


def ensure_primary_contact(
    cursor,
    user_id
):
    """
    Guarantee that a user who has contacts also has one
    primary contact.

    The oldest saved contact becomes the fallback primary.
    """

    cursor.execute(
        """
        SELECT id
        FROM emergency_contacts
        WHERE user_id = %s
          AND is_primary = 1
        ORDER BY id ASC
        LIMIT 1
        """,
        (
            user_id,
        )
    )

    primary_contact = cursor.fetchone()

    if primary_contact is not None:
        return int(
            primary_contact["id"]
        )

    cursor.execute(
        """
        SELECT id
        FROM emergency_contacts
        WHERE user_id = %s
        ORDER BY id ASC
        LIMIT 1
        """,
        (
            user_id,
        )
    )

    fallback_contact = cursor.fetchone()

    if fallback_contact is None:
        return None

    fallback_contact_id = int(
        fallback_contact["id"]
    )

    cursor.execute(
        """
        UPDATE emergency_contacts
        SET is_primary = 1
        WHERE id = %s
          AND user_id = %s
        """,
        (
            fallback_contact_id,
            user_id
        )
    )

    return fallback_contact_id


def user_has_contacts(
    cursor,
    user_id
):

    cursor.execute(
        """
        SELECT COUNT(*) AS contact_count
        FROM emergency_contacts
        WHERE user_id = %s
        """,
        (
            user_id,
        )
    )

    row = cursor.fetchone()

    return int(
        row["contact_count"]
        if row is not None
        else 0
    ) > 0


# =========================================================
# WEB PAGE — VIEW AND ADD CONTACTS
# =========================================================

@emergency.route(
    "/emergency",
    methods=[
        "GET",
        "POST"
    ]
)
def emergency_page():

    if "user_id" not in session:

        return redirect(
            url_for(
                "auth.login"
            )
        )

    database = None
    cursor = None

    try:

        database = get_db()

        cursor = database.cursor(
            dictionary=True
        )

        user_id = session["user_id"]

        if request.method == "POST":

            contact_name = (
                request.form
                .get(
                    "contact_name",
                    ""
                )
                .strip()
            )

            relationship = (
                request.form
                .get(
                    "relationship",
                    ""
                )
                .strip()
            )

            contact_phone = (
                request.form
                .get(
                    "phone",
                    ""
                )
                .strip()
            )

            contact_email = (
                request.form
                .get(
                    "contact_email",
                    ""
                )
                .strip()
                .lower()
            )

            requested_primary = (
                value_to_boolean(
                    request.form.get(
                        "is_primary"
                    ),
                    False
                )
            )

            if (
                not contact_name
                or not relationship
                or not contact_phone
            ):

                flash(
                    (
                        "Name, relationship and "
                        "phone are required."
                    ),
                    "danger"
                )

                return redirect(
                    url_for(
                        "emergency.emergency_page"
                    )
                )

            is_first_contact = (
                not user_has_contacts(
                    cursor,
                    user_id
                )
            )

            should_be_primary = (
                requested_primary
                or is_first_contact
            )

            if should_be_primary:

                clear_primary_contacts(
                    cursor,
                    user_id
                )

            cursor.execute(
                """
                INSERT INTO emergency_contacts
                (
                    user_id,
                    contact_name,
                    relationship,
                    contact_phone,
                    contact_email,
                    is_primary
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    user_id,
                    contact_name,
                    relationship,
                    contact_phone,
                    contact_email,
                    int(
                        should_be_primary
                    )
                )
            )

            ensure_primary_contact(
                cursor,
                user_id
            )

            database.commit()

            flash(
                (
                    "Emergency Contact Added "
                    "Successfully!"
                ),
                "success"
            )

            return redirect(
                url_for(
                    "emergency.emergency_page"
                )
            )

        ensure_primary_contact(
            cursor,
            user_id
        )

        database.commit()

        cursor.execute(
            """
            SELECT
                id,
                user_id,
                contact_name,
                relationship,
                contact_phone,
                contact_email,
                is_primary
            FROM emergency_contacts
            WHERE user_id = %s
            ORDER BY
                is_primary DESC,
                id DESC
            """,
            (
                user_id,
            )
        )

        contacts = cursor.fetchall()

        return render_template(
            "emergency.html",
            contacts=contacts
        )

    except mysql.connector.Error as error:

        if database is not None:
            database.rollback()

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

        if (
            database is not None
            and database.is_connected()
        ):
            database.close()


# =========================================================
# WEB PAGE — EDIT CONTACT
# =========================================================

@emergency.route(
    "/edit_contact/<int:id>",
    methods=[
        "GET",
        "POST"
    ]
)
def edit_contact(
    id
):

    if "user_id" not in session:

        return redirect(
            url_for(
                "auth.login"
            )
        )

    database = None
    cursor = None

    try:

        database = get_db()

        cursor = database.cursor(
            dictionary=True
        )

        user_id = session["user_id"]

        contact = select_contact(
            cursor,
            id,
            user_id
        )

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

        if request.method == "POST":

            contact_name = (
                request.form
                .get(
                    "contact_name",
                    ""
                )
                .strip()
            )

            relationship = (
                request.form
                .get(
                    "relationship",
                    ""
                )
                .strip()
            )

            contact_phone = (
                request.form
                .get(
                    "phone",
                    ""
                )
                .strip()
            )

            contact_email = (
                request.form
                .get(
                    "contact_email",
                    ""
                )
                .strip()
                .lower()
            )

            requested_primary = (
                value_to_boolean(
                    request.form.get(
                        "is_primary"
                    ),
                    False
                )
            )

            if (
                not contact_name
                or not relationship
                or not contact_phone
            ):

                flash(
                    (
                        "Name, relationship and "
                        "phone are required."
                    ),
                    "danger"
                )

                return redirect(
                    url_for(
                        "emergency.edit_contact",
                        id=id
                    )
                )

            if requested_primary:

                clear_primary_contacts(
                    cursor,
                    user_id
                )

            cursor.execute(
                """
                UPDATE emergency_contacts
                SET
                    contact_name = %s,
                    relationship = %s,
                    contact_phone = %s,
                    contact_email = %s,
                    is_primary = %s
                WHERE id = %s
                  AND user_id = %s
                """,
                (
                    contact_name,
                    relationship,
                    contact_phone,
                    contact_email,
                    int(
                        requested_primary
                    ),
                    id,
                    user_id
                )
            )

            ensure_primary_contact(
                cursor,
                user_id
            )

            database.commit()

            flash(
                (
                    "Contact Updated "
                    "Successfully!"
                ),
                "success"
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

        if database is not None:
            database.rollback()

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

        if (
            database is not None
            and database.is_connected()
        ):
            database.close()


# =========================================================
# WEB PAGE — SET PRIMARY CONTACT
# =========================================================

@emergency.route(
    "/set_primary_contact/<int:id>",
    methods=[
        "GET",
        "POST"
    ]
)
def set_primary_contact(
    id
):

    if "user_id" not in session:

        return redirect(
            url_for(
                "auth.login"
            )
        )

    database = None
    cursor = None

    try:

        database = get_db()

        cursor = database.cursor(
            dictionary=True
        )

        user_id = session["user_id"]

        primary_updated = (
            make_contact_primary(
                cursor,
                user_id,
                id
            )
        )

        if not primary_updated:

            flash(
                "Contact not found.",
                "danger"
            )

        else:

            database.commit()

            flash(
                "Primary contact updated.",
                "success"
            )

        return redirect(
            url_for(
                "emergency.emergency_page"
            )
        )

    except mysql.connector.Error as error:

        if database is not None:
            database.rollback()

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

        if (
            database is not None
            and database.is_connected()
        ):
            database.close()


# =========================================================
# WEB PAGE — DELETE CONTACT
# =========================================================

@emergency.route(
    "/delete_contact/<int:id>",
    methods=[
        "GET",
        "POST"
    ]
)
def delete_contact(
    id
):

    if "user_id" not in session:

        return redirect(
            url_for(
                "auth.login"
            )
        )

    database = None
    cursor = None

    try:

        database = get_db()

        cursor = database.cursor(
            dictionary=True
        )

        user_id = session["user_id"]

        contact = select_contact(
            cursor,
            id,
            user_id
        )

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

        ensure_primary_contact(
            cursor,
            user_id
        )

        database.commit()

        flash(
            (
                "Contact Deleted "
                "Successfully!"
            ),
            "success"
        )

        return redirect(
            url_for(
                "emergency.emergency_page"
            )
        )

    except mysql.connector.Error as error:

        if database is not None:
            database.rollback()

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

        if (
            database is not None
            and database.is_connected()
        ):
            database.close()


# =========================================================
# API — GET ALL EMERGENCY CONTACTS
# =========================================================

@emergency.route(
    "/api/emergency-contacts",
    methods=[
        "GET"
    ]
)
def api_get_emergency_contacts():

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Please login first.",
            "contacts": []
        }), 401

    database = None
    cursor = None

    try:

        database = get_db()

        cursor = database.cursor(
            dictionary=True
        )

        user_id = session["user_id"]

        ensure_primary_contact(
            cursor,
            user_id
        )

        database.commit()

        cursor.execute(
            """
            SELECT
                id,
                user_id,
                contact_name,
                relationship,
                contact_phone,
                contact_email,
                is_primary
            FROM emergency_contacts
            WHERE user_id = %s
            ORDER BY
                is_primary DESC,
                id DESC
            """,
            (
                user_id,
            )
        )

        contacts = cursor.fetchall()

        return jsonify({
            "success": True,
            "message": (
                "Emergency contacts "
                "loaded successfully."
            ),
            "contacts": [
                contact_to_json(
                    contact
                )
                for contact in contacts
            ]
        }), 200

    except mysql.connector.Error as error:

        return jsonify({
            "success": False,
            "message": (
                f"Database error: {error}"
            ),
            "contacts": []
        }), 500

    finally:

        if cursor is not None:
            cursor.close()

        if (
            database is not None
            and database.is_connected()
        ):
            database.close()


# =========================================================
# API — GET PRIMARY EMERGENCY CONTACT
# =========================================================

@emergency.route(
    "/api/emergency-contacts/primary",
    methods=[
        "GET"
    ]
)
def api_get_primary_contact():

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Please login first.",
            "contact": None
        }), 401

    database = None
    cursor = None

    try:

        database = get_db()

        cursor = database.cursor(
            dictionary=True
        )

        user_id = session["user_id"]

        primary_contact_id = (
            ensure_primary_contact(
                cursor,
                user_id
            )
        )

        database.commit()

        if primary_contact_id is None:

            return jsonify({
                "success": False,
                "message": (
                    "No emergency contact "
                    "is available."
                ),
                "contact": None
            }), 404

        contact = select_contact(
            cursor,
            primary_contact_id,
            user_id
        )

        return jsonify({
            "success": True,
            "message": (
                "Primary emergency contact "
                "loaded successfully."
            ),
            "contact": contact_to_json(
                contact
            )
        }), 200

    except mysql.connector.Error as error:

        return jsonify({
            "success": False,
            "message": (
                f"Database error: {error}"
            ),
            "contact": None
        }), 500

    finally:

        if cursor is not None:
            cursor.close()

        if (
            database is not None
            and database.is_connected()
        ):
            database.close()


# =========================================================
# API — ADD EMERGENCY CONTACT
# =========================================================

@emergency.route(
    "/api/emergency-contacts",
    methods=[
        "POST"
    ]
)
def api_add_emergency_contact():

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    contact_name = str(
        data.get(
            "contact_name",
            ""
        )
    ).strip()

    relationship = str(
        data.get(
            "relationship",
            ""
        )
    ).strip()

    contact_phone = str(
        data.get(
            "contact_phone",
            ""
        )
    ).strip()

    contact_email = str(
        data.get(
            "contact_email",
            ""
        )
    ).strip().lower()

    requested_primary = (
        value_to_boolean(
            data.get(
                "is_primary"
            ),
            False
        )
    )

    if not contact_name:

        return jsonify({
            "success": False,
            "message": (
                "Contact name is required."
            )
        }), 400

    if not relationship:

        return jsonify({
            "success": False,
            "message": (
                "Relationship is required."
            )
        }), 400

    if not contact_phone:

        return jsonify({
            "success": False,
            "message": (
                "Contact phone is required."
            )
        }), 400

    database = None
    cursor = None

    try:

        database = get_db()

        cursor = database.cursor(
            dictionary=True
        )

        user_id = session["user_id"]

        is_first_contact = (
            not user_has_contacts(
                cursor,
                user_id
            )
        )

        should_be_primary = (
            requested_primary
            or is_first_contact
        )

        if should_be_primary:

            clear_primary_contacts(
                cursor,
                user_id
            )

        cursor.execute(
            """
            INSERT INTO emergency_contacts
            (
                user_id,
                contact_name,
                relationship,
                contact_phone,
                contact_email,
                is_primary
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                user_id,
                contact_name,
                relationship,
                contact_phone,
                contact_email,
                int(
                    should_be_primary
                )
            )
        )

        contact_id = cursor.lastrowid

        ensure_primary_contact(
            cursor,
            user_id
        )

        database.commit()

        contact = select_contact(
            cursor,
            contact_id,
            user_id
        )

        return jsonify({
            "success": True,
            "message": (
                "Emergency contact "
                "added successfully."
            ),
            "contact": contact_to_json(
                contact
            )
        }), 201

    except mysql.connector.Error as error:

        if database is not None:
            database.rollback()

        return jsonify({
            "success": False,
            "message": (
                f"Database error: {error}"
            )
        }), 500

    finally:

        if cursor is not None:
            cursor.close()

        if (
            database is not None
            and database.is_connected()
        ):
            database.close()


# =========================================================
# API — UPDATE EMERGENCY CONTACT
# =========================================================

@emergency.route(
    "/api/emergency-contacts/<int:contact_id>",
    methods=[
        "PUT"
    ]
)
def api_update_emergency_contact(
    contact_id
):

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    contact_name = str(
        data.get(
            "contact_name",
            ""
        )
    ).strip()

    relationship = str(
        data.get(
            "relationship",
            ""
        )
    ).strip()

    contact_phone = str(
        data.get(
            "contact_phone",
            ""
        )
    ).strip()

    contact_email = str(
        data.get(
            "contact_email",
            ""
        )
    ).strip().lower()

    primary_value_provided = (
        "is_primary" in data
    )

    requested_primary = (
        value_to_boolean(
            data.get(
                "is_primary"
            ),
            False
        )
    )

    if not contact_name:

        return jsonify({
            "success": False,
            "message": (
                "Contact name is required."
            )
        }), 400

    if not relationship:

        return jsonify({
            "success": False,
            "message": (
                "Relationship is required."
            )
        }), 400

    if not contact_phone:

        return jsonify({
            "success": False,
            "message": (
                "Contact phone is required."
            )
        }), 400

    database = None
    cursor = None

    try:

        database = get_db()

        cursor = database.cursor(
            dictionary=True
        )

        user_id = session["user_id"]

        existing_contact = select_contact(
            cursor,
            contact_id,
            user_id
        )

        if existing_contact is None:

            return jsonify({
                "success": False,
                "message": (
                    "Emergency contact "
                    "not found."
                )
            }), 404

        if primary_value_provided:

            next_primary_value = (
                requested_primary
            )

        else:

            next_primary_value = bool(
                existing_contact.get(
                    "is_primary",
                    0
                )
            )

        if next_primary_value:

            clear_primary_contacts(
                cursor,
                user_id
            )

        cursor.execute(
            """
            UPDATE emergency_contacts
            SET
                contact_name = %s,
                relationship = %s,
                contact_phone = %s,
                contact_email = %s,
                is_primary = %s
            WHERE id = %s
              AND user_id = %s
            """,
            (
                contact_name,
                relationship,
                contact_phone,
                contact_email,
                int(
                    next_primary_value
                ),
                contact_id,
                user_id
            )
        )

        ensure_primary_contact(
            cursor,
            user_id
        )

        database.commit()

        contact = select_contact(
            cursor,
            contact_id,
            user_id
        )

        return jsonify({
            "success": True,
            "message": (
                "Emergency contact "
                "updated successfully."
            ),
            "contact": contact_to_json(
                contact
            )
        }), 200

    except mysql.connector.Error as error:

        if database is not None:
            database.rollback()

        return jsonify({
            "success": False,
            "message": (
                f"Database error: {error}"
            )
        }), 500

    finally:

        if cursor is not None:
            cursor.close()

        if (
            database is not None
            and database.is_connected()
        ):
            database.close()


# =========================================================
# API — SET PRIMARY EMERGENCY CONTACT
# =========================================================

@emergency.route(
    "/api/emergency-contacts/<int:contact_id>/primary",
    methods=[
        "PUT",
        "PATCH"
    ]
)
def api_set_primary_contact(
    contact_id
):

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    database = None
    cursor = None

    try:

        database = get_db()

        cursor = database.cursor(
            dictionary=True
        )

        user_id = session["user_id"]

        primary_updated = (
            make_contact_primary(
                cursor,
                user_id,
                contact_id
            )
        )

        if not primary_updated:

            return jsonify({
                "success": False,
                "message": (
                    "Emergency contact "
                    "not found."
                )
            }), 404

        database.commit()

        contact = select_contact(
            cursor,
            contact_id,
            user_id
        )

        return jsonify({
            "success": True,
            "message": (
                "Primary emergency contact "
                "updated successfully."
            ),
            "contact": contact_to_json(
                contact
            )
        }), 200

    except mysql.connector.Error as error:

        if database is not None:
            database.rollback()

        return jsonify({
            "success": False,
            "message": (
                f"Database error: {error}"
            )
        }), 500

    finally:

        if cursor is not None:
            cursor.close()

        if (
            database is not None
            and database.is_connected()
        ):
            database.close()


# =========================================================
# API — DELETE EMERGENCY CONTACT
# =========================================================

@emergency.route(
    "/api/emergency-contacts/<int:contact_id>",
    methods=[
        "DELETE"
    ]
)
def api_delete_emergency_contact(
    contact_id
):

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    database = None
    cursor = None

    try:

        database = get_db()

        cursor = database.cursor(
            dictionary=True
        )

        user_id = session["user_id"]

        contact = select_contact(
            cursor,
            contact_id,
            user_id
        )

        if contact is None:

            return jsonify({
                "success": False,
                "message": (
                    "Emergency contact "
                    "not found."
                )
            }), 404

        cursor.execute(
            """
            DELETE FROM emergency_contacts
            WHERE id = %s
              AND user_id = %s
            """,
            (
                contact_id,
                user_id
            )
        )

        ensure_primary_contact(
            cursor,
            user_id
        )

        database.commit()

        return jsonify({
            "success": True,
            "message": (
                "Emergency contact "
                "deleted successfully."
            )
        }), 200

    except mysql.connector.Error as error:

        if database is not None:
            database.rollback()

        return jsonify({
            "success": False,
            "message": (
                f"Database error: {error}"
            )
        }), 500

    finally:

        if cursor is not None:
            cursor.close()

        if (
            database is not None
            and database.is_connected()
        ):
            database.close()