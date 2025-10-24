import requests
import json

BASE_API_URL = "https://phl.carto.com/api/v2/sql"

# We are removing the WHERE clause to just peek at the first 5 records
# This lets us see ALL the columns without any filters.
spy_query = "SELECT * FROM permits WHERE address ILIKE '4012-30%' LIMIT 1"

print("🕵️‍♀️ going undercover to spy on the property data schema...")

response = requests.get(BASE_API_URL, params={'q': spy_query})

if response.status_code == 200:
    print("✨ got the secret files! here's what a few records look like:")
    data = response.json()
    print(json.dumps(data, indent=2))
else:
    print(f"😤 our spy mission failed! status code: {response.status_code}")
    print(response.text)
