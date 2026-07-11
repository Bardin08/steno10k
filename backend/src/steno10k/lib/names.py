from __future__ import annotations

from steno10k.contracts.slug import slugify


def normalize_recording_name(name: str) -> str:
    """Safe, unicode-safe recording filename: slugified stem + lowercased extension.

    Reuses `contracts.slug.slugify` (no second normalizer). The extension is the
    substring after the last "." (even a leading dot, e.g. ".m4a", counts as an
    extension with an empty stem). A name with no stem slugifies to "untitled"
    per `slugify`.
    """
    dot_index = name.rfind(".")
    if dot_index == -1:
        stem, ext = name, ""
    else:
        stem, ext = name[:dot_index], name[dot_index:]
    return f"{slugify(stem)}{ext.lower()}"
