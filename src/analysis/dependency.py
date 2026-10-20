import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.analysis.models import Finding
from src.models.repository import RepositoryWorkspace


@dataclass
class DependencyAnalysisResult:
    """Findings and warnings produced by dependency analysis."""

    findings: list[Finding] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _find_requirement_files(workspace_path: Path) -> list[Path]:
    """Find conventional Python requirements files in the repository."""
    candidates = list(workspace_path.glob("requirements*.txt"))

    requirements_dir = workspace_path / "requirements"
    if requirements_dir.is_dir():
        candidates.extend(requirements_dir.rglob("*.txt"))

    return sorted(
        {
            path.resolve()
            for path in candidates
            if path.is_file()
        }
    )


def _parse_audit_output(
    output: str,
    manifest_path: str,
) -> list[Finding]:
    """Convert pip-audit JSON output into normalized findings."""
    try:
        payload: Any = json.loads(output)
    except (json.JSONDecodeError, TypeError):
        raise ValueError("Dependency scanner returned invalid JSON") from None

    dependencies = (
        payload.get("dependencies", [])
        if isinstance(payload, dict)
        else payload
    )

    if not isinstance(dependencies, list):
        raise ValueError("Dependency scanner returned an unexpected JSON format")

    findings: list[Finding] = []

    for dependency in dependencies:
        if not isinstance(dependency, dict):
            continue

        package_name = dependency.get("name", "Unknown package")
        package_version = dependency.get("version", "unknown")
        vulnerabilities = dependency.get("vulns", [])

        if not isinstance(vulnerabilities, list):
            continue

        for vulnerability in vulnerabilities:
            if not isinstance(vulnerability, dict):
                continue

            vulnerability_id = (
                vulnerability.get("id")
                or "Unknown vulnerability"
            )
            fix_versions = vulnerability.get("fix_versions") or []
            aliases = vulnerability.get("aliases") or []
            description = vulnerability.get("description") or (
                "The vulnerability database did not provide a description."
            )

            details = [
                f"Package: {package_name}",
                f"Installed/resolved version: {package_version}",
                f"Advisory: {vulnerability_id}",
            ]

            if aliases:
                details.append(
                    "Aliases: " + ", ".join(str(item) for item in aliases)
                )

            if fix_versions:
                details.append(
                    "Available fix versions: "
                    + ", ".join(str(item) for item in fix_versions)
                )
            else:
                details.append("No fix version was reported by the scanner.")

            findings.append(
                Finding(
                    category="dependency_vulnerability",
                    severity="unknown",
                    title=f"Vulnerable dependency: {package_name}",
                    description=str(description),
                    file_path=manifest_path,
                    rule_id=str(vulnerability_id),
                    analyzer="pip-audit",
                    evidence="; ".join(details),
                )
            )

    return findings


def _audit_requirements_file(
    workspace_path: Path,
    manifest_path: Path,
) -> DependencyAnalysisResult:
    """Audit one requirements file without scanning the application's environment."""
    relative_manifest = manifest_path.relative_to(workspace_path).as_posix()

    if shutil.which("pip-audit") is None:
        return DependencyAnalysisResult(
            warnings=[
                "Dependency analysis was skipped because pip-audit is not installed."
            ]
        )

    command = [
        "pip-audit",
        "--format=json",
        "--requirement",
        str(manifest_path),
    ]

    try:
        completed = subprocess.run(
            command,
            cwd=workspace_path,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return DependencyAnalysisResult(
            warnings=[
                f"Dependency analysis timed out for {relative_manifest}."
            ]
        )
    except OSError:
        return DependencyAnalysisResult(
            warnings=[
                f"Dependency analysis could not start for {relative_manifest}."
            ]
        )

    # pip-audit may return a nonzero exit code when vulnerabilities are found.
    # Therefore, inspect the JSON output before interpreting the exit code.
    if completed.stdout.strip():
        try:
            findings = _parse_audit_output(
                completed.stdout,
                relative_manifest,
            )
        except ValueError:
            findings = None

        if findings is not None:
            result = DependencyAnalysisResult(findings=findings)

            if completed.returncode != 0 and not findings:
                result.warnings.append(
                    f"Dependency analysis could not be completed for "
                    f"{relative_manifest}; inspect sanitized server logs."
                )

            return result

    return DependencyAnalysisResult(
        warnings=[
            f"Dependency analysis could not produce valid results for "
            f"{relative_manifest}; inspect sanitized server logs."
        ]
    )


def run_dependency_analysis(
    workspace: RepositoryWorkspace,
) -> DependencyAnalysisResult:
    """Audit declared Python requirements and report scanner limitations."""
    workspace_path = Path(workspace.workspace_path).resolve()

    if not workspace_path.is_dir():
        return DependencyAnalysisResult(
            warnings=["Dependency analysis skipped: repository workspace is unavailable."]
        )

    requirement_files = _find_requirement_files(workspace_path)

    if not requirement_files:
        if (workspace_path / "pyproject.toml").is_file():
            return DependencyAnalysisResult(
                warnings=[
                    "A pyproject.toml was detected, but no requirements file "
                    "was found. This analyzer currently does not audit "
                    "pyproject.toml declarations directly."
                ]
            )

        return DependencyAnalysisResult(
            warnings=[
                "No supported Python requirements files were found; "
                "Python dependency analysis was skipped."
            ]
        )

    combined = DependencyAnalysisResult()

    for manifest_path in requirement_files:
        result = _audit_requirements_file(
            workspace_path,
            manifest_path,
        )
        combined.findings.extend(result.findings)
        combined.warnings.extend(result.warnings)

    return combined