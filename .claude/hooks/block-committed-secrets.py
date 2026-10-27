#!/usr/bin/env python3
"""
PreToolUse hook (Edit|Write): blocks writing real secrets into files that get committed.

CLAUDE.md: live keys live only in the git-ignored `.env` files; never commit secrets, never
log API keys, and never put a secret in an EXPO_PUBLIC_* variable, since those ship inside
the apps (TDD §8.2, NFR-12).

- Local `.env` files (git-ignored) may hold backend secrets, except that EXPO_PUBLIC_*
  values must never hold a server secret.
- Every other file (code, docs, `.env.example`, CI config) is blocked from holding one.

Exit code 2 blocks the tool call and shows the message to Claude.
"""

import json
import re
import sys
from pathlib import PurePath

# Provider secrets by shape. Publishable/anon keys are public by design and allowed.
SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("an OpenAI API key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}")),
    ("a Supabase secret key", re.compile(r"\bsb_secret_[A-Za-z0-9_-]{10,}")),
    ("a Resend API key", re.compile(r"\bre_[A-Za-z0-9]{20,}")),
    ("a Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}")),
    ("a Ticketmaster API key in a URL", re.compile(r"[?&]apikey=[A-Za-z0-9]{20,}")),
    ("an API-Sports key", re.compile(r"(?i)x-apisports-key['\"]?\s*[:=]\s*['\"]?[a-f0-9]{32}")),
    # A signed token literal, e.g. a Supabase service-role key (tests mint tokens at runtime).
    ("a JWT (e.g. a Supabase service-role key)",
     re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{20,}")),
]

# Database URLs with a password. Placeholders and well-known local/CI values are allowed.
DB_URL = re.compile(r"postgres(?:ql)?(?:\+\w+)?://[^:/\s@]+:([^@\s]+)@")
ALLOWED_DB_PASSWORDS = {"postgres", "CHANGE_ME", "<password>", "unused", "ci-only-password", "password"}

# Values that can't be shipped in an app bundle (NFR-12).
SERVER_SECRET_IN_PUBLIC_VAR = re.compile(
    r"EXPO_PUBLIC_[A-Z0-9_]*\s*=\s*['\"]?("
    r"sb_secret_|sk-|re_[A-Za-z0-9]{20}|eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]*cm9sZSI6InNlcnZpY2Vfcm9sZ"
    r")"
)


def is_local_env_file(path: str) -> bool:
    name = PurePath(path).name
    return name == ".env" or (name.startswith(".env.") and name != ".env.example")


def block(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(2)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # can't parse the payload: fail open

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {}) or {}
    file_path = tool_input.get("file_path", "") or ""
    if tool_name == "Write":
        content = tool_input.get("content", "") or ""
    elif tool_name == "Edit":
        content = tool_input.get("new_string", "") or ""
    else:
        sys.exit(0)

    if is_local_env_file(file_path):
        if SERVER_SECRET_IN_PUBLIC_VAR.search(content):
            block(
                f"Blocked: this write puts a server secret in an EXPO_PUBLIC_* variable in {file_path}. "
                "EXPO_PUBLIC_* values are inlined into the app bundle and are public (CLAUDE.md, NFR-12). "
                "Server secrets belong only in the repo-root .env, read by the backend."
            )
        sys.exit(0)

    for label, pattern in SECRET_PATTERNS:
        if pattern.search(content):
            block(
                f"Blocked: this write adds what looks like {label} to {file_path}. "
                "CLAUDE.md: live keys go only in the git-ignored .env; never commit secrets "
                "(TDD §8.2). Use a placeholder here and put the real value in .env."
            )

    for match in DB_URL.finditer(content):
        password = match.group(1)
        if password in ALLOWED_DB_PASSWORDS or password.startswith(("$", "<", "{")):
            continue
        block(
            f"Blocked: this write adds a database URL with a real-looking password to {file_path}. "
            "Database URLs with real passwords go only in the git-ignored .env (CLAUDE.md). "
            "Use a placeholder such as CHANGE_ME or <password>."
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
