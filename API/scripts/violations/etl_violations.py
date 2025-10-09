import os
import psycopg
import requests
import json
from dotenv import load_dotenv
from pathlib import Path

# --- 1. CONFIGURATION ---
# Load secrets from our .env file
# This smarter path logic will work from anywhere!
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
env_path = project_root / 'config' / '.env'
load_dotenv(dotenv_path=env_path)
DB_CONNECTION_STRING = os.getenv("DATABASE_URL")
# The base URL without any query parameters
BASE_API_URL = "https://phl.carto.com/api/v2/sql"
RECORDS_PER_PAGE = 500 # How many records to fetch at a time

# --- 2. DATABASE CONNECTION & SETUP ---
print("alright, connecting to the database...")
try:
    with psycopg.connect(DB_CONNECTION_STRING) as conn:
        print("🎉 connection successful!")
        with conn.cursor() as cur:
            
            print("making sure the 'violations' table exists with the CORRECT schema...")
            # I've updated the UNIQUE constraint to be on 'violation_number' which is actually unique!
            cur.execute("""
                CREATE TABLE IF NOT EXISTS violations (
                    id SERIAL PRIMARY KEY,
                    address TEXT,
                    opa_account_num TEXT,
                    violation_date TIMESTAMPTZ,
                    violation_code_title TEXT,
                    violation_status TEXT,
                    case_number TEXT,
                    violation_number TEXT UNIQUE
                );
            """)
            print("table is ready. let's get all the violation data!")

            # --- 3. PAGINATION & ETL LOOP ---
            page_num = 0
            total_inserted_count = 0
            
            while True:
                offset = page_num * RECORDS_PER_PAGE
                query = f"SELECT * FROM violations ORDER BY objectid LIMIT {RECORDS_PER_PAGE} OFFSET {offset}"
                
                print(f"\nfetching page {page_num + 1} (records {offset} to {offset + RECORDS_PER_PAGE})...")
                
                response = requests.get(BASE_API_URL, params={'q': query})

                if response.status_code == 200:
                    data = response.json()
                    violations = data.get('rows', [])

                    if not violations:
                        print("no more records to fetch. we're done!")
                        break
                    
                    print(f"found {len(violations)} violations on this page. loading into database...")
                    page_insert_count = 0
                    for violation in violations:
                        try:
                            # Now we insert the violation_number and use it for conflict detection!
                            cur.execute("""
                                INSERT INTO violations (address, opa_account_num, violation_date, violation_code_title, violation_status, case_number, violation_number)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (violation_number) DO NOTHING;
                            """, (
                                violation.get('address'),
                                violation.get('opa_account_num'),
                                violation.get('violationdate'),
                                violation.get('violationcodetitle'),
                                violation.get('violationstatus'),
                                violation.get('casenumber'),
                                violation.get('violationnumber')
                            ))
                            page_insert_count += cur.rowcount
                        except Exception as insert_error:
                             print(f"couldn't insert violation {violation.get('violationnumber')}. error: {insert_error}")

                    total_inserted_count += page_insert_count
                    print(f"inserted {page_insert_count} new records from this page.")
                    page_num += 1

                else:
                    print(f"ugh, the api call failed on page {page_num + 1}. 😤 status code: {response.status_code}")
                    print(response.text)
                    break
            
            conn.commit()
            print(f"\n--- ETL complete! ---")
            print(f"successfully inserted a grand total of {total_inserted_count} new records. ✨")

except Exception as e:
    print(f"😤 a database error occurred: {e}")

