from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for
)

import math
import requests


hospital = Blueprint(
    "hospital",
    __name__
)


DEFAULT_SEARCH_RADIUS_METERS = 15000
DEFAULT_HOSPITAL_LIMIT = 15


# =========================================================
# VALIDATE GPS COORDINATES
# =========================================================

def validate_coordinates(
    latitude,
    longitude
):
    try:
        latitude = float(latitude)
        longitude = float(longitude)

    except (TypeError, ValueError):
        raise ValueError(
            "Latitude and longitude must be numbers."
        )

    if not -90 <= latitude <= 90:
        raise ValueError(
            "Latitude must be between -90 and 90."
        )

    if not -180 <= longitude <= 180:
        raise ValueError(
            "Longitude must be between -180 and 180."
        )

    return latitude, longitude


# =========================================================
# CALCULATE DISTANCE BETWEEN TWO GPS COORDINATES
# =========================================================

def calculate_distance(
    lat1,
    lon1,
    lat2,
    lon2
):
    """
    Calculate distance between two GPS coordinates
    using the Haversine formula.

    Distance is returned in kilometres.
    """

    earth_radius = 6371.0

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    difference_latitude = (
        lat2_rad - lat1_rad
    )

    difference_longitude = (
        lon2_rad - lon1_rad
    )

    value = (
        math.sin(
            difference_latitude / 2
        ) ** 2
        + math.cos(lat1_rad)
        * math.cos(lat2_rad)
        * math.sin(
            difference_longitude / 2
        ) ** 2
    )

    angle = 2 * math.atan2(
        math.sqrt(value),
        math.sqrt(1 - value)
    )

    return earth_radius * angle


# =========================================================
# CREATE HOSPITAL ADDRESS FROM OPENSTREETMAP TAGS
# =========================================================

def create_hospital_address(tags):

    address_parts = [
        tags.get("addr:housenumber"),
        tags.get("addr:street"),
        tags.get("addr:suburb"),
        tags.get("addr:city"),
        tags.get("addr:district"),
        tags.get("addr:state"),
        tags.get("addr:postcode")
    ]

    address = ", ".join(
        str(part).strip()
        for part in address_parts
        if part and str(part).strip()
    )

    return (
        address
        if address
        else "Address not available"
    )


# =========================================================
# BUILD OVERPASS QUERY
# =========================================================

def build_hospital_query(
    latitude,
    longitude,
    radius
):

    return f"""
    [out:json][timeout:18];
    (
        nwr["amenity"="hospital"]
            (around:{radius},{latitude},{longitude});

        nwr["healthcare"="hospital"]
            (around:{radius},{latitude},{longitude});
    );
    out center tags qt;
    """


# =========================================================
# SEND REQUEST TO OVERPASS API WITH FALLBACK SERVERS
# =========================================================

def fetch_overpass_data(
    query,
    request_timeout=25
):

    
    overpass_servers = [
    (
        "https://overpass.private.coffee/"
        "api/interpreter"
    ),
    (
        "https://maps.mail.ru/osm/tools/"
        "overpass/api/interpreter"
    ),
    (
        "https://overpass-api.de/"
        "api/interpreter"
    )
]

    headers = {
        "User-Agent": (
            "DriveShieldAI/1.0 "
            "(TYBCS Academic Project)"
        ),
        "Accept": "application/json",
        "Content-Type": (
            "application/x-www-form-urlencoded; "
            "charset=UTF-8"
        )
    }

    errors = []

    for server_url in overpass_servers:

        try:
            response = requests.post(
                server_url,
                headers=headers,
                data={
                    "data": query
                },
                timeout=request_timeout
            )

            if response.status_code == 200:

                content_type = (
                    response.headers.get(
                        "Content-Type",
                        ""
                    )
                )

                response_text = (
                    response.text.lstrip()
                )

                if (
                    "json" not in
                    content_type.lower()
                    and not response_text
                    .startswith("{")
                ):
                    errors.append(
                        f"{server_url}: "
                        "Invalid response format"
                    )

                    continue

                return response.json()

            errors.append(
                f"{server_url}: "
                f"HTTP {response.status_code}"
            )

        except requests.Timeout:

            errors.append(
                f"{server_url}: "
                "Request timed out"
            )

        except requests.ConnectionError:

            errors.append(
                f"{server_url}: "
                "Connection failed"
            )

        except requests.RequestException as error:

            errors.append(
                f"{server_url}: {str(error)}"
            )

        except ValueError:

            errors.append(
                f"{server_url}: "
                "Invalid JSON response"
            )

    raise RuntimeError(
        "All nearby-hospital servers failed. "
        + " | ".join(errors)
    )


# =========================================================
# CONVERT OVERPASS RESPONSE INTO HOSPITAL LIST
# =========================================================

def parse_hospitals(
    overpass_data,
    user_latitude,
    user_longitude
):

    hospitals = []
    duplicate_keys = set()

    for element in overpass_data.get(
        "elements",
        []
    ):

        tags = element.get(
            "tags",
            {}
        )

        hospital_latitude = element.get(
            "lat"
        )

        hospital_longitude = element.get(
            "lon"
        )

        if (
            hospital_latitude is None
            or hospital_longitude is None
        ):

            center = element.get(
                "center",
                {}
            )

            hospital_latitude = center.get(
                "lat"
            )

            hospital_longitude = center.get(
                "lon"
            )

        if (
            hospital_latitude is None
            or hospital_longitude is None
        ):
            continue

        try:
            hospital_latitude = float(
                hospital_latitude
            )

            hospital_longitude = float(
                hospital_longitude
            )

        except (TypeError, ValueError):
            continue

        hospital_name = (
            tags.get("name")
            or tags.get("official_name")
            or tags.get("operator")
            or "Unnamed Hospital"
        )

        address = create_hospital_address(
            tags
        )

        phone = (
            tags.get("phone")
            or tags.get("contact:phone")
            or tags.get("telephone")
            or "Not available"
        )

        website = (
            tags.get("website")
            or tags.get("contact:website")
            or ""
        )

        emergency_service = (
            tags.get("emergency")
            or "Not specified"
        )

        distance = calculate_distance(
            user_latitude,
            user_longitude,
            hospital_latitude,
            hospital_longitude
        )

        duplicate_key = (
            hospital_name
            .lower()
            .strip(),

            round(
                hospital_latitude,
                5
            ),

            round(
                hospital_longitude,
                5
            )
        )

        if duplicate_key in duplicate_keys:
            continue

        duplicate_keys.add(
            duplicate_key
        )

        maps_url = (
            "https://www.google.com/maps/search/"
            "?api=1&query="
            f"{hospital_latitude},"
            f"{hospital_longitude}"
        )

        hospitals.append({
            "osm_id":
                element.get("id"),

            "name":
                hospital_name,

            "address":
                address,

            "phone":
                phone,

            "website":
                website,

            "emergency":
                emergency_service,

            "latitude":
                hospital_latitude,

            "longitude":
                hospital_longitude,

            "distance":
                round(distance, 2),

            "maps_url":
                maps_url
        })

    hospitals.sort(
        key=lambda item:
        item["distance"]
    )

    return hospitals


# =========================================================
# REUSABLE HOSPITAL SEARCH
# =========================================================

def find_nearby_hospitals(
    latitude,
    longitude,
    radius=DEFAULT_SEARCH_RADIUS_METERS,
    limit=DEFAULT_HOSPITAL_LIMIT,
    request_timeout=20
):
    """
    Search hospitals around the supplied coordinates.

    This function is reusable by both:
    1. The nearby-hospitals API.
    2. The automatic accident workflow.
    """

    latitude, longitude = (
        validate_coordinates(
            latitude,
            longitude
        )
    )

    radius = int(radius)
    limit = int(limit)

    if radius <= 0:
        raise ValueError(
            "Search radius must be positive."
        )

    if limit <= 0:
        raise ValueError(
            "Hospital result limit must be positive."
        )

    query = build_hospital_query(
        latitude,
        longitude,
        radius
    )

    overpass_data = fetch_overpass_data(
        query,
        request_timeout=request_timeout
    )

    hospitals = parse_hospitals(
        overpass_data,
        latitude,
        longitude
    )

    return hospitals[:limit]


def find_nearest_hospital(
    latitude,
    longitude,
    radius=DEFAULT_SEARCH_RADIUS_METERS,
    request_timeout=20
):
    """
    Return the closest hospital, or None when no hospital
    is found inside the selected radius.
    """

    hospitals = find_nearby_hospitals(
        latitude=latitude,
        longitude=longitude,
        radius=radius,
        limit=1,
        request_timeout=request_timeout
    )

    if not hospitals:
        return None

    return hospitals[0]


# =========================================================
# HOSPITAL WEB PAGE
# =========================================================

@hospital.route("/hospital")
def hospital_page():

    if "user_id" not in session:

        return redirect(
            url_for("auth.login")
        )

    return render_template(
        "hospital.html"
    )


# =========================================================
# NEARBY HOSPITAL API
# =========================================================

@hospital.route(
    "/api/nearby-hospitals",
    methods=["POST"]
)
def nearby_hospitals():

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": (
                "Please log in to continue."
            )
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
        latitude, longitude = (
            validate_coordinates(
                latitude,
                longitude
            )
        )

        nearest_hospitals = (
            find_nearby_hospitals(
                latitude=latitude,
                longitude=longitude,
                radius=
                    DEFAULT_SEARCH_RADIUS_METERS,
                limit=
                    DEFAULT_HOSPITAL_LIMIT,
                request_timeout=25
            )
        )

    except ValueError as error:

        return jsonify({
            "success": False,
            "message": str(error)
        }), 400

    except RuntimeError as error:

        print(
            "Hospital API error:",
            error
        )

        return jsonify({
            "success": False,
            "message": (
                "The nearby hospital service is "
                "temporarily unavailable. "
                "Please try again shortly."
            )
        }), 503

    return jsonify({
        "success": True,

        "count":
            len(nearest_hospitals),

        "search_radius_km":
            (
                DEFAULT_SEARCH_RADIUS_METERS
                / 1000
            ),

        "user_location": {
            "latitude": latitude,
            "longitude": longitude
        },

        "hospitals":
            nearest_hospitals,

        "message": (
            f"{len(nearest_hospitals)} "
            "nearby hospitals found."
        )
    }), 200