import os
from pathlib import Path

from dotenv import load_dotenv


# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env
load_dotenv(BASE_DIR / ".env")


class Settings:
    """
    Central configuration for the Autonomous DevSecOps application.
    """

    APP_NAME: str = os.getenv(
        "APP_NAME",
        "Autonomous DevSecOps"
    )

    ENVIRONMENT: str = os.getenv(
        "ENVIRONMENT",
        "development"
    )

    LOG_LEVEL: str = os.getenv(
        "LOG_LEVEL",
        "INFO"
    )

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        ""
    )

    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY",
        ""
    )

    JWT_ALGORITHM: str = os.getenv(
        "JWT_ALGORITHM",
        "HS256"
    )

    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv(
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
            "30"
        )
    )

    GITHUB_CLIENT_ID: str = os.getenv(
        "GITHUB_CLIENT_ID",
        ""
    )

    GITHUB_CLIENT_SECRET: str = os.getenv(
        "GITHUB_CLIENT_SECRET",
        ""
    )

    GITHUB_REDIRECT_URI: str = os.getenv(
        "GITHUB_REDIRECT_URI",
        ""
    )

    GITHUB_TOKEN_ENCRYPTION_KEY: str = os.getenv(
        "GITHUB_TOKEN_ENCRYPTION_KEY",
        ""
    )

    WORKSPACE_DIR: Path = BASE_DIR / os.getenv(
        "WORKSPACE_DIR",
        "workspace"
    )


settings = Settings()