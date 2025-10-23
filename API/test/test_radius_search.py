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
SELECT * FROM incidents_part1_part2 WHERE ST_DWithin(the_geom::geography,ST_GeographyFromText('POINT(-75.17420317059917 40.02564717274757)'), 200)
'''
# make the request to the api
response = requests.get(api_url, params={'q': radius_query})


# check if it worked (a 200 status code means success!)
if response.status_code == 200:
    print("it worked! 🎉 here's the data:")
    data = response.json()
    elapsed_time = response.elapsed
    # Convert the timedelta to total seconds for a numerical value
    response_time_seconds = elapsed_time.total_seconds()
    print(json.dumps(data, indent=2))

    print(f"Response time: {response_time_seconds} seconds")
    # this just prints it out in a pretty, readable way
else:
    print(f"ugh, it failed. 😤 status code: {response.status_code}")
    print(response.text)