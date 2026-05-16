import os
import psycopg
from dotenv import load_dotenv
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS

# --- 1. CONFIGURATION ---
# Load secrets from our .env file, just like our ETL scripts!
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
env_path = project_root / 'config' / '.env'
load_dotenv(dotenv_path=env_path)

DB_CONNECTION_STRING = os.getenv("DATABASE_URL")

# --- 2. FLASK APP SETUP ---
# This is where we create our app! So exciting!
app = Flask(__name__)
# This is a boring but important security thing. It lets our future React app talk to our backend.
CORS(app) 

# A simple little function to connect to our database. Hmph.
def get_db_connection():
    conn = psycopg.connect(DB_CONNECTION_STRING)
    return conn

# --- 3. OUR FIRST API ENDPOINT! ---
# This is the magic phone number: /api/property/<opa_account_num>
@app.route('/api/property/<string:opa_account_num>', methods=['GET'])
def get_property_details(opa_account_num):
    """
    Fetches the complete intelligence dossier for a single property
    using its unique OPA account number. So smart!
    """
    print(f"🕵️‍♀️ received a request for property: {opa_account_num}")
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # We ask our master intelligence table for the file!
            cur.execute(
                "SELECT * FROM property_intelligence WHERE opa_account_num = %s",
                (opa_account_num,)
            )
            
            property_data = cur.fetchone()
            
            if property_data is None:
                # Can't find it? Hmph. Tell them!
                return jsonify({"error": "Property not found in our intelligence database!"}), 404

            # We have to be smart and turn the raw data into a nice dictionary
            # so the frontend knows what it's looking at! I think of everything!
            columns = [desc[0] for desc in cur.description]
            property_dict = dict(zip(columns, property_data))
            
            # Send back the secret dossier! Mission accomplished!
            return jsonify(property_dict)

    except Exception as e:
        print(f"😤 ugh, something broke! error: {e}")
        return jsonify({"error": "An internal error occurred. It's probably your fault."}), 500
    finally:
        if conn:
            conn.close()


# --- 4. ADDRESS SEARCH ENDPOINT ---
# Search properties by partial address string. Finally, a civilized lookup!
@app.route('/api/properties/search', methods=['GET'])
def search_properties_by_address():
    """
    Searches the property_intelligence table by partial address string.
    Case-insensitive. Returns up to 20 matching properties.
    Usage: /api/properties/search?q=market+st
    """
    query_string = request.args.get('q', '').strip()

    if not query_string:
        return jsonify({"error": "Missing required query parameter 'q'."}), 400

    if len(query_string) < 3:
        return jsonify({"error": "Search query must be at least 3 characters."}), 400

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT opa_account_num, address, owner_name,
                       bedrooms, bathrooms, livable_area,
                       risk_level, trustability_score
                FROM property_intelligence
                WHERE address ILIKE %s
                ORDER BY address
                LIMIT 20
                """,
                (f"%{query_string}%",)
            )

            rows = cur.fetchall()

            if not rows:
                return jsonify({"results": [], "count": 0})

            columns = [desc[0] for desc in cur.description]
            results = [dict(zip(columns, row)) for row in rows]

            return jsonify({"results": results, "count": len(results)})

    except Exception as e:
        print(f"😤 search blew up! error: {e}")
        return jsonify({"error": "An internal error occurred during search."}), 500
    finally:
        if conn:
            conn.close()


# This is just so you can run the file directly to test it. Hmph.
if __name__ == '__main__':
    # I'm running it on port 5001 so it doesn't clash with your React app later! See? I think ahead!
    app.run(debug=True, port=5001)
