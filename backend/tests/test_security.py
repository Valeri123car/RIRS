from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import Settings
from app.core.security import (
    AuthConfigError,
    InvalidTokenError,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)

SECRET = "testna-skrivnost-ki-je-dovolj-dolga-za-hs256"


def settings(**values) -> Settings:
    return Settings(_env_file=None, **{"jwt_secret": SECRET, **values})


def test_geslo_je_shranjeno_kot_argon2id_zgostitev():
    hashed = hash_password("dolgo-geslo-123")

    assert hashed.startswith("$argon2id$")
    assert "dolgo-geslo-123" not in hashed


def test_preverjanje_gesla():
    hashed = hash_password("dolgo-geslo-123")

    assert verify_password(hashed, "dolgo-geslo-123")
    assert not verify_password(hashed, "napacno-geslo")
    assert not verify_password("ni-zgostitev", "dolgo-geslo-123")


def test_zeton_vsebuje_id_uporabnika():
    token = create_token(42, "access", settings())

    assert decode_token(token, "access", settings()) == 42


def test_osvezilni_zeton_ne_velja_kot_dostopni():
    token = create_token(42, "refresh", settings())

    with pytest.raises(InvalidTokenError):
        decode_token(token, "access", settings())


def test_dostopni_zeton_potece():
    old = datetime.now(UTC) - timedelta(minutes=16)
    token = create_token(42, "access", settings(), now=old)

    with pytest.raises(InvalidTokenError):
        decode_token(token, "access", settings())


def test_zeton_z_drugo_skrivnostjo_ni_veljaven():
    token = create_token(42, "access", settings(jwt_secret="druga-" + SECRET))

    with pytest.raises(InvalidTokenError):
        decode_token(token, "access", settings())


def test_zeton_brez_podpisa_ni_veljaven():
    token = jwt.encode({"sub": "42", "type": "access"}, key=None, algorithm="none")

    with pytest.raises(InvalidTokenError):
        decode_token(token, "access", settings())


@pytest.mark.parametrize("secret", [None, "prekratka"])
def test_brez_dovolj_dolge_skrivnosti_ni_zetonov(secret):
    with pytest.raises(AuthConfigError, match="JWT_SECRET"):
        create_token(42, "access", Settings(_env_file=None, jwt_secret=secret))
