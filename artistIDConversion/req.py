import requests
import re
import time

# Ticketmaster API Key
API_KEY = "P9v7AOq29cv0AHD4IcP9oq1T5HfiUnb5"
BASE_URL = "https://app.ticketmaster.com/discovery/v2/attractions"

# Input and output files
artists_file = "artists.txt"
output_file = "artist_ids_output.txt"

# Initialize output file
with open(output_file, "w") as f:
    f.write("")

# Read artists from artists.txt
with open(artists_file, "r") as f:
    artists = f.readlines()

# Compile regex to extract artist ID and name
artist_pattern = re.compile(r"Artist ID: (\d+) - (.+)")

for artist_line in artists:
    match = artist_pattern.match(artist_line.strip())
    
    if match:
        artist_id, artist_name = match.groups()
        artist_name_encoded = artist_name.replace(" ", "%20")  # Encode spaces for the URL
        
        # Build API request URL
        url = f"{BASE_URL}?apikey={API_KEY}&keyword={artist_name_encoded}&locale=*"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            # Extract the ID from the response to compare
            attractions = data.get("_embedded", {}).get("attractions", [])
            if attractions:
                tm_artist_id = attractions[0].get("id", "Not Found")
                
                # Write the original and matched artist ID to the output file
                with open(output_file, "a") as f:
                    f.write(f"Original ID: {artist_id} - Name: {artist_name} | API ID: {tm_artist_id}\n")
                
                print(f"Original ID: {artist_id} - Name: {artist_name} | API ID: {tm_artist_id}")
            else:
                print(f"No results found for artist: {artist_name}")
        
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data for artist {artist_name}: {e}")
        
        # Delay of half a second between requests
        time.sleep(0.5)
