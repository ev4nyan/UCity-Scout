import os
import psycopg
import requests
from dotenv import load_dotenv
from pathlib import Path
from tqdm import tqdm
from datetime import datetime, timedelta
import time

# --- 1. CONFIGURATION ---
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
env_path = project_root / 'config' / '.env'
load_dotenv(dotenv_path=env_path)

DB_CONNECTION_STRING = os.getenv("DATABASE_URL")
BASE_API_URL = "https://phl.carto.com/api/v2/sql"
RECORDS_PER_PAGE = 500

# University City bounding box (with ~200m buffer for edge-of-neighborhood properties)
UCITY_LAT_MIN = 39.940
UCITY_LAT_MAX = 39.970
UCITY_LNG_MIN = -75.225
UCITY_LNG_MAX = -75.180

# Only pull recent incidents (last 1 year)
LOOKBACK_DAYS = 365

# --- 2. DATABASE CONNECTION & SETUP ---
print("connecting to the database to sync crime incidents...")
try:
    with psycopg.connect(DB_CONNECTION_STRING) as conn:
        print("🎉 connection successful!")
        with conn.cursor() as cur:

            print("making sure the 'crime_incidents' table exists...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS crime_incidents (
                    dc_key TEXT PRIMARY KEY,
                    dc_dist TEXT,
                    psa TEXT,
                    dispatch_date_time TIMESTAMP WITH TIME ZONE,
                    dispatch_date TEXT,
                    dispatch_time TEXT,
                    ucr_general TEXT,
                    text_general_code TEXT,
                    location_block TEXT,
                    lat NUMERIC,
                    lng NUMERIC
                );
            """)
            print("clearing old crime data for a fresh sync...")
            cur.execute("TRUNCATE TABLE crime_incidents;")
            print("table is ready for UCity crime incident data!")

            # --- 3. GET TOTAL COUNT FOR PROGRESS BAR ---
            cutoff_date = (datetime.now() - timedelta(days=LOOKBACK_DAYS)).strftime('%Y-%m-%d')
            bbox_where = f"lat BETWEEN {UCITY_LAT_MIN} AND {UCITY_LAT_MAX} AND lng BETWEEN {UCITY_LNG_MIN} AND {UCITY_LNG_MAX} AND dispatch_date >= '{cutoff_date}'"

            print(f"let's see how many crime incidents are near University City (since {cutoff_date})...")
            count_query = f"SELECT count(*) FROM incidents_part1_part2 WHERE {bbox_where}"
            count_response = requests.get(BASE_API_URL, params={'q': count_query})

            if count_response.status_code == 200:
                total_records = count_response.json()['rows'][0]['count']
                if total_records == 0:
                    print("...hmph. the api still says zero records match. are we sure this data exists for ucity? how rude!")
                    exit()
                print(f"found {total_records} total crime incidents near University City. starting sync...")
            else:
                print("ugh, couldn't get the total count from the api. can't proceed!")
                print(f"status: {count_response.status_code}, text: {count_response.text}")
                exit()

            # --- 4. PAGINATION & ETL LOOP ---
            page_num = 0
            total_inserted_count = 0

            with tqdm(total=total_records, desc="Syncing Crime Incidents", unit=" incident") as progress_bar:
                while total_inserted_count < total_records:
                    offset = page_num * RECORDS_PER_PAGE
                    query = f"SELECT dc_key, dc_dist, psa, dispatch_date_time, dispatch_date, dispatch_time, ucr_general, text_general_code, location_block, lat, lng FROM incidents_part1_part2 WHERE {bbox_where} ORDER BY dc_key LIMIT {RECORDS_PER_PAGE} OFFSET {offset}"

                    response = requests.get(BASE_API_URL, params={'q': query}, timeout=60)

                    if response.status_code == 200:
                        data = response.json()
                        incidents = data.get('rows', [])

                        if not incidents:
                            break

                        page_insert_count = 0
                        for inc in incidents:
                            if not inc.get('dc_key'):
                                continue

                            try:
                                cur.execute("""
                                    INSERT INTO crime_incidents (
                                        dc_key, dc_dist, psa, dispatch_date_time,
                                        dispatch_date, dispatch_time, ucr_general,
                                        text_general_code, location_block,
                                        lat, lng
                                    )
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (dc_key) DO NOTHING;
                                """, (
                                    str(inc.get('dc_key')),
                                    inc.get('dc_dist'),
                                    inc.get('psa'),
                                    inc.get('dispatch_date_time'),
                                    inc.get('dispatch_date'),
                                    inc.get('dispatch_time'),
                                    str(inc.get('ucr_general')) if inc.get('ucr_general') is not None else None,
                                    inc.get('text_general_code'),
                                    inc.get('location_block'),
                                    inc.get('lat'),
                                    inc.get('lng')
                                ))
                                page_insert_count += cur.rowcount
                            except Exception as insert_error:
                                print("\n😤 HEY! The database rejected this record! Here's why:")
                                print("Error:", insert_error)
                                print("Problem Record:", inc)
                                raise

                        total_inserted_count += page_insert_count
                        progress_bar.update(len(incidents))
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

            print(f"\n--- UCity Crime Incidents ETL complete! ---")
            print(f"successfully inserted a grand total of {total_inserted_count} UCity-area crime incidents. ✨")

except Exception as e:
    print(f"😤 a database error occurred: {e}")
