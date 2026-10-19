import subprocess

from src.analysis.models import Finding
from src.models.repository import RepositoryWorkspace


class TestAnalysisError(Exception):
    """Raised when test analysis cannot be completed."""


def run_test_analysis(
    workspace: RepositoryWorkspace,
) -> list[Finding]:
    """
    Detect and execute the repository's supported test framework.
    """

    workspace_path = workspace.workspace_path

    if not workspace_path.is_dir():
        raise TestAnalysisError(
            f"Repository workspace does not exist: {workspace_path}"
        )

    framework = _detect_test_framework(workspace_path)

    if framework is None:
        return []

    command = _build_test_command(framework)

    try:
        process = subprocess.run(
            command,
            cwd=workspace_path,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise TestAnalysisError(
            "Test execution timed out."
        ) from exc
    except OSError as exc:
        raise TestAnalysisError(
            "Failed to start test framework."
        ) from exc

    if process.returncode == 0:
        return []

    return [
        Finding(
            category="test_failure",
            severity="high",
            title=f"{framework} test suite failed",
            description=(
                "The repository test suite completed with failures."
            ),
            file_path="",
            analyzer="test_runner",
            evidence=(
                f"Framework: {framework}\n\n"
                f"STDOUT:\n{process.stdout[-10000:]}\n\n"
                f"STDERR:\n{process.stderr[-10000:]}"
            ),
        )
    ]


def _detect_test_framework(workspace_path):
    """Detect the repository's supported test framework."""

    if (
        (workspace_path / "pytest.ini").exists()
        or (workspace_path / "pyproject.toml").exists()
        or (workspace_path / "setup.cfg").exists()
        or any(workspace_path.rglob("test_*.py"))
        or any(workspace_path.rglob("*_test.py"))
    ):
        return "pytest"

    if (workspace_path / "package.json").exists():
        package_json = workspace_path / "package.json"

        try:
            import json

            data = json.loads(package_json.read_text(encoding="utf-8"))

            dependencies = {
                *data.get("dependencies", {}).keys(),
                *data.get("devDependencies", {}).keys(),
            }

            if "vitest" in dependencies:
                return "vitest"

            if "jest" in dependencies:
                return "jest"

        except (OSError, ValueError):
            return None

    return None


def _build_test_command(framework: str) -> list[str]:
    """Build the command used to execute the detected framework."""

    commands = {
        "pytest": ["python", "-m", "pytest"],
        "vitest": ["npx", "vitest", "run"],
        "jest": ["npx", "jest", "--runInBand"],
    }

    try:
        return commands[framework]
    except KeyError as exc:
        raise TestAnalysisError(
            f"Unsupported test framework: {framework}"
        ) from exc