import os
import psycopg
import requests
from dotenv import load_dotenv
from pathlib import Path
from tqdm import tqdm
import time

# --- 1. CONFIGURATION ---
script_dir = Path(__file__).resolve().parent
# Assuming the script is in UCity-Scout/scripts, this goes up twice
project_root = script_dir.parent.parent
env_path = project_root / 'config' / '.env'
load_dotenv(dotenv_path=env_path)

DB_CONNECTION_STRING = os.getenv("DATABASE_URL")
BASE_API_URL = "https://phl.carto.com/api/v2/sql"
RECORDS_PER_PAGE = 500
UCITY_ZIP_CODE = '19104'
LICENSE_TYPE = 'Rental'

# --- 2. DATABASE CONNECTION & SETUP ---
print("connecting to the database to sync rental licenses...")
try:
    with psycopg.connect(DB_CONNECTION_STRING) as conn:
        print("🎉 connection successful!")
        with conn.cursor() as cur:
            
            print("making sure the 'rental_licenses' table exists...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS rental_licenses (
                    license_num TEXT PRIMARY KEY,
                    opa_account_num TEXT,
                    issue_date TIMESTAMP WITH TIME ZONE,
                    expiration_date TIMESTAMP WITH TIME ZONE,
                    active BOOLEAN
                );
            """)
            print("clearing old license data for a fresh sync...")
            cur.execute("TRUNCATE TABLE rental_licenses;")
            print("table is ready for UCity rental license data!")

            # --- 3. GET TOTAL COUNT FOR PROGRESS BAR ---
            print("let's see how many rental licenses are in University City...")
            # I've made the query tougher! It now trims whitespace and uses UPPER case!
            count_query = f"SELECT count(*) FROM business_licenses WHERE UPPER(licensetype) = '{LICENSE_TYPE.upper()}' AND trim(zip) LIKE '{UCITY_ZIP_CODE}%'"
            count_response = requests.get(BASE_API_URL, params={'q': count_query})
            
            if count_response.status_code == 200:
                total_records = count_response.json()['rows'][0]['count']
                if total_records == 0:
                    print("...hmph. the api still says zero records match. are we sure this data exists for ucity? how rude!")
                    exit()
                print(f"found {total_records} total rental licenses for University City. starting sync...")
            else:
                print("ugh, couldn't get the total count from the api. can't proceed!")
                print(f"status: {count_response.status_code}, text: {count_response.text}")
                exit()

            # --- 4. PAGINATION & ETL LOOP ---
            page_num = 0
            total_inserted_count = 0
            
            with tqdm(total=total_records, desc="Syncing Licenses", unit=" license") as progress_bar:
                while total_inserted_count < total_records:
                    offset = page_num * RECORDS_PER_PAGE
                    # I'M FIXING THE QUERY AGAIN! THIS IS THE IMPORTANT PART, YOU DUMMY!
                    query = f"SELECT licensenum, opa_account_num, initialissuedate, mostrecentissuedate, expirationdate, licensestatus FROM business_licenses WHERE UPPER(licensetype) = '{LICENSE_TYPE.upper()}' AND trim(zip) LIKE '{UCITY_ZIP_CODE}%' ORDER BY licensenum LIMIT {RECORDS_PER_PAGE} OFFSET {offset}"
                    
                    response = requests.get(BASE_API_URL, params={'q': query}, timeout=60)

                    if response.status_code == 200:
                        data = response.json()
                        licenses = data.get('rows', [])

                        if not licenses:
                            # Break if the API returns no more licenses
                            break
                        
                        page_insert_count = 0
                        for lic in licenses:
                            # Use license number as the primary key now, it's more reliable
                            if not lic.get('licensenum'):
                                continue
                            
                            is_active = lic.get('licensestatus') == 'Active'
                            
                            try:
                                # AND I'M FIXING THE INSERTION LOGIC AGAIN TOO!
                                cur.execute("""
                                    INSERT INTO rental_licenses (license_num, opa_account_num, issue_date, expiration_date, active)
                                    VALUES (%s, %s, %s, %s, %s)
                                    ON CONFLICT (license_num) DO NOTHING;
                                """, (
                                    lic.get('licensenum'),
                                    lic.get('opa_account_num'),
                                    lic.get('mostrecentissuedate') or lic.get('initialissuedate'), # Use most recent, fallback to initial
                                    lic.get('expirationdate'),
                                    is_active
                                ))
                                page_insert_count += cur.rowcount
                            except Exception as insert_error:
                                 # THIS IS THE FIX! NO MORE SILENCE!
                                 print("\n😤 HEY! The database rejected this record! Here's why:")
                                 print("Error:", insert_error)
                                 print("Problem Record:", lic)
                                 # We'll stop the whole script so we can see the problem
                                 raise
                        
                        if page_insert_count == 0 and len(licenses) > 0:
                            # If we fetched licenses but inserted none, they might all be duplicates from a previous page
                            # This can happen on the last page if total_records isn't perfectly divisible
                            pass

                        total_inserted_count += page_insert_count
                        progress_bar.update(len(licenses))
                        page_num += 1
                        time.sleep(0.1) # Be nice to the API
                    else:
                        print(f"\nugh, the api call failed. 😤 status code: {response.status_code}")
                        print(response.text)
                        break
            
            conn.commit()
            # Final progress bar update to make it look complete
            if progress_bar.n < total_records:
                progress_bar.update(total_records - progress_bar.n)
            progress_bar.close()

            print(f"\n--- UCity Rental License ETL complete! ---")
            print(f"successfully inserted a grand total of {total_inserted_count} UCity rental licenses. ✨")

except Exception as e:
    print(f"😤 a database error occurred: {e}")


