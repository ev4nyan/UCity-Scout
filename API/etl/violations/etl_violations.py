import os
import psycopg
import requests
import json
from dotenv import load_dotenv
from pathlib import Path
from tqdm import tqdm
from datetime import datetime, timedelta # We need this to do date math!

# --- 1. CONFIGURATION ---
# Load secrets from our .env file
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
env_path = project_root / 'config' / '.env'
load_dotenv(dotenv_path=env_path)

DB_CONNECTION_STRING = os.getenv("DATABASE_URL")
BASE_API_URL = "https://phl.carto.com/api/v2/sql"
RECORDS_PER_PAGE = 500
UCITY_ZIP_CODE = '19104'
# --- The new, brilliant time filter! ---
YEARS_OF_DATA = 5 # Let's only get data from the last 5 years.

# --- 2. DATABASE CONNECTION & SETUP ---
print("alright, connecting to the database...")
try:
    with psycopg.connect(DB_CONNECTION_STRING) as conn:
        print("🎉 connection successful!")
        with conn.cursor() as cur:
            
            print("making sure the 'violations' table exists...")
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
            print("clearing old data to prepare for a fresh, time-filtered sync...")
            cur.execute("TRUNCATE TABLE violations;")
            print("table is ready for relevant, recent UCity data!")

            # --- 3. GET TOTAL COUNT FOR PROGRESS BAR ---
            print("calculating our date range for the last 5 years...")
            five_years_ago = datetime.now() - timedelta(days=YEARS_OF_DATA * 365)
            date_filter_str = five_years_ago.strftime('%Y-%m-%d')
            print(f"ok, we will only fetch violations on or after: {date_filter_str}")
            
            print("let's see how many RECENT records we need to get...")
            # I've added the date filter to the count query!
            count_query = f"SELECT count(*) FROM violations WHERE zip LIKE '{UCITY_ZIP_CODE}%' AND violationdate >= '{date_filter_str}'"
            count_response = requests.get(BASE_API_URL, params={'q': count_query})
            
            if count_response.status_code == 200:
                total_records = count_response.json()['rows'][0]['count']
                print(f"found {total_records} violations in UCity from the last {YEARS_OF_DATA} years. starting sync...")
            else:
                print("ugh, couldn't get the total count from the api. can't proceed!")
                exit()

            # --- 4. PAGINATION & ETL LOOP with Progress Bar ---
            page_num = 0
            total_inserted_count = 0
            
            with tqdm(total=total_records, desc="Syncing Recent Violations", unit=" record") as progress_bar:
                while True:
                    offset = page_num * RECORDS_PER_PAGE
                    # And here is the new, smarter query with the date filter!
                    query = f"SELECT * FROM violations WHERE zip LIKE '{UCITY_ZIP_CODE}%' AND violationdate >= '{date_filter_str}' ORDER BY objectid LIMIT {RECORDS_PER_PAGE} OFFSET {offset}"
                    
                    response = requests.get(BASE_API_URL, params={'q': query})

                    if response.status_code == 200:
                        data = response.json()
                        violations = data.get('rows', [])

                        if not violations:
                            if progress_bar.n < total_records:
                                progress_bar.update(total_records - progress_bar.n)
                            break
                        
                        page_insert_count = 0
                        for violation in violations:
                            try:
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
                                 pass

                        total_inserted_count += page_insert_count
                        progress_bar.update(len(violations))
                        page_num += 1

                    else:
                        print(f"\nugh, the api call failed. 😤 status code: {response.status_code}")
                        print(response.text)
                        break
            
            conn.commit()
            print(f"\n--- UCity ETL complete! ---")
            print(f"successfully inserted a grand total of {total_inserted_count} RECENT UCity records. ✨")

except Exception as e:
    print(f"😤 a database error occurred: {e}")

