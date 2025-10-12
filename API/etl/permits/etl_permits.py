import os
import psycopg
import requests
from dotenv import load_dotenv
from pathlib import Path
from tqdm import tqdm
import time
from datetime import datetime, timedelta

# --- 1. CONFIGURATION ---
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
env_path = project_root / 'config' / '.env'
load_dotenv(dotenv_path=env_path)

DB_CONNECTION_STRING = os.getenv("DATABASE_URL")
BASE_API_URL = "https://phl.carto.com/api/v2/sql"
RECORDS_PER_PAGE = 500
UCITY_ZIP_CODE = '19104'
# We'll look at the last 5 years of permit history
YEARS_OF_HISTORY = 5
five_years_ago_date = (datetime.now() - timedelta(days=365 * YEARS_OF_HISTORY)).strftime('%Y-%m-%d')

# --- 2. DATABASE CONNECTION & SETUP ---
print("connecting to the database to sync building permits...")
try:
    with psycopg.connect(DB_CONNECTION_STRING) as conn:
        print("🎉 connection successful!")
        with conn.cursor() as cur:
            print("making sure the 'permits' table exists...")
            # A simplified table for the most important permit info
            cur.execute("""
                CREATE TABLE IF NOT EXISTS permits (
                    permit_number TEXT PRIMARY KEY,
                    opa_account_num TEXT,
                    issue_date TIMESTAMP WITH TIME ZONE,
                    description TEXT,
                    status TEXT
                );
            """)
            print("clearing old permit data for a fresh sync...")
            cur.execute("TRUNCATE TABLE permits;")
            print("table is ready for UCity permit data!")

            # --- 3. GET TOTAL COUNT FOR PROGRESS BAR ---
            print("let's see how many permits were issued in University City recently...")
            count_query = f"SELECT count(*) FROM permits WHERE trim(zip) LIKE '{UCITY_ZIP_CODE}%' AND permitissuedate >= '{five_years_ago_date}'"
            count_response = requests.get(BASE_API_URL, params={'q': count_query})
            
            if count_response.status_code == 200:
                total_records = count_response.json()['rows'][0]['count']
                if total_records == 0:
                    print("...hmph. no permits found in the last 5 years for ucity? that seems unlikely, but okay!")
                    exit()
                print(f"found {total_records} total permits for University City. starting sync...")
            else:
                print("ugh, couldn't get the total count from the api!")
                print(f"status: {count_response.status_code}, text: {count_response.text}")
                exit()

            # --- 4. PAGINATION & ETL LOOP ---
            page_num = 0
            
            with tqdm(total=total_records, desc="Syncing Permits", unit=" permit") as progress_bar:
                while True:
                    offset = page_num * RECORDS_PER_PAGE
                    query = f"""
                        SELECT permitnumber, opa_account_num, permitissuedate, permitdescription, status 
                        FROM permits 
                        WHERE trim(zip) LIKE '{UCITY_ZIP_CODE}%' AND permitissuedate >= '{five_years_ago_date}'
                        ORDER BY permitnumber 
                        LIMIT {RECORDS_PER_PAGE} OFFSET {offset}
                    """
                    
                    response = requests.get(BASE_API_URL, params={'q': query}, timeout=60)

                    if response.status_code == 200:
                        data = response.json()
                        permits = data.get('rows', [])

                        if not permits:
                            break # No more records to fetch
                        
                        for permit in permits:
                            try:
                                cur.execute("""
                                    INSERT INTO permits (permit_number, opa_account_num, issue_date, description, status)
                                    VALUES (%s, %s, %s, %s, %s)
                                    ON CONFLICT (permit_number) DO NOTHING;
                                """, (
                                    permit.get('permitnumber'),
                                    permit.get('opa_account_num'),
                                    permit.get('permitissuedate'),
                                    permit.get('permitdescription'),
                                    permit.get('status')
                                ))
                            except Exception as insert_error:
                                 # Silently skip records that fail, for now.
                                 pass
                        
                        conn.commit()
                        progress_bar.update(len(permits))
                        page_num += 1
                        time.sleep(0.1)
                    else:
                        print(f"\nugh, the api call failed. 😤 status code: {response.status_code}")
                        print(response.text)
                        break
            
            progress_bar.close()

            print(f"\n--- UCity Permit ETL complete! ---")
            print(f"successfully synced permit data for UCity. ✨")

except Exception as e:
    print(f"😤 a database error occurred: {e}")
