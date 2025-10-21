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
print("connecting to the database to sync permits...")
try:
    with psycopg.connect(DB_CONNECTION_STRING) as conn:
        print("🎉 connection successful!")
        with conn.cursor() as cur:
            
            print("making sure the 'permits' table exists...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS permits (
                    permit_number TEXT PRIMARY KEY,
                    permit_type TEXT,
                    permit_description TEXT,
                    commercial_or_residential TEXT,
                    type_of_work TEXT,
                    approved_scope_of_work TEXT,
                    permit_issue_date TIMESTAMP WITH TIME ZONE,
                    status TEXT,
                    applicant_type TEXT,
                    contractor_name TEXT,
                    contractor_address_1 TEXT,
                    contractor_address_2 TEXT,
                    opa_account_num TEXT,
                    address TEXT,
                    unit_type TEXT,
                    unit_num TEXT,
                    zip TEXT,
                    opa_owner TEXT,
                    permit_completed_date TIMESTAMP WITH TIME ZONE
                );
            """)
            print("clearing old permit data for a fresh sync...")
            cur.execute("TRUNCATE TABLE permits;")
            print("table is ready for UCity permit data!")

            # --- 3. GET TOTAL COUNT FOR PROGRESS BAR ---
            print("let's see how many permits are in University City...")
            count_query = f"SELECT count(*) FROM permits WHERE trim(zip) LIKE '{UCITY_ZIP_CODE}%'"
            count_response = requests.get(BASE_API_URL, params={'q': count_query})
            
            if count_response.status_code == 200:
                total_records = count_response.json()['rows'][0]['count']
                if total_records == 0:
                    print("...hmph. the api still says zero records match. are we sure this data exists for ucity? how rude!")
                    exit()
                print(f"found {total_records} total permits for University City. starting sync...")
            else:
                print("ugh, couldn't get the total count from the api. can't proceed!")
                print(f"status: {count_response.status_code}, text: {count_response.text}")
                exit()

            # --- 4. PAGINATION & ETL LOOP ---
            page_num = 0
            total_inserted_count = 0
            
            with tqdm(total=total_records, desc="Syncing Permits", unit=" permit") as progress_bar:
                while total_inserted_count < total_records:
                    offset = page_num * RECORDS_PER_PAGE
                    query = f"SELECT permitnumber, permittype, permitdescription, commercialorresidential, typeofwork, approvedscopeofwork, permitissuedate, status, applicanttype, contractorname, contractoraddress1, contractoraddress2, opa_account_num, address, unit_type, unit_num, zip, opa_owner, permitcompleteddate FROM permits WHERE trim(zip) LIKE '{UCITY_ZIP_CODE}%' ORDER BY permitnumber LIMIT {RECORDS_PER_PAGE} OFFSET {offset}"
                    
                    response = requests.get(BASE_API_URL, params={'q': query}, timeout=60)

                    if response.status_code == 200:
                        data = response.json()
                        permits = data.get('rows', [])

                        if not permits:
                            break
                        
                        page_insert_count = 0
                        for pmt in permits:
                            if not pmt.get('permitnumber'):
                                continue
                            
                            try:
                                cur.execute("""
                                    INSERT INTO permits (
                                        permit_number, permit_type, permit_description,
                                        commercial_or_residential, type_of_work,
                                        approved_scope_of_work, permit_issue_date,
                                        status, applicant_type, contractor_name,
                                        contractor_address_1, contractor_address_2,
                                        opa_account_num, address, unit_type, unit_num,
                                        zip, opa_owner, permit_completed_date
                                    )
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (permit_number) DO NOTHING;
                                """, (
                                    pmt.get('permitnumber'),
                                    pmt.get('permittype'),
                                    pmt.get('permitdescription'),
                                    pmt.get('commercialorresidential'),
                                    pmt.get('typeofwork'),
                                    pmt.get('approvedscopeofwork'),
                                    pmt.get('permitissuedate'),
                                    pmt.get('status'),
                                    pmt.get('applicanttype'),
                                    pmt.get('contractorname'),
                                    pmt.get('contractoraddress1'),
                                    pmt.get('contractoraddress2'),
                                    pmt.get('opa_account_num'),
                                    pmt.get('address'),
                                    pmt.get('unit_type'),
                                    pmt.get('unit_num'),
                                    pmt.get('zip'),
                                    pmt.get('opa_owner'),
                                    pmt.get('permitcompleteddate')
                                ))
                                page_insert_count += cur.rowcount
                            except Exception as insert_error:
                                print("\n😤 HEY! The database rejected this record! Here's why:")
                                print("Error:", insert_error)
                                print("Problem Record:", pmt)
                                raise
                        
                        total_inserted_count += page_insert_count
                        progress_bar.update(len(permits))
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

            print(f"\n--- UCity Permits ETL complete! ---")
            print(f"successfully inserted a grand total of {total_inserted_count} UCity permits. ✨")

except Exception as e:
    print(f"😤 a database error occurred: {e}")