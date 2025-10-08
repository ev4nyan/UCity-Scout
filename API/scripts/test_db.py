import os
import psycopg
from dotenv import load_dotenv


env_path = '../config/.env'

# This loads the variables from your .env file
load_dotenv(env_path)

# This gets your secret string from the loaded variables
connection_string = os.getenv("DATABASE_URL")

# Make sure it actually found the string!
if not connection_string:
    print("ugh, did you forget to create the .env file, you dummy?")
    print("or maybe you named the variable something other than DATABASE_URL?")
else:
    print("alright, trying to connect to your fancy cloud database...")
    try:
        # This is the magic part: it tries to connect!
        with psycopg.connect(connection_string) as conn:
            
            # If we got here, it means the connection worked!
            # Now, let's ask the database a simple question to prove we can talk.
            with conn.cursor() as cur:
                
                # We'll ask the database what version of postgresql it's running
                cur.execute("SELECT version();")
                
                # Fetch the answer from the database
                db_version = cur.fetchone()
                
                print("🎉 success! connection established!")
                print("your database says its version is:", db_version[0])

    except Exception as e:
        print("😤 hmph. it failed.")
        print("are you sure you copied the connection string correctly into the .env file?")
        print("error:", e)