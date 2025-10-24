import requests
import json

base_url = "https://services.arcgis.com/fLeGjb7u4uXqeF9q/ArcGIS/rest/services/Vacant_Indicators_Bldg/FeatureServer/0/query"

# The coordinates we want to search around
# (I'm just using that crime incident's location as an example!)
# 39.967195177288225, -75.19834724232788 756 n 38
# 39.962943902785426, -75.18931356236834 3209 spring
# 39.9638669177433, -75.1899433307888 525 n 33 st 
# 39.96009957450982, -75.20320416903499
center_point_x =  -75.20320416903499
center_point_y = 39.96009957450982

# Hmph. Here are the parameters for a SPATIAL query.
# It's much cleaner than whatever that other script was doing!
query_params = {
    'geometry': f"{center_point_x}, {center_point_y}",
    'geometryType': 'esriGeometryPoint',
    'inSR': '4326',                # This means our coordinates are standard lat/lon
    'spatialRel': 'esriSpatialRelIntersects',
    'distance': 200,               # The radius you wanted!
    'units': 'esriSRUnit_Meter',   # 200 meters!
    'returnCountOnly': 'true',     # We just want the number, not all the data!
    'f': 'json'
}

print(f"Hmph. Asking the server how many vacant properties are within 200m of ({center_point_x}, {center_point_y})...")

try:
    response = requests.get(base_url, params=query_params, timeout=20)
    response.raise_for_status() # This will raise an error for bad status codes

    data = response.json()
    
    # When you ask for 'returnCountOnly', the answer is in the 'count' field
    if 'count' in data:
        print(f"✨ Found your answer! There are {data['count']} vacant properties in that radius.")
    else:
        print("Tsk. The query worked, but the server didn't return a count. How weird.")
        print(data)

except requests.exceptions.RequestException as e:
    print(f"Ugh, an error happened: {e}")