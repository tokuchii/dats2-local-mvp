from __future__ import annotations

import json
from urllib.parse import unquote

PREFERENCES_COOKIE = "dats2_prefs"
DEFAULT_PREFERENCES = {"reduce_motion": False, "hide_hints": False}


def parse_preferences(raw: str | None) -> dict[str, bool]:
    preferences = DEFAULT_PREFERENCES.copy()
    if not raw:
        return preferences
    try:
        parsed = json.loads(unquote(raw))
    except (TypeError, ValueError):
        return preferences
    if not isinstance(parsed, dict):
        return preferences
    preferences["reduce_motion"] = parsed.get("reduce_motion") is True
    preferences["hide_hints"] = parsed.get("hide_hints") is True
    return preferences
