"""UI fixtures: page objects and fast, API-based login."""

from __future__ import annotations

from urllib.parse import urlparse

import pytest
from playwright.sync_api import BrowserContext, Page

from tests.data import seed
from tests.ui.pages.admin_page import AdminPage
from tests.ui.pages.login_page import LoginPage
from tests.ui.pages.orders_page import NewOrderPage, OrdersPage


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict, base_url: str) -> dict:
    """Default viewport and base URL for every context."""
    return {**browser_context_args, "base_url": base_url, "viewport": {"width": 1280, "height": 800}}


@pytest.fixture
def login_page(page: Page) -> LoginPage:
    return LoginPage(page)


@pytest.fixture
def orders_page(page: Page) -> OrdersPage:
    return OrdersPage(page)


@pytest.fixture
def new_order_page(page: Page) -> NewOrderPage:
    return NewOrderPage(page)


@pytest.fixture
def admin_page(page: Page) -> AdminPage:
    return AdminPage(page)


def _session_cookie(base_url: str, username: str, password: str) -> dict:
    """Log in through the API and translate the cookie for the browser context."""
    with seed.login_client(base_url, seed.Account(username, password, "")) as client:
        value = client.cookies.get("orderdesk_session")
    return {"name": "orderdesk_session", "value": value, "url": base_url}


def login_context(context: BrowserContext, base_url: str, username: str, password: str) -> None:
    """Skip the login form: inject a session cookie (the login UI has its own tests)."""
    assert urlparse(base_url).scheme in {"http", "https"}
    context.add_cookies([_session_cookie(base_url, username, password)])


@pytest.fixture
def user_page(page: Page, context: BrowserContext, base_url: str, account: seed.Account) -> Page:
    """A page already logged in as a fresh regular user."""
    login_context(context, base_url, account.username, account.password)
    return page


@pytest.fixture
def admin_session_page(page: Page, context: BrowserContext, base_url: str, admin_credentials: tuple[str, str]) -> Page:
    """A page already logged in as admin."""
    login_context(context, base_url, *admin_credentials)
    return page
