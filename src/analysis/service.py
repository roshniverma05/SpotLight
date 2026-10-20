from src.analysis.dependency import run_dependency_analysis
from src.analysis.models import AnalysisResult
from src.analysis.quality import run_code_quality_analysis
from src.analysis.semgrep import run_semgrep
from src.models.repository import RepositoryWorkspace


def analyze_repository(
    workspace: RepositoryWorkspace,
) -> AnalysisResult:
    """Run enabled analyzers and preserve warnings about skipped checks."""

    semgrep_result = run_semgrep(workspace)
    dependency_result = run_dependency_analysis(workspace)
    quality_findings = run_code_quality_analysis(workspace)

    warnings = [
        *dependency_result.warnings,
        (
            "Repository tests were not executed because isolated "
            "sandbox execution is not yet implemented."
        ),
    ]

    return AnalysisResult(
        findings=[
            *semgrep_result.findings,
            *dependency_result.findings,
            *quality_findings,
        ],
        warnings=warnings,
    )