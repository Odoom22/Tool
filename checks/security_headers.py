def run_security_headers(headers: dict) -> dict:
    required = ['Strict-Transport-Security', 'Content-Security-Policy', 'X-Frame-Options']
    missing = [h for h in required if h not in headers]
    return {'passed': not missing, 'details': {'missing': missing}}