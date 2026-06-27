import base64
import hashlib
from cryptography.fernet import Fernet
from backend.config.settings import get_settings

def _get_fernet() -> Fernet:
    """
    Derives a valid 32-byte URL-safe base64 key from the app's secret_key
    and returns a Fernet instance for symmetric encryption.
    """
    settings = get_settings()
    # Hash the secret key to get exactly 32 bytes
    key_bytes = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    # Fernet requires a URL-safe base64-encoded 32-byte key
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)

def encrypt_token(token: str) -> str:
    """Encrypts a plaintext token into a secure string."""
    if not token:
        return token
    f = _get_fernet()
    return f.encrypt(token.encode("utf-8")).decode("utf-8")

def decrypt_token(encrypted_token: str) -> str:
    """Decrypts a secure string back into a plaintext token."""
    if not encrypted_token:
        return encrypted_token
    f = _get_fernet()
    return f.decrypt(encrypted_token.encode("utf-8")).decode("utf-8")
