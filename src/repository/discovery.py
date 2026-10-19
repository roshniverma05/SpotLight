from pathlib import Path

from src.models.repository import RepositoryWorkspace
from src.models.repository_profile import RepositoryProfile


# Files that should not be scanned as source files.
IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".idea",
    ".vscode",
    "dist",
    "build",
    "target",
}


LANGUAGE_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".hpp": "C++",
}


MANIFEST_FILES = {
    "requirements.txt": ("Python", "pip"),
    "pyproject.toml": ("Python", "pip"),
    "Pipfile": ("Python", "pipenv"),
    "package.json": ("JavaScript", "npm"),
    "yarn.lock": ("JavaScript", "yarn"),
    "pnpm-lock.yaml": ("JavaScript", "pnpm"),
    "pom.xml": ("Java", "maven"),
    "build.gradle": ("Java", "gradle"),
    "build.gradle.kts": ("Java", "gradle"),
    "go.mod": ("Go", "go"),
    "Cargo.toml": ("Rust", "cargo"),
}


FRAMEWORK_INDICATORS = {
    "fastapi": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "react": "React",
    "next": "Next.js",
    "express": "Express",
    "spring": "Spring",
    "pytest": "pytest",
    "jest": "Jest",
    "vitest": "Vitest",
}


BUILD_TOOL_FILES = {
    "vite.config.js": "Vite",
    "vite.config.ts": "Vite",
    "webpack.config.js": "Webpack",
    "webpack.config.ts": "Webpack",
    "Makefile": "Make",
    "Dockerfile": "Docker",
}


TEST_FRAMEWORK_INDICATORS = {
    "pytest": "pytest",
    "jest": "Jest",
    "vitest": "Vitest",
    "unittest": "unittest",
}


def _iter_repository_files(root: Path):
    """Yield repository files while skipping generated/dependency directories."""

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        relative_parts = path.relative_to(root).parts

        if any(
            part in IGNORED_DIRECTORIES
            for part in relative_parts
        ):
            continue

        yield path


def _detect_languages(files: list[Path]) -> set[str]:
    """Detect programming languages from source file extensions."""

    languages = set()

    for file_path in files:
        language = LANGUAGE_EXTENSIONS.get(file_path.suffix.lower())

        if language:
            languages.add(language)

    return languages


def _detect_manifest_information(
    root: Path,
    files: list[Path],
) -> tuple[set[str], set[str], set[str]]:
    """
    Detect languages, package managers and manifest files.
    """

    languages = set()
    package_managers = set()
    detected_files = set()

    for file_path in files:
        filename = file_path.name

        if filename not in MANIFEST_FILES:
            continue

        detected_files.add(
            str(file_path.relative_to(root))
        )

        language, package_manager = MANIFEST_FILES[filename]

        languages.add(language)
        package_managers.add(package_manager)

    return languages, package_managers, detected_files


def _read_small_text_file(file_path: Path) -> str:
    """
    Read a reasonably small text/configuration file safely.

    Large files are skipped because discovery should remain lightweight.
    """

    try:
        if file_path.stat().st_size > 2_000_000:
            return ""

        return file_path.read_text(
            encoding="utf-8",
            errors="ignore",
        ).lower()

    except (OSError, UnicodeError):
        return ""


def _detect_frameworks_and_tests(
    files: list[Path],
) -> tuple[set[str], set[str]]:
    """Detect frameworks and test frameworks from relevant files."""

    frameworks = set()
    test_frameworks = set()

    relevant_names = {
        "requirements.txt",
        "pyproject.toml",
        "package.json",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
    }

    for file_path in files:
        if file_path.name not in relevant_names:
            continue

        content = _read_small_text_file(file_path)

        if not content:
            continue

        for indicator, framework in FRAMEWORK_INDICATORS.items():
            if indicator in content:
                frameworks.add(framework)

        for indicator, test_framework in TEST_FRAMEWORK_INDICATORS.items():
            if indicator in content:
                test_frameworks.add(test_framework)

    return frameworks, test_frameworks


def _detect_build_tools(files: list[Path]) -> set[str]:
    """Detect build and infrastructure tools from known files."""

    build_tools = set()

    for file_path in files:
        tool = BUILD_TOOL_FILES.get(file_path.name)

        if tool:
            build_tools.add(tool)

    return build_tools


def discover_repository(
    workspace: RepositoryWorkspace,
) -> RepositoryProfile:
    """
    Identify the technology stack of an acquired repository.
    """

    root = Path(workspace.workspace_path)

    if not root.exists():
        raise FileNotFoundError(
            f"Repository workspace does not exist: {root}"
        )

    if not root.is_dir():
        raise NotADirectoryError(
            f"Repository workspace is not a directory: {root}"
        )

    files = list(_iter_repository_files(root))

    languages = _detect_languages(files)

    manifest_languages, package_managers, detected_files = (
        _detect_manifest_information(root, files)
    )

    languages.update(manifest_languages)

    frameworks, test_frameworks = _detect_frameworks_and_tests(
        files
    )

    build_tools = _detect_build_tools(files)

    for file_path in files:
        relative_path = str(
            file_path.relative_to(root)
        )

        if Path(relative_path).name in {
            "Dockerfile",
            "requirements.txt",
            "pyproject.toml",
            "package.json",
            "pom.xml",
            "build.gradle",
            "build.gradle.kts",
            "go.mod",
            "Cargo.toml",
        }:
            detected_files.add(relative_path)

    return RepositoryProfile(
        languages=sorted(languages),
        frameworks=sorted(frameworks),
        package_managers=sorted(package_managers),
        build_tools=sorted(build_tools),
        test_frameworks=sorted(test_frameworks),
        detected_files=sorted(detected_files),
    ) 
