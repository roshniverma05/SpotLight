from pydantic import BaseModel, Field


class IssueInput(BaseModel):
    """Issue supplied by a user or GitHub Issue."""

    title: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    source: str = "github_issue"


class IssueLocalization(BaseModel):
    """Repository locations relevant to a supplied issue."""

    issue: IssueInput
    relevant_files: list[str] = Field(default_factory=list)
    relevant_symbols: list[str] = Field(default_factory=list)