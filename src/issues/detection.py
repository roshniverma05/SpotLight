from uuid import uuid4

from src.analysis.models import Finding
from src.issues.models import Issue, IssueDetectionResult


def detect_issues_from_findings(
    findings: list[Finding],
) -> IssueDetectionResult:
    """
    Convert repository analysis findings into normalized issues.
    """

    issues: list[Issue] = []

    for finding in findings:
        issues.append(
            Issue(
                issue_id=str(uuid4()),
                source=finding.analyzer,
                category=finding.category,
                severity=finding.severity,
                title=finding.title,
                description=finding.description,
                file_path=finding.file_path or None,
                line_start=finding.line_start,
                line_end=finding.line_end,
                rule_id=finding.rule_id,
                evidence=finding.evidence,
            )
        )

    return IssueDetectionResult(issues=issues)