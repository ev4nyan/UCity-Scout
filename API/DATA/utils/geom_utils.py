from shapely import wkb
from shapely.errors import WKBReadingError
import requests
base_url = "https://phl.carto.com/api/v2/sql"

def transform_geom_to_lat_lon(the_geom_hex: str) -> tuple | None:
    if not the_geom_hex:
        print("you gave me nothing, you dummy!")
        return None

    try:
        geom_bytes = bytes.fromhex(the_geom_hex)   
        point = wkb.loads(geom_bytes)
        latitude = point.y
        longitude = point.x
        
        return (latitude, longitude)
    except (WKBReadingError, ValueError) as e:
        print(f"ugh, i couldn't read that! are you sure it's correct? error: {e}")
        return None

    
def get_radius_query_from_geom(endpoint: str, radius: int, geom_hex: str):
    lat_lon = transform_geom_to_lat_lon(geom_hex)
    lat, lon = lat_lon[0], lat_lon[1]
    # lon lat for filter instead of lat lon
    filter = f'ST_DWithin(the_geom::geography,ST_GeographyFromText(\'POINT({lon} {lat})\'), {radius})'
    query = {"q": f'SELECT * FROM {endpoint} WHERE {filter}'}
    return query
    

def get_radius_query_from_address(endpoint: str, radius: int, address: str):
    return