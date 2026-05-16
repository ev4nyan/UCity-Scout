import os
import psycopg
from dotenv import load_dotenv
from pathlib import Path
import time
from typing import Callable, TypeVar

T = TypeVar('T')

# --- 1. CONFIGURATION ---
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent.parent
env_path = project_root / 'config' / '.env'
load_dotenv(dotenv_path=env_path)

DB_CONNECTION_STRING = os.getenv("DATABASE_URL")

# --- 2. RETRY HELPER ---
def retry_with_backoff(func: Callable[..., T], max_retries: int = 3, backoff_factor: float = 1.0) -> T:
    """
    Execute a function with exponential backoff retry logic.
    Useful for handling transient database connection issues.
    """
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait_time = backoff_factor * (2 ** attempt)
            print(f"⚠️ Attempt {attempt + 1} failed: {e}. Retrying in {wait_time:.1f}s...")
            time.sleep(wait_time)
    raise Exception("Max retries exceeded")

# --- 3. DATABASE CONNECTION & SETUP ---
print("connecting to the database to build property intelligence...")

def run_etl():
    with psycopg.connect(DB_CONNECTION_STRING) as conn:
        print("🎉 connection successful!")
        with conn.cursor() as cur:

            print("creating the 'property_intelligence' table...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS property_intelligence (
                    opa_account_num TEXT PRIMARY KEY,
                    address TEXT,
                    owner_name TEXT,
                    landlord_locality TEXT,
                    violation_count INTEGER,
                    open_violation_count INTEGER,
                    permit_count INTEGER,
                    has_rental_license BOOLEAN,
                    rental_license_active BOOLEAN,
                    is_owner_occupied BOOLEAN,
                    property_age INTEGER,
                    exterior_condition TEXT,
                    interior_condition TEXT,
                    bedrooms INTEGER,
                    bathrooms NUMERIC,
                    livable_area INTEGER,
                    has_central_air BOOLEAN,
                    has_tax_delinquency BOOLEAN,
                    tax_total_due NUMERIC,
                    tax_num_years_owed INTEGER,
                    tax_sheriff_sale BOOLEAN,
                    safety_score INTEGER,
                    maintenance_score INTEGER,
                    landlord_score INTEGER,
                    trustability_score INTEGER,
                    risk_level TEXT,
                    risk_flags TEXT[],
                    student_warnings TEXT[],
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
            print("clearing old property intelligence data for a fresh build...")
            cur.execute("TRUNCATE TABLE property_intelligence;")
            print("table is ready for property intelligence aggregation!")

            # --- 4. AGGREGATION QUERY ---
            print("aggregating data from properties, violations, permits, licenses, and tax delinquencies...")

            aggregation_query = """
                WITH base AS (
                    SELECT
                        p.parcel_number AS opa_account_num,
                        COALESCE(p.location, TRIM(p.house_number || ' ' || p.street_name || ' ' || COALESCE(p.street_designation, ''))) AS address,
                        COALESCE(p.owner_1, '') AS owner_name,
                        CASE
                            WHEN p.mailing_city_state IS NULL OR p.mailing_city_state ILIKE '%PA%' THEN 'LOCAL'
                            ELSE 'DISTANT'
                        END AS landlord_locality,
                        COALESCE(viol.violation_count, 0) AS violation_count,
                        COALESCE(viol.open_violation_count, 0) AS open_violation_count,
                        COALESCE(prm.permit_count, 0) AS permit_count,
                        COALESCE(lic.has_license, false) AS has_rental_license,
                        COALESCE(lic.is_active, false) AS rental_license_active,
                        CASE
                            WHEN p.mailing_street IS NOT NULL
                                 AND LOWER(p.mailing_street) = LOWER(p.street_name) THEN true
                            ELSE false
                        END AS is_owner_occupied,
                        CASE WHEN p.year_built ~ E'^\\d{4}$'
                             THEN (EXTRACT(YEAR FROM NOW())::INTEGER - p.year_built::INTEGER)
                             ELSE NULL
                        END AS property_age,
                        p.exterior_condition,
                        p.interior_condition,
                        p.number_of_bedrooms AS bedrooms,
                        p.number_of_bathrooms AS bathrooms,
                        NULL::INTEGER AS livable_area,
                        (p.central_air = 'Y') AS has_central_air,
                        CASE WHEN tax.opa_number IS NOT NULL THEN true ELSE false END AS has_tax_delinquency,
                        COALESCE(tax.total_due, 0) AS tax_total_due,
                        COALESCE(tax.num_years_owed, 0) AS tax_num_years_owed,
                        CASE WHEN tax.sheriff_sale IS NOT NULL AND tax.sheriff_sale != 'N' THEN true ELSE false END AS tax_sheriff_sale
                    FROM properties p
                    LEFT JOIN (
                        SELECT opa_account_num,
                               COUNT(*) AS violation_count,
                               COUNT(*) FILTER (WHERE violation_status NOT IN ('COMPLIED', 'CLOSED', 'RESOLVED')) AS open_violation_count
                        FROM violations
                        GROUP BY opa_account_num
                    ) viol ON p.parcel_number = viol.opa_account_num
                    LEFT JOIN (
                        SELECT opa_account_num, COUNT(*) AS permit_count
                        FROM permits
                        GROUP BY opa_account_num
                    ) prm ON p.parcel_number = prm.opa_account_num
                    LEFT JOIN (
                        SELECT DISTINCT ON (opa_account_num)
                               opa_account_num,
                               true AS has_license,
                               active AS is_active
                        FROM rental_licenses
                        ORDER BY opa_account_num, active DESC
                    ) lic ON p.parcel_number = lic.opa_account_num
                    LEFT JOIN (
                        SELECT opa_number,
                               total_due,
                               num_years_owed,
                               sheriff_sale
                        FROM tax_balances
                    ) tax ON p.parcel_number = tax.opa_number
                    WHERE p.zip_code = '19104'
                ),
                scored AS (
                    SELECT
                        *,
                        GREATEST(0, LEAST(100,
                            100 - (violation_count * 10) - (open_violation_count * 20)
                                - (CASE WHEN has_tax_delinquency THEN tax_num_years_owed * 5 ELSE 0 END)
                        )) AS safety_score,
                        GREATEST(0, LEAST(100,
                            CASE exterior_condition
                                WHEN 'A+' THEN 100 WHEN 'A' THEN 95 WHEN 'B' THEN 85
                                WHEN 'C' THEN 70  WHEN 'D' THEN 50  WHEN 'E' THEN 30
                                ELSE 60
                            END + (permit_count * 2)
                        )) AS maintenance_score,
                        GREATEST(0, LEAST(100,
                            CASE
                                WHEN has_rental_license AND rental_license_active THEN 80
                                WHEN has_rental_license THEN 50
                                ELSE 30
                            END + CASE WHEN landlord_locality = 'LOCAL' THEN 20 ELSE 0 END
                              - (CASE WHEN has_tax_delinquency AND tax_num_years_owed >= 3 THEN 20
                                      WHEN has_tax_delinquency THEN 10 ELSE 0 END)
                        )) AS landlord_score
                    FROM base
                ),
                final AS (
                    SELECT
                        *,
                        (safety_score * 0.4 + maintenance_score * 0.35 + landlord_score * 0.25)::INTEGER AS trustability_score
                    FROM scored
                )
                INSERT INTO property_intelligence (
                    opa_account_num, address, owner_name, landlord_locality,
                    violation_count, open_violation_count, permit_count,
                    has_rental_license, rental_license_active, is_owner_occupied,
                    property_age, exterior_condition, interior_condition,
                    bedrooms, bathrooms, livable_area, has_central_air,
                    has_tax_delinquency, tax_total_due, tax_num_years_owed, tax_sheriff_sale,
                    safety_score, maintenance_score, landlord_score, trustability_score,
                    risk_level, risk_flags, student_warnings
                )
                SELECT
                    opa_account_num, address, owner_name, landlord_locality,
                    violation_count, open_violation_count, permit_count,
                    has_rental_license, rental_license_active, is_owner_occupied,
                    property_age, exterior_condition, interior_condition,
                    bedrooms, bathrooms, livable_area, has_central_air,
                    has_tax_delinquency, tax_total_due, tax_num_years_owed, tax_sheriff_sale,
                    safety_score, maintenance_score, landlord_score, trustability_score,
                    CASE
                        WHEN trustability_score >= 75 THEN 'LOW'
                        WHEN trustability_score >= 50 THEN 'MODERATE'
                        WHEN trustability_score >= 25 THEN 'HIGH'
                        ELSE 'CRITICAL'
                    END AS risk_level,
                    ARRAY_REMOVE(ARRAY[
                        CASE WHEN open_violation_count > 0        THEN 'OPEN_VIOLATIONS'   ELSE NULL END,
                        CASE WHEN NOT has_rental_license          THEN 'NO_RENTAL_LICENSE'  ELSE NULL END,
                        CASE WHEN has_rental_license
                              AND NOT rental_license_active        THEN 'EXPIRED_LICENSE'   ELSE NULL END,
                        CASE WHEN landlord_locality = 'DISTANT'   THEN 'DISTANT_LANDLORD'  ELSE NULL END,
                        CASE WHEN exterior_condition IN ('D','E') THEN 'POOR_CONDITION'     ELSE NULL END,
                        CASE WHEN has_tax_delinquency             THEN 'TAX_DELINQUENT'    ELSE NULL END,
                        CASE WHEN tax_sheriff_sale                THEN 'SHERIFF_SALE'      ELSE NULL END
                    ], NULL) AS risk_flags,
                    ARRAY_REMOVE(ARRAY[
                        CASE WHEN open_violation_count > 2        THEN 'Multiple open code violations'          ELSE NULL END,
                        CASE WHEN NOT has_rental_license          THEN 'No rental license on file'              ELSE NULL END,
                        CASE WHEN landlord_locality = 'DISTANT'   THEN 'Landlord located outside Philadelphia'  ELSE NULL END,
                        CASE WHEN exterior_condition IN ('D','E') THEN 'Property in poor condition'             ELSE NULL END,
                        CASE WHEN has_tax_delinquency AND tax_num_years_owed >= 3 THEN 'Property has multi-year tax delinquency' ELSE NULL END,
                        CASE WHEN tax_sheriff_sale                THEN 'Property flagged for sheriff sale'      ELSE NULL END
                    ], NULL) AS student_warnings
                FROM final
            """
            
            cur.execute(aggregation_query)
            
            # Get count of inserted records
            cur.execute("SELECT COUNT(*) FROM property_intelligence;")
            count = cur.fetchone()[0]
            
            conn.commit()

            print(f"\n--- Property Intelligence ETL complete! ---")
            print(f"successfully aggregated {count} properties with intelligence data. ✨")

# Run the ETL with retry logic
try:
    retry_with_backoff(run_etl)
except Exception as e:
    print(f"😤 a database error occurred: {e}")
    import traceback
    traceback.print_exc()
