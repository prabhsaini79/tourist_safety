
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify
)
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from bson.objectid import ObjectId
from dotenv import load_dotenv
import os
import math


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)

app.secret_key = os.getenv(
    "SECRET_KEY",
    "tourist-safety-local-secret-key"
)


# ============================================================
# MONGODB CONNECTION
# ============================================================

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://localhost:27017/"
)

try:
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000
    )

    # Test database connection
    client.admin.command("ping")

    db = client["tourist_safety"]

    users_collection = db["users"]
    locations_collection = db["locations"]
    sos_collection = db["sos_alerts"]
    chats_collection = db["chats"]

    print("MongoDB connected successfully.")

except Exception as e:
    print("MongoDB connection error:", e)

    client = None
    db = None
    users_collection = None
    locations_collection = None
    sos_collection = None
    chats_collection = None


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def utc_now():
    """Return current UTC time."""
    return datetime.now(timezone.utc)


def database_available():
    """Check whether MongoDB is available."""
    return (
        users_collection is not None
        and locations_collection is not None
        and sos_collection is not None
        and chats_collection is not None
    )


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two latitude/longitude points
    using the Haversine formula.
    """

    try:
        lat1 = float(lat1)
        lon1 = float(lon1)
        lat2 = float(lat2)
        lon2 = float(lon2)

        earth_radius = 6371.0  # km

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)

        difference_lat = math.radians(lat2 - lat1)
        difference_lon = math.radians(lon2 - lon1)

        a = (
            math.sin(difference_lat / 2) ** 2
            +
            math.cos(lat1_rad)
            * math.cos(lat2_rad)
            * math.sin(difference_lon / 2) ** 2
        )

        c = 2 * math.atan2(
            math.sqrt(a),
            math.sqrt(1 - a)
        )

        return earth_radius * c

    except (ValueError, TypeError):
        return None


def get_current_user():
    """Get currently logged-in user."""

    if "user_id" not in session:
        return None

    if not database_available():
        return None

    try:
        return users_collection.find_one(
            {"_id": ObjectId(session["user_id"])}
        )
    except Exception:
        return None


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    if "user_id" in session:
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


# ============================================================
# REGISTER
# ============================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":
        return render_template("register.html")

    if not database_available():
        flash(
            "Database is not connected. Please start MongoDB.",
            "error"
        )
        return redirect(url_for("register"))

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    mobile = request.form.get("mobile", "").strip()
    password = request.form.get("password", "").strip()

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    if not name or not email or not mobile or not password:
        flash(
            "Please fill all required fields.",
            "error"
        )
        return redirect(url_for("register"))

    if len(password) < 6:
        flash(
            "Password must contain at least 6 characters.",
            "error"
        )
        return redirect(url_for("register"))

    # --------------------------------------------------------
    # Check existing email
    # --------------------------------------------------------

    existing_email = users_collection.find_one(
        {"email": email}
    )

    if existing_email:
        flash(
            "Email already registered. Please login.",
            "error"
        )
        return redirect(url_for("login"))

    # --------------------------------------------------------
    # Check existing mobile
    # --------------------------------------------------------

    existing_mobile = users_collection.find_one(
        {"mobile": mobile}
    )

    if existing_mobile:
        flash(
            "Mobile number already registered. Please login.",
            "error"
        )
        return redirect(url_for("login"))

    # --------------------------------------------------------
    # Generate Tourist ID
    # --------------------------------------------------------

    tourist_id = (
        "TSA-"
        + datetime.now().strftime("%Y%m%d%H%M%S")
    )

    # --------------------------------------------------------
    # Hash password
    # --------------------------------------------------------

    hashed_password = generate_password_hash(password)

    # --------------------------------------------------------
    # Create user
    # --------------------------------------------------------

    user_data = {
        "name": name,
        "email": email,
        "mobile": mobile,
        "password": hashed_password,
        "tourist_id": tourist_id,
        "created_at": utc_now(),
        "updated_at": utc_now()
    }

    try:

        result = users_collection.insert_one(user_data)

        if result.inserted_id:

            flash(
                "Account created successfully. Please login.",
                "success"
            )

            return redirect(url_for("login"))

    except PyMongoError as e:

        print("Registration database error:", e)

        flash(
            "Unable to create account. Please try again.",
            "error"
        )

        return redirect(url_for("register"))

    except Exception as e:

        print("Registration error:", e)

        flash(
            "Something went wrong. Please try again.",
            "error"
        )

        return redirect(url_for("register"))


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET":

        if "user_id" in session:
            return redirect(url_for("dashboard"))

        return render_template("login.html")

    # --------------------------------------------------------
    # Check database
    # --------------------------------------------------------

    if not database_available():

        flash(
            "Database is not connected. Please start MongoDB.",
            "error"
        )

        return redirect(url_for("login"))

    # --------------------------------------------------------
    # Get form values
    # --------------------------------------------------------

    email_or_mobile = request.form.get(
        "email",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    ).strip()

    if not email_or_mobile or not password:

        flash(
            "Please enter email/mobile and password.",
            "error"
        )

        return redirect(url_for("login"))

    # --------------------------------------------------------
    # Search by email OR mobile
    # --------------------------------------------------------

    login_value = email_or_mobile.lower()

    try:

        user = users_collection.find_one(
            {
                "$or": [
                    {
                        "email": login_value
                    },
                    {
                        "mobile": email_or_mobile
                    }
                ]
            }
        )

    except Exception as e:

        print("Login database error:", e)

        flash(
            "Database error. Please try again.",
            "error"
        )

        return redirect(url_for("login"))

    # --------------------------------------------------------
    # User not found
    # --------------------------------------------------------

    if not user:

        flash(
            "Invalid email/mobile or password.",
            "error"
        )

        return redirect(url_for("login"))

    stored_password = user.get("password", "")

    password_valid = False

    # --------------------------------------------------------
    # Check hashed password
    # --------------------------------------------------------

    try:

        password_valid = check_password_hash(
            stored_password,
            password
        )

    except Exception:
        password_valid = False

    # --------------------------------------------------------
    # Compatibility with old plain-text password
    #
    # If an old local account has a plain-text password,
    # convert it to a secure hash after successful login.
    # --------------------------------------------------------

    if not password_valid:

        try:

            if stored_password == password:

                password_valid = True

                users_collection.update_one(
                    {
                        "_id": user["_id"]
                    },
                    {
                        "$set": {
                            "password": generate_password_hash(password),
                            "updated_at": utc_now()
                        }
                    }
                )

        except Exception as e:

            print("Password migration error:", e)

    # --------------------------------------------------------
    # Invalid password
    # --------------------------------------------------------

    if not password_valid:

        flash(
            "Invalid email/mobile or password.",
            "error"
        )

        return redirect(url_for("login"))

    # --------------------------------------------------------
    # Create Tourist ID if missing
    # --------------------------------------------------------

    tourist_id = user.get("tourist_id")

    if not tourist_id:

        tourist_id = (
            "TSA-"
            + datetime.now().strftime("%Y%m%d%H%M%S")
        )

        users_collection.update_one(
            {
                "_id": user["_id"]
            },
            {
                "$set": {
                    "tourist_id": tourist_id,
                    "updated_at": utc_now()
                }
            }
        )

    # --------------------------------------------------------
    # Create session
    # --------------------------------------------------------

    session.clear()

    session["user_id"] = str(user["_id"])
    session["user_email"] = user.get("email", "")
    session["user_name"] = user.get("name", "")
    session["tourist_id"] = tourist_id

    print(
        "LOGIN SUCCESSFUL:",
        user.get("email", "")
    )

    return redirect(url_for("dashboard"))


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(url_for("login"))

    user = get_current_user()

    if not user:

        session.clear()

        flash(
            "User session expired. Please login again.",
            "error"
        )

        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        user=user
    )


# ============================================================
# DIGITAL TOURIST ID
# ============================================================

@app.route("/api/tourist-id", methods=["GET"])
def tourist_id():

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    user = get_current_user()

    if not user:

        return jsonify({
            "success": False,
            "message": "User not found."
        }), 404

    tourist_id_value = user.get("tourist_id")

    if not tourist_id_value:

        tourist_id_value = (
            "TSA-"
            + datetime.now().strftime("%Y%m%d%H%M%S")
        )

        users_collection.update_one(
            {
                "_id": user["_id"]
            },
            {
                "$set": {
                    "tourist_id": tourist_id_value,
                    "updated_at": utc_now()
                }
            }
        )

    return jsonify({
        "success": True,
        "tourist": {
            "name": user.get("name", ""),
            "email": user.get("email", ""),
            "mobile": user.get("mobile", ""),
            "tourist_id": tourist_id_value
        }
    })


# ============================================================
# UPDATE USER LOCATION
# ============================================================

@app.route("/update-location", methods=["POST"])
def update_location():

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    if not database_available():

        return jsonify({
            "success": False,
            "message": "Database unavailable."
        }), 500

    data = request.get_json(
        silent=True
    ) or {}

    latitude = data.get("latitude")
    longitude = data.get("longitude")

    if latitude is None or longitude is None:

        return jsonify({
            "success": False,
            "message": "Latitude and longitude are required."
        }), 400

    try:

        latitude = float(latitude)
        longitude = float(longitude)

    except (ValueError, TypeError):

        return jsonify({
            "success": False,
            "message": "Invalid location coordinates."
        }), 400

    try:

        location_data = {
            "user_id": ObjectId(session["user_id"]),
            "latitude": latitude,
            "longitude": longitude,
            "updated_at": utc_now()
        }

        locations_collection.insert_one(
            location_data
        )

        # Also update latest location in user document
        users_collection.update_one(
            {
                "_id": ObjectId(session["user_id"])
            },
            {
                "$set": {
                    "latest_location": {
                        "latitude": latitude,
                        "longitude": longitude,
                        "updated_at": utc_now()
                    }
                }
            }
        )

        return jsonify({
            "success": True,
            "message": "Location updated successfully.",
            "latitude": latitude,
            "longitude": longitude
        })

    except Exception as e:

        print("Location error:", e)

        return jsonify({
            "success": False,
            "message": "Unable to update location."
        }), 500


# ============================================================
# SOS ALERT
# ============================================================

@app.route("/sos", methods=["POST"])
def sos():

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    if not database_available():

        return jsonify({
            "success": False,
            "message": "Database unavailable."
        }), 500

    data = request.get_json(
        silent=True
    ) or {}

    latitude = data.get("latitude")
    longitude = data.get("longitude")
    message = data.get(
        "message",
        "Emergency SOS alert"
    )

    try:

        alert = {
            "user_id": ObjectId(session["user_id"]),
            "latitude": latitude,
            "longitude": longitude,
            "message": message,
            "status": "active",
            "created_at": utc_now()
        }

        result = sos_collection.insert_one(
            alert
        )

        return jsonify({
            "success": True,
            "message": "SOS alert created successfully.",
            "alert_id": str(result.inserted_id)
        })

    except Exception as e:

        print("SOS error:", e)

        return jsonify({
            "success": False,
            "message": "Unable to create SOS alert."
        }), 500


# ============================================================
# NEARBY POLICE
# ============================================================

@app.route("/nearby-police", methods=["GET", "POST"])
def nearby_police():

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    if request.method == "POST":

        data = request.get_json(
            silent=True
        ) or {}

        latitude = data.get("latitude")
        longitude = data.get("longitude")

    else:

        latitude = request.args.get("latitude")
        longitude = request.args.get("longitude")

    if latitude is None or longitude is None:

        return jsonify({
            "success": False,
            "message": "Location is required."
        }), 400

    try:

        latitude = float(latitude)
        longitude = float(longitude)

    except (ValueError, TypeError):

        return jsonify({
            "success": False,
            "message": "Invalid location."
        }), 400

    # --------------------------------------------------------
    # Demo police locations
    #
    # These are sample locations for the local project.
    # Real police locations can later be connected to a
    # maps/places service.
    # --------------------------------------------------------

    police_stations = [
        {
            "name": "Nearest Police Station",
            "latitude": latitude + 0.005,
            "longitude": longitude + 0.005,
            "phone": "112"
        },
        {
            "name": "Police Help Centre",
            "latitude": latitude - 0.008,
            "longitude": longitude + 0.004,
            "phone": "112"
        },
        {
            "name": "Emergency Police Station",
            "latitude": latitude + 0.010,
            "longitude": longitude - 0.006,
            "phone": "112"
        }
    ]

    for station in police_stations:

        distance = calculate_distance(
            latitude,
            longitude,
            station["latitude"],
            station["longitude"]
        )

        station["distance_km"] = (
            round(distance, 2)
            if distance is not None
            else None
        )

    police_stations.sort(
        key=lambda x: (
            x["distance_km"]
            if x["distance_km"] is not None
            else 999999
        )
    )

    return jsonify({
        "success": True,
        "police_stations": police_stations
    })


# ============================================================
# SEND CHAT MESSAGE
# ============================================================

@app.route("/chat/send", methods=["POST"])
def send_chat():

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    if not database_available():

        return jsonify({
            "success": False,
            "message": "Database unavailable."
        }), 500

    data = request.get_json(
        silent=True
    ) or {}

    message = data.get(
        "message",
        ""
    ).strip()

    if not message:

        return jsonify({
            "success": False,
            "message": "Message cannot be empty."
        }), 400

    try:

        chat_data = {
            "user_id": ObjectId(session["user_id"]),
            "sender": "user",
            "message": message,
            "created_at": utc_now()
        }

        result = chats_collection.insert_one(
            chat_data
        )

        return jsonify({
            "success": True,
            "message": "Message sent.",
            "chat_id": str(result.inserted_id)
        })

    except Exception as e:

        print("Chat send error:", e)

        return jsonify({
            "success": False,
            "message": "Unable to send message."
        }), 500


# ============================================================
# CHAT HISTORY
# ============================================================

@app.route("/chat/history", methods=["GET"])
def chat_history():

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    if not database_available():

        return jsonify({
            "success": False,
            "message": "Database unavailable."
        }), 500

    try:

        messages = chats_collection.find(
            {
                "user_id": ObjectId(
                    session["user_id"]
                )
            }
        ).sort(
            "created_at",
            1
        )

        result = []

        for message in messages:

            result.append({
                "id": str(message["_id"]),
                "sender": message.get(
                    "sender",
                    "user"
                ),
                "message": message.get(
                    "message",
                    ""
                ),
                "created_at": (
                    message["created_at"].isoformat()
                    if message.get("created_at")
                    else ""
                )
            })

        return jsonify({
            "success": True,
            "messages": result
        })

    except Exception as e:

        print("Chat history error:", e)

        return jsonify({
            "success": False,
            "message": "Unable to load chat history."
        }), 500


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out successfully.",
        "success"
    )

    return redirect(url_for("login"))


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():

    if not database_available():

        return jsonify({
            "status": "error",
            "database": "disconnected"
        }), 500

    try:

        client.admin.command("ping")

        return jsonify({
            "status": "ok",
            "database": "connected"
        })

    except Exception as e:

        print("Health check error:", e)

        return jsonify({
            "status": "error",
            "database": "disconnected"
        }), 500


# ============================================================
# 404 ERROR
# ============================================================

@app.errorhandler(404)
def page_not_found(error):

    return render_template(
        "login.html"
    ), 404


# ============================================================
# 500 ERROR
# ============================================================

@app.errorhandler(500)
def internal_server_error(error):

    return """
    <h1>Internal Server Error</h1>
    <p>Something went wrong on the server.</p>
    """, 500


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )


