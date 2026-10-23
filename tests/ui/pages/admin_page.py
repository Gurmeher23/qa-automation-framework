"""Admin overview with client-side filtering."""

from __future__ import annotations

from playwright.sync_api import Locator

from tests.ui.pages.base_page import BasePage


class AdminPage(BasePage):
    path = "/admin"

    @property
    def visible_rows(self) -> Locator:
        """Rows that are not hidden by the filter (Playwright treats ``hidden`` rows as invisible)."""
        return self.page.locator("[data-testid=admin-row]:visible")

    @property
    def forbidden(self) -> Locator:
        return self.page.get_by_test_id("forbidden")

    def search(self, text: str) -> None:
        self.page.get_by_label("Search customer or reference").fill(text)

    def filter_status(self, status: str) -> None:
        self.page.get_by_label("Status").select_option(status)
