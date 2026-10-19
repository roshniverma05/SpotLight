from pathlib import Path

import lizard

from src.analysis.models import Finding
from src.models.repository import RepositoryWorkspace


COMPLEXITY_THRESHOLD = 15
FUNCTION_LENGTH_THRESHOLD = 100
PARAMETER_THRESHOLD = 6

SUPPORTED_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".go",
    ".rs",
    ".c",
    ".h",
    ".cpp",
    ".cc",
    ".cxx",
}

IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    ".idea",
    ".vscode",
    "dist",
    "build",
    "target",
    ".next",
    "coverage",
}


def run_code_quality_analysis(
    workspace: RepositoryWorkspace,
) -> list[Finding]:
    """Analyze supported source files for maintainability issues."""

    workspace_path = workspace.workspace_path

    if not workspace_path.is_dir():
        raise ValueError(
            f"Repository workspace does not exist: {workspace_path}"
        )

    findings: list[Finding] = []

    for source_file in _iter_source_files(workspace_path):
        try:
            file_info = lizard.analyze_file(str(source_file))
        except (OSError, UnicodeDecodeError, IndexError, RecursionError):
            continue

        for function in file_info.function_list:
            relative_path = source_file.relative_to(
                workspace_path
            ).as_posix()

            if function.cyclomatic_complexity > COMPLEXITY_THRESHOLD:
                findings.append(
                    _complexity_finding(
                        relative_path,
                        function,
                    )
                )

            if function.nloc > FUNCTION_LENGTH_THRESHOLD:
                findings.append(
                    _length_finding(
                        relative_path,
                        function,
                    )
                )

            if function.parameter_count > PARAMETER_THRESHOLD:
                findings.append(
                    _parameter_finding(
                        relative_path,
                        function,
                    )
                )

    return findings


def _iter_source_files(workspace_path: Path):
    """Yield supported source files while skipping generated/vendor folders."""

    for path in workspace_path.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        if any(
            part.lower() in IGNORED_DIRECTORIES
            for part in path.parts
        ):
            continue

        yield path


def _complexity_finding(file_path: str, function) -> Finding:
    return Finding(
        category="code_quality",
        severity="medium",
        title="High cyclomatic complexity",
        description=(
            f"Function '{function.name}' has cyclomatic complexity "
            f"{function.cyclomatic_complexity}, exceeding the threshold "
            f"of {COMPLEXITY_THRESHOLD}."
        ),
        file_path=file_path,
        line_start=function.start_line,
        line_end=function.start_line + function.nloc - 1,
        rule_id="high-cyclomatic-complexity",
        analyzer="lizard",
        evidence=(
            f"Function: {function.name}\n"
            f"Complexity: {function.cyclomatic_complexity}\n"
            f"Threshold: {COMPLEXITY_THRESHOLD}"
        ),
    )


def _length_finding(file_path: str, function) -> Finding:
    return Finding(
        category="code_quality",
        severity="medium",
        title="Long function",
        description=(
            f"Function '{function.name}' contains {function.nloc} "
            f"non-comment lines, exceeding the threshold of "
            f"{FUNCTION_LENGTH_THRESHOLD}."
        ),
        file_path=file_path,
        line_start=function.start_line,
        line_end=function.start_line + function.nloc - 1,
        rule_id="long-function",
        analyzer="lizard",
        evidence=(
            f"Function: {function.name}\n"
            f"NLOC: {function.nloc}\n"
            f"Threshold: {FUNCTION_LENGTH_THRESHOLD}"
        ),
    )


def _parameter_finding(file_path: str, function) -> Finding:
    return Finding(
        category="code_quality",
        severity="low",
        title="Too many function parameters",
        description=(
            f"Function '{function.name}' has "
            f"{function.parameter_count} parameters, exceeding the "
            f"threshold of {PARAMETER_THRESHOLD}."
        ),
        file_path=file_path,
        line_start=function.start_line,
        line_end=function.start_line + function.nloc - 1,
        rule_id="too-many-parameters",
        analyzer="lizard",
        evidence=(
            f"Function: {function.name}\n"
            f"Parameters: {function.parameter_count}\n"
            f"Threshold: {PARAMETER_THRESHOLD}"
        ),
    )