from pydantic import BaseModel, Field


class Issue(BaseModel):
    """A normalized issue identified in a repository."""

    issue_id: str
    source: str
    category: str
    severity: str
    title: str
    description: str
    file_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    rule_id: str | None = None
    evidence: str | None = None
    expected_behavior: str | None = None


class IssueDetectionResult(BaseModel):
    """Issues identified from repository analysis or a supplied issue."""

    issues: list[Issue] = Field(default_factory=list)