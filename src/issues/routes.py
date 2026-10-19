from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.analysis.service import analyze_repository
from src.auth.dependencies import get_current_user
from src.database import SessionLocal
from src.issues.localization import localize_issue
from src.issues.models import IssueDetectionResult
from src.issues.schemas import IssueInput, IssueLocalization
from src.models.repository import RepositoryRef, RepositoryWorkspace
from src.models.repository_record import RepositoryRecord
from src.models.repository_version import RepositoryVersion
from src.models.user import User
from src.github.schemas import RepositorySelectionRequest


router = APIRouter(
    prefix="/issues",
    tags=["Issue Detection"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_workspace(
    selection: RepositorySelectionRequest,
    current_user: User,
    db: Session,
) -> RepositoryWorkspace:
    repository = RepositoryRef(
        provider="github",
        owner=selection.owner,
        repository=selection.repository,
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
        select(RepositoryVersion)
        .where(
            RepositoryVersion.repository_id == repository_record.id,
        )
        .order_by(RepositoryVersion.acquired_at.desc())
    )

    if repository_version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No acquired repository version was found.",
        )

    workspace_path = Path(repository_version.workspace_path)

    if not workspace_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "The acquired workspace no longer exists. "
                "Acquire the repository again."
            ),
        )

    return RepositoryWorkspace(
        workspace_id=repository_version.workspace_id,
        repository=repository,
        workspace_path=workspace_path,
        commit_sha=repository_version.commit_sha,
    )


@router.post(
    "/repository",
    response_model=IssueDetectionResult,
)
def detect_repository_issues(
    selection: RepositorySelectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Detect issues discovered directly from repository analysis.
    """

    workspace = _get_workspace(
        selection=selection,
        current_user=current_user,
        db=db,
    )

    try:
        analysis_result = analyze_repository(workspace)

        from src.issues.service import detect_repository_issues as detect

        return detect(analysis_result)

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Repository issue detection failed.",
        ) from exc


@router.post(
    "/localize",
    response_model=IssueLocalization,
)
def localize_supplied_issue(
    selection: RepositorySelectionRequest,
    issue: IssueInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Locate repository files and symbols relevant to a supplied
    GitHub/user issue.
    """

    workspace = _get_workspace(
        selection=selection,
        current_user=current_user,
        db=db,
    )

    try:
        return localize_issue(
            issue=issue,
            workspace=workspace,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Issue localization failed.",
        ) from exc