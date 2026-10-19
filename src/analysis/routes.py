from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.analysis.models import AnalysisResult
from src.analysis.service import analyze_repository
from src.auth.dependencies import get_current_user
from src.database import SessionLocal
from src.github.schemas import RepositorySelectionRequest
from src.models.repository import RepositoryRef, RepositoryWorkspace
from src.models.repository_record import RepositoryRecord
from src.models.repository_version import RepositoryVersion
from src.models.user import User


router = APIRouter(
    prefix="/analysis",
    tags=["Analysis"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/repository",
    response_model=AnalysisResult,
)
def analyze_selected_repository(
    selection: RepositorySelectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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

    workspace = RepositoryWorkspace(
        workspace_id=repository_version.workspace_id,
        repository=repository,
        workspace_path=workspace_path,
        commit_sha=repository_version.commit_sha,
    )

    try:
        return analyze_repository(workspace)

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Repository analysis failed.",
        ) from exc