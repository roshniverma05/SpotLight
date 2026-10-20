import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
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
from config.settings import settings


router = APIRouter(
    prefix="/auth/github",
    tags=["GitHub Authorization"],
)

OAUTH_STATE_TTL_MINUTES = 10
OAUTH_STATE_COOKIE = "github_oauth_state"


def _utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _invalid_state() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired OAuth state",
    )


@router.get("/authorize")
def authorize_github(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    state = secrets.token_urlsafe(32)

    oauth_state = GitHubOAuthState(
        user_id=current_user.id,
        state=state,
    )

    try:
        db.add(oauth_state)
        db.commit()

        authorization_url = build_github_authorization_url(state)

        response = RedirectResponse(
            url=authorization_url,
            status_code=status.HTTP_302_FOUND,
        )
        response.set_cookie(
            key=OAUTH_STATE_COOKIE,
            value=state,
            max_age=OAUTH_STATE_TTL_MINUTES * 60,
            httponly=True,
            secure=settings.ENVIRONMENT.lower() == "production",
            samesite="lax",
            path="/auth/github/callback",
        )
        return response

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not start GitHub authorization",
        ) from None


@router.get("/callback")
def github_callback(
    request: Request,
    code: str,
    state: str,
    db: Session = Depends(get_db),
):
    cookie_state = request.cookies.get(OAUTH_STATE_COOKIE)

    # Require the callback state to match the initiating browser's cookie.
    if (
        not cookie_state
        or not secrets.compare_digest(cookie_state, state)
    ):
        raise _invalid_state()

    oauth_state = (
        db.query(GitHubOAuthState)
        .filter(GitHubOAuthState.state == state)
        .with_for_update()
        .first()
    )

    if oauth_state is None:
        raise _invalid_state()

    now = datetime.now(timezone.utc)
    created_at = _utc_datetime(oauth_state.created_at)

    if now >= created_at + timedelta(
        minutes=OAUTH_STATE_TTL_MINUTES
    ):
        db.delete(oauth_state)
        db.commit()
        raise _invalid_state()

    user_id = oauth_state.user_id

    # Consume the state before external calls; it cannot be reused.
    db.delete(oauth_state)
    db.commit()

    try:
        token_data = exchange_code_for_token(code)
        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="GitHub did not return an access token",
            )

        github_user = get_github_user(access_token)

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub authorization failed",
        ) from None

    github_user_id = github_user.get("id")
    github_username = github_user.get("login")

    if not github_user_id or not github_username:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid GitHub user information",
        )

    try:
        encrypted_access_token = encrypt_token(access_token)

        refresh_token = token_data.get("refresh_token")
        encrypted_refresh_token = (
            encrypt_token(refresh_token) if refresh_token else None
        )

        now = datetime.now(timezone.utc)

        expires_in = token_data.get("expires_in")
        access_token_expires_at = (
            now + timedelta(seconds=int(expires_in))
            if expires_in is not None
            else None
        )

        refresh_expires_in = token_data.get(
            "refresh_token_expires_in"
        )
        refresh_token_expires_at = (
            now + timedelta(seconds=int(refresh_expires_in))
            if refresh_expires_in is not None
            else None
        )

        authorization = (
            db.query(GitHubAuthorization)
            .filter(GitHubAuthorization.user_id == user_id)
            .with_for_update()
            .first()
        )

        if authorization:
            authorization.github_user_id = str(github_user_id)
            authorization.github_username = github_username
            authorization.access_token_encrypted = encrypted_access_token
            authorization.refresh_token_encrypted = encrypted_refresh_token
            authorization.access_token_expires_at = access_token_expires_at
            authorization.refresh_token_expires_at = refresh_token_expires_at
        else:
            db.add(
                GitHubAuthorization(
                    user_id=user_id,
                    github_user_id=str(github_user_id),
                    github_username=github_username,
                    access_token_encrypted=encrypted_access_token,
                    refresh_token_encrypted=encrypted_refresh_token,
                    access_token_expires_at=access_token_expires_at,
                    refresh_token_expires_at=refresh_token_expires_at,
                )
            )

        db.commit()

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save GitHub authorization",
        ) from None

    response = RedirectResponse(
        url="/",
        status_code=status.HTTP_303_SEE_OTHER,
    )
    response.delete_cookie(
        key=OAUTH_STATE_COOKIE,
        path="/auth/github/callback",
        secure=settings.ENVIRONMENT.lower() == "production",
        httponly=True,
        samesite="lax",
    )
    return response
