import shutil
from pathlib import Path
from uuid import UUID, uuid4

from git import GitCommandError, Repo
from sqlalchemy import select
from sqlalchemy.orm import Session

from config.settings import settings
from src.github.repositories import (
    get_github_repository,
    get_github_repository_current_commit,
)
from src.models.repository import RepositoryRef, RepositoryWorkspace
from src.models.repository_record import RepositoryRecord
from src.models.repository_version import RepositoryVersion


def _find_repository_record(
    db: Session,
    user_id: UUID,
    repository: RepositoryRef,
) -> RepositoryRecord | None:
    statement = select(RepositoryRecord).where(
        RepositoryRecord.user_id == user_id,
        RepositoryRecord.provider == repository.provider,
        RepositoryRecord.owner == repository.owner,
        RepositoryRecord.repository == repository.repository,
    )

    return db.scalar(statement)


def _create_repository_record(
    db: Session,
    user_id: UUID,
    repository: RepositoryRef,
) -> RepositoryRecord:
    record = RepositoryRecord(
        user_id=user_id,
        provider=repository.provider,
        owner=repository.owner,
        repository=repository.repository,
    )

    db.add(record)
    db.flush()

    return record


def _find_repository_version(
    db: Session,
    repository_id: UUID,
    commit_sha: str,
) -> RepositoryVersion | None:
    statement = select(RepositoryVersion).where(
        RepositoryVersion.repository_id == repository_id,
        RepositoryVersion.commit_sha == commit_sha,
    )

    return db.scalar(statement)


def _workspace_exists(
    version: RepositoryVersion,
) -> bool:
    return Path(version.workspace_path).is_dir()


def _clone_repository(
    repository: RepositoryRef,
    access_token: str,
) -> tuple[UUID, Path, str]:
    workspace_id = uuid4()

    workspace_path = (
        settings.WORKSPACE_DIR
        / f"repo_{workspace_id.hex}"
    )

    workspace_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    clone_url = (
        f"https://x-access-token:{access_token}"
        f"@github.com/"
        f"{repository.owner}/"
        f"{repository.repository}.git"
    )

    try:
        repo = Repo.clone_from(
            clone_url,
            workspace_path,
        )

        commit_sha = repo.head.commit.hexsha

        return workspace_id, workspace_path, commit_sha

    except (GitCommandError, OSError):
        if workspace_path.exists():
            shutil.rmtree(
                workspace_path,
                ignore_errors=True,
            )

        raise


def acquire_or_reuse_repository(
    db: Session,
    user_id: UUID,
    repository: RepositoryRef,
    access_token: str,
) -> RepositoryWorkspace:
    if repository.provider != "github":
        raise ValueError(
            "Repository acquisition currently supports GitHub only."
        )

    # 1. Get repository metadata from GitHub.
    github_repository = get_github_repository(
        access_token=access_token,
        owner=repository.owner,
        repository=repository.repository,
    )

    default_branch = github_repository.get("default_branch")

    if not default_branch:
        raise RuntimeError(
            "GitHub repository does not have a default branch."
        )

    # 2. Determine the exact current repository version.
    current_commit_sha = get_github_repository_current_commit(
        access_token=access_token,
        owner=repository.owner,
        repository=repository.repository,
        default_branch=default_branch,
    )

    # 3. Find or create the logical repository record.
    repository_record = _find_repository_record(
        db=db,
        user_id=user_id,
        repository=repository,
    )

    if repository_record is None:
        repository_record = _create_repository_record(
            db=db,
            user_id=user_id,
            repository=repository,
        )

    # 4. Find the exact commit version.
    existing_version = _find_repository_version(
        db=db,
        repository_id=repository_record.id,
        commit_sha=current_commit_sha,
    )

    # 5. Reuse existing physical workspace when possible.
    if existing_version and _workspace_exists(existing_version):
        return RepositoryWorkspace(
            workspace_id=existing_version.workspace_id,
            repository=repository,
            workspace_path=Path(existing_version.workspace_path),
            commit_sha=existing_version.commit_sha,
        )

    # 6. Clone only when the exact version is not available locally.
    (
        workspace_id,
        workspace_path,
        acquired_commit_sha,
    ) = _clone_repository(
        repository=repository,
        access_token=access_token,
    )

    # The clone must represent the commit we identified from GitHub.
    if acquired_commit_sha != current_commit_sha:
        shutil.rmtree(
            workspace_path,
            ignore_errors=True,
        )

        raise RuntimeError(
            "Repository changed during acquisition. "
            "Please retry the acquisition."
        )

    # 7. Existing DB version, but physical workspace was removed.
    if existing_version:
        existing_version.workspace_id = workspace_id
        existing_version.workspace_path = str(workspace_path)

        db.commit()
        db.refresh(existing_version)

        return RepositoryWorkspace(
            workspace_id=existing_version.workspace_id,
            repository=repository,
            workspace_path=Path(existing_version.workspace_path),
            commit_sha=existing_version.commit_sha,
        )

    # 8. First acquisition of this repository version.
    version = RepositoryVersion(
        repository_id=repository_record.id,
        commit_sha=acquired_commit_sha,
        workspace_id=workspace_id,
        workspace_path=str(workspace_path),
    )

    db.add(version)
    db.commit()
    db.refresh(version)

    return RepositoryWorkspace(
        workspace_id=version.workspace_id,
        repository=repository,
        workspace_path=Path(version.workspace_path),
        commit_sha=version.commit_sha,
    )