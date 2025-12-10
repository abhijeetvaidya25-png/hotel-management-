import csv
import sqlite3
import os

# --- New, more robust path logic ---
# Get the absolute path to the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Join the script's directory path with the filenames
# This ensures the script finds the files, regardless of where you run it from
DB_NAME = os.path.join(SCRIPT_DIR, 'stayease.db')

# --- FIX: Changed this to the new, clean CSV filename ---
CSV_NAME = os.path.join(SCRIPT_DIR, 'hotel_bookings_200_new.csv')
# --- END FIX ---


def create_database():
    """Creates the SQLite database and the bookings table."""
    # Delete old database file if it exists
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        print(f"Removed old database '{DB_NAME}'.")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Create the bookings table schema based on the CSV headers
    # This schema MUST match the columns in 'hotel_bookings_200_new.csv'
    cursor.execute('''
    CREATE TABLE bookings (
        booking_id TEXT PRIMARY KEY,
        name TEXT,
        age INTEGER,
        gender TEXT,
        country TEXT,
        email TEXT,
        phone TEXT,
        booking_date TEXT,
        checkin_date TEXT,
        checkout_date TEXT,
        days_stayed INTEGER,
        number_of_guests INTEGER,
        room_type TEXT,
        price_per_night REAL,
        promo_code TEXT,
        discount_pct REAL,
        subtotal REAL,
        total_paid REAL,
        payment_method TEXT,
        booking_channel TEXT,
        special_requests TEXT,
        repeat_guest INTEGER,
        cancelled INTEGER,
        rating REAL,
        review TEXT
    )
    ''')
    print("Database and 'bookings' table created successfully.")
    return conn

def import_csv_data(conn):
    """Imports data from the CSV file into the bookings table."""
    
    try:
        # Use 'utf-8-sig' as a safeguard, even though the new file is clean.
        # This prevents the 'ï»¿' (BOM) error.
        with open(CSV_NAME, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            bookings_to_insert = []
            for row in reader:
                # Convert 'True'/'False' strings to 1/0 for boolean columns
                # Our new data uses "TRUE"/"FALSE"
                repeat_guest = 1 if row['repeat_guest'].strip().upper() == 'TRUE' else 0
                cancelled = 1 if row['cancelled'].strip().upper() == 'TRUE' else 0
                
                # Use strip() as a safeguard, even though the new file is clean.
                bookings_to_insert.append((
                    row['booking_id'].strip(), row['name'].strip(), int(row['age']), row['gender'].strip(),
                    row['country'].strip(), row['email'].strip(), row['phone'].strip(), row['booking_date'].strip(),
                    row['checkin_date'].strip(), row['checkout_date'].strip(), int(row['days_stayed']),
                    int(row['number_of_guests']), row['room_type'].strip(), float(row['price_per_night']),
                    row['promo_code'].strip(), float(row['discount_pct']), float(row['subtotal']),
                    float(row['total_paid']), row['payment_method'].strip(), row['booking_channel'].strip(),
                    row['special_requests'].strip(), repeat_guest, cancelled, float(row['rating']),
                    row['review'].strip()
                ))

            # Use executemany for efficient bulk insertion
            cursor = conn.cursor()
            cursor.executemany('''
            INSERT INTO bookings (
                booking_id, name, age, gender, country, email, phone,
                booking_date, checkin_date, checkout_date, days_stayed,
                number_of_guests, room_type, price_per_night, promo_code,
                discount_pct, subtotal, total_paid, payment_method,
                booking_channel, special_requests, repeat_guest, cancelled,
                rating, review
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', bookings_to_insert)
            
            conn.commit()
            print(f"Successfully imported {len(bookings_to_insert)} rows from '{CSV_NAME}'.")
            
    except FileNotFoundError:
        print(f"ERROR: The file '{CSV_NAME}' was not found.")
        print("Please make sure it's in the same directory as this script.")
        conn.rollback()
    except Exception as e:
        print(f"An error occurred during import: {e}")
        conn.rollback()
    finally:
        conn.close()
        print("Database connection closed.")

if __name__ == "__main__":
    # This check ensures the new CSV file exists before trying to import
    if not os.path.exists(CSV_NAME):
        print(f"Error: '{CSV_NAME}' not found.")
        print("Please make sure your new CSV file is in the same folder as this script.")
    else:
        db_conn = create_database()
        import_csv_data(db_conn)