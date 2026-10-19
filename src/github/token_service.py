from datetime import datetime, timedelta, timezone

import requests
from sqlalchemy.orm import Session

from config.settings import settings
from src.github.encryption import decrypt_token, encrypt_token
from src.models.github_authorization import GitHubAuthorization


GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"


class GitHubTokenRefreshError(Exception):
    """Raised when a GitHub access token cannot be refreshed."""


def refresh_github_access_token(
    db: Session,
    authorization: GitHubAuthorization,
) -> str:
    if not authorization.refresh_token_encrypted:
        raise GitHubTokenRefreshError(
            "GitHub refresh token is not available. "
            "GitHub authorization must be renewed."
        )

    refresh_token = decrypt_token(
        authorization.refresh_token_encrypted
    )

    response = requests.post(
        GITHUB_TOKEN_URL,
        params={
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        headers={
            "Accept": "application/json",
        },
        timeout=10,
    )

    data = response.json()

    if not response.ok or not data.get("access_token"):
        error = data.get("error", "unknown_error")
        description = data.get(
            "error_description",
            "GitHub token refresh failed.",
        )

        raise GitHubTokenRefreshError(
            f"{error}: {description}"
        )

    new_access_token = data["access_token"]
    new_refresh_token = data.get("refresh_token")

    expires_in = data.get("expires_in")
    refresh_token_expires_in = data.get(
        "refresh_token_expires_in"
    )

    now = datetime.now(timezone.utc)

    authorization.access_token_encrypted = encrypt_token(
        new_access_token
    )

    if new_refresh_token:
        authorization.refresh_token_encrypted = encrypt_token(
            new_refresh_token
        )

    if expires_in is not None:
        authorization.access_token_expires_at = (
            now + timedelta(seconds=int(expires_in))
        )

    if refresh_token_expires_in is not None:
        authorization.refresh_token_expires_at = (
            now + timedelta(
                seconds=int(refresh_token_expires_in)
            )
        )

    authorization.updated_at = now

    db.commit()
    db.refresh(authorization)

    return new_access_token


def get_stored_access_token(
    authorization: GitHubAuthorization,
) -> str:
    return decrypt_token(
        authorization.access_token_encrypted
    )