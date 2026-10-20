from src.analysis.models import Finding
from src.models.repository import RepositoryWorkspace


class TestAnalysisError(RuntimeError):
    """Raised when safe test execution is unavailable."""


def run_test_analysis(
    workspace: RepositoryWorkspace,
) -> list[Finding]:
    raise TestAnalysisError(
        "Test execution is disabled until sandboxed execution "
        "is implemented."
    )