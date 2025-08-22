import asyncio
import logging
from scanners.consent_crawler import crawl_with_consent

# Configure basic logging to see the output from the crawler
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def main():
    domain = "kingdomstoreonline.com"
    print(f"--- Starting crawler test for {domain} ---")
    result = await crawl_with_consent(domain)
    print(f"--- Crawler test finished for {domain} ---")
    print("Result:")
    # Pretty print the result dictionary
    import json
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
