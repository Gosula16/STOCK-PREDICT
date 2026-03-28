"""
Agent pipeline: observe → features → predict → strategy → risk → (execution stub).

With GROWW_AUTH_TOKEN + GROWW_INSTRUMENTS_JSON, LTP is fetched from Groww (real feed).
Decision logic is still a placeholder until you plug a model or rule engine.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Literal

from app.brokers.groww import fetch_ltp_by_instruments, parse_instruments_json
from app.config import get_settings
from app.ml.hf_infer import infer_text_sentiment, sentiment_to_bias

logger = logging.getLogger(__name__)

Decision = Literal["BUY", "SELL", "HOLD"]


@dataclass
class SignalRow:
    symbol: str
    decision: Decision
    confidence: float
    rationale: str
    last_price: float | None = None
    hf_label: str | None = None
    hf_score: float | None = None


def _decision_from_symbol(sym: str) -> Decision:
    x = sum(ord(c) for c in sym) % 3
    return ("BUY", "SELL", "HOLD")[x]


def run_pipeline_tick() -> list[SignalRow]:
    settings = get_settings()
    demo_symbols = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK"]

    instruments: list[dict[str, str]] = []
    try:
        instruments = parse_instruments_json(settings.groww_instruments_json)
    except ValueError as e:
        logger.warning("Invalid GROWW_INSTRUMENTS_JSON: %s", e)
        instruments = []

    ltps: dict[str, float | None] = {}
    if settings.groww_auth_token and instruments:
        try:
            ltps = fetch_ltp_by_instruments(
                settings.groww_auth_token,
                instruments,
                settings.groww_ltp_wait_seconds,
            )
        except Exception:
            logger.exception("Groww LTP fetch failed")

    if instruments:
        symbols = [i.get("symbol") or i["exchange_token"] for i in instruments]
    else:
        symbols = demo_symbols

    rng = random.Random(42)
    out: list[SignalRow] = []
    for idx, sym in enumerate(symbols):
        ltp = ltps.get(sym)
        if ltp is not None:
            d = _decision_from_symbol(sym)
            conf = round(0.58 + (ltp % 7) * 0.01, 2)
            if conf > 0.92:
                conf = 0.92
            rationale = (
                f"Live LTP ₹{ltp:.2f} via Groww · {settings.universe} ({settings.broker_mode})"
            )
        elif instruments:
            d = "HOLD"
            conf = 0.5
            if settings.groww_auth_token:
                rationale = (
                    "Groww auth OK but no LTP yet — check exchange_token in "
                    "GROWW_INSTRUMENTS_JSON (see Groww instrument CSV)."
                )
            else:
                rationale = (
                    "Instruments configured — set GROWW_AUTH_TOKEN for live LTP from Groww."
                )
        else:
            roll = rng.random()
            if roll < 0.33:
                d = "BUY"
            elif roll < 0.66:
                d = "SELL"
            else:
                d = "HOLD"
            conf = round(0.55 + rng.random() * 0.35, 2)
            hint = ""
            if settings.groww_auth_token and not instruments:
                hint = " · set GROWW_INSTRUMENTS_JSON for live LTP"
            rationale = f"{settings.universe} demo signal ({settings.broker_mode}){hint}"

        hf_label: str | None = None
        hf_score: float | None = None
        tok = settings.huggingface_api_token
        if (
            tok
            and settings.hf_enable_in_pipeline
            and idx < settings.hf_max_symbols_per_tick
        ):
            snippet = (
                f"Short-term market view for Indian large-cap {sym}. "
                f"Reference price INR {ltp if ltp is not None else 'n/a'}."
            )
            hf_label, hf_score = infer_text_sentiment(
                tok, settings.hf_inference_model, snippet
            )
            if hf_label:
                bias = sentiment_to_bias(hf_label)
                conf = min(0.95, max(0.05, round(conf + bias, 3)))
                rationale = f"{rationale} · HF:{hf_label}"

        out.append(
            SignalRow(
                symbol=sym,
                decision=d,
                confidence=conf,
                rationale=rationale,
                last_price=ltp,
                hf_label=hf_label,
                hf_score=hf_score,
            )
        )
    return out
