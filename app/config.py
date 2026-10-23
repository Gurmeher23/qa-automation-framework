"""Runtime configuration, read from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    """Application settings.

    The defaults are for local development and tests only. Stage and
    production deployments must override them through environment variables.
    """

    database_url: str = field(default_factory=lambda: _env("DATABASE_URL", "sqlite:///./orderdesk.db"))
    secret_key: str = field(default_factory=lambda: _env("SECRET_KEY", "dev-only-secret-change-me"))
    admin_username: str = field(default_factory=lambda: _env("ADMIN_USERNAME", "admin"))
    admin_password: str = field(default_factory=lambda: _env("ADMIN_PASSWORD", "admin-dev-password"))
    https_only_cookies: bool = field(default_factory=lambda: _env("HTTPS_ONLY_COOKIES", "0") == "1")
