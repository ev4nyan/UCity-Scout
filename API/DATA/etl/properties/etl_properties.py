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
print("connecting to the database to sync properties...")
try:
    with psycopg.connect(DB_CONNECTION_STRING) as conn:
        print("🎉 connection successful!")
        with conn.cursor() as cur:
            
            print("making sure the 'properties' table exists...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS properties (
                    parcel_number TEXT PRIMARY KEY,
                    assessment_date TIMESTAMP WITH TIME ZONE,
                    building_code_description TEXT,
                    category_code_description TEXT,
                    central_air TEXT,
                    exterior_condition TEXT,
                    general_construction TEXT,
                    house_extension TEXT,
                    house_number TEXT,
                    interior_condition TEXT,
                    location TEXT,
                    mailing_address_1 TEXT,
                    mailing_address_2 TEXT,
                    mailing_city_state TEXT,
                    mailing_street TEXT,
                    mailing_zip TEXT,
                    number_of_bathrooms INTEGER,
                    number_of_bedrooms INTEGER,
                    number_of_rooms INTEGER,
                    number_stories INTEGER,
                    owner_1 TEXT,
                    owner_2 TEXT,
                    quality_grade TEXT,
                    street_designation TEXT,
                    street_name TEXT,
                    year_built TEXT,
                    year_built_estimate TEXT,
                    zip_code TEXT,
                    building_code_description_new TEXT
                );
            """)
            print("clearing old property data for a fresh sync...")
            cur.execute("TRUNCATE TABLE properties;")
            print("table is ready for UCity property data!")

            # --- 3. GET TOTAL COUNT FOR PROGRESS BAR ---
            print("let's see how many properties are in University City...")
            count_query = f"SELECT count(*) FROM opa_properties_public WHERE trim(zip_code) LIKE '{UCITY_ZIP_CODE}%'"
            count_response = requests.get(BASE_API_URL, params={'q': count_query})
            
            if count_response.status_code == 200:
                total_records = count_response.json()['rows'][0]['count']
                if total_records == 0:
                    print("...hmph. the api still says zero records match. are we sure this data exists for ucity? how rude!")
                    exit()
                print(f"found {total_records} total properties for University City. starting sync...")
            else:
                print("ugh, couldn't get the total count from the api. can't proceed!")
                print(f"status: {count_response.status_code}, text: {count_response.text}")
                exit()

            # --- 4. PAGINATION & ETL LOOP ---
            page_num = 0
            total_inserted_count = 0
            
            with tqdm(total=total_records, desc="Syncing Properties", unit=" property") as progress_bar:
                while total_inserted_count < total_records:
                    offset = page_num * RECORDS_PER_PAGE
                    query = f"SELECT assessment_date, building_code_description, category_code_description, central_air, exterior_condition, general_construction, house_extension, house_number, interior_condition, location, mailing_address_1, mailing_address_2, mailing_city_state, mailing_street, mailing_zip, number_of_bathrooms, number_of_bedrooms, number_of_rooms, number_stories, owner_1, owner_2, parcel_number, quality_grade, street_designation, street_name, year_built, year_built_estimate, zip_code, building_code_description_new FROM opa_properties_public WHERE trim(zip_code) LIKE '{UCITY_ZIP_CODE}%' ORDER BY parcel_number LIMIT {RECORDS_PER_PAGE} OFFSET {offset}"
                    
                    response = requests.get(BASE_API_URL, params={'q': query}, timeout=60)

                    if response.status_code == 200:
                        data = response.json()
                        properties = data.get('rows', [])

                        if not properties:
                            break
                        
                        page_insert_count = 0
                        for prop in properties:
                            if not prop.get('parcel_number'):
                                continue
                            
                            try:
                                cur.execute("""
                                    INSERT INTO properties (
                                        parcel_number, assessment_date, building_code_description,
                                        category_code_description, central_air, exterior_condition,
                                        general_construction, house_extension, house_number,
                                        interior_condition, location, mailing_address_1,
                                        mailing_address_2, mailing_city_state, mailing_street,
                                        mailing_zip, number_of_bathrooms, number_of_bedrooms,
                                        number_of_rooms, number_stories, owner_1, owner_2,
                                        quality_grade, street_designation, street_name,
                                        year_built, year_built_estimate, zip_code,
                                        building_code_description_new
                                    )
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (parcel_number) DO NOTHING;
                                """, (
                                    prop.get('parcel_number'),
                                    prop.get('assessment_date'),
                                    prop.get('building_code_description'),
                                    prop.get('category_code_description'),
                                    prop.get('central_air'),
                                    prop.get('exterior_condition'),
                                    prop.get('general_construction'),
                                    prop.get('house_extension'),
                                    prop.get('house_number'),
                                    prop.get('interior_condition'),
                                    prop.get('location'),
                                    prop.get('mailing_address_1'),
                                    prop.get('mailing_address_2'),
                                    prop.get('mailing_city_state'),
                                    prop.get('mailing_street'),
                                    prop.get('mailing_zip'),
                                    prop.get('number_of_bathrooms'),
                                    prop.get('number_of_bedrooms'),
                                    prop.get('number_of_rooms'),
                                    prop.get('number_stories'),
                                    prop.get('owner_1'),
                                    prop.get('owner_2'),
                                    prop.get('quality_grade'),
                                    prop.get('street_designation'),
                                    prop.get('street_name'),
                                    prop.get('year_built'),
                                    prop.get('year_built_estimate'),
                                    prop.get('zip_code'),
                                    prop.get('building_code_description_new')
                                ))
                                page_insert_count += cur.rowcount
                            except Exception as insert_error:
                                print("\n😤 HEY! The database rejected this record! Here's why:")
                                print("Error:", insert_error)
                                print("Problem Record:", prop)
                                raise
                        
                        total_inserted_count += page_insert_count
                        progress_bar.update(len(properties))
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

            print(f"\n--- UCity Properties ETL complete! ---")
            print(f"successfully inserted a grand total of {total_inserted_count} UCity properties. ✨")

except Exception as e:
    print(f"😤 a database error occurred: {e}")