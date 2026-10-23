"""Login page."""

from __future__ import annotations

from playwright.sync_api import Locator

from tests.ui.pages.base_page import BasePage


class LoginPage(BasePage):
    path = "/login"

    @property
    def error(self) -> Locator:
        return self.page.get_by_test_id("login-error")

    def login(self, username: str, password: str) -> None:
        """Fill the form and submit."""
        self.page.get_by_label("Username").fill(username)
        self.page.get_by_label("Password").fill(password)
        self.page.get_by_role("button", name="Sign in").click()
