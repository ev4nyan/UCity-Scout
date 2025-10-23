import requests
import json
from utils import geom_utils

api_url = "https://phl.carto.com/api/v2/sql"
query = geom_utils.get_radius_query_from_geom("incidents_part1_part2", 200)


response = requests.get(api_url, params=query)
if response.status_code == 200:
    print("it worked! 🎉 here's the data:")
    data = response.json()
    print(json.dumps(data, indent=2))
else:
    print(f"ugh, it failed. 😤 status code: {response.status_code}")
    print(response.text)