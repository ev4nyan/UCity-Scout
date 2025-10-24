import requests
import json

base_url = "https://services.arcgis.com/fLeGjb7u4uXqeF9q/ArcGIS/rest/services/Vacant_Indicators_Bldg/FeatureServer/0/query"

# Hmph. Here are the parameters.
# This is much cleaner than a giant URL string!
query_params = {
    'where': "zipcode='19104'",
    'resultRecordCount': 1,
    'outFields': '*',
    'f': 'json'
}

print("Sending a REAL query this time...")

try:
    response = requests.get(base_url, params=query_params, timeout=20)
    response.raise_for_status() # This will raise an error for bad status codes like 400 or 500

    print("✨ It worked, obviously! Here's the count of properties found:")
    data = response.json()
    print(data)
    if 'features' in data:
        print(f"Found {len(data['features'])} properties matching your query.")
        # You can now loop through data['features'] to see them all
    else:
        # Sometimes ArcGIS sends back a count instead of features
        if 'count' in data:
             print(f"Found {data['count']} properties matching your query.")
        else:
             print("Query was successful, but no matching features were found.")


except requests.exceptions.RequestException as e:
    print(f"Ugh, an error happened: {e}")