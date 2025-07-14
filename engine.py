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
    try:
        resp = httpx.get(f"https://{domain}", timeout=10)
        html = resp.text
        headers = dict(resp.headers)
    except Exception as e:
        logging.error("HTTPX fetch failed: %s", traceback.format_exc())
        report['errors'].append(f"HTTPX fetch failed: {str(e)}")
        return report

    # 3. Evaluate rules
    for rule in rules:
        rule_passed = True
        details = []

        for chk in rule.get('checks', []):
            t = chk.get('type')
            rec = chk.get('recommendation')
            passed = False
            detail = None

            try:
                if t == 'https':
                    out = run_security_headers(headers)
                    passed, detail = out['passed'], out['details']

                elif t == 'http_header':
                    header = chk['config'].get('header')
                    passed = header in headers
                    detail = headers.get(header, 'Missing')

                elif t == 'dom_notices':
                    out = run_dom_scan(html)
                    passed, detail = out['passed'], out['details']

                elif t == 'scenario_tracker':
                    urls_before = scenarios.get('har_before', {}).get('urls', [])
                    urls_after = scenarios.get('har_after', {}).get('urls', [])

                    # Trackers loaded before consent action
                    before_trackers = {u for u in urls_before if is_tracker(u)}

                    # Cumulative trackers loaded after consent action
                    after_trackers_cumulative = {u for u in urls_after if is_tracker(u)}

                    # Trackers loaded *only* after consent action
                    new_after_trackers = list(after_trackers_cumulative - before_trackers)

                    # The rule passes if no trackers are loaded before consent is given.
                    passed = len(before_trackers) == 0
                    detail = {
                        'before_trackers': list(before_trackers),
                        'after_trackers': new_after_trackers
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