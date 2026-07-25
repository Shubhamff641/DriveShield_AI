from flask import Blueprint, render_template, session, redirect, url_for

gps = Blueprint("gps", __name__)


@gps.route("/gps")
def gps_page():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    return render_template("gps.html")