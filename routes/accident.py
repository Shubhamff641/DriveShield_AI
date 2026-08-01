import threading
import uuid

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for
)

from database.db import get_db_connection
from models.accident import Accident
from routes.hospital import find_nearest_hospital
from utils.email_sender import send_accident_email
from utils.firebase_sender import send_accident_push_notifications


accident = Blueprint(
    "accident",
    __name__
)


@accident.route("/accidents")
def accident_history():

    if "user_id" not in session:

        return redirect(
            url_for("auth.login")
        )

    accidents = Accident.get_accidents(
        session["user_id"]
    )

    return render_template(
        "accident_history.html",
        accidents=accidents
    )


@accident.route(
    "/accident/<int:accident_id>"
)
def accident_details(
    accident_id
):

    if "user_id" not in session:

        return redirect(
            url_for("auth.login")
        )

    accident_data = Accident.get_accident(
        accident_id
    )

    if accident_data is None:

        flash(
            "Accident record not found.",
            "danger"
        )

        return redirect(
            url_for(
                "accident.accident_history"
            )
        )

    return render_template(
        "accident_details.html",
        accident=accident_data
    )


@accident.route(
    "/delete_accident/<int:accident_id>",
    methods=[
        "GET",
        "POST"
    ]
)
def delete_accident(
    accident_id
):

    if "user_id" not in session:

        return redirect(
            url_for("auth.login")
        )

    Accident.delete_accident(
        accident_id
    )

    flash(
        "Accident deleted successfully.",
        "success"
    )

    return redirect(
        url_for(
            "accident.accident_history"
        )
    )


def _find_hospital_name(
    latitude,
    longitude,
    client_hospital_name
):

    default_hospital_values = {
        "",
        "nearest hospital not available",
        "not available",
        "unknown"
    }

    if (
        client_hospital_name.lower()
        not in default_hospital_values
    ):

        return (
            client_hospital_name,
            None
        )

    try:

        nearest_hospital = (
            find_nearest_hospital(
                latitude=latitude,
                longitude=longitude,
                radius=15000,
                request_timeout=5
            )
        )

        if nearest_hospital is None:

            return (
                "No hospital found within 15 km",
                None
            )

        hospital_name = str(
            nearest_hospital.get(
                "name"
            )
            or "Nearest hospital"
        ).strip()

        distance = nearest_hospital.get(
            "distance"
        )

        address = str(
            nearest_hospital.get(
                "address"
            )
            or ""
        ).strip()

        display_parts = [
            hospital_name
        ]

        if distance is not None:

            try:

                display_parts.append(
                    f"{float(distance):.2f} km away"
                )

            except (TypeError, ValueError):

                pass

        if address:

            display_parts.append(
                address
            )

        return (
            " - ".join(
                display_parts
            ),
            nearest_hospital
        )

    except Exception as error:

        print(
            "Nearest hospital lookup error:",
            error,
            flush=True
        )

        return (
            "Nearest hospital lookup unavailable",
            None
        )


def _process_accident_workflow(
    flask_app,
    job_id,
    user_id,
    driver_name,
    latitude,
    longitude,
    severity,
    hospital_id,
    client_hospital_name,
    description,
    impact_force
):

    with flask_app.app_context():

        connection = None
        cursor = None

        try:

            hospital_name, nearest_hospital = (
                _find_hospital_name(
                    latitude=latitude,
                    longitude=longitude,
                    client_hospital_name=
                        client_hospital_name
                )
            )

            connection = get_db_connection()

            cursor = connection.cursor(
                dictionary=True
            )

            cursor.execute(
                """
                SELECT
                    id,
                    contact_name,
                    relationship,
                    contact_phone,
                    contact_email
                FROM emergency_contacts
                WHERE user_id = %s
                ORDER BY
                    is_primary DESC,
                    id ASC
                """,
                (
                    user_id,
                )
            )

            contacts = cursor.fetchall()

            emails_sent = 0

            for contact in contacts:

                contact_email = str(
                    contact.get(
                        "contact_email"
                    )
                    or ""
                ).strip()

                if not contact_email:
                    continue

                try:

                    sent = send_accident_email(
                        receiver_email=
                            contact_email,

                        driver_name=
                            driver_name,

                        latitude=
                            latitude,

                        longitude=
                            longitude,

                        hospital_name=
                            hospital_name,

                        severity=
                            severity,

                        impact_force=
                            impact_force,

                        description=
                            description,

                        contact_name=
                            contact.get(
                                "contact_name",
                                "Emergency Contact"
                            )
                    )

                    if sent:
                        emails_sent += 1

                except Exception as error:

                    print(
                        "Emergency email error:",
                        error,
                        flush=True
                    )

            push_result = (
                send_accident_push_notifications(
                    connection=connection,
                    contacts=contacts,
                    driver_user_id=user_id,
                    driver_name=driver_name,
                    latitude=latitude,
                    longitude=longitude,
                    severity=severity,
                    hospital_name=hospital_name
                )
            )

            notifications_sent = int(
                push_result.get(
                    "notifications_sent",
                    0
                )
                or 0
            )

            alert_delivered = (
                emails_sent > 0
                or notifications_sent > 0
            )

            Accident.create_accident(
                user_id,
                latitude,
                longitude,
                severity,
                hospital_id,
                alert_delivered,
                (
                    "ALERT_SENT"
                    if alert_delivered
                    else "DETECTED"
                ),
                description
            )

            print(
                (
                    f"Accident job {job_id} completed: "
                    f"emails={emails_sent}, "
                    f"push={notifications_sent}, "
                    f"hospital={hospital_name}, "
                    f"nearest={nearest_hospital is not None}"
                ),
                flush=True
            )

        except Exception as error:

            print(
                (
                    f"Accident job {job_id} failed: "
                    f"{error}"
                ),
                flush=True
            )

            try:

                Accident.create_accident(
                    user_id,
                    latitude,
                    longitude,
                    severity,
                    hospital_id,
                    False,
                    "DETECTED",
                    (
                        f"{description} "
                        "Emergency processing error: "
                        f"{str(error)[:300]}"
                    )
                )

            except Exception as save_error:

                print(
                    (
                        f"Accident job {job_id} "
                        f"fallback save failed: "
                        f"{save_error}"
                    ),
                    flush=True
                )

        finally:

            if cursor is not None:
                cursor.close()

            if (
                connection is not None
                and connection.is_connected()
            ):

                connection.close()


@accident.route(
    "/api/accident-detected",
    methods=[
        "POST"
    ]
)
def api_accident_detected():

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

    latitude = data.get(
        "latitude"
    )

    longitude = data.get(
        "longitude"
    )

    severity = str(
        data.get(
            "severity",
            "HIGH"
        )
    ).strip().upper()

    client_hospital_name = str(
        data.get(
            "hospital_name",
            ""
        )
    ).strip()

    hospital_id = data.get(
        "hospital_id"
    )

    description = str(
        data.get(
            "description",
            "Accident detected automatically."
        )
    ).strip()

    impact_force = data.get(
        "impact_force"
    )

    if (
        latitude is None
        or longitude is None
    ):

        return jsonify({
            "success": False,
            "message": (
                "Latitude and longitude "
                "are required."
            )
        }), 400

    try:

        latitude = float(
            latitude
        )

        longitude = float(
            longitude
        )

    except (TypeError, ValueError):

        return jsonify({
            "success": False,
            "message": (
                "Invalid GPS coordinates."
            )
        }), 400

    if not (
        -90.0 <= latitude <= 90.0
        and -180.0 <= longitude <= 180.0
    ):

        return jsonify({
            "success": False,
            "message": (
                "GPS coordinates are outside "
                "the valid range."
            )
        }), 400

    if not severity:
        severity = "HIGH"

    if not description:

        description = (
            "Accident detected automatically."
        )

    if impact_force is not None:

        try:

            impact_force = float(
                impact_force
            )

            if (
                "impact force"
                not in description.lower()
            ):

                description = (
                    f"{description} "
                    f"Impact force: "
                    f"{impact_force:.2f} G."
                )

        except (TypeError, ValueError):

            impact_force = None

    user_id = session["user_id"]

    driver_name = session.get(
        "user_name",
        "DriveShield AI User"
    )

    job_id = uuid.uuid4().hex

    flask_app = (
        current_app
        ._get_current_object()
    )

    worker = threading.Thread(
        target=
            _process_accident_workflow,

        kwargs={
            "flask_app":
                flask_app,

            "job_id":
                job_id,

            "user_id":
                user_id,

            "driver_name":
                driver_name,

            "latitude":
                latitude,

            "longitude":
                longitude,

            "severity":
                severity,

            "hospital_id":
                hospital_id,

            "client_hospital_name":
                client_hospital_name,

            "description":
                description,

            "impact_force":
                impact_force
        },

        daemon=True,

        name=(
            f"accident-alert-"
            f"{job_id[:8]}"
        )
    )

    worker.start()

    return jsonify({
        "success": True,
        "message": (
            "Emergency workflow accepted. "
            "Email and Firebase alerts are "
            "processing in the background."
        ),
        "processing": True,
        "job_id": job_id,
        "accident_saved": False,
        "email_sent": False,
        "latitude": latitude,
        "longitude": longitude,
        "severity": severity
    }), 202