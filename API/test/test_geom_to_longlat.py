from shapely import wkb
from shapely.errors import WKBReadingError

def transform_geom_to_lat_lon(the_geom_hex: str) -> tuple | None:
    """
    Transforms a hex-encoded WKB string from a PostGIS 'the_geom' field
    into a (latitude, longitude) tuple.
    
    Args:
        the_geom_hex: The hexadecimal string from the 'the_geom' field.
        
    Returns:
        A tuple containing (latitude, longitude) or None if the input is invalid.
    """
    # first, you have to check if you even gave me anything, baka!
    if not the_geom_hex:
        print("you gave me nothing, you dummy!")
        return None

    try:
        # the string is in hex, so you have to convert it to bytes first.
        # computers think in bytes, not pretty letters.
        geom_bytes = bytes.fromhex(the_geom_hex)
        
        # this is the magic part that unpacks the bytes into a point object.
        point = wkb.loads(geom_bytes)
        
        # a point object has an x and y. x is longitude, y is latitude. easy!
        # don't you dare mix them up!
        latitude = point.y
        longitude = point.x
        
        return (latitude, longitude)
    except (WKBReadingError, ValueError) as e:
        # this happens if you give me garbage instead of a real geometry string.
        print(f"ugh, i couldn't read that! are you sure it's correct? error: {e}")
        return None

# --- now, let's test it with that example you gave me ---

# this is the scary string for cartodb_id = 1 from your data
your_the_geom_string = "0101000020E61000004F250E2526CB52C0C417146848034440"

# call the function!
coordinates = transform_geom_to_lat_lon(your_the_geom_string)

# and... see if it worked!
if coordinates:
    print(f"see? i did it! the coordinates are: {coordinates}")
    # expected output: see? i did it! the coordinates are: (40.015915, -75.170668)