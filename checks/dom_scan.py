from bs4 import BeautifulSoup

def run_dom_scan(html: str) -> dict:
    soup = BeautifulSoup(html, 'lxml')
    links = [a['href'] for a in soup.find_all('a', href=True)
             if 'privacy' in a.get_text(strip=True).lower()]
    text = soup.get_text().lower()
    rights = [kw for kw in ['access', 'delete', 'rectify'] if kw in text]
    passed = bool(links) and bool(rights)
    return {'passed': passed, 'details': {'links': links, 'rights': rights}}