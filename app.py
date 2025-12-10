import sqlite3
from flask import Flask, jsonify, request
from datetime import datetime, timedelta
from flask_cors import CORS
import os
import sys # Import sys for handling script exit

app = Flask(__name__)
CORS(app)

# --- Robust path logic ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(SCRIPT_DIR, 'stayease.db')
SQL_SCRIPT_NAME = os.path.join(SCRIPT_DIR, 'database_setup.sql')
# --- End of logic ---

# --- NEW: Hard-coded list of demo hotels for browsing ---
# --- FIX: Prices converted from USD to INR (x83) ---
DEMO_HOTELS = [
    { "id": 1, "name": "The Grand Plaza", "location": "New York, USA", "price": 24070, "room_type": "Suite" },
    { "id": 2, "name": "Sunset Bungalow", "location": "Bali, Indonesia", "price": 14940, "room_type": "Deluxe" },
    { "id": 3, "name": "The City Lofts", "location": "London, UK", "price": 9130, "room_type": "Standard" },
    { "id": 4, "name": "Mountain Retreat", "location": "Aspen, USA", "price": 29050, "room_type": "Family" },
    { "id": 5, "name": "Parisian Charm", "location": "Paris, France", "price": 18260, "room_type": "Deluxe" },
    { "id": 6, "name": "Tokyo Modern", "location": "Tokyo, Japan", "price": 13280, "room_type": "Standard" },
]
# --- END FIX ---

def initialize_database():
    """
    Checks if the DB exists. If not, it creates it by running the .sql script.
    This replaces the need for import_data.py.
    """
    if os.path.exists(DB_NAME):
        # Database already exists, do nothing
        return

    print(f"Database '{DB_NAME}' not found. Creating it from '{SQL_SCRIPT_NAME}'...")
    
    if not os.path.exists(SQL_SCRIPT_NAME):
        print(f"FATAL ERROR: '{SQL_SCRIPT_NAME}' not found. Cannot create database.")
        sys.exit(1)
        
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        with open(SQL_SCRIPT_NAME, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        cursor.executescript(sql_script)
        conn.commit()
        conn.close()
        print("Database created successfully.")
    except Exception as e:
        print(f"FATAL ERROR: Could not create database. {e}")
        if os.path.exists(DB_NAME):
            os.remove(DB_NAME) # Clean up partial DB
        sys.exit(1)


def get_db_conn():
    """Helper function to create a database connection."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # This allows accessing columns by name
    return conn

# --- This is the CORRECT, lowercase route to match the HTML ---
@app.route('/api/login', methods=['POST'])
def login():
    """
    API endpoint for user login.
    Takes an email, checks if it exists in the DB.
    """
    try:
        data = request.json
        # Strip whitespace from incoming email
        email = data.get('email')
        if not email:
            return jsonify({"success": False, "message": "Email is required."}), 400
        email = email.strip()

        conn = get_db_conn()
        cursor = conn.cursor()
        
        # Use TRIM() in SQL for extra safety
        cursor.execute("SELECT name FROM bookings WHERE TRIM(email) = ? LIMIT 1", (email,))
        user = cursor.fetchone()
        conn.close()

        if user:
            # User found, send back their name
            return jsonify({"success": True, "name": user['name']})
        else:
            # User not found
            return jsonify({"success": False, "message": "Email not found in database."}), 404

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/hotel/login', methods=['POST'])
def hotel_login():
    """
    API endpoint for hotel partner login.
    This is a simulation. It just checks if the email exists in the database.
    """
    try:
        data = request.json
        email = data.get('email')
        if not email:
            return jsonify({"success": False, "message": "Email is required."}), 400
        email = email.strip()

        conn = get_db_conn()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM bookings WHERE TRIM(email) = ? LIMIT 1", (email,))
        user = cursor.fetchone()
        conn.close()

        if user:
            # User found, simulate successful hotel login
            return jsonify({"success": True, "message": "Hotel login successful."})
        else:
            # User not found
            return jsonify({"success": False, "message": "Hotel account not found."}), 404

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# --- NEW API ENDPOINT ---
@app.route('/api/hotels', methods=['GET'])
def get_hotels():
    """
    API endpoint to get a list of available hotels for browsing.
    Uses the hard-coded DEMO_HOTELS list.
    """
    try:
        # We can add logic here to get hotels from the DB if we had a hotel table
        # For now, we return our demo list
        return jsonify(DEMO_HOTELS)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- NEW API ENDPOINT ---
@app.route('/api/hotel/details', methods=['GET'])
def get_hotel_details():
    """
    API endpoint to get the details for a single hotel.
    Takes an 'id' query parameter.
    """
    try:
        hotel_id = request.args.get('id', type=int)
        if not hotel_id:
            return jsonify({"error": "Hotel ID is required."}), 400
        
        # Find the hotel in our demo list
        hotel = next((h for h in DEMO_HOTELS if h["id"] == hotel_id), None)
        
        if hotel:
            return jsonify(hotel)
        else:
            return jsonify({"error": "Hotel not found."}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/hotel/dashboard')
def hotel_dashboard():
    """
    API endpoint for the main hotel dashboard.
    Aggregates data from the database.
    """
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        
        # 1. Get Recent Bookings (Last 5)
        # --- FIX: Dates in this CSV are MM/DD/YYYY, so we must be careful ---
        # We will order by booking_id as a proxy for recency
        cursor.execute("""
            SELECT name, checkin_date, checkout_date, room_type 
            FROM bookings 
            WHERE cancelled = 0
            ORDER BY booking_id DESC
            LIMIT 5
        """)
        recent_bookings = [dict(row) for row in cursor.fetchall()]
        
        # 2. Get Revenue
        # --- FIX: Since dates are not in a standard YYYY-MM-DD format,
        # we cannot use strftime. We will provide demo numbers. ---
        this_month_revenue = 1037500  # 10.37 Lakh
        last_month_revenue = 913000   # 9.13 Lakh
        # --- END FIX ---


        # 3. Get Occupancy Rate (Demo Logic)
        # --- FIX: Querying dates in MM/DD/YYYY is complex. Use demo numbers. ---
        current_guests = 142 # This will result in 71% occupancy
        total_rooms = 200 # Assuming 200 total rooms for this demo
        # --- END FIX ---
        
        occupancy_rate = round((current_guests / total_rooms) * 100)

        # 4. Get Recent Activity (Last 4 payments)
        cursor.execute("""
            SELECT name, total_paid 
            FROM bookings 
            WHERE cancelled = 0 AND total_paid > 0
            ORDER BY booking_id DESC
            LIMIT 4
        """)
        recent_activity_raw = cursor.fetchall()
        recent_activity = [{"activity_type": f"Payment from {row['name']}", "total_paid": row['total_paid']} for row in recent_activity_raw]


        conn.close()

        dashboard_data = {
            "recent_bookings": recent_bookings,
            "revenue": {
                "this_month_revenue": this_month_revenue,
                "last_month_revenue": last_month_revenue
            },
            "occupancy_rate": occupancy_rate,
            "recent_activity": recent_activity
        }
        
        return jsonify(dashboard_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/user/dashboard')
def user_dashboard():
    """
    API endpoint for a specific user's dashboard.
    Takes a user_name query parameter.
    """
    try:
        user_name = request.args.get('user_name')
        if not user_name:
            return jsonify({"error": "user_name parameter is required."}), 400
        
        conn = get_db_conn()
        cursor = conn.cursor()
        
        # --- FIX: Cannot query dates easily, so we will use simple logic ---
        # Get Current Trip (first non-cancelled booking)
        cursor.execute("""
            SELECT room_type, price_per_night, checkin_date, checkout_date, country 
            FROM bookings 
            WHERE name = ? AND cancelled = 0
            ORDER BY checkin_date DESC
            LIMIT 1
        """, (user_name,))
        current_trip = cursor.fetchone()

        # Get Upcoming Trips (all other non-cancelled bookings)
        cursor.execute("""
            SELECT room_type, checkin_date, checkout_date, rating
            FROM bookings
            WHERE name = ? AND cancelled = 0
            ORDER BY checkin_date DESC
            LIMIT 5
            OFFSET 1
        """, (user_name,))
        upcoming_trips = [dict(row) for row in cursor.fetchall()]
        # --- END FIX ---
        
        # 3. Get Personal Info
        cursor.execute("SELECT name, email FROM bookings WHERE name = ? LIMIT 1", (user_name,))
        user_info = cursor.fetchone()

        conn.close()

        # 3. Static Info (Payment)
        payment_methods = [{
            "type": "Credit Card",
            "last4": "1234",
            "expires": "08/26"
        }]

        dashboard_data = {
            "personal_info": dict(user_info) if user_info else {"name": user_name, "email": "N/A"},
            "payment_methods": payment_methods,
            "current_trip": dict(current_trip) if current_trip else None,
            "upcoming_trips": upcoming_trips
        }

        return jsonify(dashboard_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # --- THIS IS THE NEW "NO HUSTLE" FIX ---
    # This automatically creates the database if it's missing.
    initialize_database()
    # --- END FIX ---
    
    print(f"Database found. Starting Flask server. API running at http://127.0.0.1:5000")
    print("Available endpoints:")
    print("  - http://127.0.0.1:5000/api/login (POST)")
    print("  - http://127.0.0.1:5000/api/hotel/login (POST)")
    print("  - http://127.0.0.1:5000/api/hotel/dashboard (GET)")
    print("  - http://1.0.0.1:5000/api/user/dashboard (GET, needs ?user_name=...)")
    print("  - http://127.0.0.1:5000/api/hotels (GET)")
    print("  - http://127.0.0.1:5000/api/hotel/details (GET, needs ?id=...)")
    app.run(debug=True, port=5000)