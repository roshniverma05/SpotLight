
from pydantic import BaseModel, Field


class Finding(BaseModel):
    """A single issue discovered during repository analysis."""

    category: str
    severity: str
    title: str
    description: str
    file_path: str
    line_start: int | None = None
    line_end: int | None = None
    rule_id: str | None = None
    analyzer: str
    evidence: str | None = None


class AnalysisResult(BaseModel):
    """Repository findings and any checks that could not run."""

    findings: list[Finding] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
