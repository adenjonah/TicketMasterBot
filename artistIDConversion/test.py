import requests
import re

# List of artist IDs

    # "1094215", "1159272", "2453935", "2811359", "1508961", "2404695", "3168081", "3103513",
    # "3251698", "731454", "806431", "766720", "806203", "3184880", "807367", "770768", "1435919",
    # "2222681", "2892837", "2782189", "1957114", "736262", "2150342", "1020885", "2253625",
    # "2288122", "734977", "3175130", "1567745", "2625223", "1747243", "1788754", "2001092",
    # "2257710", "772848", "735647", "1997046", "798903", "777416", "766722", "2880729", "2903928",
    # "1833710", "2194218", "2119390", "2131374", "768018", "2730221", "718655", "2300002",
    # "2818001", "2869566", "767870", "712214", "2826519", "2397430", "2075742", "862453", "703831",
    # "2712573", "775700", "1113792", "847841", "1057637", "2663489", "863832", "1148845", "2194370",
    # "3164506", "847492", "2431961", "803682", "2660883", "2182670", "732705", "767989", "1429693",
    # "1646704", "2998425", "1536543", "2514177", "779049", "111163", "1896592", "1580836", "3178720",
    # "1904831", "2282847", "2895379", "1638380", "735392", "755226", "2733829", "726146", "2499958",
    # "2590072", "2110227", "2281371", "942726", "2842518", 

artist_ids = [
"1542376", "1319618", "1266616", "1871860",
    "1506392", "1983434", "1013826", "3008978", "2555869", "3109542", "1244865", "2543736", "806762",
    "773309", "3297169", "2433469", "836902", "1114794"
]

output_file = "output.txt"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36"
}

# Regular expression to extract content from <title> tag
title_pattern = re.compile(r"<title>(.*?)</title>", re.IGNORECASE)

# Open output file in write mode to clear it initially
with open(output_file, "w") as f:
    f.write("")

# Loop through each artist ID to fetch data, parse, and extract title content
for artist_id in artist_ids:
    url = f"https://www.ticketmaster.com/artist/{artist_id}"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Ensure the request was successful
        
        # Extract only the first 500 characters from the response for faster parsing
        response_head = response.text[:500]
        
        # Attempt to extract the title content from the head of the response
        match = title_pattern.search(response_head)
        if match:
            artist_title = match.group(1).strip()
            artist_name = artist_title.split(" Tickets")[0].strip()  # Extract artist name only
            
            with open(output_file, "a") as f:
                f.write(f"Artist ID: {artist_id} - {artist_name}\n")
            
            print(f"Extracted artist name: {artist_name}")
        else:
            print(f"No title tag found for artist ID: {artist_id}")
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for artist {artist_id}: {e}")
