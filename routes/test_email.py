from flask import Blueprint, session, redirect, url_for, flash
from database.db import get_db_connection
from utils.email_sender import send_accident_email

test_email = Blueprint("test_email", __name__)


@test_email.route("/test-email")
def send_test_email():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT contact_email
            FROM emergency_contacts
            WHERE user_id = %s
              AND contact_email IS NOT NULL
              AND contact_email != ''
            LIMIT 1
            """,
            (session["user_id"],)
        )

        contact = cursor.fetchone()

        if not contact:
            flash(
                "Add an email address to an emergency contact first.",
                "warning"
            )
            return redirect(
                url_for("dashboard.dashboard_page")
            )

        email_sent = send_accident_email(
            receiver_email=contact["contact_email"],
            driver_name=session.get(
                "user_name",
                "DriveShield AI User"
            ),
            latitude=19.0760,
            longitude=72.8777,
            hospital_name="Test Hospital",
            severity="TEST"
        )

        if email_sent:
            flash(
                "Test emergency email sent successfully.",
                "success"
            )
        else:
            flash(
                "Email sending failed. Check the Flask terminal.",
                "danger"
            )

    except Exception as error:
        print("Test email error:", error)

        flash(
            "An error occurred while testing the email.",
            "danger"
        )

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()

    return redirect(
        url_for("dashboard.dashboard_page")
    )