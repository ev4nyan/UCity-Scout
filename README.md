README:
-----
**Philly Public API Links:**
Violations (pull from last 5 years) / investigations:
https://opendataphilly.org/datasets/licenses-and-inspections-code-violations/
https://opendataphilly.org/datasets/licenses-and-inspections-case-investigations/

General Property Info:
https://opendataphilly.org/datasets/philadelphia-properties-and-assessment-history/

Zoning Permits:
https://opendataphilly.org/datasets/licenses-and-inspections-building-and-zoning-permits/

Rental Licenses / CRS:
https://opendataphilly.org/datasets/licenses-and-inspections-business-licenses/
https://opendataphilly.org/datasets/certified-for-rental-suitability/

Crime (100 meters):
https://opendataphilly.org/datasets/crime-incidents/

Vacant Property Indicator (100 meters):
https://opendataphilly.org/datasets/vacant-property-indicators/

311 Complaints (Property AND 100 meters):
https://opendataphilly.org/datasets/licenses-and-inspections-complaints/

Real Estate Tax Balances: check if prop. owner is tax delinquent
https://opendataphilly.org/datasets/real-estate-tax-balances/



Vacancies:
## good (healthy range): 0-4 properties
this is a normal, healthy number for a thriving city neighborhood. it indicates standard turnover—people moving, apartments being renovated, properties changing hands. a few vacancies are just the sign of a dynamic market. it's like seeing a few empty seats in a popular restaurant; it doesn't mean the business is failing!

what it looks like: a stable, desirable block.

verdict: green flag! 💚 everything is fine here.

## concerning (the yellow flag): 5-12 properties
okay, now you should be paying attention. this isn't a disaster, but it's a warning sign. this number is higher than normal turnover. it could mean a few small apartment buildings are struggling to find tenants, or there's a pocket of neglect on a specific block. the area might be on the edge of a decline or just going through a rough patch.

what it looks like: a block with a couple of noticeably neglected buildings.

verdict: yellow flag. 💛 proceed with caution and look for other warning signs.

## bad (the red flag): 13+ properties
this is a definite red flag. a number this high in a 200-meter radius (about two city blocks) means there are systemic problems. you're likely looking at widespread economic distress, visible blight, and a higher potential for crime. this is the kind of concentration that actively drags down property values and the quality of life for the entire area.

what it looks like: multiple abandoned or boarded-up properties are visible from one spot.

verdict: red flag! 🚩 this indicates significant neighborhood-level issues.

**API dependencies**
```
pip install "psycopg[binary]"
pip install python-dotenv
pip install flask
pip install flask_cors
pip install shapely
```
