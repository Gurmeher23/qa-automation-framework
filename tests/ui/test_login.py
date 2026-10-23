"""Login / logout through the browser."""

import re

import pytest
from playwright.sync_api import Page, expect

from tests.ui.pages.login_page import LoginPage
from tests.ui.pages.orders_page import OrdersPage


@pytest.mark.smoke
def test_login_with_valid_credentials(login_page: LoginPage, orders_page: OrdersPage, page: Page, account):
    login_page.open()
    login_page.login(account.username, account.password)
    expect(page).to_have_url(re.compile(r"/orders$"))
    expect(orders_page.current_user).to_have_text(account.username)
    expect(orders_page.count).to_have_text("0 order(s)")


@pytest.mark.regression
@pytest.mark.parametrize("password", ["wrong-password", ""], ids=["wrong", "empty"])
def test_login_with_bad_password_shows_error(login_page: LoginPage, page: Page, account, password):
    login_page.open()
    login_page.login(account.username, password)
    expect(login_page.error).to_have_text("Invalid username or password")
    expect(page).to_have_url(re.compile(r"/login$"))


@pytest.mark.smoke
def test_anonymous_user_is_redirected_to_login(page: Page):
    page.goto("/orders")
    expect(page).to_have_url(re.compile(r"/login$"))


@pytest.mark.regression
def test_logout_returns_to_login_and_blocks_pages(login_page: LoginPage, orders_page: OrdersPage, page: Page, account):
    login_page.open()
    login_page.login(account.username, account.password)
    orders_page.logout()
    expect(page).to_have_url(re.compile(r"/login$"))
    page.goto("/orders")
    expect(page).to_have_url(re.compile(r"/login$"))


@pytest.mark.regression
def test_session_survives_reload(user_page: Page, orders_page: OrdersPage, account):
    orders_page.open()
    user_page.reload()
    expect(orders_page.current_user).to_have_text(account.username)
