import os
from datetime import timedelta

from dotenv import load_dotenv


# Load values from the .env file placed beside config.py.
BASE_DIR = os.path.abspath(
    os.path.dirname(__file__)
)

load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)


def env_boolean(
    variable_name,
    default=False
):
    """
    Convert environment values such as true, yes, 1 and on
    into a Python Boolean value.
    """

    value = os.getenv(
        variable_name,
        str(default)
    )

    return value.strip().lower() in {
        "true",
        "yes",
        "1",
        "on"
    }


class Config:

    # =====================================================
    # FLASK
    # =====================================================

    # Keeps the same fallback key used by the original project.
    # You may optionally override it from .env later.
    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "DriveShieldAI@2026"
    )

    DEBUG = env_boolean(
        "FLASK_DEBUG",
        True
    )

    # Keep the login session valid for 30 days.
    PERMANENT_SESSION_LIFETIME = timedelta(
        days=int(
            os.getenv(
                "SESSION_LIFETIME_DAYS",
                "30"
            )
        )
    )

    SESSION_REFRESH_EACH_REQUEST = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Keep False for localhost and local development.
    # Set True only when the website is permanently hosted on HTTPS.
    SESSION_COOKIE_SECURE = env_boolean(
        "SESSION_COOKIE_SECURE",
        False
    )

    # =====================================================
    # MYSQL
    # =====================================================

    MYSQL_HOST = os.getenv(
        "MYSQL_HOST",
        "localhost"
    )

    MYSQL_PORT = int(
        os.getenv(
            "MYSQL_PORT",
            "3306"
        )
    )

    MYSQL_USER = os.getenv(
        "MYSQL_USER",
        "root"
    )

    MYSQL_PASSWORD = os.getenv(
        "MYSQL_PASSWORD",
        "root"
    )

    MYSQL_DB = os.getenv(
        "MYSQL_DB",
        "driveshield_ai"
    )

    # =====================================================
    # FILE UPLOAD
    # =====================================================

    UPLOAD_FOLDER = os.path.join(
        BASE_DIR,
        "static",
        "uploads"
    )

    # Maximum upload size: 10 MB.
    MAX_CONTENT_LENGTH = int(
        os.getenv(
            "MAX_CONTENT_LENGTH_BYTES",
            str(10 * 1024 * 1024)
        )
    )

    ALLOWED_EXTENSIONS = {
        "png",
        "jpg",
        "jpeg"
    }

    # =====================================================
    # EMAIL / FLASK-MAIL
    # =====================================================

    MAIL_SERVER = os.getenv(
        "MAIL_SERVER",
        "smtp.gmail.com"
    )

    MAIL_PORT = int(
        os.getenv(
            "MAIL_PORT",
            "587"
        )
    )

    MAIL_USE_TLS = env_boolean(
        "MAIL_USE_TLS",
        True
    )

    MAIL_USE_SSL = env_boolean(
        "MAIL_USE_SSL",
        False
    )

    MAIL_USERNAME = os.getenv(
        "MAIL_USERNAME",
        ""
    )

    MAIL_PASSWORD = os.getenv(
        "MAIL_PASSWORD",
        ""
    )

    MAIL_DEFAULT_SENDER = os.getenv(
        "MAIL_DEFAULT_SENDER",
        MAIL_USERNAME
    )

    # =====================================================
    # EMAIL / RESEND HTTPS API
    # =====================================================

    # Create this key in the Resend dashboard and store it
    # only in .env locally or Render Environment online.
    RESEND_API_KEY = os.getenv(
        "RESEND_API_KEY",
        ""
    ).strip()

    # Testing sender:
    # DriveShield AI <onboarding@resend.dev>
    #
    # The resend.dev sender can send only to the email
    # address connected to your Resend account. For real
    # emergency contacts, verify your own domain and use:
    # DriveShield AI <alerts@yourdomain.com>
    RESEND_FROM_EMAIL = os.getenv(
        "RESEND_FROM_EMAIL",
        "DriveShield AI <onboarding@resend.dev>"
    ).strip()

    # Optional address that receives replies.
    RESEND_REPLY_TO = os.getenv(
        "RESEND_REPLY_TO",
        ""
    ).strip()
