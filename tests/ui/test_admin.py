"""Admin overview: access control and table filtering."""

import pytest
from playwright.sync_api import Page, expect

from tests.ui.pages.admin_page import AdminPage


@pytest.mark.smoke
def test_admin_sees_seeded_orders(admin_session_page: Page, admin_page: AdminPage, seeded):
    admin_page.open()
    admin_page.search(seeded.token)
    expect(admin_page.visible_rows).to_have_count(3)


@pytest.mark.regression
def test_text_filter_narrows_table(admin_session_page: Page, admin_page: AdminPage, seeded):
    admin_page.open()
    admin_page.search(f"Seeded-{seeded.token}-paid")
    expect(admin_page.visible_rows).to_have_count(1)
    expect(admin_page.visible_rows.first).to_contain_text("paid")
    expect(admin_session_page.get_by_test_id("visible-count")).to_have_text("1 order(s) shown")


@pytest.mark.regression
@pytest.mark.parametrize("status", ["new", "paid", "shipped"])
def test_status_filter_combines_with_text(admin_session_page: Page, admin_page: AdminPage, seeded, status):
    admin_page.open()
    admin_page.search(seeded.token)
    admin_page.filter_status(status)
    expect(admin_page.visible_rows).to_have_count(1)
    expect(admin_page.visible_rows.first).to_contain_text(f"Seeded-{seeded.token}-{status}")


@pytest.mark.regression
def test_filter_without_matches_shows_no_rows_and_reset_restores(
    admin_session_page: Page, admin_page: AdminPage, seeded
):
    admin_page.open()
    admin_page.search("zzz-no-such-customer")
    expect(admin_page.visible_rows).to_have_count(0)
    admin_page.search(seeded.token)
    expect(admin_page.visible_rows).to_have_count(3)


@pytest.mark.smoke
def test_regular_user_gets_403_on_admin_page(user_page: Page, admin_page: AdminPage):
    response = user_page.goto("/admin")
    assert response is not None and response.status == 403
    expect(admin_page.forbidden).to_be_visible()
    expect(user_page.get_by_test_id("nav-admin")).to_have_count(0)


@pytest.mark.regression
def test_admin_nav_link_is_visible_for_admin_only(admin_session_page: Page, admin_page: AdminPage):
    admin_page.open()
    expect(admin_session_page.get_by_test_id("nav-admin")).to_be_visible()
