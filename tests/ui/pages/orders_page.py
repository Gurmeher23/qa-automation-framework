"""Orders list and new-order form."""

from __future__ import annotations

from playwright.sync_api import Locator

from tests.ui.pages.base_page import BasePage


class OrdersPage(BasePage):
    path = "/orders"

    @property
    def rows(self) -> Locator:
        return self.page.get_by_test_id("order-row")

    @property
    def flash(self) -> Locator:
        return self.page.get_by_test_id("flash")

    @property
    def count(self) -> Locator:
        return self.page.get_by_test_id("order-count")

    def row_for(self, customer: str) -> Locator:
        return self.rows.filter(has_text=customer)


class NewOrderPage(BasePage):
    path = "/orders/new"

    @property
    def errors(self) -> Locator:
        return self.page.get_by_test_id("form-error")

    def submit(self, customer: str, item: str, quantity: str | int) -> None:
        """Fill and submit the form (values are strings, as typed by a user)."""
        self.page.get_by_label("Customer").fill(customer)
        self.page.get_by_label("Item").fill(item)
        self.page.get_by_label("Quantity").fill(str(quantity))
        self.page.get_by_role("button", name="Create order").click()
