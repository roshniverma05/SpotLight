from pathlib import Path
import re

from src.issues.schemas import IssueInput, IssueLocalization
from src.models.repository import RepositoryWorkspace


MAX_RELEVANT_FILES = 5
MAX_RELEVANT_SYMBOLS = 10
MIN_FILE_SCORE = 8

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


def localize_issue(
    issue: IssueInput,
    workspace: RepositoryWorkspace,
) -> IssueLocalization:
    """
    Locate the strongest repository candidates for a supplied issue.

    Candidate ranking considers:
    - filename relevance
    - directory/path relevance
    - symbol relevance
    - content relevance

    Only candidates above the minimum confidence threshold are returned.
    """

    workspace_path = workspace.workspace_path

    if not workspace_path.is_dir():
        raise ValueError(
            f"Repository workspace does not exist: {workspace_path}"
        )

    issue_text = f"{issue.title} {issue.description}"
    keywords = _extract_keywords(issue_text)

    if not keywords:
        return IssueLocalization(issue=issue)

    candidates: list[tuple[int, Path, list[str]]] = []

    for source_file in _iter_source_files(workspace_path):
        try:
            content = source_file.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except OSError:
            continue

        symbols = _extract_symbols(content)

        score = _calculate_file_score(
            source_file=source_file,
            workspace_path=workspace_path,
            content=content,
            symbols=symbols,
            keywords=keywords,
        )

        if score < MIN_FILE_SCORE:
            continue

        matching_symbols = _rank_symbols(
            symbols=symbols,
            keywords=keywords,
        )

        candidates.append(
            (
                score,
                source_file,
                matching_symbols,
            )
        )

    candidates.sort(
        key=lambda item: (
            -item[0],
            str(item[1]).lower(),
        )
    )

    selected = candidates[:MAX_RELEVANT_FILES]

    relevant_files = [
        path.relative_to(workspace_path).as_posix()
        for _, path, _ in selected
    ]

    relevant_symbols: list[str] = []

    for _, _, symbols in selected:
        relevant_symbols.extend(symbols)

    relevant_symbols = _unique(relevant_symbols)[
        :MAX_RELEVANT_SYMBOLS
    ]

    return IssueLocalization(
        issue=issue,
        relevant_files=relevant_files,
        relevant_symbols=relevant_symbols,
    )


def _calculate_file_score(
    source_file: Path,
    workspace_path: Path,
    content: str,
    symbols: list[str],
    keywords: list[str],
) -> int:
    """Score a file according to its relevance to the issue."""

    score = 0

    filename = source_file.stem.lower()

    relative_path = source_file.relative_to(
        workspace_path
    ).as_posix().lower()

    path_parts = re.split(
        r"[/\\._-]+",
        relative_path,
    )

    content_lower = content.lower()

    for keyword in keywords:
        keyword_lower = keyword.lower()

        # Strongest signal: exact filename match.
        if keyword_lower == filename:
            score += 20
        elif keyword_lower in filename:
            score += 12

        # Directory/path match.
        if keyword_lower in path_parts:
            score += 6

        # Symbol match.
        for symbol in symbols:
            symbol_lower = symbol.lower()

            if keyword_lower == symbol_lower:
                score += 15
            elif keyword_lower in symbol_lower:
                score += 8

        # Content match.
        occurrences = len(
            re.findall(
                rf"\b{re.escape(keyword_lower)}\b",
                content_lower,
            )
        )

        # Content alone cannot dominate the score.
        score += min(occurrences, 3)

    return score


def _extract_keywords(text: str) -> list[str]:
    """Extract meaningful technical terms from issue text."""

    normalized = text.lower()

    normalized = re.sub(
        r"[/_.:-]+",
        " ",
        normalized,
    )

    words = re.findall(
        r"[a-zA-Z][a-zA-Z0-9]{2,}",
        normalized,
    )

    stop_words = {
        "the",
        "and",
        "for",
        "with",
        "this",
        "that",
        "from",
        "when",
        "then",
        "have",
        "has",
        "does",
        "not",
        "was",
        "were",
        "are",
        "is",
        "can",
        "could",
        "should",
        "would",
        "will",
        "into",
        "user",
        "users",
        "issue",
        "error",
        "problem",
        "please",
        "unable",
        "working",
        "works",
        "function",
        "application",
        "system",
        "valid",
        "enter",
        "entered",
        "credentials",
    }

    return _unique(
        word
        for word in words
        if word not in stop_words
    )


def _extract_symbols(content: str) -> list[str]:
    """Extract common functions, classes and JavaScript components."""

    patterns = [
        r"^\s*(?:async\s+)?def\s+"
        r"([A-Za-z_][A-Za-z0-9_]*)",

        r"^\s*class\s+"
        r"([A-Za-z_][A-Za-z0-9_]*)",

        r"^\s*(?:export\s+)?"
        r"(?:default\s+)?function\s+"
        r"([A-Za-z_][A-Za-z0-9_]*)",

        r"^\s*(?:export\s+)?const\s+"
        r"([A-Za-z_][A-Za-z0-9_]*)\s*=",
    ]

    symbols: list[str] = []

    for pattern in patterns:
        symbols.extend(
            re.findall(
                pattern,
                content,
                re.MULTILINE,
            )
        )

    return _unique(symbols)


def _rank_symbols(
    symbols: list[str],
    keywords: list[str],
) -> list[str]:
    """Rank symbols according to issue relevance."""

    ranked: list[tuple[int, str]] = []

    for symbol in symbols:
        symbol_lower = symbol.lower()
        score = 0

        for keyword in keywords:
            keyword_lower = keyword.lower()

            if keyword_lower == symbol_lower:
                score += 15
            elif keyword_lower in symbol_lower:
                score += 8

        if score > 0:
            ranked.append(
                (score, symbol)
            )

    ranked.sort(
        key=lambda item: (
            -item[0],
            item[1].lower(),
        )
    )

    return [
        symbol
        for _, symbol in ranked
    ]


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


def _unique(values) -> list[str]:
    """Return unique values while preserving order."""

    return list(dict.fromkeys(values))