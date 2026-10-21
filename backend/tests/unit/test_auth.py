import uuid
from typing import Any

import httpx
import jwt
import pytest
import respx

from app.core.auth import TokenVerifier
from app.core.errors import ProblemError
from tests.conftest import TEST_SUPABASE_URL, TokenFactory, make_settings

JWKS_URL = f"{TEST_SUPABASE_URL}/auth/v1/.well-known/jwks.json"


@pytest.fixture
def verifier(jwks: dict[str, Any]) -> TokenVerifier:
    return TokenVerifier(make_settings())


async def verify(verifier: TokenVerifier, jwks: dict[str, Any], token: str) -> Any:
    with respx.mock:
        respx.get(JWKS_URL).mock(return_value=httpx.Response(200, json=jwks))
        return await verifier.verify(token)


async def test_valid_token_returns_claims(
    verifier: TokenVerifier, jwks: dict[str, Any], make_token: TokenFactory
) -> None:
    sub = str(uuid.uuid4())
    claims = await verify(verifier, jwks, make_token(sub=sub, email="ben@example.com"))
    assert claims.user_id == uuid.UUID(sub)
    assert claims.email == "ben@example.com"
    assert claims.age_confirmed is True


async def test_age_confirmed_false_without_metadata(
    verifier: TokenVerifier, jwks: dict[str, Any], make_token: TokenFactory
) -> None:
    claims = await verify(verifier, jwks, make_token(age_confirmed=False))
    assert claims.age_confirmed is False


@pytest.mark.parametrize(
    "overrides",
    [
        {"expires_in": -60},
        {"issuer": "http://evil.test/auth/v1"},
        {"audience": "anon"},
        {"kid": "unknown-key"},
        {"role": "anon"},
        {"is_anonymous": True},
        {"email": ""},
        {"sub": "not-a-uuid"},
    ],
    ids=["expired", "issuer", "audience", "kid", "role", "anonymous", "email", "sub"],
)
async def test_rejected_tokens(
    verifier: TokenVerifier,
    jwks: dict[str, Any],
    make_token: TokenFactory,
    overrides: dict[str, Any],
) -> None:
    with pytest.raises(ProblemError) as err:
        await verify(verifier, jwks, make_token(**overrides))
    assert err.value.status == 401


async def test_token_signed_with_other_key_is_rejected(
    verifier: TokenVerifier, jwks: dict[str, Any]
) -> None:
    from cryptography.hazmat.primitives.asymmetric import ec

    other = ec.generate_private_key(ec.SECP256R1())
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "aud": "authenticated",
            "iss": f"{TEST_SUPABASE_URL}/auth/v1",
            "exp": 9999999999,
            "iat": 1,
            "role": "authenticated",
            "email": "x@example.com",
        },
        other,
        algorithm="ES256",
        headers={"kid": "test-key-1"},
    )
    with pytest.raises(ProblemError):
        await verify(verifier, jwks, token)


async def test_hs256_token_is_rejected_in_jwks_mode(
    verifier: TokenVerifier, jwks: dict[str, Any]
) -> None:
    token = jwt.encode({"sub": str(uuid.uuid4())}, "x" * 32, algorithm="HS256")
    with pytest.raises(ProblemError):
        await verify(verifier, jwks, token)


async def test_secret_mode_accepts_hs256() -> None:
    secret = "s" * 40
    verifier = TokenVerifier(make_settings(supabase_jwt_mode="secret", supabase_jwt_secret=secret))
    sub = str(uuid.uuid4())
    token = jwt.encode(
        {
            "sub": sub,
            "aud": "authenticated",
            "iss": f"{TEST_SUPABASE_URL}/auth/v1",
            "exp": 9999999999,
            "iat": 1,
            "role": "authenticated",
            "email": "x@example.com",
        },
        secret,
        algorithm="HS256",
    )
    assert (await verifier.verify(token)).user_id == uuid.UUID(sub)


async def test_jwks_unavailable_without_cached_keys_is_503(
    verifier: TokenVerifier, make_token: TokenFactory
) -> None:
    with respx.mock:
        respx.get(JWKS_URL).mock(return_value=httpx.Response(500))
        with pytest.raises(ProblemError) as err:
            await verifier.verify(make_token())
    assert err.value.status == 503


async def test_jwks_is_cached(
    verifier: TokenVerifier, jwks: dict[str, Any], make_token: TokenFactory
) -> None:
    with respx.mock:
        route = respx.get(JWKS_URL).mock(return_value=httpx.Response(200, json=jwks))
        await verifier.verify(make_token())
        await verifier.verify(make_token())
    assert route.call_count == 1
