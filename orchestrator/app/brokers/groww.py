"""
Groww Trade API integration (growwapi SDK).

Auth: set GROWW_AUTH_TOKEN to the API auth token from Groww (JWT), not the app API_SECRET.
Instruments: GROWW_INSTRUMENTS_JSON — see .env.example.

Docs: https://www.groww.in/trade-api/docs/python-sdk
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


def _sdk():
    try:
        from growwapi import GrowwAPI, GrowwFeed

        return GrowwAPI, GrowwFeed
    except ImportError as e:
        logger.warning("growwapi not installed: %s", e)
        return None, None


def client_from_token(token: str) -> Any | None:
    GrowwAPI, _ = _sdk()
    if not GrowwAPI:
        return None
    return GrowwAPI(token)


def get_user_profile(token: str) -> dict[str, Any]:
    g = client_from_token(token)
    if not g:
        raise RuntimeError("growwapi is not installed")
    return g.get_user_profile()


def parse_instruments_json(raw: str) -> list[dict[str, str]]:
    if not raw or not raw.strip():
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"GROWW_INSTRUMENTS_JSON is not valid JSON: {e}") from e
    if not isinstance(data, list):
        raise ValueError("GROWW_INSTRUMENTS_JSON must be a JSON array")
    out: list[dict[str, str]] = []
    for row in data:
        if not isinstance(row, dict):
            continue
        ex = str(row.get("exchange", "NSE"))
        seg = str(row.get("segment", "CASH"))
        tok = str(row.get("exchange_token", "")).strip()
        if not tok:
            continue
        sym = str(row.get("symbol", tok)).strip()
        out.append(
            {
                "exchange": ex,
                "segment": seg,
                "exchange_token": tok,
                "symbol": sym,
            }
        )
    return out


def fetch_ltp_by_instruments(
    token: str,
    instruments: list[dict[str, str]],
    wait_seconds: float = 2.0,
) -> dict[str, float | None]:
    """Subscribe to LTP, wait, read once, unsubscribe. Returns symbol -> ltp."""
    GrowwAPI, GrowwFeed = _sdk()
    if not GrowwAPI or not GrowwFeed:
        raise RuntimeError("growwapi is not installed")
    if not instruments:
        return {}

    groww = GrowwAPI(token)
    try:
        feed = GrowwFeed(groww)
    except Exception as e:
        raise RuntimeError(
            "Groww feed auth failed (expired or invalid GROWW_AUTH_TOKEN?)"
        ) from e
    inst_core = [
        {
            "exchange": i["exchange"],
            "segment": i["segment"],
            "exchange_token": i["exchange_token"],
        }
        for i in instruments
    ]
    feed.subscribe_ltp(inst_core)
    time.sleep(max(0.5, wait_seconds))
    payload = feed.get_ltp()
    try:
        feed.unsubscribe_ltp(inst_core)
    except Exception as e:
        logger.debug("groww unsubscribe_ltp: %s", e)

    return _ltp_map_from_feed(payload, instruments)


def _ltp_map_from_feed(
    payload: Any,
    instruments: list[dict[str, str]],
) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for i in instruments:
        sym = i.get("symbol") or i["exchange_token"]
        out[sym] = None

    if payload is None:
        return out

    root = payload
    if isinstance(payload, dict) and "ltp" in payload:
        root = payload["ltp"]

    if not isinstance(root, dict):
        logger.warning("Unexpected Groww get_ltp() shape: %s", type(payload))
        return out

    for i in instruments:
        sym = i.get("symbol") or i["exchange_token"]
        ex, seg, tok = i["exchange"], i["segment"], str(i["exchange_token"])
        try:
            node = root[ex][seg][tok]
            if isinstance(node, dict) and "ltp" in node:
                out[sym] = float(node["ltp"])
        except (KeyError, TypeError, ValueError) as e:
            logger.debug("No LTP for %s: %s", sym, e)
    return out


def place_order(
    token: str,
    *,
    trading_symbol: str,
    quantity: int,
    order_type: str,
    transaction_type: str,
    product: str,
    price: float | None = None,
    trigger_price: float | None = None,
    order_reference_id: str | None = None,
) -> dict[str, Any]:
    g = client_from_token(token)
    if not g:
        raise RuntimeError("growwapi is not installed")

    ot = order_type.upper().replace("-", "_")
    tt = transaction_type.upper()
    prod = product.upper()

    def c(name: str) -> Any:
        return getattr(g, name)

    order_type_const = {
        "LIMIT": c("ORDER_TYPE_LIMIT"),
        "MARKET": c("ORDER_TYPE_MARKET"),
        "STOP_LOSS": c("ORDER_TYPE_STOP_LOSS"),
        "STOP_LOSS_MARKET": c("ORDER_TYPE_STOP_LOSS_MARKET"),
    }.get(ot)
    if order_type_const is None:
        raise ValueError(f"Unsupported order_type: {order_type}")

    tt_const = {"BUY": c("TRANSACTION_TYPE_BUY"), "SELL": c("TRANSACTION_TYPE_SELL")}.get(
        tt
    )
    if tt_const is None:
        raise ValueError(f"Unsupported transaction_type: {transaction_type}")

    product_map = {
        "CNC": c("PRODUCT_CNC"),
        "MIS": c("PRODUCT_MIS"),
        "NRML": c("PRODUCT_NRML"),
    }
    product_const = product_map.get(prod)
    if product_const is None:
        raise ValueError(f"Unsupported product: {product}")

    kwargs: dict[str, Any] = {
        "trading_symbol": trading_symbol,
        "quantity": int(quantity),
        "validity": c("VALIDITY_DAY"),
        "exchange": c("EXCHANGE_NSE"),
        "segment": c("SEGMENT_CASH"),
        "product": product_const,
        "order_type": order_type_const,
        "transaction_type": tt_const,
    }
    if price is not None:
        kwargs["price"] = float(price)
    if trigger_price is not None:
        kwargs["trigger_price"] = float(trigger_price)
    if order_reference_id:
        kwargs["order_reference_id"] = order_reference_id

    return g.place_order(**kwargs)


def resolve_segment(g: Any, segment_key: str) -> Any:
    k = segment_key.upper().strip()
    attr = {
        "CASH": "SEGMENT_CASH",
        "FNO": "SEGMENT_FNO",
        "COMMODITY": "SEGMENT_COMMODITY",
    }.get(k, "SEGMENT_CASH")
    return getattr(g, attr)


def resolve_order_type_const(g: Any, order_type: str) -> Any:
    ot = order_type.upper().replace("-", "_")
    def c(name: str) -> Any:
        return getattr(g, name)

    m = {
        "LIMIT": c("ORDER_TYPE_LIMIT"),
        "MARKET": c("ORDER_TYPE_MARKET"),
        "STOP_LOSS": c("ORDER_TYPE_STOP_LOSS"),
        "STOP_LOSS_MARKET": c("ORDER_TYPE_STOP_LOSS_MARKET"),
    }
    v = m.get(ot)
    if v is None:
        raise ValueError(f"Unsupported order_type: {order_type}")
    return v


def list_orders(
    token: str,
    *,
    page: int = 0,
    page_size: int = 25,
    segment: str | None = None,
) -> dict[str, Any]:
    g = client_from_token(token)
    if not g:
        raise RuntimeError("growwapi is not installed")
    seg = resolve_segment(g, segment) if segment else None
    return g.get_order_list(page=page, page_size=page_size, segment=seg)


def get_holdings(token: str) -> dict[str, Any]:
    g = client_from_token(token)
    if not g:
        raise RuntimeError("growwapi is not installed")
    return g.get_holdings_for_user()


def cancel_order_by_id(
    token: str,
    *,
    groww_order_id: str,
    segment: str,
) -> dict[str, Any]:
    g = client_from_token(token)
    if not g:
        raise RuntimeError("growwapi is not installed")
    return g.cancel_order(
        groww_order_id=groww_order_id,
        segment=resolve_segment(g, segment),
    )


def modify_order_by_id(
    token: str,
    *,
    groww_order_id: str,
    segment: str,
    quantity: int,
    order_type: str,
    price: float | None = None,
    trigger_price: float | None = None,
) -> dict[str, Any]:
    g = client_from_token(token)
    if not g:
        raise RuntimeError("growwapi is not installed")
    return g.modify_order(
        order_type=resolve_order_type_const(g, order_type),
        segment=resolve_segment(g, segment),
        groww_order_id=groww_order_id,
        quantity=int(quantity),
        price=price,
        trigger_price=trigger_price,
    )


def order_margin_preview(
    token: str,
    *,
    segment: str,
    orders: list[dict[str, Any]],
) -> dict[str, Any]:
    g = client_from_token(token)
    if not g:
        raise RuntimeError("growwapi is not installed")
    return g.get_order_margin_details(
        segment=resolve_segment(g, segment),
        orders=orders,
    )


def get_order_status(
    token: str,
    *,
    groww_order_id: str,
    segment: str,
) -> dict[str, Any]:
    g = client_from_token(token)
    if not g:
        raise RuntimeError("growwapi is not installed")
    return g.get_order_status(
        segment=resolve_segment(g, segment),
        groww_order_id=groww_order_id,
    )
