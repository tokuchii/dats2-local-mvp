from __future__ import annotations

import json
from urllib.parse import quote

from app.preferences import DEFAULT_PREFERENCES, parse_preferences


def test_preferences_default_to_disabled():
    assert parse_preferences(None) == DEFAULT_PREFERENCES
    assert parse_preferences("") == DEFAULT_PREFERENCES


def test_preferences_parse_encoded_cookie():
    raw = quote(json.dumps({"reduce_motion": True, "hide_hints": True}))
    assert parse_preferences(raw) == {"reduce_motion": True, "hide_hints": True}


def test_preferences_ignore_unknown_and_non_boolean_values():
    raw = quote(json.dumps({"reduce_motion": "yes", "hide_hints": True, "theme": "dark"}))
    assert parse_preferences(raw) == {"reduce_motion": False, "hide_hints": True}


def test_preferences_fall_back_on_invalid_json():
    assert parse_preferences("%7Bnot-json") == DEFAULT_PREFERENCES
