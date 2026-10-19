from src.analysis.models import AnalysisResult
from src.issues.detection import detect_issues_from_findings
from src.issues.models import IssueDetectionResult


def detect_repository_issues(
    analysis_result: AnalysisResult,
) -> IssueDetectionResult:
    """
    Detect actionable issues from repository analysis findings.
    """

    return detect_issues_from_findings(
        findings=analysis_result.findings,
    )