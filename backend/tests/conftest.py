import time
import uuid
from collections.abc import Callable
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app.core.settings import Settings

TEST_SUPABASE_URL = "http://supabase.test"
TEST_KID = "test-key-1"


def make_settings(**overrides: Any) -> Settings:
    """Settings for unit tests, independent of the local .env."""
    values: dict[str, Any] = {
        "database_url": "postgresql+asyncpg://unused:unused@localhost:1/unused",
        "supabase_url": TEST_SUPABASE_URL,
        "cors_origins": "",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.fixture(scope="session")
def signing_key() -> ec.EllipticCurvePrivateKey:
    return ec.generate_private_key(ec.SECP256R1())


@pytest.fixture(scope="session")
def jwks(signing_key: ec.EllipticCurvePrivateKey) -> dict[str, Any]:
    public_jwk = jwt.algorithms.ECAlgorithm.to_jwk(signing_key.public_key(), as_dict=True)
    return {"keys": [{**public_jwk, "kid": TEST_KID, "alg": "ES256", "use": "sig"}]}


type TokenFactory = Callable[..., str]


@pytest.fixture(scope="session")
def make_token(signing_key: ec.EllipticCurvePrivateKey) -> TokenFactory:
    """Mint a Supabase-shaped access token signed with the test key."""

    def factory(
        *,
        sub: str | None = None,
        email: str = "fan@example.com",
        age_confirmed: bool = True,
        expires_in: int = 3600,
        issuer: str = f"{TEST_SUPABASE_URL}/auth/v1",
        audience: str = "authenticated",
        kid: str = TEST_KID,
        **extra: Any,
    ) -> str:
        now = int(time.time())
        claims: dict[str, Any] = {
            "sub": sub or str(uuid.uuid4()),
            "email": email,
            "role": "authenticated",
            "aud": audience,
            "iss": issuer,
            "iat": now,
            "exp": now + expires_in,
            "is_anonymous": False,
            "user_metadata": {"age_confirmed": True} if age_confirmed else {},
        }
        claims.update(extra)
        return jwt.encode(claims, signing_key, algorithm="ES256", headers={"kid": kid})

    return factory
