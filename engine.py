import json
import httpx
import traceback
import logging # This is fine, will use root logger config from main.py if already set
from scanners.consent_crawler import crawl_with_consent
from scanners.filter_list import is_tracker, is_consent_element
from checks.dom_scan import run_dom_scan
from checks.security_headers import run_security_headers

async def audit_site(domain: str) -> dict:
    report = {"site": domain, "rules": [], "scenarios": {}, "errors": []}
    passed_count = 0

    # Load rules
    try:
        with open('rules/act843_rules.json', 'r', encoding='utf-8') as f:
            rules = json.load(f)
    except Exception as e:
        logging.error("Failed to load rules: %s", traceback.format_exc())
        report['errors'].append(f"Rule loading failed: {str(e)}")
        return report

    total_rules = len(rules)

    # 1. Scenario-based crawl: get HARs, cookies, trackers
    try:
        scenarios = await crawl_with_consent(domain)
        report['scenarios'] = scenarios
    except Exception as e:
        logging.error("Playwright crawl failed: %s", traceback.format_exc())
        report['errors'].append(f"Playwright crawl failed: {str(e)}")
        return report

    # 2. Static fetch for HTML and headers
    headers = httpx.Headers() # Initialize headers to an empty object
    try:
        resp = httpx.get(f"https://{domain}", timeout=10, follow_redirects=True)
        # Note: main_page_html is now retrieved by the crawler, but we still need headers.
        headers = resp.headers
    except Exception as e:
        logging.error("HTTPX fetch failed: %s", traceback.format_exc())
        report['errors'].append(f"HTTPX fetch failed: {str(e)}")
        # We can still proceed with scenario-based checks even if this fails

    main_page_html = scenarios.get('main_page_text', '')
    privacy_policy_html = scenarios.get('privacy_policy_text', '')

    # 3. Evaluate rules
    for rule in rules:
        rule_passed = True
        details = []

        for chk in rule.get('checks', []):
            t = chk.get('type')
            rec = chk.get('recommendation')
            config = chk.get('config', {})
            passed = False
            detail = None

            try:
                if t == 'https':
                    passed = resp.url.scheme == 'https'
                    detail = {'https_enabled': passed}

                elif t == 'http_header':
                    header = config.get('header')
                    passed = header in headers
                    detail = headers.get(header, 'Missing')

                elif t == 'dom_notices':
                    out = run_dom_scan(main_page_html, privacy_policy_html, config)
                    passed, detail = out['passed'], out['details']

                elif t == 'scenario_tracker':
                    urls_before = scenarios.get('har_before', {}).get('urls', [])
                    urls_after = scenarios.get('har_after', {}).get('urls', [])

                    before_trackers = [u for u in urls_before if is_tracker(u)]
                    after_trackers = [u for u in urls_after if is_tracker(u)]

                    # The rule passes if no trackers are loaded before consent is given.
                    passed = len(before_trackers) == 0
                    detail = {
                        'before_trackers': before_trackers,
                        'after_trackers': after_trackers
                    }

                elif t == 'cookie_attributes':
                    attrs_before = scenarios['cookies_before']
                    missing_attrs = [c for c, flags in attrs_before.items() if not flags.get('secure')]
                    passed = len(missing_attrs) == 0
                    detail = {'missing_secure_cookie_attrs': missing_attrs}

                else:
                    detail = 'Unknown check type'

                if not passed:
                    rule_passed = False

                entry = {'check': t, 'passed': passed, 'detail': detail}
                if rec:
                    entry['recommendation'] = rec
                details.append(entry)

            except Exception as e:
                logging.error("Check dispatch failed: %s", traceback.format_exc())
                details.append({
                    'check': t,
                    'passed': False,
                    'detail': f"Check error: {str(e)}",
                    'recommendation': rec or 'Review check configuration.'
                })
                rule_passed = False

        if rule_passed:
            passed_count += 1

        report['rules'].append({
            'id': rule['id'],
            'description': rule.get('description'),
            'passed': rule_passed,
            'details': details
        })

    report['score'] = int((passed_count / total_rules) * 100) if total_rules else 0
    return report