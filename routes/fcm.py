from flask import (
    Blueprint,
    jsonify,
    request,
    session
)

from database.db import get_db_connection


fcm = Blueprint(
    "fcm",
    __name__
)


@fcm.route(
    "/api/fcm-token",
    methods=[
        "POST"
    ]
)
def register_fcm_token():

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Login required."
        }), 401

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    fcm_token = str(
        data.get(
            "fcm_token",
            ""
        )
    ).strip()

    device_name = str(
        data.get(
            "device_name",
            "Android device"
        )
    ).strip()[:255]

    if not fcm_token:

        return jsonify({
            "success": False,
            "message": "Firebase token is required."
        }), 400

    if len(fcm_token) > 512:

        return jsonify({
            "success": False,
            "message": "Firebase token is too long."
        }), 400

    user_id = session["user_id"]

    connection = None
    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            INSERT INTO fcm_tokens
            (
                user_id,
                fcm_token,
                device_name,
                is_active
            )
            VALUES
            (
                %s,
                %s,
                %s,
                1
            )
            ON DUPLICATE KEY UPDATE
                user_id = VALUES(user_id),
                device_name = VALUES(device_name),
                is_active = 1,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                user_id,
                fcm_token,
                device_name
            )
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message": (
                "Firebase token registered "
                "successfully."
            )
        }), 200

    except Exception as error:

        if connection is not None:
            connection.rollback()

        print(
            "FCM token registration error:",
            error
        )

        return jsonify({
            "success": False,
            "message": (
                "Unable to register Firebase token: "
                f"{str(error)}"
            )
        }), 500

    finally:

        if cursor is not None:
            cursor.close()

        if (
            connection is not None
            and connection.is_connected()
        ):
            connection.close()


@fcm.route(
    "/api/fcm-token",
    methods=[
        "DELETE"
    ]
)
def deactivate_fcm_token():

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Login required."
        }), 401

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    fcm_token = str(
        data.get(
            "fcm_token",
            ""
        )
    ).strip()

    if not fcm_token:

        return jsonify({
            "success": False,
            "message": "Firebase token is required."
        }), 400

    connection = None
    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE fcm_tokens
            SET is_active = 0
            WHERE user_id = %s
              AND fcm_token = %s
            """,
            (
                session["user_id"],
                fcm_token
            )
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message": (
                "Firebase token deactivated "
                "successfully."
            )
        }), 200

    except Exception as error:

        if connection is not None:
            connection.rollback()

        print(
            "FCM token deactivation error:",
            error
        )

        return jsonify({
            "success": False,
            "message": (
                "Unable to deactivate Firebase token: "
                f"{str(error)}"
            )
        }), 500

    finally:

        if cursor is not None:
            cursor.close()

        if (
            connection is not None
            and connection.is_connected()
        ):
            connection.close()