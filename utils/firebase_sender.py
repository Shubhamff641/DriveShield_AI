import base64
import json
import threading

import firebase_admin
from firebase_admin import (
    credentials,
    messaging
)
from flask import current_app


_firebase_initialization_lock = threading.Lock()


def _load_service_account():

    raw_json = str(
        current_app.config.get(
            "FIREBASE_SERVICE_ACCOUNT_JSON",
            ""
        )
        or ""
    ).strip()

    base64_json = str(
        current_app.config.get(
            "FIREBASE_SERVICE_ACCOUNT_BASE64",
            ""
        )
        or ""
    ).strip()

    if raw_json:

        try:

            return json.loads(
                raw_json
            )

        except json.JSONDecodeError as error:

            raise RuntimeError(
                "FIREBASE_SERVICE_ACCOUNT_JSON "
                "contains invalid JSON."
            ) from error

    if base64_json:

        try:

            decoded_json = (
                base64.b64decode(
                    base64_json
                )
                .decode(
                    "utf-8"
                )
            )

            return json.loads(
                decoded_json
            )

        except Exception as error:

            raise RuntimeError(
                "FIREBASE_SERVICE_ACCOUNT_BASE64 "
                "is invalid."
            ) from error

    return None


def initialize_firebase():

    try:

        return firebase_admin.get_app()

    except ValueError:

        pass

    with _firebase_initialization_lock:

        try:

            return firebase_admin.get_app()

        except ValueError:

            service_account = (
                _load_service_account()
            )

            if service_account is None:

                raise RuntimeError(
                    "Firebase service-account "
                    "credentials are not configured."
                )

            firebase_credential = (
                credentials.Certificate(
                    service_account
                )
            )

            return firebase_admin.initialize_app(
                firebase_credential
            )


def normalize_phone(
    phone_number
):

    digits = "".join(
        character
        for character in str(
            phone_number
            or ""
        )
        if character.isdigit()
    )

    if len(digits) > 10:
        return digits[-10:]

    return digits


def find_registered_contact_user(
    cursor,
    contact_email,
    contact_phone,
    driver_user_id
):

    email = str(
        contact_email
        or ""
    ).strip().lower()

    phone = normalize_phone(
        contact_phone
    )

    conditions = []
    parameters = []

    if email:

        conditions.append(
            "LOWER(email) = %s"
        )

        parameters.append(
            email
        )

    if phone:

        conditions.append(
            """
            RIGHT(
                REPLACE(
                    REPLACE(
                        REPLACE(
                            REPLACE(
                                REPLACE(
                                    phone,
                                    ' ',
                                    ''
                                ),
                                '-',
                                ''
                            ),
                            '+',
                            ''
                        ),
                        '(',
                        ''
                    ),
                    ')',
                    ''
                ),
                10
            ) = %s
            """
        )

        parameters.append(
            phone[-10:]
        )

    if not conditions:
        return None

    parameters.append(
        driver_user_id
    )

    cursor.execute(
        f"""
        SELECT
            id,
            full_name,
            email,
            phone
        FROM users
        WHERE
            (
                {' OR '.join(conditions)}
            )
          AND id <> %s
        ORDER BY id ASC
        LIMIT 1
        """,
        tuple(parameters)
    )

    return cursor.fetchone()


def deactivate_invalid_tokens(
    cursor,
    invalid_tokens
):

    if not invalid_tokens:
        return

    placeholders = ", ".join(
        ["%s"] * len(
            invalid_tokens
        )
    )

    cursor.execute(
        f"""
        UPDATE fcm_tokens
        SET is_active = 0
        WHERE fcm_token IN (
            {placeholders}
        )
        """,
        tuple(
            invalid_tokens
        )
    )


def send_accident_push_notifications(
    connection,
    contacts,
    driver_user_id,
    driver_name,
    latitude,
    longitude,
    severity,
    hospital_name
):

    result = {
        "configured": False,
        "matched_contacts": 0,
        "tokens_found": 0,
        "notifications_sent": 0,
        "notifications_failed": 0,
        "invalid_tokens": []
    }

    try:

        initialize_firebase()

        result["configured"] = True

    except Exception as error:

        print(
            "Firebase initialization error:",
            error
        )

        result["error"] = str(
            error
        )

        return result

    cursor = connection.cursor(
        dictionary=True
    )

    try:

        tokens = []
        token_contacts = {}

        for contact in contacts:

            registered_user = (
                find_registered_contact_user(
                    cursor=cursor,
                    contact_email=contact.get(
                        "contact_email"
                    ),
                    contact_phone=contact.get(
                        "contact_phone"
                    ),
                    driver_user_id=driver_user_id
                )
            )

            if registered_user is None:
                continue

            result["matched_contacts"] += 1

            cursor.execute(
                """
                SELECT
                    fcm_token
                FROM fcm_tokens
                WHERE user_id = %s
                  AND is_active = 1
                ORDER BY updated_at DESC
                """,
                (
                    registered_user["id"],
                )
            )

            token_rows = cursor.fetchall()

            for token_row in token_rows:

                token = str(
                    token_row.get(
                        "fcm_token"
                    )
                    or ""
                ).strip()

                if (
                    token
                    and token not in tokens
                ):

                    tokens.append(
                        token
                    )

                    token_contacts[token] = (
                        contact.get(
                            "contact_name"
                        )
                        or "Emergency Contact"
                    )

        result["tokens_found"] = len(
            tokens
        )

        if not tokens:
            return result

        maps_url = (
            "https://www.google.com/maps/search/"
            f"?api=1&query={latitude},{longitude}"
        )

        title = (
            f"🚨 {severity.title()} Accident Alert"
        )

        body = (
            f"{driver_name} may have been in an accident. "
            f"Nearest hospital: {hospital_name}. "
            "Open the alert for location details."
        )

        messages = []

        for token in tokens:

            messages.append(
                messaging.Message(
                    notification=(
                        messaging.Notification(
                            title=title,
                            body=body
                        )
                    ),
                    data={
                        "type": "accident_alert",
                        "driver_name": str(
                            driver_name
                        ),
                        "severity": str(
                            severity
                        ),
                        "latitude": str(
                            latitude
                        ),
                        "longitude": str(
                            longitude
                        ),
                        "maps_url": maps_url,
                        "hospital_name": str(
                            hospital_name
                        ),
                        "contact_name": str(
                            token_contacts.get(
                                token,
                                "Emergency Contact"
                            )
                        )
                    },
                    android=(
                        messaging.AndroidConfig(
                            priority="high",
                            notification=(
                                messaging.AndroidNotification(
                                    channel_id=(
                                        "drive_shield_"
                                        "firebase_emergency"
                                    ),
                                    sound="default",
                                    priority="max",
                                    default_vibrate_timings=True
                                )
                            )
                        )
                    ),
                    token=token
                )
            )

        batch_response = (
            messaging.send_each(
                messages
            )
        )

        invalid_tokens = []

        for index, response in enumerate(
            batch_response.responses
        ):

            if response.success:

                result[
                    "notifications_sent"
                ] += 1

                continue

            result[
                "notifications_failed"
            ] += 1

            exception_text = str(
                response.exception
                or ""
            ).lower()

            if any(
                marker in exception_text
                for marker in (
                    "registration-token-not-registered",
                    "unregistered",
                    "invalid-argument",
                    "invalid registration"
                )
            ):

                invalid_tokens.append(
                    tokens[index]
                )

        result["invalid_tokens"] = (
            invalid_tokens
        )

        if invalid_tokens:

            deactivate_invalid_tokens(
                cursor,
                invalid_tokens
            )

            connection.commit()

        return result

    except Exception as error:

        print(
            "Firebase accident notification error:",
            error
        )

        result["error"] = str(
            error
        )

        return result

    finally:

        cursor.close()