import os
import psycopg
import requests
from dotenv import load_dotenv
from pathlib import Path
from tqdm import tqdm
import time

# --- 1. CONFIGURATION ---
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
env_path = project_root / 'config' / '.env'
load_dotenv(dotenv_path=env_path)

DB_CONNECTION_STRING = os.getenv("DATABASE_URL")
BASE_API_URL = "https://phl.carto.com/api/v2/sql"
RECORDS_PER_PAGE = 500
UCITY_ZIP_CODE = '19104'

# --- 2. DATABASE CONNECTION & SETUP ---
print("connecting to the database to sync violations...")
try:
    with psycopg.connect(DB_CONNECTION_STRING) as conn:
        print("🎉 connection successful!")
        with conn.cursor() as cur:
            
            print("making sure the 'violations' table exists...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS violations (
                    violation_number TEXT PRIMARY KEY,
                    case_number TEXT,
                    case_priority_desc TEXT,
                    violation_date TIMESTAMP WITH TIME ZONE,
                    violation_code TEXT,
                    violation_code_title TEXT,
                    violation_status TEXT,
                    violation_resolution_date TIMESTAMP WITH TIME ZONE,
                    violation_resolution_code TEXT,
                    case_type TEXT,
                    case_status TEXT,
                    opa_account_num TEXT,
                    address TEXT,
                    zip TEXT,
                    opa_owner TEXT
                );
            """)
            print("clearing old violation data for a fresh sync...")
            cur.execute("TRUNCATE TABLE violations;")
            print("table is ready for UCity violation data!")

            # --- 3. GET TOTAL COUNT FOR PROGRESS BAR ---
            print("let's see how many violations are in University City...")
            count_query = f"SELECT count(*) FROM violations WHERE trim(zip) LIKE '{UCITY_ZIP_CODE}%'"
            count_response = requests.get(BASE_API_URL, params={'q': count_query})
            
            if count_response.status_code == 200:
                total_records = count_response.json()['rows'][0]['count']
                if total_records == 0:
                    print("...hmph. the api still says zero records match. are we sure this data exists for ucity? how rude!")
                    exit()
                print(f"found {total_records} total violations for University City. starting sync...")
            else:
                print("ugh, couldn't get the total count from the api. can't proceed!")
                print(f"status: {count_response.status_code}, text: {count_response.text}")
                exit()

            # --- 4. PAGINATION & ETL LOOP ---
            page_num = 0
            total_inserted_count = 0
            
            with tqdm(total=total_records, desc="Syncing Violations", unit=" violation") as progress_bar:
                while total_inserted_count < total_records:
                    offset = page_num * RECORDS_PER_PAGE
                    query = f"SELECT casenumber, caseprioritydesc, violationnumber, violationdate, violationcode, violationcodetitle, violationstatus, violationresolutiondate, violationresolutioncode, casetype, casestatus, opa_account_num, address, zip, opa_owner FROM violations WHERE trim(zip) LIKE '{UCITY_ZIP_CODE}%' ORDER BY violationnumber LIMIT {RECORDS_PER_PAGE} OFFSET {offset}"
                    
                    response = requests.get(BASE_API_URL, params={'q': query}, timeout=60)

                    if response.status_code == 200:
                        data = response.json()
                        violations = data.get('rows', [])

                        if not violations:
                            break
                        
                        page_insert_count = 0
                        for vio in violations:
                            if not vio.get('violationnumber'):
                                continue
                            
                            try:
                                cur.execute("""
                                    INSERT INTO violations (
                                        violation_number, case_number, case_priority_desc,
                                        violation_date, violation_code, violation_code_title,
                                        violation_status, violation_resolution_date, 
                                        violation_resolution_code, case_type, case_status,
                                        opa_account_num, address, zip, opa_owner
                                    )
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (violation_number) DO NOTHING;
                                """, (
                                    vio.get('violationnumber'),
                                    vio.get('casenumber'),
                                    vio.get('caseprioritydesc'),
                                    vio.get('violationdate'),
                                    vio.get('violationcode'),
                                    vio.get('violationcodetitle'),
                                    vio.get('violationstatus'),
                                    vio.get('violationresolutiondate'),
                                    vio.get('violationresolutioncode'),
                                    vio.get('casetype'),
                                    vio.get('casestatus'),
                                    vio.get('opa_account_num'),
                                    vio.get('address'),
                                    vio.get('zip'),
                                    vio.get('opa_owner')
                                ))
                                page_insert_count += cur.rowcount
                            except Exception as insert_error:
                                print("\n😤 HEY! The database rejected this record! Here's why:")
                                print("Error:", insert_error)
                                print("Problem Record:", vio)
                                raise
                        
                        total_inserted_count += page_insert_count
                        progress_bar.update(len(violations))
                        page_num += 1
                        time.sleep(0.1)
                    else:
                        print(f"\nugh, the api call failed. 😤 status code: {response.status_code}")
                        print(response.text)
                        break
            
            conn.commit()
            if progress_bar.n < total_records:
                progress_bar.update(total_records - progress_bar.n)
            progress_bar.close()

            print(f"\n--- UCity Violations ETL complete! ---")
            print(f"successfully inserted a grand total of {total_inserted_count} UCity violations. ✨")

except Exception as e:
    print(f"😤 a database error occurred: {e}")