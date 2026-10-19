from src.analysis.dependency import run_dependency_analysis
from src.analysis.models import AnalysisResult
from src.analysis.quality import run_code_quality_analysis
from src.analysis.semgrep import run_semgrep
from src.analysis.tests import run_test_analysis
from src.models.repository import RepositoryWorkspace


def analyze_repository(
    workspace: RepositoryWorkspace,
) -> AnalysisResult:
    """Run all currently implemented repository analyzers."""

    semgrep_result = run_semgrep(workspace)

    dependency_findings = run_dependency_analysis(workspace)

    test_findings = run_test_analysis(workspace)

    quality_findings = run_code_quality_analysis(workspace)

    return AnalysisResult(
        findings=[
            *semgrep_result.findings,
            *dependency_findings,
            *test_findings,
            *quality_findings,
        ],
    )