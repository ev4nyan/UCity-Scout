import os
import psycopg
from dotenv import load_dotenv
from pathlib import Path
from tqdm import tqdm
import re

# --- 1. CONFIGURATION ---
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
env_path = project_root / 'config' / '.env'
load_dotenv(dotenv_path=env_path)

DB_CONNECTION_STRING = os.getenv("DATABASE_URL")
UCITY_CENTER = (39.9522, -75.1932)  # Center of 19104 (UPenn area)
DISTANCE_THRESHOLD_MILES = 100

# --- 2. HELPER FUNCTIONS ---
def estimate_distance_from_zip(zip_code):
    """
    Estimate if a landlord is local based on zip code.
    Returns: 'LOCAL' if within ~100 miles, 'DISTANT' if far, 'UNKNOWN' if can't determine
    """
    if not zip_code:
        return 'UNKNOWN'
    
    # Clean the zip code
    zip_str = str(zip_code).strip()[:5]
    
    # PA zips generally within range
    pa_nearby = ['19', '18', '17']
    # NJ zips within range (South Jersey)
    nj_nearby = ['080', '081', '082', '083', '084']
    # DE zips within range
    de_nearby = ['197', '198', '199']
    
    # Check if it starts with nearby prefixes
    for prefix in pa_nearby:
        if zip_str.startswith(prefix):
            return 'LOCAL'
    for prefix in nj_nearby:
        if zip_str.startswith(prefix):
            return 'LOCAL'
    for prefix in de_nearby:
        if zip_str.startswith(prefix):
            return 'LOCAL'
    
    # Anything else is probably distant
    return 'DISTANT'

def extract_zip_from_address(mailing_city_state):
    """Extract zip code from the mailing_city_state field"""
    if not mailing_city_state:
        return None
    
    # Try to find a 5-digit zip code
    match = re.search(r'\b(\d{5})\b', str(mailing_city_state))
    if match:
        return match.group(1)
    return None

# --- 3. DATABASE CONNECTION & SETUP ---
print("connecting to the database to build STUDENT-FOCUSED property intelligence...")
try:
    with psycopg.connect(DB_CONNECTION_STRING) as conn:
        print("🎉 connection successful!")
        with conn.cursor() as cur:
            
            print("designing the 'property_intelligence' table for students...")
            cur.execute("DROP TABLE IF EXISTS property_intelligence;")
            cur.execute("""
                CREATE TABLE property_intelligence (
                    opa_account_num TEXT PRIMARY KEY,
                    address TEXT,
                    owner_name TEXT,
                    landlord_locality TEXT,  -- LOCAL, DISTANT, or UNKNOWN
                    
                    -- Raw counts
                    violation_count INTEGER DEFAULT 0,
                    open_violation_count INTEGER DEFAULT 0,
                    permit_count INTEGER DEFAULT 0,
                    has_rental_license BOOLEAN DEFAULT FALSE,
                    rental_license_active BOOLEAN DEFAULT FALSE,
                    
                    -- Property characteristics students care about
                    is_owner_occupied BOOLEAN DEFAULT FALSE,
                    property_age INTEGER,
                    exterior_condition TEXT,
                    interior_condition TEXT,
                    bedrooms INTEGER,
                    bathrooms INTEGER,
                    livable_area INTEGER,
                    has_central_air BOOLEAN,
                    
                    -- Student-focused scores (0-100 scale)
                    safety_score NUMERIC,           -- Safety & code compliance
                    maintenance_score NUMERIC,      -- Property upkeep
                    landlord_score NUMERIC,         -- Landlord responsiveness indicators
                    trustability_score NUMERIC,     -- Overall student trustability
                    
                    -- Risk flags
                    risk_level TEXT,
                    risk_flags TEXT[],
                    student_warnings TEXT[],        -- Specific warnings for students
                    
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Create indexes for better performance
            cur.execute("CREATE INDEX idx_trustability ON property_intelligence(trustability_score DESC);")
            cur.execute("CREATE INDEX idx_risk_level ON property_intelligence(risk_level);")
            cur.execute("CREATE INDEX idx_landlord_locality ON property_intelligence(landlord_locality);")
            
            print("table is ready! now gathering student-relevant intelligence...")

            # --- 4. GET PROPERTY COUNT ---
            cur.execute("SELECT COUNT(*) FROM properties;")
            total_properties = cur.fetchone()[0]
            print(f"found {total_properties} properties to analyze for students. let's go!")

            # --- 5. INTELLIGENCE GATHERING LOOP ---
            batch_size = 100
            processed = 0
            
            with tqdm(total=total_properties, desc="Building Student Intelligence", unit=" property") as progress_bar:
                while processed < total_properties:
                    # Fetch a batch of properties
                    cur.execute("""
                        SELECT 
                            opa_account_num, address, owner_1, is_owner_occupied,
                            year_built, exterior_condition, interior_condition,
                            mailing_city_state, bedrooms, bathrooms, livable_area,
                            has_central_air
                        FROM properties
                        ORDER BY opa_account_num
                        LIMIT %s OFFSET %s
                    """, (batch_size, processed))
                    
                    properties = cur.fetchall()
                    if not properties:
                        break
                    
                    for prop in properties:
                        (opa_num, addr, owner, owner_occ, year_built, ext_cond, 
                         int_cond, mailing_city_state, beds, baths, sq_ft, central_air) = prop
                        
                        # Calculate property age
                        from datetime import datetime
                        prop_age = datetime.now().year - year_built if year_built else None
                        
                        # Determine landlord locality
                        landlord_zip = extract_zip_from_address(mailing_city_state)
                        landlord_locality = estimate_distance_from_zip(landlord_zip)
                        
                        # --- GATHER INTELLIGENCE DATA ---
                        
                        # Violation counts
                        cur.execute("""
                            SELECT 
                                COUNT(*) as total,
                                COUNT(*) FILTER (WHERE violation_status IN ('OPEN', 'IN VIOLATION')) as open_count
                            FROM violations 
                            WHERE opa_account_num = %s
                        """, (opa_num,))
                        viol_total, viol_open = cur.fetchone()
                        
                        # Permit counts (recent maintenance/improvements)
                        cur.execute("""
                            SELECT COUNT(*) 
                            FROM permits 
                            WHERE opa_account_num = %s
                        """, (opa_num,))
                        permit_count = cur.fetchone()[0]
                        
                        # Rental license status
                        cur.execute("""
                            SELECT 
                                COUNT(*) > 0 as has_license,
                                BOOL_OR(active) as is_active
                            FROM rental_licenses 
                            WHERE opa_account_num = %s
                        """, (opa_num,))
                        result = cur.fetchone()
                        has_license, license_active = result if result else (False, False)
                        
                        # --- CALCULATE STUDENT-FOCUSED SCORES ---
                        
                        # 1. SAFETY SCORE (0-100) - Most important for students!
                        safety = 100.0
                        
                        # Open violations are a major red flag
                        if viol_open > 0:
                            safety -= min(viol_open * 20, 80)  # -20 per open violation, max -80
                        
                        # History of violations matters too
                        if viol_total > 5:
                            safety -= min((viol_total - 5) * 3, 15)  # -3 for each violation over 5
                        
                        # No rental license is a big deal for student rentals
                        if not owner_occ and not has_license:
                            safety -= 25
                        elif has_license and not license_active:
                            safety -= 15
                        
                        safety = max(0, safety)
                        
                        # 2. MAINTENANCE SCORE (0-100) - Are things kept up?
                        maintenance = 50.0  # Base score
                        
                        # Condition scoring
                        condition_map = {
                            'EXCELLENT': 25, 'GOOD': 18, 'ABOVE AVERAGE': 12,
                            'AVERAGE': 5, 'BELOW AVERAGE': -8, 'FAIR': -15,
                            'POOR': -25, 'VERY POOR': -35
                        }
                        if ext_cond:
                            maintenance += condition_map.get(ext_cond.upper(), 0)
                        if int_cond:
                            maintenance += condition_map.get(int_cond.upper(), 0)
                        
                        # Recent permits show active maintenance
                        if permit_count > 0:
                            maintenance += min(permit_count * 8, 25)
                        elif prop_age and prop_age > 50:
                            maintenance -= 15  # Old building with no recent work
                        
                        # Central air is nice for students
                        if central_air:
                            maintenance += 5
                        
                        maintenance = max(0, min(100, maintenance))
                        
                        # 3. LANDLORD SCORE (0-100) - Responsiveness indicators
                        landlord = 50.0  # Base score
                        
                        # Local landlords tend to be more responsive
                        if landlord_locality == 'LOCAL':
                            landlord += 20
                        elif landlord_locality == 'DISTANT':
                            landlord -= 15
                        
                        # Owner-occupied shows landlord cares about property
                        if owner_occ:
                            landlord += 15
                        
                        # Having proper licensing shows professionalism
                        if has_license and license_active:
                            landlord += 15
                        elif not has_license and not owner_occ:
                            landlord -= 20
                        
                        # Recent permits show responsiveness to issues
                        if permit_count > 2:
                            landlord += 10
                        elif permit_count == 0 and prop_age and prop_age > 30:
                            landlord -= 10
                        
                        # Chronic violations suggest unresponsive landlord
                        if viol_total > 10:
                            landlord -= 20
                        
                        landlord = max(0, min(100, landlord))
                        
                        # 4. TRUSTABILITY SCORE (weighted average for students)
                        trustability = (
                            safety * 0.45 +          # Safety is paramount
                            maintenance * 0.30 +     # Maintenance is important
                            landlord * 0.25          # Landlord quality matters
                        )
                        trustability = round(trustability, 2)
                        
                        # --- DETERMINE RISK LEVEL & FLAGS ---
                        risk_flags = []
                        student_warnings = []
                        
                        if viol_open > 2:
                            risk_flags.append('MULTIPLE_OPEN_VIOLATIONS')
                            student_warnings.append('Property has multiple unresolved code violations')
                        
                        if viol_total > 10:
                            risk_flags.append('CHRONIC_VIOLATOR')
                            student_warnings.append('Long history of code violations')
                        
                        if not owner_occ and not has_license:
                            risk_flags.append('UNLICENSED_RENTAL')
                            student_warnings.append('Operating as rental without proper license')
                        
                        if has_license and not license_active:
                            risk_flags.append('EXPIRED_LICENSE')
                            student_warnings.append('Rental license has expired')
                        
                        if landlord_locality == 'DISTANT':
                            risk_flags.append('DISTANT_LANDLORD')
                            student_warnings.append('Landlord is located far from property - may be less responsive')
                        
                        if ext_cond and ext_cond.upper() in ['POOR', 'VERY POOR']:
                            risk_flags.append('POOR_EXTERIOR')
                            student_warnings.append('Property exterior is in poor condition')
                        
                        if int_cond and int_cond.upper() in ['POOR', 'VERY POOR']:
                            risk_flags.append('POOR_INTERIOR')
                            student_warnings.append('Property interior is in poor condition')
                        
                        if permit_count == 0 and prop_age and prop_age > 50:
                            risk_flags.append('NO_RECENT_IMPROVEMENTS')
                            student_warnings.append('No recent maintenance or improvements on older building')
                        
                        if not central_air and prop_age and prop_age < 30:
                            risk_flags.append('NO_CENTRAL_AIR')
                        
                        # Determine overall risk level
                        if trustability >= 75:
                            risk_level = 'LOW'
                        elif trustability >= 50:
                            risk_level = 'MODERATE'
                        elif trustability >= 25:
                            risk_level = 'HIGH'
                        else:
                            risk_level = 'CRITICAL'
                        
                        # --- INSERT INTELLIGENCE RECORD ---
                        try:
                            cur.execute("""
                                INSERT INTO property_intelligence (
                                    opa_account_num, address, owner_name, landlord_locality,
                                    violation_count, open_violation_count, permit_count,
                                    has_rental_license, rental_license_active,
                                    is_owner_occupied, property_age, exterior_condition,
                                    interior_condition, bedrooms, bathrooms, livable_area,
                                    has_central_air,
                                    safety_score, maintenance_score, landlord_score,
                                    trustability_score, risk_level, risk_flags, student_warnings
                                )
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                opa_num, addr, owner, landlord_locality,
                                viol_total, viol_open, permit_count,
                                has_license, license_active, owner_occ, prop_age,
                                ext_cond, int_cond, beds, baths, sq_ft, central_air,
                                round(safety, 2), round(maintenance, 2), round(landlord, 2),
                                trustability, risk_level, risk_flags, student_warnings
                            ))
                        except Exception as e:
                            print(f"\n😤 Error processing property {opa_num}: {e}")
                            continue
                    
                    conn.commit()
                    processed += len(properties)
                    progress_bar.update(len(properties))
            
            # --- 6. GENERATE STUDENT-FOCUSED SUMMARY STATISTICS ---
            print("\n--- generating student intelligence summary ---")
            
            cur.execute("""
                SELECT 
                    risk_level,
                    COUNT(*) as count,
                    ROUND(AVG(trustability_score), 2) as avg_score
                FROM property_intelligence
                GROUP BY risk_level
                ORDER BY 
                    CASE risk_level
                        WHEN 'CRITICAL' THEN 1
                        WHEN 'HIGH' THEN 2
                        WHEN 'MODERATE' THEN 3
                        WHEN 'LOW' THEN 4
                    END
            """)
            
            print("\n📊 Student Safety Risk Distribution:")
            for risk, count, avg_score in cur.fetchall():
                print(f"   {risk:10} | {count:5} properties | Avg Score: {avg_score}")
            
            cur.execute("""
                SELECT 
                    landlord_locality,
                    COUNT(*) as count,
                    ROUND(AVG(trustability_score), 2) as avg_score,
                    ROUND(AVG(landlord_score), 2) as avg_landlord_score
                FROM property_intelligence
                GROUP BY landlord_locality
                ORDER BY avg_score DESC
            """)
            
            print("\n🏠 Landlord Locality Analysis:")
            for locality, count, avg_trust, avg_landlord in cur.fetchall():
                print(f"   {locality:10} | {count:5} properties | Trust: {avg_trust} | Landlord: {avg_landlord}")
            
            cur.execute("""
                SELECT 
                    UNNEST(student_warnings) as warning,
                    COUNT(*) as occurrences
                FROM property_intelligence
                WHERE student_warnings IS NOT NULL AND ARRAY_LENGTH(student_warnings, 1) > 0
                GROUP BY warning
                ORDER BY occurrences DESC
                LIMIT 10
            """)
            
            print("\n⚠️  Top Student Warnings:")
            for warning, count in cur.fetchall():
                print(f"   {warning[:60]:60} | {count:5} properties")
            
            cur.execute("""
                SELECT 
                    ROUND(AVG(trustability_score), 2) as avg_trust,
                    ROUND(AVG(safety_score), 2) as avg_safety,
                    ROUND(AVG(maintenance_score), 2) as avg_maint,
                    ROUND(AVG(landlord_score), 2) as avg_landlord
                FROM property_intelligence
            """)
            
            avg_trust, avg_safety, avg_maint, avg_landlord = cur.fetchone()
            print(f"\n✨ Average Scores for UCity Student Rentals:")
            print(f"   Overall Trustability: {avg_trust}/100")
            print(f"   Safety:              {avg_safety}/100")
            print(f"   Maintenance:         {avg_maint}/100")
            print(f"   Landlord Quality:    {avg_landlord}/100")
            
            print(f"\n--- Student Property Intelligence ETL complete! ---")
            print(f"successfully analyzed {processed} properties for student safety! 🎓")

except Exception as e:
    print(f"😤 a database error occurred: {e}")
    raise