import json
import logging

import pytest

from app.core.logging import configure_logging, get_logger


@pytest.fixture
def lines(capsys: pytest.CaptureFixture[str]) -> list[dict[str, object]]:
    configure_logging("INFO")
    get_logger("test").info(
        "provider_call", url="https://x.test/events?apikey=SECRET1", authorization="Bearer abc"
    )
    logging.getLogger("third.party").warning("GET https://x.test/?key=SECRET2 failed")
    logging.getLogger("httpx").info("HTTP Request: GET https://x.test/?apikey=SECRET3")
    return [json.loads(line) for line in capsys.readouterr().out.splitlines() if line]


def test_structlog_events_are_json_and_redacted(lines: list[dict[str, object]]) -> None:
    event = next(e for e in lines if e["event"] == "provider_call")
    assert event["url"] == "https://x.test/events?apikey=***"
    assert event["authorization"] == "***"
    assert event["level"] == "info"


def test_stdlib_library_logs_are_json_and_redacted(lines: list[dict[str, object]]) -> None:
    event = next(e for e in lines if e.get("logger") == "third.party")
    assert event["event"] == "GET https://x.test/?key=*** failed"


def test_httpx_request_logs_are_suppressed(lines: list[dict[str, object]]) -> None:
    assert not any("SECRET" in json.dumps(e) for e in lines)
    assert not any(e.get("logger") == "httpx" for e in lines)
