import os
import psycopg
import requests
from dotenv import load_dotenv
from pathlib import Path
from tqdm import tqdm

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
print("alright, connecting to the database to build the ULTIMATE property dossiers...")
try:
    with psycopg.connect(DB_CONNECTION_STRING) as conn:
        print("🎉 connection successful!")
        with conn.cursor() as cur:
            
            print("designing the new 'properties' table schema...")
            # I've upgraded the table with ALL your new intelligence fields!
            cur.execute("DROP TABLE IF EXISTS properties;") # Start fresh with our new design!
            cur.execute("""
                CREATE TABLE properties (
                    opa_account_num TEXT PRIMARY KEY,
                    address TEXT,
                    zip_code TEXT,
                    owner_1 TEXT,
                    owner_2 TEXT,
                    mailing_address TEXT,
                    mailing_city_state TEXT,
                    is_owner_occupied BOOLEAN,
                    market_value NUMERIC,
                    last_sale_date DATE,
                    exterior_condition TEXT,
                    interior_condition TEXT,
                    quality_grade TEXT,
                    year_built INTEGER,
                    bedrooms INTEGER,
                    bathrooms INTEGER,
                    livable_area INTEGER,
                    has_central_air BOOLEAN,
                    building_description TEXT,
                    ward TEXT
                );
            """)
            print("table is ready for UCity property data!")

            # --- 3. GET TOTAL COUNT FOR PROGRESS BAR ---
            print("let's see how many properties are in University City...")
            count_query = f"SELECT count(*) FROM opa_properties_public WHERE trim(zip_code) LIKE '{UCITY_ZIP_CODE}%'"
            count_response = requests.get(BASE_API_URL, params={'q': count_query})
            
            if count_response.status_code == 200:
                total_records = count_response.json()['rows'][0]['count']
                if total_records == 0:
                    print("😤 still got 0 records... are you SURE 19104 is the right zip code?")
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
                    # The ultimate query to get everything we need!
                    query = f"""
                        SELECT 
                            parcel_number, location, zip_code, owner_1, owner_2,
                            mailing_address_1, mailing_city_state, homestead_exemption,
                            market_value, sale_date, exterior_condition, interior_condition,
                            quality_grade, year_built, number_of_bedrooms, number_of_bathrooms,
                            total_livable_area, central_air, building_code_description, geographic_ward
                        FROM opa_properties_public 
                        WHERE trim(zip_code) LIKE '{UCITY_ZIP_CODE}%' 
                        ORDER BY parcel_number 
                        LIMIT {RECORDS_PER_PAGE} OFFSET {offset}
                    """
                    
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
                                # And the ultimate INSERT statement!
                                cur.execute("""
                                    INSERT INTO properties (
                                        opa_account_num, address, zip_code, owner_1, owner_2,
                                        mailing_address, mailing_city_state, is_owner_occupied,
                                        market_value, last_sale_date, exterior_condition, interior_condition,
                                        quality_grade, year_built, bedrooms, bathrooms,
                                        livable_area, has_central_air, building_description, ward
                                    )
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (opa_account_num) DO NOTHING;
                                """, (
                                    prop.get('parcel_number'),
                                    prop.get('location'),
                                    prop.get('zip_code'),
                                    prop.get('owner_1'),
                                    prop.get('owner_2'),
                                    prop.get('mailing_address_1'),
                                    prop.get('mailing_city_state'),
                                    prop.get('homestead_exemption', 0) > 0,
                                    prop.get('market_value'),
                                    prop.get('sale_date'),
                                    prop.get('exterior_condition'),
                                    prop.get('interior_condition'),
                                    prop.get('quality_grade'),
                                    int(prop['year_built']) if prop.get('year_built') and prop.get('year_built').isdigit() else None,
                                    prop.get('number_of_bedrooms'),
                                    prop.get('number_of_bathrooms'),
                                    prop.get('total_livable_area'),
                                    prop.get('central_air') == 'Y',
                                    prop.get('building_code_description'),
                                    prop.get('geographic_ward')
                                ))
                                page_insert_count += cur.rowcount
                            except Exception as insert_error:
                                pass # Silently skip records with insert errors for now

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

