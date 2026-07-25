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

from database.db import get_db_connection


settings = Blueprint(
    "settings",
    __name__
)


def create_settings_table(
    connection
):

    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INT PRIMARY KEY,
            email_alerts_enabled TINYINT(1) NOT NULL DEFAULT 1,
            drowsiness_alarm_enabled TINYINT(1) NOT NULL DEFAULT 1,
            location_sharing_enabled TINYINT(1) NOT NULL DEFAULT 1,
            accident_alert_delay INT NOT NULL DEFAULT 20,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP
        )
        """
    )

    cursor.close()
    connection.commit()


def create_default_settings(
    connection,
    user_id
):

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO user_settings (
            user_id
        )
        VALUES (%s)
        ON DUPLICATE KEY UPDATE
            user_id = VALUES(user_id)
        """,
        (user_id,)
    )

    cursor.close()
    connection.commit()


def get_user_and_settings(
    connection,
    user_id
):

    cursor = connection.cursor(
        dictionary=True
    )

    cursor.execute(
        """
        SELECT
            id,
            full_name,
            email,
            phone,
            password,
            profile_image
        FROM users
        WHERE id = %s
        LIMIT 1
        """,
        (user_id,)
    )

    user = cursor.fetchone()

    cursor.execute(
        """
        SELECT
            user_id,
            email_alerts_enabled,
            drowsiness_alarm_enabled,
            location_sharing_enabled,
            accident_alert_delay,
            created_at,
            updated_at
        FROM user_settings
        WHERE user_id = %s
        LIMIT 1
        """,
        (user_id,)
    )

    user_preferences = cursor.fetchone()

    cursor.close()

    return user, user_preferences


def settings_to_json(
    user,
    user_preferences
):

    return {
        "user": {
            "id": user["id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "phone": user["phone"],
            "profile_image": (
                user.get("profile_image")
                or "default.png"
            )
        },
        "preferences": {
            "email_alerts_enabled": bool(
                user_preferences[
                    "email_alerts_enabled"
                ]
            ),
            "drowsiness_alarm_enabled": bool(
                user_preferences[
                    "drowsiness_alarm_enabled"
                ]
            ),
            "location_sharing_enabled": bool(
                user_preferences[
                    "location_sharing_enabled"
                ]
            ),
            "accident_alert_delay": int(
                user_preferences[
                    "accident_alert_delay"
                ]
            )
        }
    }


@settings.route(
    "/settings",
    methods=["GET", "POST"]
)
def settings_page():

    if "user_id" not in session:

        return redirect(
            url_for("auth.login")
        )

    connection = None
    cursor = None
    user_id = session["user_id"]

    try:

        connection = get_db_connection()

        create_settings_table(
            connection
        )

        create_default_settings(
            connection,
            user_id
        )

        if request.method == "POST":

            action = request.form.get(
                "action",
                ""
            ).strip()

            cursor = connection.cursor(
                dictionary=True
            )

            if action == "update_account":

                full_name = request.form.get(
                    "full_name",
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

                if (
                    not full_name
                    or not email
                    or not phone
                ):

                    flash(
                        "Full name, email and phone are required.",
                        "danger"
                    )

                    return redirect(
                        url_for(
                            "settings.settings_page"
                        )
                    )

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

                existing_user = cursor.fetchone()

                if existing_user:

                    flash(
                        "This email is already used by another account.",
                        "danger"
                    )

                    return redirect(
                        url_for(
                            "settings.settings_page"
                        )
                    )

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
                        full_name,
                        email,
                        phone,
                        user_id
                    )
                )

                connection.commit()

                session["user_name"] = full_name
                session["user_email"] = email

                flash(
                    "Account details updated successfully.",
                    "success"
                )

            elif action == "update_preferences":

                email_alerts_enabled = (
                    1
                    if request.form.get(
                        "email_alerts_enabled"
                    ) == "on"
                    else 0
                )

                drowsiness_alarm_enabled = (
                    1
                    if request.form.get(
                        "drowsiness_alarm_enabled"
                    ) == "on"
                    else 0
                )

                location_sharing_enabled = (
                    1
                    if request.form.get(
                        "location_sharing_enabled"
                    ) == "on"
                    else 0
                )

                try:

                    accident_alert_delay = int(
                        request.form.get(
                            "accident_alert_delay",
                            "20"
                        )
                    )

                except ValueError:

                    accident_alert_delay = 20

                if accident_alert_delay not in {
                    10,
                    20,
                    30,
                    45,
                    60
                }:

                    flash(
                        "Please select a valid alert delay.",
                        "danger"
                    )

                    return redirect(
                        url_for(
                            "settings.settings_page"
                        )
                    )

                cursor.execute(
                    """
                    UPDATE user_settings
                    SET
                        email_alerts_enabled = %s,
                        drowsiness_alarm_enabled = %s,
                        location_sharing_enabled = %s,
                        accident_alert_delay = %s
                    WHERE user_id = %s
                    """,
                    (
                        email_alerts_enabled,
                        drowsiness_alarm_enabled,
                        location_sharing_enabled,
                        accident_alert_delay,
                        user_id
                    )
                )

                connection.commit()

                flash(
                    "Safety preferences saved successfully.",
                    "success"
                )

            elif action == "change_password":

                current_password = request.form.get(
                    "current_password",
                    ""
                )

                new_password = request.form.get(
                    "new_password",
                    ""
                )

                confirm_password = request.form.get(
                    "confirm_password",
                    ""
                )

                cursor.execute(
                    """
                    SELECT password
                    FROM users
                    WHERE id = %s
                    LIMIT 1
                    """,
                    (user_id,)
                )

                password_record = cursor.fetchone()

                if (
                    not password_record
                    or password_record["password"]
                    != current_password
                ):

                    flash(
                        "Current password is incorrect.",
                        "danger"
                    )

                    return redirect(
                        url_for(
                            "settings.settings_page"
                        )
                    )

                if len(new_password) < 6:

                    flash(
                        "New password must contain at least 6 characters.",
                        "danger"
                    )

                    return redirect(
                        url_for(
                            "settings.settings_page"
                        )
                    )

                if new_password != confirm_password:

                    flash(
                        "New password and confirmation do not match.",
                        "danger"
                    )

                    return redirect(
                        url_for(
                            "settings.settings_page"
                        )
                    )

                if new_password == current_password:

                    flash(
                        "New password must be different from the current password.",
                        "danger"
                    )

                    return redirect(
                        url_for(
                            "settings.settings_page"
                        )
                    )

                cursor.execute(
                    """
                    UPDATE users
                    SET password = %s
                    WHERE id = %s
                    """,
                    (
                        new_password,
                        user_id
                    )
                )

                connection.commit()

                flash(
                    "Password changed successfully.",
                    "success"
                )

            else:

                flash(
                    "Invalid settings request.",
                    "danger"
                )

            return redirect(
                url_for(
                    "settings.settings_page"
                )
            )

        user, user_preferences = (
            get_user_and_settings(
                connection,
                user_id
            )
        )

        if not user:

            session.clear()

            flash(
                "User account was not found.",
                "danger"
            )

            return redirect(
                url_for("auth.login")
            )

        return render_template(
            "settings.html",
            user=user,
            preferences=user_preferences
        )

    except mysql.connector.Error as error:

        if connection is not None:
            connection.rollback()

        print(
            "Settings database error:",
            error
        )

        flash(
            "A database error occurred while loading settings.",
            "danger"
        )

        return redirect(
            url_for(
                "dashboard.dashboard_page"
            )
        )

    except Exception as error:

        if connection is not None:
            connection.rollback()

        print(
            "Settings error:",
            error
        )

        flash(
            "An unexpected error occurred while processing settings.",
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
            connection is not None
            and connection.is_connected()
        ):
            connection.close()


@settings.route(
    "/api/settings",
    methods=["GET", "PUT"]
)
def api_settings():

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    connection = None
    cursor = None
    user_id = session["user_id"]

    try:

        connection = get_db_connection()

        create_settings_table(
            connection
        )

        create_default_settings(
            connection,
            user_id
        )

        if request.method == "PUT":

            data = request.get_json(
                silent=True
            ) or {}

            cursor = connection.cursor()

            email_alerts_enabled = (
                1
                if data.get(
                    "email_alerts_enabled",
                    True
                )
                else 0
            )

            drowsiness_alarm_enabled = (
                1
                if data.get(
                    "drowsiness_alarm_enabled",
                    True
                )
                else 0
            )

            location_sharing_enabled = (
                1
                if data.get(
                    "location_sharing_enabled",
                    True
                )
                else 0
            )

            try:

                accident_alert_delay = int(
                    data.get(
                        "accident_alert_delay",
                        20
                    )
                )

            except (
                TypeError,
                ValueError
            ):

                return jsonify({
                    "success": False,
                    "message": "Invalid alert delay."
                }), 400

            if accident_alert_delay not in {
                10,
                20,
                30,
                45,
                60
            }:

                return jsonify({
                    "success": False,
                    "message": "Invalid alert delay."
                }), 400

            cursor.execute(
                """
                UPDATE user_settings
                SET
                    email_alerts_enabled = %s,
                    drowsiness_alarm_enabled = %s,
                    location_sharing_enabled = %s,
                    accident_alert_delay = %s
                WHERE user_id = %s
                """,
                (
                    email_alerts_enabled,
                    drowsiness_alarm_enabled,
                    location_sharing_enabled,
                    accident_alert_delay,
                    user_id
                )
            )

            connection.commit()

        user, user_preferences = (
            get_user_and_settings(
                connection,
                user_id
            )
        )

        if not user:

            return jsonify({
                "success": False,
                "message": "User account was not found."
            }), 404

        response_data = settings_to_json(
            user,
            user_preferences
        )

        return jsonify({
            "success": True,
            "message": "Settings loaded successfully.",
            **response_data
        }), 200

    except mysql.connector.Error as error:

        if connection is not None:
            connection.rollback()

        print(
            "Settings API database error:",
            error
        )

        return jsonify({
            "success": False,
            "message": "A database error occurred."
        }), 500

    except Exception as error:

        if connection is not None:
            connection.rollback()

        print(
            "Settings API error:",
            error
        )

        return jsonify({
            "success": False,
            "message": "An unexpected error occurred."
        }), 500

    finally:

        if cursor is not None:
            cursor.close()

        if (
            connection is not None
            and connection.is_connected()
        ):
            connection.close()