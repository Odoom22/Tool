import asyncio
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

def get_network_requests(driver):
    """Extracts network request URLs from performance logs."""
    urls = []
    try:
        logs = driver.get_log('performance')
        for entry in logs:
            log = json.loads(entry['message'])['message']
            if log['method'] == 'Network.requestWillBeSent':
                url = log['params']['request']['url']
                urls.append(url)
    except (WebDriverException, json.JSONDecodeError) as e:
        print(f"Could not get performance logs: {e}")
    return urls

async def crawl_with_consent(domain: str) -> dict:
    """
    Crawls a website using Selenium to capture data before and after consent.
    """
    url = f"https://{domain}"
    result = {
        'har_before': {'urls': []},
        'har_after': {'urls': []},
        'cookies_before': {},
        'cookies_after': {}
    }

    # Setup Chrome options for Selenium
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.binary_location = "/usr/bin/google-chrome" # Specify binary location
    # Enable performance logging
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

    # Use a single driver instance for the whole process
    driver = None # Ensure driver is defined in the outer scope for the finally block
    try:
        # Using a context manager for the service might be cleaner if available, but this is fine
        driver_path = "/home/jules/.wdm/drivers/chromedriver/linux64/114.0.5735.90/chromedriver"
        service = ChromeService(executable_path=driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(60)
    except Exception as e:
        # Handle case where driver fails to initialize
        print(f"Error initializing WebDriver: {e}")
        if driver:
            driver.quit()
        return result

    try:
        # --- Simplified Crawl Logic ---
        print(f"Navigating to {url}...")
        driver.get(url)
        await asyncio.sleep(5) # Wait for initial page load

        # --- "Before" Data Capture ---
        print("Capturing 'before consent' data...")
        result['cookies_before'] = {cookie['name']: cookie for cookie in driver.get_cookies()}
        result['har_before']['urls'] = get_network_requests(driver)

        # --- Consent Action ---
        try:
            print("Attempting to find and click consent button...")
            consent_button_xpath = (
                "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept') or "
                "contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree') or "
                "contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'allow') or "
                "contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'consent')]"
            )
            consent_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, consent_button_xpath))
            )
            consent_button.click()
            print("Clicked a consent-related button.")
            await asyncio.sleep(5) # Wait for new trackers to load after consent
        except TimeoutException:
            print("Could not find a consent button within 5 seconds.")
            pass # If no button is found, proceed anyway

        # --- "After" Data Capture ---
        print("Capturing 'after consent' data...")
        result['cookies_after'] = {cookie['name']: cookie for cookie in driver.get_cookies()}
        # The 'after' urls will be a cumulative log of everything so far.
        result['har_after']['urls'] = get_network_requests(driver)

    except TimeoutException:
        print(f"Page load timed out for {url}")
        result['errors'] = result.get('errors', []) + [f"Page load timed out for {url}"]
    except WebDriverException as e:
        print(f"A WebDriver error occurred: {e}")
        result['errors'] = result.get('errors', []) + [f"A WebDriver error occurred: {e}"]
    finally:
        # Ensure the driver is closed
        if driver:
            driver.quit()
            print("WebDriver session closed.")

    return result