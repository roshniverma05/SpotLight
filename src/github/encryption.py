from cryptography.fernet import Fernet, InvalidToken

from config.settings import settings


def _get_fernet() -> Fernet:
    """Create a Fernet encryption instance from application settings."""

    key = settings.GITHUB_TOKEN_ENCRYPTION_KEY

    if not key:
        raise RuntimeError(
            "GITHUB_TOKEN_ENCRYPTION_KEY is not configured."
        )

    try:
        return Fernet(key.encode())
    except Exception as exc:
        raise RuntimeError(
            "GITHUB_TOKEN_ENCRYPTION_KEY is invalid."
        ) from exc


def encrypt_token(token: str) -> str:
    """Encrypt a GitHub token before database storage."""

    if not token:
        raise ValueError("Token cannot be empty.")

    fernet = _get_fernet()

    encrypted = fernet.encrypt(token.encode())

    return encrypted.decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a stored GitHub token when it is needed."""

    if not encrypted_token:
        raise ValueError("Encrypted token cannot be empty.")

    fernet = _get_fernet()

    try:
        decrypted = fernet.decrypt(encrypted_token.encode())
    except InvalidToken as exc:
        raise ValueError(
            "Unable to decrypt token."
        ) from exc

    return decrypted.decode()