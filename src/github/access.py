from sqlalchemy.orm import Session

from src.github.repositories import GitHubAuthenticationError
from src.github.token_service import (
    GitHubTokenRefreshError,
    get_stored_access_token,
    refresh_github_access_token,
)
from src.models.github_authorization import GitHubAuthorization


def execute_with_github_access(
    db: Session,
    authorization: GitHubAuthorization,
    operation,
):
    """
    Execute one GitHub operation.

    Normal path:
        stored access token -> operation

    Authentication failure:
        stored access token -> 401
        -> refresh token
        -> persist rotated tokens
        -> retry once
    """

    access_token = get_stored_access_token(
        authorization
    )

    try:
        return operation(access_token)

    except GitHubAuthenticationError:
        try:
            refreshed_access_token = (
                refresh_github_access_token(
                    db=db,
                    authorization=authorization,
                )
            )
        except GitHubTokenRefreshError:
            raise

        return operation(refreshed_access_token)