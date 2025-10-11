import requests
import json

BASE_API_URL = "https://phl.carto.com/api/v2/sql"

# We are spying on the 'business_licenses' table this time!
# Let's see what secrets it's hiding...
spy_query = "SELECT * FROM business_licenses LIMIT 5"

print("🕵️‍♀️ deploying spy script to investigate the business licenses data...")
print("(this time i'll be more patient, i guess... hmph!)")

try:
    # I added a timeout of 30 seconds! Now it will wait longer.
    response = requests.get(BASE_API_URL, params={'q': spy_query}, timeout=30)
    response.raise_for_status()  # This will raise an error if the request was bad

    print("✨ mission successful! we've acquired the intel. here are the files:")
    data = response.json()
    
    if not data.get('rows'):
        print("\n...hmph. the server responded, but it gave us an empty box. how rude!")
        print("maybe the 'business_licenses' table is empty or we have the wrong name?")
    else:
        print(json.dumps(data, indent=2))
        print("\n--- Mission Debrief ---")
        print("agent evan, your new mission is to analyze these records.")
        print("1. find the field that actually contains the zip code. is it `zip`? or something else?")
        print("2. find the field that says 'Rental'. is it `licensetype`? or something else?")

except requests.exceptions.Timeout:
    print("😤 ugh! the server took too long to answer! it's so rude!")
    print("maybe try again in a little bit?")
except requests.exceptions.RequestException as e:
    print(f"😤 our spy mission has been compromised! status code: {e.response.status_code if e.response else 'Unknown'}")
    print(f"error: {e}")

