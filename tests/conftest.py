"""Shared fixtures: live server, API clients, provisioned accounts, seeded data.

The app under test is started once per pytest process (so once per xdist
worker, each with its own SQLite file). Set ``BASE_URL`` to run the same suite
against an already running environment such as ``make stage-up``; in that case
``ADMIN_USERNAME`` / ``ADMIN_PASSWORD`` must match that deployment.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

from tests.data import seed
from tests.server import LiveServer

_ADMIN_DEFAULT = ("admin", "admin-test-password")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Tag tests with api/ui/unit by directory so the folder layout is the single source of truth."""
    for item in items:
        parts = Path(str(item.fspath)).parts
        for area in ("api", "ui", "unit"):
            if "tests" in parts and area in parts[parts.index("tests") + 1 : -1]:
                item.add_marker(getattr(pytest.mark, area))


@pytest.fixture(scope="session")
def admin_credentials() -> tuple[str, str]:
    if os.environ.get("BASE_URL"):
        return os.environ.get("ADMIN_USERNAME", "admin"), os.environ["ADMIN_PASSWORD"]
    return _ADMIN_DEFAULT


@pytest.fixture(scope="session")
def live_server(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    """Base URL of the app under test (local thread, or ``BASE_URL`` if set)."""
    external = os.environ.get("BASE_URL")
    if external:
        yield external.rstrip("/")
        return
    server = LiveServer(tmp_path_factory.mktemp("db") / "orderdesk.db").start()
    yield server.url
    server.stop()


@pytest.fixture(scope="session")
def base_url(live_server: str) -> str:
    """Overrides pytest-base-url so Playwright's ``page.goto('/x')`` hits our server."""
    return live_server


@pytest.fixture(scope="session")
def admin_api(live_server: str, admin_credentials: tuple[str, str]) -> Iterator[httpx.Client]:
    """httpx client logged in as admin (session scoped; used to provision data)."""
    client = seed.admin_client(live_server, *admin_credentials)
    yield client
    client.close()


@pytest.fixture
def anon_api(live_server: str) -> Iterator[httpx.Client]:
    """Unauthenticated client."""
    with httpx.Client(base_url=live_server, timeout=15) as client:
        yield client


@pytest.fixture
def account(admin_api: httpx.Client) -> seed.Account:
    """A fresh regular user per test: tests never share mutable state."""
    return seed.create_account(admin_api)


@pytest.fixture
def api(live_server: str, account: seed.Account) -> Iterator[httpx.Client]:
    """Client logged in as the per-test regular user."""
    with seed.login_client(live_server, account) as client:
        yield client


@pytest.fixture(scope="session")
def seeded(live_server: str, admin_api: httpx.Client) -> seed.SeededData:
    """Baseline dataset (orders in several states), created once per session."""
    return seed.seed_baseline(live_server, admin_api)
