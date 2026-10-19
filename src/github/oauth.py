import requests

from config.settings import settings


GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_URL = "https://api.github.com"


def build_github_authorization_url(state: str) -> str:
    """Build the GitHub OAuth authorization URL."""

    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": settings.GITHUB_REDIRECT_URI,
        "state": state,
    }

    response = requests.Request(
        "GET",
        GITHUB_AUTHORIZE_URL,
        params=params,
    ).prepare()

    return response.url


def exchange_code_for_token(code: str) -> dict:
    """Exchange a GitHub authorization code for tokens."""

    response = requests.post(
        GITHUB_TOKEN_URL,
        data={
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": settings.GITHUB_REDIRECT_URI,
        },
        headers={
            "Accept": "application/json",
        },
        timeout=10,
    )

    response.raise_for_status()

    return response.json()


def get_github_user(access_token: str) -> dict:
    """Get the GitHub identity associated with an access token."""

    response = requests.get(
        f"{GITHUB_API_URL}/user",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
            "X-GitHub-Api-Version": "2026-03-10",
        },
        timeout=10,
    )

    response.raise_for_status()

    return response.json()