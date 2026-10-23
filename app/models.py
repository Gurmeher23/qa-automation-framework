"""ORM models."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, TypeDecorator, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

ORDER_STATUSES = ("new", "paid", "shipped", "cancelled")

# Allowed status transitions: the business rule the API tests exercise.
TRANSITIONS: dict[str, set[str]] = {
    "new": {"paid", "cancelled"},
    "paid": {"shipped", "cancelled"},
    "shipped": set(),
    "cancelled": set(),
}


def utcnow() -> datetime:
    """Timezone-aware current time."""
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator):
    """Always return timezone-aware UTC datetimes (SQLite drops tzinfo otherwise)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_result_value(self, value: datetime | None, dialect):  # noqa: ANN001, ANN201
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class User(Base):
    """An application user. ``role`` is either ``user`` or ``admin``."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(16), default="user")

    orders: Mapped[list[Order]] = relationship(back_populates="owner")


class Order(Base):
    """A customer order owned by a user."""

    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("owner_id", "idempotency_key", name="uq_owner_idem"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference: Mapped[str] = mapped_column(String(16), default="", index=True)
    customer: Mapped[str] = mapped_column(String(80))
    item: Mapped[str] = mapped_column(String(80))
    quantity: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="new", index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)

    owner: Mapped[User] = relationship(back_populates="orders")
