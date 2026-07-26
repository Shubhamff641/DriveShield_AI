from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for
)


camera = Blueprint(
    "camera",
    __name__
)


# =========================================================
# WEB DROWSINESS PAGE
# =========================================================

@camera.route("/camera")
def camera_page():

    if "user_id" not in session:

        return redirect(
            url_for("auth.login")
        )

    return render_template(
        "camera.html"
    )


# =========================================================
# OLD SERVER-CAMERA ENDPOINT
# =========================================================

@camera.route("/video_feed")
def video_feed():
    """
    The hosted application cannot access the visitor's camera
    through cv2.VideoCapture(0).

    Web drowsiness detection now runs inside the visitor's
    browser through JavaScript and MediaPipe.
    """

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Please log in first."
        }), 401

    return jsonify({
        "success": False,
        "message": (
            "Server-side video streaming has been replaced "
            "by browser-based drowsiness detection."
        )
    }), 410


# =========================================================
# LEGACY PHONE PAGE
# =========================================================

@camera.route("/phone")
def phone():

    if "user_id" not in session:

        return redirect(
            url_for("auth.login")
        )

    return render_template(
        "phone.html"
    )


# =========================================================
# LEGACY ACCIDENT SENSOR ENDPOINT
# =========================================================

@camera.route(
    "/accident",
    methods=["POST"]
)
def legacy_accident_report():

    data = request.get_json(
        silent=True
    ) or {}

    print(
        "========== ACCIDENT DETECTED =========="
    )

    print("X :", data.get("x"))
    print("Y :", data.get("y"))
    print("Z :", data.get("z"))

    print(
        "Latitude :",
        data.get("latitude")
    )

    print(
        "Longitude:",
        data.get("longitude")
    )

    print(
        "======================================="
    )

    return jsonify({
        "status": "success"
    })