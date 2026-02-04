import cloudscraper
import sys

# This script fetches the HTML of a Kwik page, bypassing Cloudflare
scraper = cloudscraper.create_scraper()
try:
    html = scraper.get(sys.argv[1]).text
    print(html)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
