import re

def getBotTag(message):
    if 'upbit' in message.lower():
        match1 = re.findall(r"\((\w{2,10})\)", message)

        # Pattern 2: $COIN, e.g., $RAY or $ALT
        match2 = re.findall(r"\$([A-Z]{2,10})", message)

        # Combine and deduplicate matches
        slugs = list(set(match1 + match2))
        return slugs
