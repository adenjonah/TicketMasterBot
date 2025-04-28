import sys
import re
import urllib.parse
import logging
from urllib.parse import urlparse, quote, unquote

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("url_test")

# Problematic URL found in the database
PROBLEMATIC_URL = 'Https://lepointdevente.com/billets/ff1250703001'

def _fix_url(url):
    """Ensures a URL has the correct http/https scheme and is well-formed."""
    if not url:
        return "https://example.com"  # Fallback URL if none is provided
    
    # For logging only in debug mode
    original_url = url
    
    try:
        # Remove any whitespace and control characters
        url = url.strip()
        url = re.sub(r'[\x00-\x1F\x7F]', '', url)  # Remove control characters
        
        # Handle specific case with capitalized protocol (Https://, Http://)
        # Discord requires lowercase protocol
        if url.startswith('Https://'):
            url = 'https://' + url[8:]
        elif url.startswith('Http://'):
            url = 'http://' + url[7:]
        
        # Check for common malformed URLs
        elif url.startswith('ttps://'):
            url = 'https://' + url[7:]
        elif url.startswith('hhttps://'):
            url = 'https://' + url[8:]
        elif url.startswith('http:/www.'):
            url = 'http://www.' + url[9:]
        elif url.startswith('https:/www.'):
            url = 'https://www.' + url[10:]
        elif url.startswith('www.'):
            url = 'https://' + url
        elif not (url.startswith('http://') or url.startswith('https://')):
            url = 'https://' + url
        
        # Replace double slashes (except after protocol)
        url = re.sub(r'(?<!:)//+', '/', url)
        
        # Fix potential percent encoding issues
        try:
            # First decode any already encoded parts to avoid double encoding
            decoded_url = unquote(url)
            
            # Parse into components
            parsed = urlparse(decoded_url)
            
            # Basic validation
            if not parsed.netloc:
                logger.warning(f"URL missing domain: {url}")
                return "https://example.com"
                
            # Ensure the URL components are properly encoded
            path = quote(parsed.path, safe='/-_.~')
            query = quote(parsed.query, safe='=&-_.~')
            fragment = quote(parsed.fragment, safe='-_.~')
            
            # Reconstruct the URL with encoded components
            # Always use lowercase scheme (http or https) as required by Discord
            scheme = parsed.scheme.lower()
            fixed_url = f"{scheme}://{parsed.netloc}{path}"
            if query:
                fixed_url += f"?{query}"
            if fragment:
                fixed_url += f"#{fragment}"
                
            # One final validation with regex for RFC 3986 compliant URLs
            if not re.match(r'^(https?):\/\/[^\s/$.?#].[^\s]*$', fixed_url):
                logger.warning(f"URL failed final validation: {fixed_url}")
                return "https://example.com"
            
            logger.debug(f"Fixed URL: '{original_url}' -> '{fixed_url}'")
            return fixed_url
            
        except Exception as e:
            logger.warning(f"Error encoding URL components: {e}")
            return "https://example.com"
            
    except Exception as e:
        logger.error(f"Error fixing URL: {e}")
        return "https://example.com"

def is_valid_discord_url(url):
    """Check if a URL is valid for Discord embeds."""
    # Discord's URL validation requires:
    # 1. Valid scheme (http or https, lowercase)
    # 2. Valid domain
    # 3. Well-formed URL according to RFC 3986
    if not url:
        return False
        
    try:
        parsed = urlparse(url)
        
        # Check for valid scheme
        if parsed.scheme not in ['http', 'https']:
            return False
            
        # Check for valid domain
        if not parsed.netloc:
            return False
            
        # Check overall format with regex
        if not re.match(r'^(https?):\/\/[^\s/$.?#].[^\s]*$', url):
            return False
            
        return True
    except Exception:
        return False

def test_url_fix():
    print(f"Testing URL fixing with problematic URL: '{PROBLEMATIC_URL}'")
    
    # Test our fixed function
    fixed_url = _fix_url(PROBLEMATIC_URL)
    print(f"Fixed URL: '{fixed_url}'")
    
    # Validate if it would work with Discord
    is_valid = is_valid_discord_url(fixed_url)
    print(f"Is valid for Discord: {is_valid}")
    
    # Compare with direct lowercase conversion
    simple_fixed = PROBLEMATIC_URL.lower()
    print(f"Simple lowercase: '{simple_fixed}'")
    is_valid_simple = is_valid_discord_url(simple_fixed)
    print(f"Simple fix valid for Discord: {is_valid_simple}")
    
    # Test parsed components
    parsed = urlparse(fixed_url)
    print("\nParsed components:")
    print(f"  Scheme: '{parsed.scheme}'")
    print(f"  Netloc: '{parsed.netloc}'")
    print(f"  Path: '{parsed.path}'")
    
    # Generate a link that would definitely work
    fallback = f"https://www.ticketmaster.com/event/1AsZk19Gkd3D7VP"
    print(f"\nFallback URL: '{fallback}'")
    print(f"Fallback valid for Discord: {is_valid_discord_url(fallback)}")

if __name__ == "__main__":
    test_url_fix() 