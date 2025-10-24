

import requests
url = "https://phl.carto.com/api/v2/sql"

query = "SELECT opa_account_num FROM business_licenses WHERE zip LIKE '19104%' AND (licensetype LIKE 'Rental' OR licensetype LIKE 'High Rise' OR licensetype LIKE 'Vacant Residential Property / Lot')"
query2 = "SELECT COUNT(*) FROM business_licenses WHERE zip LIKE '19104%'"

print(requests.get(url, params={'q': query}).text)
print(requests.get(url, params={'q': query2}).text)