import requests

# the url that ACTUALLY exists! hmph!
base = "https://phl.carto.com/api/v2/sql"

query = "SELECT * FROM incidents_part1_part2 LIMIT 5"

print(requests.get(base, params={"q": query}).text)