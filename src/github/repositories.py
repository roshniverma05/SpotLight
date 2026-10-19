import requests


GITHUB_API_URL = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"


class GitHubAuthenticationError(Exception):
    """Raised when a GitHub access token is invalid."""


def _github_headers(access_token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {access_token}",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
        "User-Agent": "Autonomous-DevSecOps",
    }


def _github_get(
    access_token: str,
    url: str,
    params: dict | None = None,
) -> requests.Response:
    response = requests.get(
        url,
        headers=_github_headers(access_token),
        params=params,
        timeout=10,
    )

    if response.status_code == 401:
        raise GitHubAuthenticationError(
            "GitHub access token is invalid or revoked."
        )

    response.raise_for_status()

    return response


def list_github_repositories(
    access_token: str,
) -> list[dict]:
    repositories: list[dict] = []
    page = 1

    while True:
        response = _github_get(
            access_token=access_token,
            url=f"{GITHUB_API_URL}/user/repos",
            params={
                "per_page": 100,
                "page": page,
                "sort": "updated",
            },
        )

        page_data = response.json()

        if not page_data:
            break

        repositories.extend(page_data)

        if len(page_data) < 100:
            break

        page += 1

    return repositories


def get_github_repository(
    access_token: str,
    owner: str,
    repository: str,
) -> dict:
    response = _github_get(
        access_token=access_token,
        url=f"{GITHUB_API_URL}/repos/{owner}/{repository}",
    )

    return response.json()


def get_github_repository_current_commit(
    access_token: str,
    owner: str,
    repository: str,
    default_branch: str,
) -> str:
    response = _github_get(
        access_token=access_token,
        url=(
            f"{GITHUB_API_URL}/repos/"
            f"{owner}/{repository}/commits/"
            f"{default_branch}"
        ),
    )

    commit_sha = response.json().get("sha")

    if not commit_sha:
        raise RuntimeError(
            "GitHub did not return a commit SHA."
        )

    return commit_sha