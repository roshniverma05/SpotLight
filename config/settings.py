import os
from pathlib import Path

from cryptography.fernet import Fernet
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _required_setting(name: str) -> str:
    """Read a required environment variable without accepting placeholders."""
    value = os.getenv(name, "").strip()

    if not value:
        raise RuntimeError(
            f"Missing required configuration: {name}. "
            "Set it in the project-root .env file."
        )

    normalized = value.lower()
    if any(
        marker in normalized
        for marker in ("your_", "change_me", "replace_me", "<", ">")
    ):
        raise RuntimeError(
            f"Configuration {name} still contains a placeholder. "
            "Set a real value in the project-root .env file."
        )

    return value


class Settings:
    """Application configuration loaded from environment variables."""

    def __init__(self) -> None:
        self.APP_NAME = os.getenv(
            "APP_NAME",
            "Autonomous DevSecOps",
        ).strip()

        self.ENVIRONMENT = os.getenv(
            "ENVIRONMENT",
            "development",
        ).strip().lower()

        self.LOG_LEVEL = os.getenv(
            "LOG_LEVEL",
            "INFO",
        ).strip().upper()

        self.DATABASE_URL = _required_setting("DATABASE_URL")

        self.JWT_SECRET_KEY = _required_setting("JWT_SECRET_KEY")
        if len(self.JWT_SECRET_KEY) < 32:
            raise RuntimeError(
                "JWT_SECRET_KEY must contain at least 32 characters. "
                "Generate a strong random secret."
            )

        self.JWT_ALGORITHM = os.getenv(
            "JWT_ALGORITHM",
            "HS256",
        ).strip()

        if self.JWT_ALGORITHM != "HS256":
            raise RuntimeError(
                "This configuration currently supports HS256 only. "
                "Use JWT_ALGORITHM=HS256 unless the authentication "
                "implementation is deliberately changed and reviewed."
            )

        try:
            self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(
                os.getenv(
                    "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
                    "30",
                )
            )
        except ValueError:
            raise RuntimeError(
                "JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be an integer."
            ) from None

        if self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES <= 0:
            raise RuntimeError(
                "JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be positive."
            )

        self.GITHUB_CLIENT_ID = _required_setting("GITHUB_CLIENT_ID")
        self.GITHUB_CLIENT_SECRET = _required_setting(
            "GITHUB_CLIENT_SECRET"
        )
        self.GITHUB_REDIRECT_URI = _required_setting(
            "GITHUB_REDIRECT_URI"
        )

        self.GITHUB_TOKEN_ENCRYPTION_KEY = _required_setting(
            "GITHUB_TOKEN_ENCRYPTION_KEY"
        )

        try:
            Fernet(
                self.GITHUB_TOKEN_ENCRYPTION_KEY.encode("utf-8")
            )
        except (ValueError, TypeError):
            raise RuntimeError(
                "GITHUB_TOKEN_ENCRYPTION_KEY is invalid. "
                "Generate a valid Fernet key."
            ) from None

        workspace_setting = os.getenv(
            "WORKSPACE_DIR",
            "workspace",
        ).strip()

        workspace_path = Path(workspace_setting)
        if not workspace_path.is_absolute():
            workspace_path = BASE_DIR / workspace_path

        self.WORKSPACE_DIR = workspace_path.resolve()


settings = Settings()
