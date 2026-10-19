from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher


password_hash = PasswordHash(
    hashers=[Argon2Hasher()]
)


def hash_password(password: str) -> str:
    """Hash a plain-text password."""
    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """Verify a plain-text password against its hash."""
    return password_hash.verify(
        plain_password,
        hashed_password,
    )