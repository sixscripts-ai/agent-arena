import pytest

from agent_arena.crypto import decrypt_key, encrypt_key, mask_key, new_key


def test_roundtrip():
    key = new_key()
    token = encrypt_key("sk-secret-value-1234567890", key)
    assert decrypt_key(token, key) == "sk-secret-value-1234567890"


def test_wrong_key_fails():
    key = new_key()
    token = encrypt_key("secret", key)
    with pytest.raises(ValueError):
        decrypt_key(token, new_key())


def test_tampered_token_fails():
    key = new_key()
    token = encrypt_key("secret", key)
    with pytest.raises(ValueError):
        decrypt_key(token[:-1] + ("X" if token[-1] != "X" else "Y"), key)


def test_mask():
    assert mask_key("sk-abcdefghijkl1234") == "sk-a********1234"
    assert mask_key("short") == "*****"
    assert "sk-abcdefghijkl1234" not in mask_key("sk-abcdefghijkl1234")
