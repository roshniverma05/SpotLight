from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.auth.dependencies import get_current_user
from src.database import SessionLocal
from src.github.access import execute_with_github_access
from src.github.repositories import (
    get_github_repository,
    get_github_repository_current_commit,
    list_github_repositories,
)
from src.github.schemas import RepositorySelectionRequest
from src.models.github_authorization import GitHubAuthorization
from src.models.repository import RepositoryRef, RepositoryWorkspace
from src.models.repository_record import RepositoryRecord
from src.models.repository_version import RepositoryVersion
from src.models.user import User
from src.repository.acquisition import acquire_or_reuse_repository
from src.repository.discovery import discover_repository


router = APIRouter(
    prefix="/github/repositories",
    tags=["GitHub Repositories"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_github_authorization(
    db: Session,
    user_id: UUID,
) -> GitHubAuthorization:
    authorization = db.scalar(
        select(GitHubAuthorization).where(
            GitHubAuthorization.user_id == user_id
        )
    )

    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GitHub account is not authorized.",
        )

    return authorization


@router.get("")
def list_repositories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    authorization = _get_github_authorization(
        db=db,
        user_id=current_user.id,
    )

    try:
        repositories = execute_with_github_access(
            db=db,
            authorization=authorization,
            operation=list_github_repositories,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to retrieve repositories from GitHub.",
        ) from exc

    return [
        {
            "owner": repository.get("owner", {}).get("login"),
            "repository": repository.get("name"),
            "private": repository.get("private", False),
            "default_branch": repository.get("default_branch"),
            "html_url": repository.get("html_url"),
        }
        for repository in repositories
    ]


@router.post(
    "/select",
    response_model=RepositoryRef,
)
def select_repository(
    selection: RepositorySelectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    authorization = _get_github_authorization(
        db=db,
        user_id=current_user.id,
    )

    try:
        execute_with_github_access(
            db=db,
            authorization=authorization,
            operation=lambda access_token: get_github_repository(
                access_token=access_token,
                owner=selection.owner,
                repository=selection.repository,
            ),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Selected repository is not accessible.",
        ) from exc

    return RepositoryRef(
        provider="github",
        owner=selection.owner,
        repository=selection.repository,
    )


@router.post(
    "/acquire",
    response_model=RepositoryWorkspace,
)
def acquire_repository(
    selection: RepositorySelectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    authorization = _get_github_authorization(
        db=db,
        user_id=current_user.id,
    )

    try:
        return execute_with_github_access(
            db=db,
            authorization=authorization,
            operation=lambda access_token: acquire_or_reuse_repository(
                db=db,
                user_id=current_user.id,
                repository=RepositoryRef(
                    provider="github",
                    owner=selection.owner,
                    repository=selection.repository,
                ),
                access_token=access_token,
            ),
        )

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Repository acquisition failed.",
        ) from exc


@router.post("/discover")
def discover_selected_repository(
    selection: RepositorySelectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    authorization = _get_github_authorization(
        db=db,
        user_id=current_user.id,
    )

    repository = RepositoryRef(
        provider="github",
        owner=selection.owner,
        repository=selection.repository,
    )

    try:
        github_repository = execute_with_github_access(
            db=db,
            authorization=authorization,
            operation=lambda access_token: get_github_repository(
                access_token=access_token,
                owner=repository.owner,
                repository=repository.repository,
            ),
        )

        default_branch = github_repository.get("default_branch")

        if not default_branch:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="GitHub repository has no default branch.",
            )

        current_commit_sha = execute_with_github_access(
            db=db,
            authorization=authorization,
            operation=lambda access_token: (
                get_github_repository_current_commit(
                    access_token=access_token,
                    owner=repository.owner,
                    repository=repository.repository,
                    default_branch=default_branch,
                )
            ),
        )

        repository_record = db.scalar(
            select(RepositoryRecord).where(
                RepositoryRecord.user_id == current_user.id,
                RepositoryRecord.provider == repository.provider,
                RepositoryRecord.owner == repository.owner,
                RepositoryRecord.repository == repository.repository,
            )
        )

        if repository_record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository has not been acquired yet.",
            )

        repository_version = db.scalar(
            select(RepositoryVersion).where(
                RepositoryVersion.repository_id == repository_record.id,
                RepositoryVersion.commit_sha == current_commit_sha,
            )
        )

        if repository_version is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "Current repository version has not been acquired yet."
                ),
            )

        workspace_path = Path(
            repository_version.workspace_path
        )

        if not workspace_path.is_dir():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "The acquired workspace no longer exists. "
                    "Acquire the repository again."
                ),
            )

        workspace = RepositoryWorkspace(
            workspace_id=repository_version.workspace_id,
            repository=repository,
            workspace_path=workspace_path,
            commit_sha=repository_version.commit_sha,
        )

        profile = discover_repository(
            workspace
        )

        return {
            "workspace_id": workspace.workspace_id,
            "provider": workspace.repository.provider,
            "owner": workspace.repository.owner,
            "repository": workspace.repository.repository,
            "workspace_path": str(workspace.workspace_path),
            "commit_sha": workspace.commit_sha,
            "profile": profile,
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Repository discovery failed.",
        ) from exc