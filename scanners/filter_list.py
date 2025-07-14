from adblockparser import AdblockRules

# Load EasyPrivacy and Fanboy rules as UTF‑8, ignoring any invalid bytes
with open('rules/easyprivacy.txt', encoding='utf-8', errors='ignore') as f:
    easy_rules = AdblockRules(f)

with open('rules/fanboy-privacy.txt', encoding='utf-8', errors='ignore') as f:
    privacy_rules = AdblockRules(f)

def is_tracker(url: str) -> bool:
    return easy_rules.should_block(url)

def is_consent_element(selector: str) -> bool:
    return privacy_rules.should_block(selector)