from bs4 import BeautifulSoup

def run_dom_scan(main_page_html: str, privacy_policy_html: str, config: dict) -> dict:
    """
    Scans HTML content based on a flexible configuration.

    :param main_page_html: The HTML content of the main page.
    :param privacy_policy_html: The HTML content of the privacy policy page.
    :param config: A dictionary specifying what to check.
                   Expected keys: 'check_type', 'keywords'.
    :return: A dictionary with 'passed' status and 'details'.
    """
    check_type = config.get('check_type')
    keywords = config.get('keywords', [])

    main_soup = BeautifulSoup(main_page_html, 'lxml')

    privacy_text = ""
    if privacy_policy_html:
        privacy_soup = BeautifulSoup(privacy_policy_html, 'lxml')
        privacy_text = privacy_soup.get_text()

    # Combine text from both pages for keyword searching
    main_text = main_soup.get_text()
    full_text = (main_text + " " + privacy_text).lower()

    passed = False
    details = {}

    if check_type == 'privacy_policy_link':
        # This check just looks for a link to the privacy policy on the main page.
        links = [a.get('href') for a in main_soup.find_all('a', href=True)
                 if any(keyword.lower() in a.get_text(strip=True).lower() for keyword in ["privacy", "legal", "terms"])]
        passed = bool(links)
        details = {'found_links': list(set(links))}

    elif check_type == 'keyword_presence':
        # This check looks for specific keywords in the combined text of both pages.
        found_keywords = [kw for kw in keywords if kw.lower() in full_text]
        passed = bool(found_keywords)
        details = {'found_keywords': found_keywords, 'searched_in_privacy_policy': bool(privacy_policy_html)}

    elif check_type == 'dpc_link':
        # This check looks for a link to the DPC website.
        dpc_url = "dataprotection.org.gh"
        links = [a.get('href') for a in main_soup.find_all('a', href=True) if dpc_url in a.get('href', '')]
        if not links and privacy_policy_html:
            privacy_soup = BeautifulSoup(privacy_policy_html, 'lxml')
            links = [a.get('href') for a in privacy_soup.find_all('a', href=True) if dpc_url in a.get('href', '')]

        passed = bool(links)
        details = {'found_links': list(set(links))}

    elif check_type == 'cookie_policy_link':
        # This check looks for a link to the cookie policy on the main page.
        links = [a.get('href') for a in main_soup.find_all('a', href=True)
                 if any(keyword.lower() in a.get_text(strip=True).lower() for keyword in keywords)]
        passed = bool(links)
        details = {'found_links': list(set(links))}

    else:
        details = {'error': f'Unknown check_type: {check_type}'}

    return {'passed': passed, 'details': details}