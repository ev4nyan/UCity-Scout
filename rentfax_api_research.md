# RentFax — API & Data Source Reference

**A comprehensive inventory of APIs and public datasets relevant to building a Carfax-style rental property history tool for the Philadelphia area.**

---

## Overview

This document catalogs every data source — free local, free national, and commercial — that can power a rental property report. Sources are grouped by data type, with endpoint info, update frequency, cost, and relevance to the RentFax use case noted for each.

---

## Philadelphia-Local Free APIs

These are free, publicly available APIs maintained by the City of Philadelphia and updated regularly. They are the backbone of a Philly-specific product.

---

### Property Identity & Ownership

**Philadelphia Properties & Assessment History**
- **Source:** OpenDataPhilly / Office of Property Assessment (OPA)
- **Endpoint:** `https://phl.carto.com/api/v2/sql?q=SELECT * FROM opa_properties_public WHERE location='<ADDRESS>'`
- **What it contains:** Owner name, mailing address, land use code, zoning, year built, number of stories, total livable area, number of bedrooms/bathrooms, garage spaces, basement type, exterior condition, interior condition, total assessed value (land + building), market value, taxable land/building values, homestead/abatement flags
- **Update frequency:** Nightly[cite:1]
- **Cost:** Free
- **Relevance:** Foundation record for every property. Surfaces ownership, physical characteristics, and market value used to anchor the report.

**Property Assessment History**
- **Source:** OpenDataPhilly / OPA
- **Endpoint:** `https://phl.carto.com/api/v2/sql?q=SELECT * FROM assessments WHERE parcel_number='<OPA_ACCOUNT>'`
- **What it contains:** Year-over-year assessed values for each property going back many years
- **Update frequency:** Nightly[cite:1]
- **Cost:** Free
- **Relevance:** Shows whether a landlord's property is gaining or losing assessed value — useful context for investment quality.

**Department of Records Property Parcels**
- **Source:** OpenDataPhilly / Department of Records (DOR)
- **Endpoint:** Available via ArcGIS REST or Carto SQL API
- **What it contains:** Legal parcel boundaries (GeoJSON/SHP), parcel ID, deed cross-references
- **Update frequency:** Continuous as deeds are recorded[cite:2]
- **Cost:** Free
- **Relevance:** Provides the GIS geometry for map views and parcel-level joins.

---

### Ownership Transfers & Deed History

**Real Estate Transfers (Deeds / Mortgages / Sheriff Deeds)**
- **Source:** OpenDataPhilly / Department of Records
- **URL:** `https://data.phila.gov/visualizations/real-estate-transfers`
- **API:** Available via Carto SQL API
- **What it contains:** All property transfer transactions recorded from December 1999 to present — deed type (sale, sheriff, gift), sale date, grantor, grantee, sale price, realty transfer tax paid, document type, recording date[cite:5]
- **Update frequency:** Continuously updated as documents are recorded
- **Cost:** Free
- **Relevance:** Core ownership timeline. Enables "how many times has this property changed hands?" and flags sheriff/foreclosure deeds, which are major red flags.

---

### Rental Licensing

**eCLIPSE Rental License Lookup**
- **Source:** City of Philadelphia Department of Licenses & Inspections
- **URL:** `https://eclipse.phila.gov/phillylmsprod/pub/lms/Default.aspx?PossePresentation=BusinessLicenseSearchByLocRent`
- **What it contains:** Whether a property has an active rental license (license type "3202 Rental"), license number, expiration date, licensee name[cite:28]
- **Update frequency:** Real-time
- **Cost:** Free (no documented public API — scraping or Atlas lookups required)
- **Relevance:** Critical flag. In Philadelphia, it is **illegal** for a landlord to collect rent without a valid rental license[cite:25]. An expired or missing license is the #1 red flag for tenants.

**L&I Property History Tool**
- **Source:** City of Philadelphia L&I
- **URL:** `https://li.phila.gov/property-history`
- **What it contains:** All business licenses (including rental), violations, permits, and inspections for any address[cite:28]
- **Cost:** Free (web interface; scraping required for API access)
- **Relevance:** Good fallback / cross-reference for the rental license + violations combo.

---

### Code Violations & Complaints

**L&I Code Violations**
- **Source:** OpenDataPhilly / Department of Licenses & Inspections
- **Endpoint:** `https://phl.carto.com/api/v2/sql?q=SELECT * FROM violations WHERE address='<ADDRESS>'`
- **API Docs:** `https://cityofphiladelphia.github.io/carto-api-explorer/#violations`
- **What it contains:** Violation case number, violation date, violation code, description, compliance date, status (open/closed), inspector name[cite:16]
- **Update frequency:** Daily[cite:31]
- **Cost:** Free
- **Relevance:** The most direct signal of housing quality and landlord negligence. Open violations with no compliance date are especially damaging.

**L&I Unsafe Buildings**
- **Source:** OpenDataPhilly / L&I
- **Endpoint:** `https://cityofphiladelphia.github.io/carto-api-explorer/#unsafe`
- **What it contains:** Properties officially declared structurally unsafe or imminently dangerous[cite:20]
- **Cost:** Free
- **Relevance:** Highest-severity flag. A property on this list should generate an automatic warning in any report.

**L&I Complaints (311 Complaints routed to L&I)**
- **Source:** OpenDataPhilly / L&I
- **Endpoint:** `https://phl.carto.com/api/v2/sql?q=SELECT * FROM complaints WHERE address='<ADDRESS>'`
- **What it contains:** Every complaint submitted via 311 or directly to L&I — complaint type, date, resolution status. Formerly called "Service Requests"[cite:23]
- **Update frequency:** Daily
- **Cost:** Free
- **Relevance:** Complaints are pre-violation signals — they show a history of tenant grievances even when no formal violation was issued.

**L&I Case Investigations**
- **Source:** data.gov / L&I
- **What it contains:** All completed property maintenance investigations by L&I inspectors, with violation writeups[cite:17]
- **Cost:** Free
- **Relevance:** Deeper detail than the complaints or violations tables. Shows what inspectors actually found on-site.

---

### Building Permits

**L&I Building & Zoning Permits (2007–Present)**
- **Source:** OpenDataPhilly / L&I
- **Endpoint:** `https://phl.carto.com/api/v2/sql?q=SELECT * FROM permits WHERE address='<ADDRESS>'`
- **What it contains:** Permit type, issue date, expiration date, status, applicant name, contractor info, work description, estimated job cost[cite:31]
- **Update frequency:** Daily[cite:31]
- **Cost:** Free
- **Relevance:** Shows renovation and repair history. Unpermitted work is a liability. Frequent permit activity may indicate either good maintenance or chronic structural issues.

**Permit Contractors**
- **Source:** OpenDataPhilly / L&I
- **What it contains:** Contractor names and license numbers associated with permitted work[cite:31]
- **Cost:** Free
- **Relevance:** Supplemental data for understanding who has worked on the property.

---

### Eviction Records

**Philadelphia Municipal Court Landlord-Tenant Docket**
- **Source:** First Judicial District of Pennsylvania
- **URL:** `https://fjdclaims.phila.gov`
- **What it contains:** All Landlord-Tenant (LT) filings — landlord name, tenant name, case filing date, judgment outcome, continuances[cite:27]
- **Cost:** Free (public access; no official API — scraping or manual lookup)
- **Relevance:** The landlord eviction history is a key signal. A landlord with a pattern of eviction filings may indicate predatory practices or poorly managed properties. Note: the Philadelphia Bar Association has proposed sealing dismissed eviction records[cite:24].

**LSC Civil Court Data Initiative — Eviction Tracker**
- **Source:** Legal Services Corporation
- **URL:** `https://civilcourtdata.lsc.gov/data/eviction/pennsylvania/philadelphia/`
- **What it contains:** Multi-year eviction filing trend data for Philadelphia County, with Census cross-references (rent burden, housing units, renter population)[cite:21]
- **Cost:** Free
- **Relevance:** Useful for neighborhood-level eviction rate context rather than individual property lookup.

---

### Crime Data

**Crime Incidents (2006–Present)**
- **Source:** OpenDataPhilly / Philadelphia Police Department
- **Endpoint:** `https://phl.carto.com/api/v2/sql?q=SELECT * FROM incidents_part1_part2 WHERE lat > X AND lat < Y AND lng > A AND lng < B`
- **What it contains:** Incident type, date/time, dispatch date, location (lat/long and block-level address), UCR general code, text general (crime type description)[cite:44][cite:47]
- **Update frequency:** Daily (30-day API also available)[cite:47]
- **Cost:** Free
- **Relevance:** Enables neighborhood safety scoring within a configurable radius of any property. Filter by incident type for violent vs. property crimes.

---

### Zoning & Land Use

**Zoning / Planning Data**
- **Source:** City of Philadelphia / PHLmaps (ArcGIS)
- **URL:** `https://data-phl.opendata.arcgis.com/search?categories=%252Fcategories%252Fproperty`
- **What it contains:** Zoning classification, zoning overlay districts, flood zone designations, historic district designations[cite:11]
- **Cost:** Free
- **Relevance:** Verifies legal land use, identifies flood risk, and flags historic preservation restrictions that may complicate renovations.

---

### Neighborhood Context

**Atlas.phila.gov (Aggregator Tool)**
- **Source:** City of Philadelphia
- **URL:** `https://atlas.phila.gov`
- **What it contains:** A unified lookup tool aggregating OPA assessment data, L&I permits/violations/licenses, deed history, 311 complaints, zoning, voting district, and more — all by address[cite:49][cite:55]
- **Cost:** Free
- **Relevance:** Use as a cross-reference and QA tool during development. Atlas is essentially a front-end for the same Carto APIs listed above.

---

## National Free APIs

---

### U.S. Census Bureau

**American Community Survey (ACS) 5-Year Data**
- **Source:** U.S. Census Bureau
- **Endpoint:** `https://api.census.gov/data/2024/acs/acs5?get=<VARIABLES>&for=tract:<TRACT>&in=state:42+county:101`
- **What it contains:** At census tract / block group level: rent burden (% income spent on rent), housing unit counts, renter vs. owner population, vacancy rates, median gross rent, median household income, poverty rate, housing age[cite:36]
- **Update frequency:** Annual (5-year rolling)
- **Cost:** Free (API key required, free)
- **Relevance:** Neighborhood-level context. Rent burden and vacancy rates are critical signals for market health around a property. Philadelphia is FIPS state `42`, county `101`.

**Rental Housing Finance Survey (RHFS)**
- **Source:** U.S. Census Bureau
- **What it contains:** Financial, mortgage, and property characteristics of rental housing properties nationwide[cite:39]
- **Cost:** Free
- **Relevance:** Macro benchmarking — useful for investor-facing features comparing Philadelphia rental market to national averages.

---

## Commercial APIs

These require paid subscriptions but offer national coverage, deeper data, and clean APIs. Relevant if the app expands beyond Philadelphia or needs data not in public sources.

| Provider | Data Coverage | Key Data Points | Pricing | Free Tier |
|----------|--------------|----------------|---------|-----------|
| **ATTOM Data** | 158M properties, 35B records[cite:43] | Sales history (10 yrs), deed/mortgage, AVM, permits, tax assessments, foreclosure activity, vacancy rates, school data[cite:38][cite:41] | ~$95/month entry[cite:50] | Free trial |
| **HouseCanary** | 136M properties, 20-yr HPI[cite:43] | Institutional-grade AVM, 36-month price forecasts, fair-market rent estimates, risk analytics[cite:53] | Custom / ~$0.50/call[cite:53] | None documented |
| **BatchData** | 155M properties, 30+ years[cite:43] | Bulk processing, MLS data add-on (+$600/mo), building permits add-on (+$1,250/mo), skip tracing, owner data[cite:53] | $1,000/month+[cite:53] | None |
| **Mashvisor** | 150M properties, 36 months STR[cite:43] | Short-term rental analytics (Airbnb comps), LTR income projections, ROI calculations, 11M+ active STR listings[cite:50] | Tiered, usage-based | 7-day trial (30 credits) |
| **Zillow Bridge / Public Records API** | Full U.S. parcel coverage | Parcel + assessment + transactional county data (~15 years back)[cite:10] | Invite-only / commercial | None |

---

## Atlas of Useful Data Fields (By Report Section)

The table below maps each section of a RentFax report to the specific API fields that populate it.

| Report Section | Data Fields | Source |
|----------------|------------|--------|
| **Property Identity** | Owner name, OPA account, parcel ID, year built, property type, total area, lot size, zoning | OPA Properties API[cite:1] |
| **Ownership History** | Grantor, grantee, deed type, sale date, sale price, transfer tax | DOR Real Estate Transfers[cite:5] |
| **Rental License Status** | License number, type (3202), status, expiration date, licensee | eCLIPSE[cite:28] / L&I Property History[cite:28] |
| **Code Violations** | Violation code, description, date issued, compliance date, open/closed status | L&I Violations API[cite:16] |
| **Unsafe Building Flag** | Unsafe building designation date, address, reason | L&I Unsafe Buildings[cite:20] |
| **Permit History** | Permit type, issue date, status, work description, contractor, estimated cost | L&I Permits API[cite:31] |
| **Complaint History** | Complaint type, date filed, resolution, source (311 or L&I) | L&I Complaints API[cite:23] |
| **Eviction History** | Case filing date, plaintiff (landlord), defendant (tenant), outcome | FJD Claims[cite:27] |
| **Neighborhood Crime** | Crime type, date, distance from property | Crime Incidents API[cite:44] |
| **Assessment / Value** | Assessed land value, assessed building value, market value, year-over-year delta | OPA Assessment History[cite:1] |
| **Neighborhood Context** | Rent burden %, vacancy rate, median rent, % renters, poverty rate | ACS 5-Year Census API[cite:36] |
| **Flood / Zoning Risk** | Zoning class, flood zone, overlay district, historic designation | PHLmaps ArcGIS[cite:11] |

---

## Integration Architecture Notes

### Carto SQL API (Primary query layer for Philly data)
Most OpenDataPhilly datasets are served through Carto's SQL API. The pattern is:

```
GET https://phl.carto.com/api/v2/sql?q=SELECT * FROM {table} WHERE {column}='{value}'
```

Key tables:
- `opa_properties_public` — OPA property characteristics
- `assessments` — assessment history
- `violations` — L&I code violations
- `permits` — building permits
- `complaints` — L&I complaints (formerly Hansen service requests)
- `incidents_part1_part2` — crime incidents

### ArcGIS REST API (PHLmaps)
Zoning, parcel boundaries, and some L&I data are served through ArcGIS:
```
GET https://services.arcgis.com/fLeGjb7u4uXqeF9q/arcgis/rest/services/{layer}/FeatureServer/0/query?where=ADDRESS='{address}'&outFields=*&f=json
```

### Census API
```
GET https://api.census.gov/data/2024/acs/acs5?get=B25070_001E,B25032_001E,B25008_001E&for=tract:*&in=state:42+county:101&key={API_KEY}
```
Replace `B25070_001E` etc. with the variable codes for rent burden, housing units, and renter population.

### Rate Limits & Usage Notes
- Carto/OpenDataPhilly APIs: No documented rate limits for reasonable use; large datasets recommend using the CSV download + local storage
- Census API: No rate limit; free API key at api.census.gov
- eCLIPSE / FJD Claims: No public API — web scraping required; check ToS before implementing
- ATTOM: Free trial available; key for adding national data post-MVP

---

## Priority Recommendation for MVP

| Priority | Source | Why |
|----------|--------|-----|
| P0 | OPA Properties API | Anchor record for every report |
| P0 | L&I Violations API | Most direct quality signal |
| P0 | eCLIPSE Rental License | Legal compliance flag — most impactful feature |
| P0 | DOR Real Estate Transfers | Ownership history timeline |
| P1 | L&I Permits API | Renovation/repair history |
| P1 | L&I Complaints API | Pre-violation signals |
| P1 | Crime Incidents API | Neighborhood safety score |
| P1 | FJD Claims (evictions) | Landlord behavior history |
| P2 | ACS Census API | Neighborhood context panel |
| P2 | L&I Unsafe Buildings | Edge case but high-severity flag |
| P3 | ATTOM / HouseCanary | National expansion / AVM features |

