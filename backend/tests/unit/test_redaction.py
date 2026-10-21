from app.core.redaction import REDACTED, redact_text, redact_value


def test_query_string_keys_are_redacted() -> None:
    url = "https://app.ticketmaster.com/discovery/v2/events.json?apikey=SECRET123&size=5&key=K2"
    assert redact_text(url) == (
        f"https://app.ticketmaster.com/discovery/v2/events.json?apikey={REDACTED}&size=5&key={REDACTED}"
    )


def test_bearer_tokens_and_jwts_are_redacted() -> None:
    jwt_like = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.sig-nature_x"
    assert "eyJ" not in redact_text(f"Authorization: Bearer {jwt_like}")
    assert redact_text(f"token={jwt_like}") == f"token={REDACTED}"


def test_secret_keys_in_mappings_are_redacted() -> None:
    event = {
        "headers": {"X-Apisports-Key": "abc", "Accept": "json"},
        "password": "hunter2",
        "items": ["https://x.test/?api_key=zzz"],
    }
    assert redact_value(None, event) == {
        "headers": {"X-Apisports-Key": REDACTED, "Accept": "json"},
        "password": REDACTED,
        "items": [f"https://x.test/?api_key={REDACTED}"],
    }


def test_harmless_text_is_unchanged() -> None:
    assert (
        redact_text("monkey business at /keyboard?monkey=1")
        == "monkey business at /keyboard?monkey=1"
    )
