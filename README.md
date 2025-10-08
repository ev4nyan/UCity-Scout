README:
-----
**Philly Public API Links:
**
Licenses and Inspections Code Violations: you already have this one! it's still the #1 most important dataset. the holy grail.
https://opendataphilly.org/datasets/licenses-and-inspections-code-violations/

Department of Records Property Parcels: this is the official map of every single piece of property in the city. it's the base layer of your entire app. everything happens on a parcel. this is how you link different datasets to the same physical location.
https://opendataphilly.org/datasets/department-of-records-property-parcels/

Philadelphia Properties and Assessment History: this is the opa data. it tells you who owns the property, its official value, and its basic characteristics (like square footage). this is how you connect a violation to a specific landlord.
https://opendataphilly.org/datasets/philadelphia-properties-and-assessment-history/

Licenses and Inspections Building and Zoning Permits: this shows the history of construction. was that new kitchen you see in the photos built legally? this dataset knows. a long history of no permits is a bad sign.
https://opendataphilly.org/datasets/licenses-and-inspections-building-and-zoning-permits/

Certified for Rental Suitability: this is the rental license data! it's a simple yes/no: is the landlord legally allowed to rent this property? if the answer is no, that's a gigantic red flag 🚩 you show to the user.
https://opendataphilly.org/datasets/certified-for-rental-suitability/

Nice-to-haves:

Vacant Property Indicators: super useful for a neighborhood score. a block with a lot of vacant buildings feels less safe and stable. your app could warn users about this.
https://opendataphilly.org/datasets/vacant-property-indicators/

Real Estate Tax Balances: this is a sneaky genius move. a landlord who doesn't pay their taxes is probably a landlord who doesn't fix a leaky roof. it's a great way to judge how responsible they are.
https://opendataphilly.org/datasets/real-estate-tax-balances/

Building Demolitions: good for context. nobody wants to sign a lease and find out the building next door is being torn down for the next 12 months.
https://opendataphilly.org/datasets/building-demolitions/

Zillow (Phila. only): as i said before, this is how you'll eventually get the actual, live rental listings. this is what turns your intelligence tool into a real search engine.
https://opendataphilly.org/datasets/zillow-phila-only/


**API dependencies**
```
pip install "psycopg[binary]"
pip install python-dotenv```
