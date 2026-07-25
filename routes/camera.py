import os

from flask import (
    Blueprint,
    Response,
    jsonify,
    redirect,
    render_template,
    render_template_string,
    request,
    session,
    url_for
)


camera = Blueprint("camera", __name__)


def camera_feature_enabled():
    configured_value = os.getenv("ENABLE_WEB_CAMERA")

    if configured_value is not None:
        return configured_value.strip().lower() in {
            "true",
            "1",
            "yes",
            "on"
        }

    return os.name == "nt"


def generate_frames(
    cv2,
    detect_face,
    draw_landmarks,
    detect_drowsiness
):
    capture = cv2.VideoCapture(0)

    if not capture.isOpened():
        capture.release()
        return

    try:
        while True:
            success, frame = capture.read()

            if not success:
                break

            result = detect_face(frame)
            drowsy, ear = detect_drowsiness(result)
            frame = draw_landmarks(frame, result)

            if drowsy:
                cv2.putText(
                    frame,
                    "DROWSINESS ALERT!",
                    (50, 80),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 255),
                    3
                )

            encoded, buffer = cv2.imencode(".jpg", frame)

            if not encoded:
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + buffer.tobytes()
                + b"\r\n"
            )

    finally:
        capture.release()


@camera.route("/camera")
def camera_page():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if not camera_feature_enabled():
        return render_template_string(
            """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Web Camera - DriveShield AI</title>
                <link
                    href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.7/dist/css/bootstrap.min.css"
                    rel="stylesheet"
                >
            </head>
            <body class="bg-light">
                <main class="container py-5">
                    <div class="card border-0 shadow-sm rounded-4 mx-auto" style="max-width: 680px;">
                        <div class="card-body p-5 text-center">
                            <div class="display-4 mb-3">📷</div>
                            <h1 class="h3 fw-bold">Web Camera Unavailable on Cloud</h1>
                            <p class="text-muted mt-3">
                                Server-side camera detection works only when DriveShield AI
                                runs on your Windows computer. Use the Android app for
                                drowsiness detection when the website is hosted online.
                            </p>
                            <a
                                href="{{ url_for('dashboard.dashboard_page') }}"
                                class="btn btn-primary mt-3"
                            >
                                Back to Dashboard
                            </a>
                        </div>
                    </div>
                </main>
            </body>
            </html>
            """
        )

    return render_template("camera.html")


@camera.route("/video_feed")
def video_feed():
    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    if not camera_feature_enabled():
        return jsonify({
            "success": False,
            "message": "Web camera detection is unavailable on the cloud server."
        }), 503

    try:
        import cv2

        from ai.drowsiness import (
            detect_drowsiness,
            detect_face,
            draw_landmarks
        )

    except Exception as error:
        return jsonify({
            "success": False,
            "message": f"Unable to initialize web camera detection: {error}"
        }), 503

    return Response(
        generate_frames(
            cv2,
            detect_face,
            draw_landmarks,
            detect_drowsiness
        ),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@camera.route("/phone")
def phone():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    return render_template("phone.html")


@camera.route("/accident", methods=["POST"])
def legacy_accident_report():
    data = request.get_json(silent=True) or {}

    print("========== ACCIDENT DETECTED ==========")
    print("X :", data.get("x"))
    print("Y :", data.get("y"))
    print("Z :", data.get("z"))
    print("Latitude :", data.get("latitude"))
    print("Longitude:", data.get("longitude"))
    print("=======================================")

    return jsonify({
        "status": "success"
    })