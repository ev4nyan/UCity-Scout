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
print("connecting to the database to sync real estate tax delinquencies...")
try:
    with psycopg.connect(DB_CONNECTION_STRING) as conn:
        print("🎉 connection successful!")
        with conn.cursor() as cur:

            print("making sure the 'tax_balances' table exists...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tax_balances (
                    opa_number TEXT PRIMARY KEY,
                    owner TEXT,
                    street_address TEXT,
                    zip_code TEXT,
                    principal_due NUMERIC,
                    penalty_due NUMERIC,
                    interest_due NUMERIC,
                    other_charges_due NUMERIC,
                    total_due NUMERIC,
                    num_years_owed INTEGER,
                    most_recent_year_owed INTEGER,
                    oldest_year_owed INTEGER,
                    most_recent_payment_date TIMESTAMP WITH TIME ZONE,
                    is_actionable BOOLEAN,
                    payment_agreement BOOLEAN,
                    sheriff_sale TEXT,
                    bankruptcy BOOLEAN,
                    building_category TEXT
                );
            """)
            print("clearing old tax data for a fresh sync...")
            cur.execute("TRUNCATE TABLE tax_balances;")
            print("table is ready for UCity tax delinquency data!")

            # --- 3. GET TOTAL COUNT FOR PROGRESS BAR ---
            print("let's see how many tax delinquencies are in University City...")
            count_query = f"SELECT count(*) FROM real_estate_tax_delinquencies WHERE trim(zip_code) LIKE '{UCITY_ZIP_CODE}%'"
            count_response = requests.get(BASE_API_URL, params={'q': count_query})

            if count_response.status_code == 200:
                total_records = count_response.json()['rows'][0]['count']
                if total_records == 0:
                    print("...hmph. the api still says zero records match. are we sure this data exists for ucity? how rude!")
                    exit()
                print(f"found {total_records} total tax delinquencies for University City. starting sync...")
            else:
                print("ugh, couldn't get the total count from the api. can't proceed!")
                print(f"status: {count_response.status_code}, text: {count_response.text}")
                exit()

            # --- 4. PAGINATION & ETL LOOP ---
            page_num = 0
            total_inserted_count = 0

            with tqdm(total=total_records, desc="Syncing Tax Delinquencies", unit=" record") as progress_bar:
                while total_inserted_count < total_records:
                    offset = page_num * RECORDS_PER_PAGE
                    query = f"SELECT opa_number, owner, street_address, zip_code, principal_due, penalty_due, interest_due, other_charges_due, total_due, num_years_owed, most_recent_year_owed, oldest_year_owed, most_recent_payment_date, is_actionable, payment_agreement, sheriff_sale, bankruptcy, building_category FROM real_estate_tax_delinquencies WHERE trim(zip_code) LIKE '{UCITY_ZIP_CODE}%' ORDER BY opa_number LIMIT {RECORDS_PER_PAGE} OFFSET {offset}"

                    response = requests.get(BASE_API_URL, params={'q': query}, timeout=60)

                    if response.status_code == 200:
                        data = response.json()
                        tax_records = data.get('rows', [])

                        if not tax_records:
                            break

                        page_insert_count = 0
                        for tax in tax_records:
                            if not tax.get('opa_number'):
                                continue

                            try:
                                cur.execute("""
                                    INSERT INTO tax_balances (
                                        opa_number, owner, street_address, zip_code,
                                        principal_due, penalty_due, interest_due,
                                        other_charges_due, total_due, num_years_owed,
                                        most_recent_year_owed, oldest_year_owed,
                                        most_recent_payment_date, is_actionable,
                                        payment_agreement, sheriff_sale, bankruptcy,
                                        building_category
                                    )
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (opa_number) DO NOTHING;
                                """, (
                                    tax.get('opa_number'),
                                    tax.get('owner'),
                                    tax.get('street_address'),
                                    tax.get('zip_code'),
                                    tax.get('principal_due'),
                                    tax.get('penalty_due'),
                                    tax.get('interest_due'),
                                    tax.get('other_charges_due'),
                                    tax.get('total_due'),
                                    tax.get('num_years_owed'),
                                    tax.get('most_recent_year_owed'),
                                    tax.get('oldest_year_owed'),
                                    tax.get('most_recent_payment_date') or None,
                                    tax.get('is_actionable', '').lower() == 'true' if tax.get('is_actionable') else False,
                                    tax.get('payment_agreement', '').lower() == 'true' if tax.get('payment_agreement') else False,
                                    tax.get('sheriff_sale'),
                                    tax.get('bankruptcy', '').lower() == 'true' if tax.get('bankruptcy') else False,
                                    tax.get('building_category')
                                ))
                                page_insert_count += cur.rowcount
                            except Exception as insert_error:
                                print("\n😤 HEY! The database rejected this record! Here's why:")
                                print("Error:", insert_error)
                                print("Problem Record:", tax)
                                raise

                        total_inserted_count += page_insert_count
                        progress_bar.update(len(tax_records))
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

            print(f"\n--- UCity Tax Delinquencies ETL complete! ---")
            print(f"successfully inserted a grand total of {total_inserted_count} UCity tax delinquency records. ✨")

except Exception as e:
    print(f"😤 a database error occurred: {e}")