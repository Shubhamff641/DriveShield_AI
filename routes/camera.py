from flask import Blueprint, render_template, Response, redirect, url_for, session,request,jsonify
import cv2

from ai.drowsiness import( detect_face,draw_landmarks,detect_drowsiness)


camera = Blueprint("camera", __name__)


cap = cv2.VideoCapture(0)


def generate_frames():

    while True:

        success, frame = cap.read()

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

        ret, buffer = cv2.imencode(".jpg", frame)

        frame = buffer.tobytes()

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + frame
            + b"\r\n"
        )
@camera.route("/camera")
def camera_page():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    return render_template("camera.html")


@camera.route("/video_feed")
def video_feed():

    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )
@camera.route("/phone")
def phone():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    return render_template("phone.html")
@camera.route("/accident", methods=["POST"])
def accident():

    data = request.get_json()

    x = data.get("x")
    y = data.get("y")
    z = data.get("z")
    latitude = data.get("latitude")
    longitude = data.get("longitude")

    print("========== ACCIDENT DETECTED ==========")
    print("X :", x)
    print("Y :", y)
    print("Z :", z)
    print("Latitude :", latitude)
    print("Longitude:", longitude)
    print("=======================================")

    return jsonify({
        "status": "success"
    })