from cryptography.fernet import Fernet, InvalidToken


def new_key() -> bytes:
    return Fernet.generate_key()


def encrypt_key(plaintext: str, key: bytes) -> str:
    return Fernet(key).encrypt(plaintext.encode()).decode()


def decrypt_key(token: str, key: bytes) -> str:
    try:
        return Fernet(key).decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Invalid key or tampered ciphertext") from exc


def mask_key(plaintext: str) -> str:
    if len(plaintext) <= 8:
        return "*" * len(plaintext)
    return f"{plaintext[:4]}{'*' * 8}{plaintext[-4:]}"
