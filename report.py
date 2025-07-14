def generate_summary(report: dict) -> str:
    lines = [f"Audit Report: {report['site']}"]
    for r in report.get('rules', []):
        status = 'PASSED' if r['passed'] else 'FAILED'
        lines.append(f"{r['id']} ({r['description']}): {status}")
        for d in r['details']:
            rec_txt = f" Recommendation: {d.get('recommendation')}" if not d['passed'] and d.get('recommendation') else ''
            lines.append(f"  * {d['check']}: {'OK' if d['passed'] else 'FAIL'} - {d['detail']}{rec_txt}")
    return "\n".join(lines)