"""Shared page-object behaviour."""

from __future__ import annotations

from playwright.sync_api import Locator, Page


class BasePage:
    """Wraps a Playwright ``Page``; subclasses expose user-level actions, not selectors."""

    path = "/"

    def __init__(self, page: Page) -> None:
        self.page = page

    def open(self) -> None:
        """Navigate to this page (relative to the configured base URL)."""
        self.page.goto(self.path)

    @property
    def current_user(self) -> Locator:
        return self.page.get_by_test_id("current-user")

    def nav(self, name: str) -> None:
        """Click a header link by test id suffix: orders, new, admin."""
        self.page.get_by_test_id(f"nav-{name}").click()

    def logout(self) -> None:
        self.page.get_by_role("button", name="Log out").click()
