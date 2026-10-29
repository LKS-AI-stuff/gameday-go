"""Secret scrubbing for URLs and log events (TDD §8.2 step 5, FR-T8, FR-O6)."""

import hashlib
import re
import uuid
from collections.abc import Mapping
from typing import Any

REDACTED = "***"

# Query parameters that carry provider API keys
# (Ticketmaster `apikey`, Google `key`, generic `api_key`).
_SECRET_QUERY_PARAMS = re.compile(r"(?i)([?&](?:apikey|api_key|key)=)[^&#\s]+")
_BEARER = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+")
# Compact JWS (three base64url segments starting with a JSON header).
_JWT = re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*")

# Header and field names whose values are never logged.
SECRET_KEYS = frozenset(
    {
        "authorization",
        "x-apisports-key",
        "x-goog-api-key",
        "apikey",
        "api_key",
        "password",
        "token",
        "access_token",
        "refresh_token",
        "secret",
    }
)


def redact_text(text: str) -> str:
    text = _SECRET_QUERY_PARAMS.sub(rf"\g<1>{REDACTED}", text)
    text = _BEARER.sub(rf"\g<1>{REDACTED}", text)
    return _JWT.sub(REDACTED, text)


def redact_value(key: str | None, value: Any) -> Any:
    if key is not None and key.lower() in SECRET_KEYS:
        return REDACTED
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Mapping):
        return {k: redact_value(str(k), v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [redact_value(None, v) for v in value]
    return value


def hash_user_id(user_id: uuid.UUID) -> str:
    """A stable, non-reversible user reference for logs (TDD §15)."""
    return hashlib.sha256(user_id.bytes).hexdigest()[:16]
