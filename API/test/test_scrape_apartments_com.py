import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.edge.service import Service
# We don't need the manager anymore! Hmph!
# from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.edge.options import Options
from pathlib import Path

# --- 1. MISSION PARAMETERS ---
TARGET_URL = "https://www.apartments.com/philadelphia-pa-19104/"

# THIS IS THE NEW PART, YOU DUMMY!
# Tell the script where you put the driver file!
script_dir = Path(__file__).resolve().parent
# If you made a 'drivers' folder next to your 'scripts' folder:
DRIVER_PATH = script_dir.parent / 'driver' / 'msedgedriver.exe'


print("🕵️‍♀️ deploying ADVANCED robot spy to apartments.com...")
print("i'm giving it the tools manually this time so it doesn't get caught by your firewall!")

# --- 2. SETUP OUR ADVANCED SPY (THE EDGE BROWSER... SIGH) ---
edge_options = Options()
edge_options.add_argument("--headless")
edge_options.add_argument("--window-size=1920,1080")
edge_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36")

# This is the new, genius line! No more downloading!
service = Service(executable_path=str(DRIVER_PATH))

driver = None
try:
    # LAUNCH THE SPY! It will use the local file now!
    driver = webdriver.Edge(service=service, options=edge_options)

    # --- 3. EXECUTE THE SPY MISSION ---
    driver.get(TARGET_URL)

    # We still have to be patient!
    time.sleep(5) 

    print("✨ success! we're inside! i guess even an Edge browser can sneak in...")

    # Now we get the FINAL html, after all the javascript has finished.
    final_html = driver.page_source

    # And now we can use our goggles to read it, just like before.
    soup = BeautifulSoup(final_html, 'lxml')

    # --- 4. EXTRACT THE INTEL ---
    listings = soup.find_all('article', class_='placard')

    if not listings:
        print("😤 hmph. my advanced spy got in, but i still couldn't find any listings. they must have changed their website's layout again to trick me! so rude!")
    else:
        print(f"\n--- MISSION REPORT ---")
        print(f"found {len(listings)} listings on the first page. here's the intel:\n")
        
        for listing in listings:
            address_tag = listing.find('div', class_='property-address')
            price_tag = listing.find(class_='property-pricing') # Made this a little more flexible
            
            address = address_tag.text.strip() if address_tag else "Address not found"
            price = price_tag.text.strip() if price_tag else "Price not listed"
            
            print(f"📍 Address: {address}")
            print(f"💰 Price: {price}")
            print("-" * 20)

except Exception as e:
    print(f"\n😤 MISSION FAILED! our advanced spy got caught or something broke!")
    print(f"error: {e}")

finally:
    # A good spy always cleans up after themselves!
    if driver:
        driver.quit()
    print("\n🕵️‍♀️ spy has left the building.")

