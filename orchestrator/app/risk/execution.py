"""Pre-trade risk checks (env-tunable). Not a substitute for broker or regulatory limits."""

from __future__ import annotations

import threading
from datetime import date
from typing import Any

from app.config import Settings


class OrderRateLimiter:
    """Simple in-process daily counter (resets per local calendar date)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._day: date | None = None
        self._count = 0

    def assert_can_place(self, max_per_day: int) -> None:
        if max_per_day <= 0:
            return
        today = date.today()
        with self._lock:
            if self._day != today:
                self._day = today
                self._count = 0
            if self._count >= max_per_day:
                raise ValueError(
                    f"Daily order cap reached ({max_per_day}). Resets at next local day."
                )

    def record_placed(self) -> None:
        with self._lock:
            self._count += 1


_limiter = OrderRateLimiter()


def record_order_placed() -> None:
    _limiter.record_placed()


def broker_mutations_allowed(settings: Settings) -> bool:
    return settings.groww_allow_broker_mutations or settings.groww_allow_place_order


def validate_order_request(settings: Settings, body: dict[str, Any]) -> None:
    """Raise ValueError if the order fails static risk rules."""
    qty = int(body.get("quantity", 0))
    if qty <= 0:
        raise ValueError("quantity must be positive")
    if qty > settings.risk_max_order_quantity:
        raise ValueError(
            f"quantity {qty} exceeds RISK_MAX_ORDER_QUANTITY={settings.risk_max_order_quantity}"
        )

    ot = str(body.get("order_type", "LIMIT")).upper()
    if settings.risk_require_limit_price and ot == "MARKET":
        raise ValueError(
            "MARKET orders blocked: set RISK_REQUIRE_LIMIT_PRICE=false to allow (dangerous)."
        )

    if ot == "LIMIT":
        if body.get("price") in (None, ""):
            raise ValueError("LIMIT orders require price")

    price = body.get("price")
    if price is not None and settings.risk_max_notional_per_order > 0:
        try:
            notional = float(price) * qty
        except (TypeError, ValueError) as e:
            raise ValueError("Invalid price for notional check") from e
        if notional > settings.risk_max_notional_per_order:
            raise ValueError(
                f"Order notional ₹{notional:.2f} exceeds RISK_MAX_NOTIONAL_PER_ORDER="
                f"{settings.risk_max_notional_per_order}"
            )

    _limiter.assert_can_place(settings.risk_max_orders_per_day)
