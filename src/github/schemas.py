from pydantic import BaseModel, Field


class RepositorySelectionRequest(BaseModel):
    """Repository selected by the authenticated user."""

    owner: str = Field(..., min_length=1)
    repository: str = Field(..., min_length=1)