# Crime Incidents ETL — Design & Integration

## Data Source

- **API**: Philadelphia Carto SQL API (`https://phl.carto.com/api/v2/sql`)
- **Table**: `incidents_part1_part2` — all Part I and Part II crime incidents reported to the Philadelphia Police Department
- **Update frequency**: Daily
- **Documentation**: https://opendataphilly.org/datasets/crime-incidents/

## How We Filter

Crime data doesn't have ZIP codes — it uses lat/lng coordinates. Instead of filtering by ZIP like the other ETLs, we use a **geographic bounding box** around University City:

| Bound | Value | Notes |
|-------|-------|-------|
| Lat min | 39.940 | ~200m south of UCity's southern edge |
| Lat max | 39.970 | ~200m north of UCity's northern edge |
| Lng min | -75.225 | ~200m west of 52nd St |
| Lng max | -75.180 | ~200m east of Schuylkill River |

We also apply a **365-day lookback** so only recent incidents are synced. The cutoff date is computed at runtime.

## Table Schema

```sql
CREATE TABLE crime_incidents (
    dc_key TEXT PRIMARY KEY,          -- unique incident identifier
    dc_dist TEXT,                     -- police district number
    psa TEXT,                         -- police service area
    dispatch_date_time TIMESTAMPTZ,   -- full timestamp of dispatch
    dispatch_date TEXT,               -- date portion (YYYY-MM-DD)
    dispatch_time TEXT,               -- time portion (HH:MM:SS)
    ucr_general TEXT,                 -- UCR crime category code
    text_general_code TEXT,           -- human-readable crime type
    location_block TEXT,              -- block-level address
    lat NUMERIC,                      -- latitude
    lng NUMERIC                       -- longitude
);
```

## UCR General Codes (Key Categories)

| Code | Category |
|------|----------|
| 100 | Homicide |
| 200 | Rape |
| 300 | Robbery |
| 400 | Aggravated Assault |
| 500 | Burglary |
| 600 | Theft |
| 700 | Motor Vehicle Theft |
| 800 | Other Assaults |
| 900 | Arson |
| 1500+ | Other (weapons, drugs, fraud, etc.) |

Codes **100–400** are classified as **violent crimes** in our scoring model.

## Property Proximity Matching (100m Radius)

The `property_intelligence` aggregation ETL associates crime with individual properties using a `LEFT JOIN LATERAL`:

```sql
LEFT JOIN LATERAL (
    SELECT
        COUNT(*) AS nearby_crime_count,
        COUNT(*) FILTER (WHERE c.ucr_general IN ('100','200','300','400'))
            AS nearby_violent_crime_count
    FROM crime_incidents c
    WHERE p.lat IS NOT NULL AND p.lng IS NOT NULL
      AND c.lat BETWEEN p.lat - 0.0009 AND p.lat + 0.0009
      AND c.lng BETWEEN p.lng - 0.00117 AND p.lng + 0.00117
) crime ON true
```

### Why those offsets?

At Philadelphia's latitude (~40°N):
- **1° latitude ≈ 111,320 meters** → 100m ≈ **0.0009°**
- **1° longitude ≈ 111,320 × cos(40°) ≈ 85,276 meters** → 100m ≈ **0.00117°**

This creates a rectangular bounding box approximation of a 100m radius. It slightly over-counts at the corners (~141m diagonal) but is fast in pure SQL without PostGIS.

### Prerequisite

The `properties` table must include `lat` and `lng` columns (pulled from `opa_properties_public` on Carto). These were added to `etl_properties.py` as part of this integration.

## Scoring Impact

Crime data feeds into the **safety_score** in `property_intelligence`:

```
safety_score = 100
    - (violation_count × 10)
    - (open_violation_count × 20)
    - (tax_num_years_owed × 5)       [if tax delinquent]
    - (min(nearby_crime_count, 20) × 1)   ← NEW
    - (nearby_violent_crime_count × 3)     ← NEW
```

- Total crime is capped at 20 incidents (max -20 penalty) to prevent one hotspot from zeroing out the score
- Violent crime has a 3× multiplier with no cap

## Risk Flags & Student Warnings

| Flag | Condition |
|------|-----------|
| `HIGH_CRIME_AREA` | 15+ crime incidents within 100m |
| *Student warning*: "Violent crime incidents reported nearby" | 3+ violent crime incidents within 100m |
| *Student warning*: "High volume of crime near this property" | 15+ total crime incidents within 100m |

## Workflow

The crime ETL runs in the daily-sync GitHub Action after the other data ETLs but **before** the property intelligence build:

```
Properties → Violations → Permits → Licenses → Crime → Property Intelligence
```

This ensures `crime_incidents` and `properties.lat/lng` are both populated before the LATERAL join executes.
