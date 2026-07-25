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

from database.db import get_db_connection
from models.accident import Accident
from routes.hospital import find_nearest_hospital
from utils.email_sender import send_accident_email


accident = Blueprint(
    "accident",
    __name__
)


# =========================================================
# VIEW ACCIDENT HISTORY
# =========================================================

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


# =========================================================
# ADD ACCIDENT FROM WEB FORM
# =========================================================

@accident.route(
    "/add_accident",
    methods=["POST"]
)
def add_accident():

    if "user_id" not in session:

        return redirect(
            url_for("auth.login")
        )

    latitude = (
        request.form
        .get("latitude", "")
        .strip()
    )

    longitude = (
        request.form
        .get("longitude", "")
        .strip()
    )

    severity = (
        request.form
        .get("severity", "UNKNOWN")
        .strip()
        .upper()
    )

    hospital_id = request.form.get(
        "hospital_id"
    )

    description = (
        request.form
        .get("description", "")
        .strip()
    )

    if not latitude or not longitude:

        flash(
            "Latitude and longitude are required.",
            "danger"
        )

        return redirect(
            url_for(
                "accident.accident_history"
            )
        )

    try:
        latitude = float(latitude)
        longitude = float(longitude)

    except (TypeError, ValueError):

        flash(
            "Invalid GPS coordinates.",
            "danger"
        )

        return redirect(
            url_for(
                "accident.accident_history"
            )
        )

    Accident.create_accident(
        session["user_id"],
        latitude,
        longitude,
        severity,
        hospital_id,
        False,
        "DETECTED",
        description
    )

    flash(
        "Accident saved successfully.",
        "success"
    )

    return redirect(
        url_for(
            "accident.accident_history"
        )
    )


# =========================================================
# VIEW SINGLE ACCIDENT
# =========================================================

@accident.route(
    "/accident/<int:accident_id>"
)
def accident_details(accident_id):

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


# =========================================================
# DELETE ACCIDENT
# =========================================================

@accident.route(
    "/delete_accident/<int:accident_id>",
    methods=["GET", "POST"]
)
def delete_accident(accident_id):

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


# =========================================================
# ANDROID API — AUTOMATIC ACCIDENT WORKFLOW
# =========================================================

@accident.route(
    "/api/accident-detected",
    methods=["POST"]
)
def api_accident_detected():

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Login required."
        }), 401

    data = request.get_json(
        silent=True
    ) or {}

    latitude = data.get(
        "latitude"
    )

    longitude = data.get(
        "longitude"
    )

    severity = (
        str(
            data.get(
                "severity",
                "HIGH"
            )
        )
        .strip()
        .upper()
    )

    client_hospital_name = (
        str(
            data.get(
                "hospital_name",
                ""
            )
        )
        .strip()
    )

    hospital_id = data.get(
        "hospital_id"
    )

    description = (
        str(
            data.get(
                "description",
                "Accident detected automatically."
            )
        )
        .strip()
    )

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
        latitude = float(latitude)
        longitude = float(longitude)

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

    # -----------------------------------------------------
    # AUTOMATICALLY FIND THE NEAREST HOSPITAL
    # -----------------------------------------------------

    nearest_hospital = None
    hospital_lookup_message = ""

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

        hospital_name = (
            client_hospital_name
        )

        hospital_lookup_message = (
            "Hospital supplied by the client."
        )

    else:

        try:
            nearest_hospital = (
                find_nearest_hospital(
                    latitude=latitude,
                    longitude=longitude,
                    radius=15000,
                    request_timeout=20
                )
            )

            if nearest_hospital is None:

                hospital_name = (
                    "No hospital found within 15 km"
                )

                hospital_lookup_message = (
                    "No hospital was found inside "
                    "the 15 km search radius."
                )

            else:

                hospital_name = (
                    nearest_hospital["name"]
                )

                distance = (
                    nearest_hospital.get(
                        "distance"
                    )
                )

                address = (
                    nearest_hospital.get(
                        "address"
                    )
                    or "Address not available"
                )

                display_parts = [
                    hospital_name
                ]

                if distance is not None:

                    display_parts.append(
                        f"{distance:.2f} km away"
                    )

                if (
                    address
                    != "Address not available"
                ):

                    display_parts.append(
                        address
                    )

                hospital_name = " - ".join(
                    display_parts
                )

                hospital_lookup_message = (
                    "Nearest hospital found "
                    "automatically."
                )

        except Exception as hospital_error:

            print(
                "Nearest hospital lookup error:",
                hospital_error
            )

            hospital_name = (
                "Nearest hospital lookup unavailable"
            )

            hospital_lookup_message = (
                "Hospital lookup service was "
                "temporarily unavailable."
            )

    connection = None
    cursor = None

    contacts = []
    email_results = []

    emails_attempted = 0
    emails_sent = 0
    accident_saved = False

    try:
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
            ORDER BY id ASC
            """,
            (user_id,)
        )

        contacts = cursor.fetchall()

        for contact in contacts:

            contact_email = (
                contact.get(
                    "contact_email"
                ) or ""
            ).strip()

            if not contact_email:
                continue

            emails_attempted += 1

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

            except Exception as email_error:

                print(
                    "Emergency email error for "
                    f"{contact_email}:",
                    email_error
                )

                sent = False

            if sent:
                emails_sent += 1

            email_results.append({
                "contact_id":
                    contact.get("id"),

                "contact_name":
                    contact.get(
                        "contact_name"
                    )
                    or "Emergency Contact",

                "contact_email":
                    contact_email,

                "sent":
                    bool(sent)
            })

        alert_status = (
            "ALERT_SENT"
            if emails_sent > 0
            else "DETECTED"
        )

        Accident.create_accident(
            user_id,
            latitude,
            longitude,
            severity,
            hospital_id,
            emails_sent > 0,
            alert_status,
            description
        )

        accident_saved = True

        if emails_attempted == 0:

            response_message = (
                "Accident saved, but no emergency "
                "contact has an email address."
            )

        elif emails_sent == emails_attempted:

            response_message = (
                f"Accident saved and emergency alert "
                f"sent to {emails_sent} contact"
                f"{'' if emails_sent == 1 else 's'}."
            )

        elif emails_sent > 0:

            failed_count = (
                emails_attempted -
                emails_sent
            )

            response_message = (
                f"Accident saved. Alert sent to "
                f"{emails_sent} contact"
                f"{'' if emails_sent == 1 else 's'}, "
                f"but failed for {failed_count}."
            )

        else:

            response_message = (
                "Accident saved, but emergency emails "
                "could not be sent."
            )

        return jsonify({
            "success": True,
            "message": response_message,
            "accident_saved": accident_saved,
            "email_sent": emails_sent > 0,
            "emails_attempted": emails_attempted,
            "emails_sent": emails_sent,
            "contacts_found": len(contacts),
            "hospital_name": hospital_name,
            "hospital_lookup_message":
                hospital_lookup_message,
            "nearest_hospital":
                nearest_hospital,
            "severity": severity,
            "latitude": latitude,
            "longitude": longitude,
            "maps_url": (
                "https://www.google.com/maps/search/"
                f"?api=1&query="
                f"{latitude},{longitude}"
            ),
            "email_results": email_results
        }), 200

    except Exception as error:

        print(
            "Automatic accident workflow error:",
            error
        )

        return jsonify({
            "success": False,
            "message": (
                "Accident workflow failed: "
                f"{str(error)}"
            ),
            "accident_saved": accident_saved,
            "email_sent": emails_sent > 0,
            "emails_attempted": emails_attempted,
            "emails_sent": emails_sent,
            "hospital_name": hospital_name,
            "nearest_hospital":
                nearest_hospital
        }), 500

    finally:

        if cursor is not None:
            cursor.close()

        if (
            connection is not None
            and connection.is_connected()
        ):
            connection.close()