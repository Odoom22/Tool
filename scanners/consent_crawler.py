import asyncio
from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, ElementNotInteractableException
from urllib.parse import urljoin

async def crawl_with_consent(domain: str) -> dict:
    """
    Crawls a website using selenium-wire to capture data, including privacy policy text.
    Relies on Selenium Manager to handle the chromedriver.
    """
    url = f"https://{domain}"
    result = {
        'har_before': {'urls': []},
        'har_after': {'urls': []},
        'cookies_before': {},
        'cookies_after': {},
        'main_page_html': '',
        'privacy_policy_html': ''
    }

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(90)
    except Exception as e:
        print(f"Error initializing WebDriver: {e}")
        if driver:
            driver.quit()
        return result

    try:
        print(f"Navigating to {url}...")
        driver.get(url)

        print("Waiting for page to render...")
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        await asyncio.sleep(3) # Extra wait for dynamic content
        print("Page render detected.")

        result['main_page_html'] = driver.page_source

        print("Capturing 'before consent' data...")
        result['cookies_before'] = {cookie['name']: cookie for cookie in driver.get_cookies()}
        result['har_before']['urls'] = [req.url for req in driver.requests if req.url]
        del driver.requests

        try:
            print("Attempting to find and click consent button...")
            consent_xpath = (
                "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept') or "
                "contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree') or "
                "contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'allow') or "
                "contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'consent') or "
                "contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept all') or "
                "contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'gree') or "
                "contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ok')] | "
                "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept') or "
                "contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree') or "
                "contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'allow') or "
                "contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'consent') or "
                "contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept all') or "
                "contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'gree') or "
                "contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ok')]"
            )
            consent_element = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, consent_xpath)))
            consent_element.click()
            print("Clicked a consent-related element.")
            await asyncio.sleep(5)
        except Exception:
            print("Could not find or click a consent element.")
            pass

        print("Capturing 'after consent' data...")
        result['cookies_after'] = {cookie['name']: cookie for cookie in driver.get_cookies()}
        result['har_after']['urls'] = [req.url for req in driver.requests if req.url]

        try:
            print("Searching for privacy policy link...")
            privacy_policy_xpath = (
                "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'privacy') or "
                "contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'cookie policy') or "
                "contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'legal') or "
                "contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'data protection') or "
                "contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'data privacy')]"
            )

            # Use WebDriverWait to ensure links are present
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, privacy_policy_xpath)))
            privacy_links = driver.find_elements(By.XPATH, privacy_policy_xpath)

            policy_url_found = False
            if privacy_links:
                # Prioritize links with "privacy" in the text
                sorted_links = sorted(privacy_links, key=lambda x: 'privacy' in x.text.lower(), reverse=True)

                for link in sorted_links:
                    try:
                        href = link.get_attribute('href')
                        if href and href.strip() and not href.lower().startswith('javascript:'):
                            policy_url = urljoin(driver.current_url, href)
                            print(f"Navigating to privacy policy: {policy_url}")
                            driver.get(policy_url)

                            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                            await asyncio.sleep(3) # Wait for JS to render

                            result['privacy_policy_html'] = driver.page_source
                            print("Successfully extracted HTML from privacy policy page.")

                            policy_url_found = True
                            break # Stop after finding the first valid policy
                    except Exception as e:
                        print(f"Could not interact with a privacy link ({href}): {e}")
                        continue

            if not policy_url_found:
                 print("No valid privacy policy link was successfully navigated to.")

        except TimeoutException:
            print("Timed out waiting for privacy policy links to appear.")
        except Exception as e:
            print(f"An error occurred while trying to find/crawl the privacy policy: {e}")

    except Exception as e:
        print(f"A critical error occurred during the crawl: {e}")
        result['errors'] = result.get('errors', []) + [f"Crawl failed: {e}"]
    finally:
        if driver:
            driver.quit()
            print("WebDriver session closed.")

    return result