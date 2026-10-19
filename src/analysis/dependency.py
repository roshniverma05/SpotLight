import json
import subprocess

from src.analysis.models import Finding
from src.models.repository import RepositoryWorkspace


class DependencyAnalysisError(Exception):
    """Raised when dependency analysis cannot be completed."""


def run_dependency_analysis(
    workspace: RepositoryWorkspace,
) -> list[Finding]:
    """
    Audit Python dependencies in the repository using pip-audit.

    Returns normalized findings for known dependency vulnerabilities.
    """

    workspace_path = workspace.workspace_path

    if not workspace_path.is_dir():
        raise DependencyAnalysisError(
            f"Repository workspace does not exist: {workspace_path}"
        )

    command = [
        "pip-audit",
        "--format=json",
        "--path",
        str(workspace_path),
    ]

    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except FileNotFoundError as exc:
        raise DependencyAnalysisError(
            "pip-audit executable was not found."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise DependencyAnalysisError(
            "Dependency analysis timed out."
        ) from exc
    except OSError as exc:
        raise DependencyAnalysisError(
            "Failed to start pip-audit."
        ) from exc

    if not process.stdout.strip():
        raise DependencyAnalysisError(
            f"pip-audit returned no output: {process.stderr.strip()}"
        )

    try:
        audit_data = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise DependencyAnalysisError(
            "pip-audit returned invalid JSON."
        ) from exc

    return [
        _convert_vulnerability(vulnerability)
        for vulnerability in _extract_vulnerabilities(audit_data)
    ]


def _extract_vulnerabilities(audit_data: dict) -> list[dict]:
    """Extract vulnerability records from pip-audit JSON output."""

    vulnerabilities: list[dict] = []

    for dependency in audit_data.get("dependencies", []):
        for vulnerability in dependency.get("vulns", []):
            vulnerabilities.append(
                {
                    "package": dependency.get("name", "unknown"),
                    "version": dependency.get("version", "unknown"),
                    **vulnerability,
                }
            )

    return vulnerabilities


def _convert_vulnerability(vulnerability: dict) -> Finding:
    """Convert one pip-audit vulnerability into our Finding model."""

    package = vulnerability["package"]
    version = vulnerability["version"]
    vulnerability_id = vulnerability.get(
        "id",
        "unknown-vulnerability",
    )

    description = vulnerability.get(
        "description",
        "Known vulnerability found in a dependency.",
    )

    fix_versions = vulnerability.get("fix_versions", [])

    fix_text = (
        f"Upgrade to: {', '.join(fix_versions)}."
        if fix_versions
        else "No fixed version was reported."
    )

    return Finding(
        category="dependency",
        severity="high",
        title=f"Vulnerable dependency: {package}",
        description=description,
        file_path="",
        rule_id=vulnerability_id,
        analyzer="pip-audit",
        evidence=(
            f"Package: {package}\n"
            f"Installed version: {version}\n"
            f"{fix_text}"
        ),
    )