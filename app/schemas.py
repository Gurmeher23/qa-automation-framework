"""Pydantic request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Status = Literal["new", "paid", "shipped", "cancelled"]


class LoginIn(BaseModel):
    username: str
    password: str


class UserIn(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)
    role: Literal["user", "admin"] = "user"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    role: str


class OrderIn(BaseModel):
    customer: str = Field(min_length=1, max_length=80)
    item: str = Field(min_length=1, max_length=80)
    quantity: int = Field(ge=1, le=1000)

    @field_validator("customer", "item")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class OrderPatch(BaseModel):
    """Partial update; only ``status`` and ``quantity`` are mutable."""

    status: Status | None = None
    quantity: int | None = Field(default=None, ge=1, le=1000)


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    reference: str
    customer: str
    item: str
    quantity: int
    status: str
    owner_id: int
    created_at: datetime


class OrderPage(BaseModel):
    items: list[OrderOut]
    total: int
    page: int
    page_size: int
