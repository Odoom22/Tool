import asyncio
import logging
from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, JavascriptException, ElementNotInteractableException
from urllib.parse import urljoin

# Configure logging
logger = logging.getLogger(__name__)

async def find_and_click_consent_button(driver, timeout=15):
    """
    Finds and clicks a consent button using multiple strategies.
    """
    # Try to remove the chat widget first
    try:
        chat_widget = driver.find_element(By.TAG_NAME, 'inbox-online-store-chat')
        if chat_widget:
            driver.execute_script("arguments[0].parentNode.removeChild(arguments[0]);", chat_widget)
            logger.info("Removed chat widget to prevent obstruction.")
    except Exception as e:
        logger.debug(f"Could not remove chat widget: {e}")

    # More specific XPaths are generally better.
    consent_xpaths = [
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'allow')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'consent')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ok')]",
        "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]",
        "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree')]",
    ]

    for xpath in consent_xpaths:
        try:
            consent_element = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            try:
                consent_element.click()
                logger.info(f"Clicked consent button with XPath: {xpath}")
            except (ElementNotInteractableException, JavascriptException):
                logger.warning(f"Regular click failed for XPath {xpath}, trying JavaScript click.")
                driver.execute_script("arguments[0].click();", consent_element)
                logger.info(f"Clicked consent button with JavaScript for XPath: {xpath}")

            await asyncio.sleep(5)  # Wait for the banner to disappear
            return
        except TimeoutException:
            logger.debug(f"Could not find consent button with XPath: {xpath}")
        except Exception as e:
            logger.warning(f"Error clicking consent button with XPath {xpath}: {e}")

    # Fallback for buttons in iframes
    try:
        iframes = driver.find_elements(By.TAG_NAME, 'iframe')
        for iframe in iframes:
            try:
                driver.switch_to.frame(iframe)
                logger.info("Switched to an iframe to search for consent button.")
                for xpath in consent_xpaths:
                    try:
                        consent_element = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, xpath))
                        )
                        consent_element.click()
                        logger.info(f"Clicked consent button in iframe with XPath: {xpath}")
                        driver.switch_to.default_content()
                        await asyncio.sleep(3)
                        return
                    except TimeoutException:
                        continue
                driver.switch_to.default_content()
            except Exception as e:
                logger.warning(f"Could not process an iframe: {e}")
                driver.switch_to.default_content()
    except Exception as e:
        logger.error(f"Error while searching for iframes: {e}")

    # Fallback for shadow DOM
    try:
        # This is a generic way to find shadow roots. It might need to be adapted for specific sites.
        all_elements = driver.find_elements(By.CSS_SELECTOR, '*')
        for element in all_elements:
            try:
                shadow_root = driver.execute_script('return arguments[0].shadowRoot', element)
                if shadow_root:
                    # Once we have the shadow root, we need to find the button within it.
                    # This is a simplified example.
                    accept_button = shadow_root.find_element(By.CSS_SELECTOR, 'button.accept-button') # Example selector
                    accept_button.click()
                    logger.info("Clicked consent button in shadow DOM.")
                    await asyncio.sleep(3)
                    return
            except JavascriptException:
                continue # Element does not have a shadow root
            except Exception:
                continue # Other errors
    except Exception as e:
        logger.error(f"Error while searching for shadow DOM: {e}")


    logger.warning("Could not find or click a consent element after trying all strategies.")


async def find_and_extract_privacy_policy(driver, base_url):
    """
    Finds the privacy policy link and extracts its HTML content.
    """
    privacy_policy_html = ''
    try:
        logger.info("Searching for privacy policy link...")
        privacy_policy_xpath = (
            "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'privacy') or "
            "contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'cookie policy')]"
        )

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, privacy_policy_xpath)))
        privacy_links = driver.find_elements(By.XPATH, privacy_policy_xpath)

        if privacy_links:
            sorted_links = sorted(privacy_links, key=lambda x: 'privacy' in x.text.lower(), reverse=True)
            for link in sorted_links:
                try:
                    href = link.get_attribute('href')
                    if href and href.strip() and not href.lower().startswith('javascript:'):
                        policy_url = urljoin(base_url, href)
                        logger.info(f"Navigating to privacy policy: {policy_url}")
                        driver.get(policy_url)
                        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                        await asyncio.sleep(2) # Wait for final rendering
                        privacy_policy_html = driver.page_source
                        logger.info("Successfully extracted HTML from privacy policy page.")
                        return privacy_policy_html
                except Exception as e:
                    logger.warning(f"Could not process privacy link ({href}): {e}")
                    continue
    except TimeoutException:
        logger.warning("Timed out waiting for privacy policy links.")
    except Exception as e:
        logger.error(f"An error occurred while finding the privacy policy: {e}")

    return privacy_policy_html


async def crawl_with_consent(domain: str) -> dict:
    """
    Crawls a website using selenium-wire to capture data, including privacy policy text.
    """
    url = f"https://{domain}"
    result = {
        'har_before': {'urls': []}, 'har_after': {'urls': []},
        'cookies_before': {}, 'cookies_after': {},
        'main_page_html': '', 'privacy_policy_html': '', 'errors': []
    }

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(90)

        logger.info(f"Navigating to {url}...")
        driver.get(url)

        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        logger.info("Page has loaded.")

        result['main_page_html'] = driver.page_source
        result['cookies_before'] = {c['name']: c for c in driver.get_cookies()}
        result['har_before']['urls'] = [req.url for req in driver.requests if req.url]
        del driver.requests

        await find_and_click_consent_button(driver)

        result['cookies_after'] = {c['name']: c for c in driver.get_cookies()}
        result['har_after']['urls'] = [req.url for req in driver.requests if req.url]

        result['privacy_policy_html'] = await find_and_extract_privacy_policy(driver, url)

    except WebDriverException as e:
        logger.critical(f"WebDriver error during crawl of {domain}: {e}")
        result['errors'].append(f"WebDriver error: {e}")
    except Exception as e:
        logger.critical(f"A critical error occurred during the crawl of {domain}: {e}")
        result['errors'].append(f"Crawl failed: {e}")
    finally:
        if driver:
            driver.quit()
            logger.info(f"WebDriver session closed for {domain}.")

    return result