import os
import psycopg
import requests
import json
from dotenv import load_dotenv
from pathlib import Path
from tqdm import tqdm

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

# --- 2. DATABASE CONNECTION & SETUP ---
print("alright, connecting to the database to sync properties...")
try:
    with psycopg.connect(DB_CONNECTION_STRING) as conn:
        print("🎉 connection successful!")
        with conn.cursor() as cur:
            
            print("making sure the 'properties' table exists...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS properties (
                    opa_account_num TEXT PRIMARY KEY,
                    address TEXT,
                    owner_name TEXT,
                    zip_code TEXT,
                    market_value NUMERIC,
                    square_footage INTEGER
                );
            """)
            print("clearing old property data to prepare for a fresh sync...")
            cur.execute("TRUNCATE TABLE properties;")
            print("table is ready for UCity property data!")

            # --- 3. GET TOTAL COUNT FOR PROGRESS BAR ---
            print("let's see how many properties are in University City...")
            # Here is the fix! We will TRIM the whitespace from the zip_code!
            count_query = f"SELECT count(*) FROM opa_properties_public WHERE trim(zip_code) LIKE '{UCITY_ZIP_CODE}%'"
            count_response = requests.get(BASE_API_URL, params={'q': count_query})
            
            if count_response.status_code == 200:
                total_records = count_response.json()['rows'][0]['count']
                if total_records == 0:
                    print("😤 still got 0 records... are you SURE 19104 is the right zip code? maybe try another one close by?")
                    exit()
                print(f"found {total_records} total properties for University City. starting sync...")
            else:
                print("ugh, couldn't get the total count from the api. can't proceed!")
                exit()

            # --- 4. PAGINATION & ETL LOOP with Progress Bar ---
            page_num = 0
            total_inserted_count = 0
            
            with tqdm(total=total_records, desc="Syncing Properties", unit=" property") as progress_bar:
                while True:
                    offset = page_num * RECORDS_PER_PAGE
                    # And here is the fix again! TRIM() to the rescue!
                    query = f"SELECT parcel_number, location, owner_1, zip_code, market_value, total_livable_area FROM opa_properties_public WHERE trim(zip_code) LIKE '{UCITY_ZIP_CODE}%' ORDER BY parcel_number LIMIT {RECORDS_PER_PAGE} OFFSET {offset}"
                    
                    response = requests.get(BASE_API_URL, params={'q': query})

                    if response.status_code == 200:
                        data = response.json()
                        properties = data.get('rows', [])

                        if not properties:
                            if progress_bar.n < total_records:
                                progress_bar.update(total_records - progress_bar.n)
                            break
                        
                        page_insert_count = 0
                        for prop in properties:
                            try:
                                # I changed full_address to location, based on your spy data!
                                cur.execute("""
                                    INSERT INTO properties (opa_account_num, address, owner_name, zip_code, market_value, square_footage)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (opa_account_num) DO NOTHING;
                                """, (
                                    prop.get('parcel_number'),
                                    prop.get('location'),
                                    prop.get('owner_1'),
                                    prop.get('zip_code'),
                                    prop.get('market_value'),
                                    prop.get('total_livable_area')
                                ))
                                page_insert_count += cur.rowcount
                            except Exception as insert_error:
                                 pass

                        total_inserted_count += page_insert_count
                        progress_bar.update(len(properties))
                        page_num += 1

                    else:
                        print(f"\nugh, the api call failed. 😤 status code: {response.status_code}")
                        print(response.text)
                        break
            
            conn.commit()
            print(f"\n--- UCity Property ETL complete! ---")
            print(f"successfully inserted a grand total of {total_inserted_count} UCity property records. ✨")

except Exception as e:
    print(f"😤 a database error occurred: {e}")

