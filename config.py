import os
from datetime import timedelta

from dotenv import load_dotenv


BASE_DIR = os.path.abspath(
    os.path.dirname(__file__)
)

load_dotenv(
    os.path.join(
        BASE_DIR,
        ".env"
    ),
    override=True
)


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

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "DriveShieldAI@2026"
    )

    DEBUG = env_boolean(
        "FLASK_DEBUG",
        True
    )

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
    #
    # These settings are kept because app.py still
    # initializes the Flask-Mail extension.
    # Accident alerts now use Brevo HTTPS API instead.

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
    # EMAIL / BREVO HTTPS API
    # =====================================================

    BREVO_API_KEY = os.getenv(
        "BREVO_API_KEY",
        ""
    ).strip()

    BREVO_SENDER_EMAIL = os.getenv(
        "BREVO_SENDER_EMAIL",
        ""
    ).strip()

    BREVO_SENDER_NAME = os.getenv(
        "BREVO_SENDER_NAME",
        "DriveShield AI"
    ).strip()

    BREVO_REPLY_TO = os.getenv(
        "BREVO_REPLY_TO",
        ""
    ).strip()