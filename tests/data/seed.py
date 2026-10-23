"""Seeding through the public API.

Seeding via HTTP (not by writing to the database) means the same code works
against a local server, the Docker stage environment, or any shared stage,
and it exercises the admin endpoints as a side effect.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

import httpx

from tests.data.factories import order_payload, unique_suffix, user_payload


@dataclass(frozen=True)
class Account:
    """Credentials of a provisioned user."""

    username: str
    password: str
    role: str


@dataclass
class SeededData:
    """What ``seed_baseline`` created, so tests can assert on exact values."""

    token: str
    user: Account
    customers: dict[str, list[str]] = field(default_factory=dict)  # status -> customer names

    @property
    def customer_names(self) -> list[str]:
        return [name for names in self.customers.values() for name in names]


def admin_client(base_url: str, username: str, password: str) -> httpx.Client:
    """An httpx client already logged in as admin."""
    client = httpx.Client(base_url=base_url, timeout=15)
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    resp.raise_for_status()
    return client


def create_account(admin: httpx.Client, role: str = "user", prefix: str = "qa") -> Account:
    """Provision a fresh, uniquely named account through the admin API."""
    body = user_payload(prefix=prefix, role=role)
    admin.post("/api/admin/users", json=body).raise_for_status()
    return Account(body["username"], body["password"], role)


@contextmanager
def login_client(base_url: str, account: Account) -> Iterator[httpx.Client]:
    """Context manager yielding an httpx client logged in as ``account``."""
    with httpx.Client(base_url=base_url, timeout=15) as client:
        client.post(
            "/api/auth/login", json={"username": account.username, "password": account.password}
        ).raise_for_status()
        yield client


def seed_baseline(base_url: str, admin: httpx.Client) -> SeededData:
    """Create one user with orders in the new/paid/shipped states.

    Customer names carry a unique token so the admin-filter UI test can assert
    exact counts even if other tests keep adding rows concurrently.
    """
    token = unique_suffix()
    account = create_account(admin, prefix="seed")
    data = SeededData(token=token, user=account)
    with login_client(base_url, account) as client:
        for status, steps in {"new": [], "paid": ["paid"], "shipped": ["paid", "shipped"]}.items():
            customer = f"Seeded-{token}-{status}"
            order = client.post("/api/orders", json=order_payload(customer=customer)).json()
            for step in steps:
                client.patch(f"/api/orders/{order['id']}", json={"status": step}).raise_for_status()
            data.customers.setdefault(status, []).append(customer)
    return data
