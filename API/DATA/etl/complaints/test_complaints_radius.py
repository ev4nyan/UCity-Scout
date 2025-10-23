import requests
import json

api_url = "https://phl.carto.com/api/v2/sql"

geom_query = '''
SELECT
  ST_Y(the_geom) AS latitude,
  ST_X(the_geom) AS longitude
FROM
    complaints
WHERE
  cartodb_id = 1;
'''
radius_query = '''
SELECT * FROM complaints WHERE ST_DWithin(the_geom::geography,ST_GeographyFromText('POINT(-75.17420317059917 40.02564717274757)'), 200)
'''
response = requests.get(api_url, params={'q': radius_query})

if response.status_code == 200:
    print("it worked! 🎉 here's the data:")
    data = response.json()
    print(json.dumps(data, indent=2))
else:
    print(f"ugh, it failed. 😤 status code: {response.status_code}")
    print(response.text)