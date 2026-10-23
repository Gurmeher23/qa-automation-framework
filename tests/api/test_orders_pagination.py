"""Listing: pagination, ordering and filtering."""

import pytest

from tests.data.factories import order_payload


@pytest.fixture
def twelve_orders(api):
    """Twelve orders of the per-test user; returns ids oldest-first."""
    return [api.post("/api/orders", json=order_payload(customer=f"Page-{i}")).json()["id"] for i in range(12)]


@pytest.mark.smoke
def test_first_page_defaults(api, twelve_orders):
    body = api.get("/api/orders").json()
    assert (body["total"], body["page"], body["page_size"]) == (12, 1, 20)
    assert len(body["items"]) == 12


@pytest.mark.regression
def test_pages_partition_results_newest_first(api, twelve_orders):
    seen: list[int] = []
    for page, expected_len in [(1, 5), (2, 5), (3, 2)]:
        body = api.get("/api/orders", params={"page": page, "page_size": 5}).json()
        assert len(body["items"]) == expected_len
        assert body["total"] == 12
        seen += [o["id"] for o in body["items"]]
    assert seen == sorted(twelve_orders, reverse=True)
    assert len(set(seen)) == 12


@pytest.mark.regression
def test_page_beyond_end_is_empty_not_an_error(api, twelve_orders):
    body = api.get("/api/orders", params={"page": 99, "page_size": 5}).json()
    assert body["items"] == []
    assert body["total"] == 12


@pytest.mark.regression
@pytest.mark.parametrize(
    "params",
    [{"page": 0}, {"page": -1}, {"page_size": 0}, {"page_size": 101}, {"page": "x"}, {"status": "bogus"}],
    ids=["page-0", "page-negative", "size-0", "size-over-max", "page-nan", "bad-status"],
)
def test_invalid_pagination_params(api, params):
    assert api.get("/api/orders", params=params).status_code == 422


@pytest.mark.regression
def test_status_filter(api, twelve_orders):
    for oid in twelve_orders[:4]:
        api.patch(f"/api/orders/{oid}", json={"status": "paid"}).raise_for_status()
    paid = api.get("/api/orders", params={"status": "paid"}).json()
    assert paid["total"] == 4
    assert {o["status"] for o in paid["items"]} == {"paid"}
    assert api.get("/api/orders", params={"status": "shipped"}).json()["total"] == 0


@pytest.mark.regression
def test_admin_stats_reflect_orders(api, admin_api, twelve_orders):
    stats = admin_api.get("/api/admin/stats").json()
    assert stats.get("new", 0) >= 12
