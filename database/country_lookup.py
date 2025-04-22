"""
Country lookup utilities for venue processing
"""

# Country mapping based on country code (ISO 2-letter codes)
COUNTRY_CODE_TO_NAME = {
    "UK": "United Kingdom",
    "GB": "United Kingdom",
    "DE": "Germany", 
    "FR": "France",
    "IT": "Italy",
    "ES": "Spain",
    "NL": "Netherlands",
    "BE": "Belgium",
    "SE": "Sweden",
    "DK": "Denmark",
    "NO": "Norway",
    "FI": "Finland",
    "AT": "Austria",
    "CH": "Switzerland",
    "IE": "Ireland",
    "PT": "Portugal",
    "GR": "Greece",
    "PL": "Poland",
    "CZ": "Czech Republic",
    "HU": "Hungary",
    "RO": "Romania",
    "BG": "Bulgaria",
    "HR": "Croatia",
    "SK": "Slovakia",
    "SI": "Slovenia",
    "LU": "Luxembourg",
    "MT": "Malta",
    "CY": "Cyprus",
    "EE": "Estonia",
    "LV": "Latvia",
    "LT": "Lithuania",
    # Add more country codes as needed
}

# City to country mapping for common European cities
CITY_TO_COUNTRY = {
    "London": "United Kingdom",
    "Manchester": "United Kingdom",
    "Birmingham": "United Kingdom",
    "Glasgow": "United Kingdom",
    "Edinburgh": "United Kingdom",
    "Liverpool": "United Kingdom",
    "Sheffield": "United Kingdom",
    "Leeds": "United Kingdom",
    "Bristol": "United Kingdom",
    "Cardiff": "United Kingdom",
    "Paris": "France",
    "Lyon": "France",
    "Marseille": "France",
    "Berlin": "Germany",
    "Munich": "Germany",
    "Hamburg": "Germany",
    "Frankfurt": "Germany",
    "Madrid": "Spain",
    "Barcelona": "Spain",
    "Rome": "Italy",
    "Milan": "Italy",
    "Amsterdam": "Netherlands",
    "Brussels": "Belgium",
    "Stockholm": "Sweden",
    "Copenhagen": "Denmark",
    "Oslo": "Norway",
    "Helsinki": "Finland",
    "Vienna": "Austria",
    "Zurich": "Switzerland",
    "Geneva": "Switzerland",
    "Dublin": "Ireland",
    "Lisbon": "Portugal",
    "Athens": "Greece",
    "Warsaw": "Poland",
    "Prague": "Czech Republic",
    "Budapest": "Hungary",
    # Add more cities as needed
}

def determine_country_from_venue(venue_data):
    """
    Determine the country for a venue based on venue data from Ticketmaster API.
    
    Args:
        venue_data (dict): Venue data from Ticketmaster API
        
    Returns:
        str: The country name or None if country couldn't be determined
    """
    # Check if country is directly provided in the venue data
    if venue_data.get('country') and venue_data['country'].get('name'):
        return venue_data['country']['name']
    
    # Check if the country code is provided
    if venue_data.get('country') and venue_data['country'].get('countryCode'):
        country_code = venue_data['country']['countryCode']
        if country_code in COUNTRY_CODE_TO_NAME:
            return COUNTRY_CODE_TO_NAME[country_code]
    
    # Try to determine country from city
    if venue_data.get('city') and venue_data['city'].get('name'):
        city_name = venue_data['city']['name']
        if city_name in CITY_TO_COUNTRY:
            return CITY_TO_COUNTRY[city_name]
    
    # Try to determine from address
    if venue_data.get('address') and venue_data['address'].get('line1'):
        address = venue_data['address']['line1'].lower()
        
        # Check for country names in address
        for country_name in set(COUNTRY_CODE_TO_NAME.values()):
            if country_name.lower() in address:
                return country_name
    
    # Try to determine from postal code patterns
    if venue_data.get('postalCode'):
        postal_code = venue_data['postalCode']
        
        # UK postal codes typically start with letters
        if postal_code and any(c.isalpha() for c in postal_code):
            return "United Kingdom"
            
        # French postal codes are 5 digits and start with a specific range
        if postal_code and len(postal_code) == 5 and postal_code.isdigit():
            first_two = postal_code[:2]
            if 1 <= int(first_two) <= 95:
                return "France"
                
        # German postal codes are 5 digits
        if postal_code and len(postal_code) == 5 and postal_code.isdigit():
            return "Germany"
    
    # Default for European venues when no other determination is possible
    return None

def is_european_venue(venue_data):
    """
    Determine if a venue is in Europe based on the available information.
    
    Args:
        venue_data (dict): Venue data from Ticketmaster API
        
    Returns:
        bool: True if the venue is likely in Europe, False otherwise
    """
    # Check country code
    if venue_data.get('country') and venue_data['country'].get('countryCode'):
        country_code = venue_data['country']['countryCode']
        return country_code in COUNTRY_CODE_TO_NAME
    
    # Check if country name is provided and is European
    if venue_data.get('country') and venue_data['country'].get('name'):
        country_name = venue_data['country']['name']
        return country_name in COUNTRY_CODE_TO_NAME.values()
    
    # Check if city is known European city
    if venue_data.get('city') and venue_data['city'].get('name'):
        city_name = venue_data['city']['name']
        return city_name in CITY_TO_COUNTRY
        
    # Otherwise, we can't determine if it's European
    return False 