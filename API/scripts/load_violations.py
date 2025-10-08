import os
import psycopg
import requests
import json
from dotenv import load_dotenv

# --- 1. CONFIGURATION ---
# Load secrets from our .env file
load_dotenv()
DB_CONNECTION_STRING = os.getenv("DATABASE_URL")
API_URL = "https://phl.carto.com/api/v2/sql?q=SELECT * FROM violations LIMIT 5"

# --- 2. DATABASE CONNECTION & SETUP ---
print("alright, connecting to the database...")
try:
    # Use 'with' statements for connections and cursors
    # This is important because it handles closing them automatically!
    with psycopg.connect(DB_CONNECTION_STRING) as conn:
        print("🎉 connection successful!")
        with conn.cursor() as cur:
            
            # Create the table if it doesn't already exist.
            # This is a super useful trick so you don't have to run it manually.
            print("making sure the 'violations' table exists...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS violations (
                    id SERIAL PRIMARY KEY,
                    address TEXT,
                    opa_account_num TEXT,
                    violation_date TIMESTAMP,
                    violation_code_title TEXT,
                    violation_status TEXT,
                    case_number TEXT UNIQUE
                );
            """)
            print("table is ready. let's get some data!")

            # --- 3. EXTRACT - Get data from the API ---
            print(f"fetching data from the api: {API_URL}")
            response = requests.get(API_URL)

            if response.status_code == 200:
                print("api data fetched successfully!")
                data = response.json()
                violations = data.get('rows', []) # Use .get for safety

                if not violations:
                    print("hmph. the api gave us data, but there were no 'rows' in it.")
                else:
                    # --- 4. LOAD - Insert data into the database ---
                    print(f"found {len(violations)} violations. loading them into the database...")
                    
                    insert_count = 0
                    for violation in violations:
                        # Using 'ON CONFLICT (case_number) DO NOTHING' is another pro move.
                        # It prevents errors if you try to insert the same violation twice.
                        # We use the 'casenumber' as a unique identifier.
                        try:
                            cur.execute("""
                                INSERT INTO violations (address, opa_account_num, violation_date, violation_code_title, violation_status, case_number)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                ON CONFLICT (case_number) DO NOTHING;
                            """, (
                                violation.get('address'),
                                violation.get('opa_account_num'),
                                violation.get('violationdate'),
                                violation.get('violationcodetitle'),
                                violation.get('violationstatus'),
                                violation.get('casenumber')
                            ))
                            # cur.rowcount tells us if a row was actually inserted (1) or ignored (0)
                            insert_count += cur.rowcount
                        except Exception as insert_error:
                             print(f"couldn't insert case {violation.get('casenumber')}. error: {insert_error}")

                    # VERY IMPORTANT: This saves all the changes you made.
                    conn.commit()
                    print(f"done! successfully inserted {insert_count} new records.")

            else:
                print(f"ugh, the api call failed. 😤 status code: {response.status_code}")

except Exception as e:
    print(f"😤 a database error occurred: {e}")
