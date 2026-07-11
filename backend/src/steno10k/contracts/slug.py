from __future__ import annotations

import re
import unicodedata

# Practical Cyrillic (Ukrainian/Russian) -> Latin transliteration, applied
# before ASCII folding so slugs stay readable instead of dropping the letters.
_CYRILLIC_MAP = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "h",
    "ґ": "g",
    "д": "d",
    "е": "e",
    "є": "ie",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "y",
    "і": "i",
    "ї": "i",
    "й": "i",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "kh",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "shch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "iu",
    "я": "ia",
}


def slugify(title: str) -> str:
    """Unicode-safe, lowercased, hyphenated slug. Empty -> 'untitled'."""
    lowered = title.lower()
    transliterated = "".join(_CYRILLIC_MAP.get(ch, ch) for ch in lowered)
    normalized = unicodedata.normalize("NFKD", transliterated)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    hyphenated = re.sub(r"[^a-z0-9]+", "-", ascii_only).strip("-")
    return hyphenated or "untitled"


def resolve_collision(existing: set[str], slug: str) -> str:
    """Return `slug`, or `slug_2`, `slug_3`, ... if it collides with `existing`."""
    if slug not in existing:
        return slug
    n = 2
    while f"{slug}_{n}" in existing:
        n += 1
    return f"{slug}_{n}"
