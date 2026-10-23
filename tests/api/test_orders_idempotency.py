"""Idempotency-Key semantics: safe client retries must not duplicate orders."""

import pytest

from tests.data.factories import order_payload, unique_suffix


@pytest.mark.smoke
def test_retry_with_same_key_returns_original_order(api):
    key = f"key-{unique_suffix()}"
    payload = order_payload()
    first = api.post("/api/orders", json=payload, headers={"Idempotency-Key": key})
    second = api.post("/api/orders", json=payload, headers={"Idempotency-Key": key})
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json() == first.json()
    assert api.get("/api/orders").json()["total"] == 1


@pytest.mark.regression
def test_same_key_with_different_payload_conflicts(api):
    key = f"key-{unique_suffix()}"
    api.post("/api/orders", json=order_payload(quantity=1), headers={"Idempotency-Key": key})
    resp = api.post("/api/orders", json=order_payload(quantity=2), headers={"Idempotency-Key": key})
    assert resp.status_code == 409
    assert api.get("/api/orders").json()["total"] == 1


@pytest.mark.regression
def test_without_key_every_post_creates_an_order(api):
    payload = order_payload()
    ids = {api.post("/api/orders", json=payload).json()["id"] for _ in range(3)}
    assert len(ids) == 3


@pytest.mark.regression
def test_keys_are_scoped_per_user(api, live_server, admin_api):
    from tests.data import seed

    key = f"shared-{unique_suffix()}"
    mine = api.post("/api/orders", json=order_payload(), headers={"Idempotency-Key": key})
    with seed.login_client(live_server, seed.create_account(admin_api)) as other:
        theirs = other.post("/api/orders", json=order_payload(), headers={"Idempotency-Key": key})
    assert mine.status_code == theirs.status_code == 201
    assert mine.json()["id"] != theirs.json()["id"]


@pytest.mark.regression
def test_overlong_key_is_rejected(api):
    resp = api.post("/api/orders", json=order_payload(), headers={"Idempotency-Key": "k" * 65})
    assert resp.status_code == 422
