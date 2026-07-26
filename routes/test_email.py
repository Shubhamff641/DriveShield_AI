from flask import (
    Blueprint,
    jsonify,
    session
)

from database.db import get_db_connection
from utils.email_sender import send_accident_email


test_email = Blueprint(
    "test_email",
    __name__
)


@test_email.route(
    "/test-email",
    methods=["GET"]
)
def send_test_email():
    """
    Test the Brevo accident-email integration and return
    the exact result as JSON instead of redirecting.
    """

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": (
                "Please log in to the DriveShield AI "
                "website in this browser first."
            )
        }), 401

    connection = None
    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT
                contact_name,
                contact_email
            FROM emergency_contacts
            WHERE user_id = %s
              AND contact_email IS NOT NULL
              AND TRIM(contact_email) != ''
            ORDER BY id ASC
            LIMIT 1
            """,
            (
                session["user_id"],
            )
        )

        contact = cursor.fetchone()

        if not contact:

            return jsonify({
                "success": False,
                "message": (
                    "No emergency contact with an email "
                    "address was found for this account."
                )
            }), 400

        receiver_email = str(
            contact.get("contact_email")
            or ""
        ).strip()

        contact_name = str(
            contact.get("contact_name")
            or "Emergency Contact"
        ).strip()

        print(
            "Brevo test started for:",
            receiver_email
        )

        email_sent = send_accident_email(
            receiver_email=receiver_email,
            driver_name=session.get(
                "user_name",
                "DriveShield AI User"
            ),
            latitude=19.0760,
            longitude=72.8777,
            hospital_name="DriveShield AI Test Hospital",
            severity="TEST",
            impact_force=0.0,
            description=(
                "This is a Brevo emergency-email "
                "integration test."
            ),
            contact_name=contact_name
        )

        if email_sent:

            return jsonify({
                "success": True,
                "message": (
                    "Brevo accepted the test email. "
                    "Check the recipient inbox, spam, "
                    "and Brevo transactional logs."
                ),
                "recipient": receiver_email
            }), 200

        return jsonify({
            "success": False,
            "message": (
                "Brevo email sending failed. "
                "Open Render logs and search for "
                "'Brevo failed' to see the exact error."
            ),
            "recipient": receiver_email
        }), 500

    except Exception as error:

        print(
            "Brevo test route error:",
            repr(error)
        )

        return jsonify({
            "success": False,
            "message": (
                "The test route failed before the email "
                "could be sent."
            ),
            "error": str(error)
        }), 500

    finally:

        if cursor is not None:
            cursor.close()

        if (
            connection is not None
            and connection.is_connected()
        ):
            connection.close()