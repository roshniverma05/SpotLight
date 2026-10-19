import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from src.auth.dependencies import get_current_user, get_db
from src.github.encryption import encrypt_token
from src.github.oauth import (
    build_github_authorization_url,
    exchange_code_for_token,
    get_github_user,
)
from src.models.github_authorization import GitHubAuthorization
from src.models.github_oauth_state import GitHubOAuthState
from src.models.user import User


router = APIRouter(
    prefix="/auth/github",
    tags=["GitHub Authorization"],
)


@router.get("/authorize")
def authorize_github(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start GitHub OAuth for the authenticated application user."""

    state = secrets.token_urlsafe(32)

    oauth_state = GitHubOAuthState(
        user_id=current_user.id,
        state=state,
    )

    db.add(oauth_state)
    db.commit()

    authorization_url = build_github_authorization_url(state)

    return RedirectResponse(url=authorization_url)


@router.get("/callback")
def github_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db),
):
    """Handle the GitHub OAuth callback."""

    # 1. Validate OAuth state
    oauth_state = (
        db.query(GitHubOAuthState)
        .filter(GitHubOAuthState.state == state)
        .first()
    )

    if not oauth_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state",
        )

    # 2. Exchange authorization code for GitHub tokens
    try:
        token_data = exchange_code_for_token(code)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to exchange authorization code with GitHub",
        ) from exc

    access_token = token_data.get("access_token")

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub did not return an access token",
        )

    # 3. Get GitHub identity
    try:
        github_user = get_github_user(access_token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to retrieve GitHub user information",
        ) from exc

    github_user_id = github_user.get("id")
    github_username = github_user.get("login")

    if not github_user_id or not github_username:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid GitHub user information",
        )

    # 4. Encrypt tokens before database storage
    encrypted_access_token = encrypt_token(access_token)

    refresh_token = token_data.get("refresh_token")

    encrypted_refresh_token = (
        encrypt_token(refresh_token)
        if refresh_token
        else None
    )

    # 5. Calculate token expiration times
    now = datetime.now(timezone.utc)

    access_token_expires_at = None
    refresh_token_expires_at = None

    expires_in = token_data.get("expires_in")

    if expires_in is not None:
        access_token_expires_at = (
            now + timedelta(seconds=int(expires_in))
        )

    refresh_token_expires_in = token_data.get(
        "refresh_token_expires_in"
    )

    if refresh_token_expires_in is not None:
        refresh_token_expires_at = (
            now + timedelta(
                seconds=int(refresh_token_expires_in)
            )
        )

    # 6. Check whether this user already has a GitHub authorization
    authorization = (
        db.query(GitHubAuthorization)
        .filter(
            GitHubAuthorization.user_id == oauth_state.user_id
        )
        .first()
    )

    if authorization:
        authorization.github_user_id = str(github_user_id)
        authorization.github_username = github_username
        authorization.access_token_encrypted = encrypted_access_token
        authorization.refresh_token_encrypted = encrypted_refresh_token
        authorization.access_token_expires_at = (
            access_token_expires_at
        )
        authorization.refresh_token_expires_at = (
            refresh_token_expires_at
        )

    else:
        authorization = GitHubAuthorization(
            user_id=oauth_state.user_id,
            github_user_id=str(github_user_id),
            github_username=github_username,
            access_token_encrypted=encrypted_access_token,
            refresh_token_encrypted=encrypted_refresh_token,
            access_token_expires_at=access_token_expires_at,
            refresh_token_expires_at=refresh_token_expires_at,
        )

        db.add(authorization)

    # 7. Make OAuth state single-use
    db.delete(oauth_state)

    db.commit()

    return {
        "message": "GitHub authorization successful",
        "github_username": github_username,
        "access_token_expires_at": (
            access_token_expires_at.isoformat()
            if access_token_expires_at
            else None
        ),
        "refresh_token_expires_at": (
            refresh_token_expires_at.isoformat()
            if refresh_token_expires_at
            else None
        ),
    }