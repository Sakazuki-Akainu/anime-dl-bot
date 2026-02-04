import cloudscraper
import sys

# Creates a browser-like session to fool Cloudflare
scraper = cloudscraper.create_scraper()

try:
    # Arg 1 is the URL
    url = sys.argv[1]
    # Fetch the text (HTML or JSON)
    response = scraper.get(url)
    print(response.text)
except Exception as e:
    # If it fails, print nothing or error to stderr
    print(f"Error: {e}", file=sys.stderr)
