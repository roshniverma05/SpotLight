import json
import subprocess

from src.analysis.models import AnalysisResult, Finding
from src.models.repository import RepositoryWorkspace


class SemgrepAnalysisError(Exception):
    """Raised when Semgrep analysis cannot be completed."""


def run_semgrep(workspace: RepositoryWorkspace) -> AnalysisResult:
    """Run Semgrep against an acquired repository workspace."""

    workspace_path = workspace.workspace_path

    if not workspace_path.is_dir():
        raise SemgrepAnalysisError(
            f"Repository workspace does not exist: {workspace_path}"
        )

    command = [
        "semgrep",
        "scan",
        "--config",
        "auto",
        "--json",
        "--quiet",
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
        raise SemgrepAnalysisError(
            "Semgrep executable was not found."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise SemgrepAnalysisError(
            "Semgrep analysis timed out."
        ) from exc
    except OSError as exc:
        raise SemgrepAnalysisError(
            "Failed to start Semgrep."
        ) from exc

    if not process.stdout:
        if process.returncode != 0:
            raise SemgrepAnalysisError(
                f"Semgrep failed: {process.stderr.strip()}"
            )

        return AnalysisResult()

    try:
        semgrep_data = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise SemgrepAnalysisError(
            "Semgrep returned invalid JSON."
        ) from exc

    findings = [
        _convert_finding(result)
        for result in semgrep_data.get("results", [])
    ]

    return AnalysisResult(findings=findings)


def _convert_finding(result: dict) -> Finding:
    """Convert one Semgrep result into our normalized Finding."""

    extra = result.get("extra", {})
    start = result.get("start", {})
    end = result.get("end", {})

    metadata = extra.get("metadata", {})

    severity = (
        metadata.get("severity")
        or extra.get("severity")
        or "unknown"
    )

    category = metadata.get("category", "static_analysis")

    return Finding(
        category=str(category),
        severity=str(severity).lower(),
        title=extra.get("message", "Semgrep finding"),
        description=extra.get(
            "message",
            "Potential issue detected by Semgrep.",
        ),
        file_path=result.get("path", ""),
        line_start=start.get("line"),
        line_end=end.get("line"),
        rule_id=result.get("check_id"),
        analyzer="semgrep",
        evidence=extra.get("lines"),
    )