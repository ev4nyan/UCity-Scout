import requests
import json

# i added a limit so you don't accidentally download the whole city!
# seriously, don't remove the "LIMIT 5" for now!!!
api_url = "https://phl.carto.com/api/v2/sql?q=SELECT * FROM violations LIMIT 5"

print("okay, trying to get the data now...")

# make the request to the api
response = requests.get(api_url)

# check if it worked (a 200 status code means success!)
if response.status_code == 200:
    print("it worked! 🎉 here's the data:")
    data = response.json()
    # this just prints it out in a pretty, readable way
    print(json.dumps(data, indent=2))
else:
    print(f"ugh, it failed. 😤 status code: {response.status_code}")
    print(response.text)