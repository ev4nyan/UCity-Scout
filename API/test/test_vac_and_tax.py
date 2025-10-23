tax_query = "SELECT * FROM real_estate_tax_balances WHERE location LIKE '4012-30 BARING%';"
vac_query = "SELECT * FROM vacant_property_indicators WHERE location LIKE '4012-30 BARING%';"
table_names_query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
base_url = "https://phl.carto.com/api/v2/sql"

import requests


yes = requests.get(base_url, params={"q": tax_query})


print(yes.text)