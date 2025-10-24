import requests
import json
import os
import sys
from pathlib import Path

script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
sys.path.insert(0, str(project_root / 'utils'))
import geom_utils

api_url = "https://phl.carto.com/api/v2/sql"
query = geom_utils.get_radius_query_from_geom("vacant_property_indicators", 200, "0101000020E6100000D350DE5127CC52C0C56F414B5FFB4340")
print(query)
response = requests.get(api_url, params=query)
if response.status_code == 200:
    print("it worked! 🎉 here's the data:")
    data = response.json()
    print(json.dumps(data, indent=2))
else:
    print(f"ugh, it failed. 😤 status code: {response.status_code}")
    print(response.text)