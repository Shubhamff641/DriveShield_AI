from flask import current_app
from flask_mail import Message

from app import mail


def send_accident_email(
    recipient,
    driver_name,
    latitude,
    longitude,
    severity,
    hospital_name=None
):
    """
    Send an emergency accident email.

    Returns True when sent successfully,
    otherwise returns False.
    """

    maps_url = (
        "https://www.google.com/maps/search/"
        "?api=1&query="
        f"{latitude},{longitude}"
    )

    hospital_text = (
        hospital_name
        if hospital_name
        else "Not available"
    )

    subject = (
        "Emergency Alert - "
        "DriveShield AI Accident Detected"
    )

    body = f"""
Emergency Accident Alert

Driver: {driver_name}
Severity: {severity}

Latitude: {latitude}
Longitude: {longitude}

Nearest Hospital:
{hospital_text}

Google Maps Location:
{maps_url}

This message was generated automatically
by DriveShield AI.
"""

    try:
        message = Message(
            subject=subject,
            recipients=[recipient],
            body=body
        )

        mail.send(message)

        return True

    except Exception as error:
        current_app.logger.error(
            "Emergency email failed: %s",
            error
        )

        return False