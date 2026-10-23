"""Creating and listing orders through the UI."""

import re

import pytest
from playwright.sync_api import Page, expect

from tests.data.factories import order_payload, unique_suffix
from tests.ui.pages.orders_page import NewOrderPage, OrdersPage


@pytest.mark.smoke
def test_create_order_via_ui_appears_in_list(user_page: Page, new_order_page: NewOrderPage, orders_page: OrdersPage):
    customer = f"UI Customer {unique_suffix()}"
    new_order_page.open()
    new_order_page.submit(customer, "Pressure valve", 12)

    expect(user_page).to_have_url(re.compile(r"/orders\?created=ORD-\d{6}$"))
    expect(orders_page.flash).to_contain_text("created")
    row = orders_page.row_for(customer)
    expect(row).to_have_count(1)
    expect(row).to_contain_text("Pressure valve")
    expect(row).to_contain_text("12")
    expect(row).to_contain_text("new")
    expect(orders_page.count).to_have_text("1 order(s)")


@pytest.mark.regression
@pytest.mark.parametrize(
    ("customer", "item", "quantity", "message"),
    [
        ("", "Fan module", "3", "Customer"),
        ("Acme", "", "3", "Item"),
        ("Acme", "Fan module", "0", "Quantity"),
        ("Acme", "Fan module", "abc", "Quantity"),
        ("Acme", "Fan module", "5000", "Quantity"),
    ],
    ids=["no-customer", "no-item", "qty-zero", "qty-text", "qty-too-large"],
)
def test_validation_message_and_no_order_created(
    user_page: Page, new_order_page: NewOrderPage, orders_page: OrdersPage, customer, item, quantity, message
):
    new_order_page.open()
    new_order_page.submit(customer, item, quantity)

    expect(new_order_page.errors).to_be_visible()
    expect(new_order_page.errors).to_contain_text(message)
    expect(user_page).to_have_url(re.compile(r"/orders/new$"))
    orders_page.open()
    expect(orders_page.rows).to_have_count(0)


@pytest.mark.regression
def test_form_keeps_typed_values_after_validation_error(user_page: Page, new_order_page: NewOrderPage):
    new_order_page.open()
    new_order_page.submit("Keeper AG", "Fan module", 0)
    expect(user_page.get_by_label("Customer")).to_have_value("Keeper AG")
    expect(user_page.get_by_label("Item")).to_have_value("Fan module")


@pytest.mark.regression
def test_orders_created_through_api_show_up_in_ui(user_page: Page, api, orders_page: OrdersPage):
    """Hybrid test: arrange through the fast API, verify through the browser."""
    customers = [f"Hybrid {i} {unique_suffix()}" for i in range(3)]
    for name in customers:
        api.post("/api/orders", json=order_payload(customer=name)).raise_for_status()
    orders_page.open()
    expect(orders_page.rows).to_have_count(3)
    for name in customers:
        expect(orders_page.row_for(name)).to_have_count(1)


@pytest.mark.regression
def test_user_sees_only_own_orders(user_page: Page, orders_page: OrdersPage, admin_api):
    """Another user's order must never leak into this user's table."""
    from tests.data import seed

    other = seed.create_account(admin_api)
    with seed.login_client(str(admin_api.base_url), other) as client:
        client.post("/api/orders", json=order_payload(customer="Secret Corp")).raise_for_status()
    orders_page.open()
    expect(user_page.get_by_text("Secret Corp")).to_have_count(0)
