import json
from firebase_admin import credentials, firestore, initialize_app
from flask import Flask, jsonify, request
from flask_cors import CORS
from firebase_functions import https_fn
from datetime import datetime

# Initialize Firebase Admin SDK
initialize_app()
db = firestore.client()

app = Flask(__name__)
CORS(app)

# --- DEMO DATA (Hardcoded for browsing) ---
DEMO_HOTELS = [
    { "id": 1, "name": "The Grand Plaza", "location": "New York, USA", "price": 24070, "room_type": "Suite" },
    { "id": 2, "name": "Sunset Bungalow", "location": "Bali, Indonesia", "price": 14940, "room_type": "Deluxe" },
    { "id": 3, "name": "The City Lofts", "location": "London, UK", "price": 9130, "room_type": "Standard" },
    { "id": 4, "name": "Mountain Retreat", "location": "Aspen, USA", "price": 29050, "room_type": "Family" },
    { "id": 5, "name": "Parisian Charm", "location": "Paris, France", "price": 18260, "room_type": "Deluxe" },
    { "id": 6, "name": "Tokyo Modern", "location": "Tokyo, Japan", "price": 13280, "room_type": "Standard" },
]

# --- HELPER ROUTE: SEED DATA ---
@app.route('/api/init', methods=['GET'])
def seed_data():
    """
    Run this once to populate Firestore with dummy bookings so Login works.
    Visit: https://<your-project-url>/api/init
    """
    bookings_ref = db.collection('bookings')
    
    # Check if we already have data to avoid duplicates
    docs = bookings_ref.limit(1).stream()
    if any(docs):
        return jsonify({"message": "Database already populated."})

    # Create dummy bookings for testing
    dummy_bookings = [
        {
            "name": "Abhijeet Vaidya", 
            "email": "mason.davis456@example.com", 
            "checkin_date": "2025-10-26",
            "checkout_date": "2025-11-02",
            "room_type": "Suite",
            "cancelled": 0,
            "total_paid": 50000,
            "rating": 5.0,
            "country": "Bali, Indonesia",
            "price_per_night": 14940
        },
        {
            "name": "John Doe",
            "email": "john@example.com",
            "checkin_date": "2025-12-01",
            "checkout_date": "2025-12-05",
            "room_type": "Standard",
            "cancelled": 0,
            "total_paid": 30000,
            "rating": 4.0,
            "country": "London, UK",
            "price_per_night": 9130
        }
    ]

    for booking in dummy_bookings:
        bookings_ref.add(booking)

    return jsonify({"success": True, "message": "Dummy data created in Firestore."})


# --- API ROUTES ---

@app.route('/api/login', methods=['POST'])
def login():
    """
    Checks if the email exists in the Firestore 'bookings' collection.
    """
    try:
        data = request.json
        email = data.get('email', '').strip()
        if not email:
            return jsonify({"success": False, "message": "Email is required."}), 400

        # Query Firestore for a booking with this email
        bookings_ref = db.collection('bookings')
        query = bookings_ref.where('email', '==', email).limit(1).stream()
        
        user_found = None
        for doc in query:
            user_found = doc.to_dict()
            break

        if user_found:
            return jsonify({"success": True, "name": user_found['name']})
        else:
            return jsonify({"success": False, "message": "Email not found. (Did you run /api/init?)"}), 404

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/hotel/login', methods=['POST'])
def hotel_login():
    """
    Simulates hotel login by reusing the user login logic for this demo.
    """
    return login() 

@app.route('/api/hotels', methods=['GET'])
def get_hotels():
    """Returns the hardcoded list of demo hotels."""
    return jsonify(DEMO_HOTELS)

@app.route('/api/hotel/details', methods=['GET'])
def get_hotel_details():
    """Returns details for a specific hotel ID."""
    try:
        hotel_id = request.args.get('id', type=int)
        hotel = next((h for h in DEMO_HOTELS if h["id"] == hotel_id), None)
        if hotel:
            return jsonify(hotel)
        else:
            return jsonify({"error": "Hotel not found."}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/hotel/dashboard')
def hotel_dashboard():
    """Returns data for the Hotel Partner Dashboard."""
    try:
        bookings_ref = db.collection('bookings')
        
        # 1. Recent Bookings (Active only)
        # Note: In a real app, you might need a composite index for ordering by date.
        # We will just grab 5 for now.
        docs = bookings_ref.where('cancelled', '==', 0).limit(5).stream()
        recent_bookings = []
        for doc in docs:
            d = doc.to_dict()
            recent_bookings.append(d)

        # 2. Revenue & Occupancy (Simulated based on static demo data)
        dashboard_data = {
            "recent_bookings": recent_bookings,
            "revenue": {
                "this_month_revenue": 1037500,
                "last_month_revenue": 913000
            },
            "occupancy_rate": 75,
            "recent_activity": [
                {"activity_type": "Payment from Abhijeet", "total_paid": 24000}
            ]
        }
        return jsonify(dashboard_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/user/dashboard')
def user_dashboard():
    """Returns trips and info for the User Dashboard."""
    try:
        user_name = request.args.get('user_name')
        if not user_name:
            return jsonify({"error": "user_name parameter is required."}), 400
        
        bookings_ref = db.collection('bookings')
        
        # Query bookings for this name
        query = bookings_ref.where('name', '==', user_name).where('cancelled', '==', 0).stream()
        
        all_trips = []
        user_email = "N/A"
        for doc in query:
            d = doc.to_dict()
            user_email = d.get('email', user_email)
            all_trips.append(d)
        
        # Sort manually in Python (Most recent date first)
        all_trips.sort(key=lambda x: x.get('checkin_date', ''), reverse=True)

        current_trip = all_trips[0] if all_trips else None
        upcoming_trips = all_trips[1:] if len(all_trips) > 1 else []

        dashboard_data = {
            "personal_info": {"name": user_name, "email": user_email},
            "payment_methods": [{"type": "Credit Card", "last4": "1234", "expires": "08/26"}],
            "current_trip": current_trip,
            "upcoming_trips": upcoming_trips
        }
        return jsonify(dashboard_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- FIREBASE ENTRY POINT ---
# This matches the "function": "app_function" in your firebase.json
@https_fn.on_request()
def app_function(req: https_fn.Request) -> https_fn.Response:
    with app.request_context(req.environ):
        return app.full_dispatch_request()