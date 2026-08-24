from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_is_hashed_and_verifiable():
    password = "correct horse battery staple"
    digest = hash_password(password)

    assert digest != password
    assert verify_password(password, digest)
    assert not verify_password("wrong password", digest)


def test_access_token_contains_subject():
    token = create_access_token("42", expires_minutes=5)

    assert decode_access_token(token)["sub"] == "42"
