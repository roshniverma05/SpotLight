from pydantic import BaseModel, Field


class RepositoryProfile(BaseModel):
    """Describes the technology stack detected in a repository."""

    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    package_managers: list[str] = Field(default_factory=list)
    build_tools: list[str] = Field(default_factory=list)
    test_frameworks: list[str] = Field(default_factory=list)
    detected_files: list[str] = Field(default_factory=list)