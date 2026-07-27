import os

from flask import Flask, jsonify, session

from config import Config
from extensions import mail
from routes.accident import accident
from routes.auth import auth
from routes.camera import camera
from routes.dashboard import dashboard
from routes.emergency import emergency
from routes.fcm import fcm
from routes.gps import gps
from routes.hospital import hospital
from routes.profile import profile
from routes.test_email import test_email


app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config["SECRET_KEY"]

os.makedirs(
    app.config["UPLOAD_FOLDER"],
    exist_ok=True
)

mail.init_app(app)

app.register_blueprint(auth)
app.register_blueprint(dashboard)
app.register_blueprint(profile)
app.register_blueprint(emergency)
app.register_blueprint(camera)
app.register_blueprint(accident)
app.register_blueprint(fcm)
app.register_blueprint(gps)
app.register_blueprint(hospital)
app.register_blueprint(test_email)


@app.after_request
def keep_authenticated_session_permanent(response):

    if "user_id" in session:
        session.permanent = True

    return response


@app.errorhandler(413)
def image_too_large(error):

    return jsonify({
        "success": False,
        "message": (
            "The selected image is too large. "
            "Please select an image smaller than 10 MB."
        )
    }), 413


@app.errorhandler(404)
def page_not_found(error):

    return jsonify({
        "success": False,
        "message": "The requested page was not found."
    }), 404


@app.errorhandler(500)
def internal_server_error(error):

    return jsonify({
        "success": False,
        "message": "An internal server error occurred."
    }), 500


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=app.config["DEBUG"]
    )