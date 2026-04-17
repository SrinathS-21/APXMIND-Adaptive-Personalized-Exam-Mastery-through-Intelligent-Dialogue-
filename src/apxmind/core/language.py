"""Language utilities used across API routes and prompt generation."""

from __future__ import annotations

from typing import Any, Optional

DEFAULT_LANGUAGE = "en"

LANGUAGE_ALIASES: dict[str, str] = {
    "en": "en",
    "english": "en",
    "en-us": "en",
    "en-in": "en",
    "hi": "en",
    "hindi": "en",
    "ta": "ta",
    "tamil": "ta",
    "te": "en",
    "telugu": "en",
    "bn": "en",
    "bengali": "en",
    "mr": "en",
    "marathi": "en",
}

LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "ta": "Tamil",
}


def normalize_language(value: Optional[str], default: str = DEFAULT_LANGUAGE) -> str:
    """Normalize language aliases and locale-like values to short codes."""
    if not value:
        return default

    cleaned = value.strip().lower().replace("_", "-")
    if cleaned in LANGUAGE_ALIASES:
        return LANGUAGE_ALIASES[cleaned]

    base = cleaned.split("-")[0]
    if base in LANGUAGE_ALIASES:
        return LANGUAGE_ALIASES[base]

    return default


def language_name(code: Optional[str]) -> str:
    """Return the canonical display name for prompt instructions."""
    normalized = normalize_language(code)
    return LANGUAGE_NAMES.get(normalized, "English")


def resolve_request_language(
    *,
    explicit: Optional[str] = None,
    context: Optional[dict[str, Any]] = None,
    header: Optional[str] = None,
    user_preference: Optional[str] = None,
    default: str = DEFAULT_LANGUAGE,
) -> str:
    """Resolve request language with stable precedence."""
    candidates = [
        explicit,
        context.get("language") if isinstance(context, dict) else None,
        header,
        user_preference,
    ]

    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return normalize_language(candidate, default=default)

    return default
