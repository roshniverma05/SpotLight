from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class RepositoryRef(BaseModel):
    """Identifies an authorized GitHub repository."""

    provider: Literal["github"] = "github"
    owner: str = Field(..., min_length=1)
    repository: str = Field(..., min_length=1)


class RepositoryWorkspace(BaseModel):
    """Represents an acquired repository workspace."""

    workspace_id: UUID
    repository: RepositoryRef
    workspace_path: Path
    commit_sha: str = Field(..., min_length=7)