import re


def normalize_key(text: str) -> str:
    """Lowercase/slug form used to dedup preference-memory facts so the same
    requirement (however it's phrased next time) maps to the same key."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
