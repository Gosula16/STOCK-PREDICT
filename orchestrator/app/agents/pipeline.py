"""
Agent pipeline: observe → features → predict → strategy → risk → (execution stub).

Replace stubs with real data feeds, trained models, and broker adapters for production.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Literal

from app.config import get_settings


Decision = Literal["BUY", "SELL", "HOLD"]


@dataclass
class SignalRow:
    symbol: str
    decision: Decision
    confidence: float
    rationale: str


def run_pipeline_tick() -> list[SignalRow]:
    """One orchestration cycle; deterministic enough for demos without external APIs."""
    settings = get_settings()
    # Demo symbols — wire to NIFTY50 constituents + live quotes in production.
    symbols = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK"]
    rng = random.Random(42)  # stable demo outputs
    out: list[SignalRow] = []
    for sym in symbols:
        roll = rng.random()
        if roll < 0.33:
            d: Decision = "BUY"
        elif roll < 0.66:
            d = "SELL"
        else:
            d = "HOLD"
        conf = round(0.55 + rng.random() * 0.35, 2)
        out.append(
            SignalRow(
                symbol=sym,
                decision=d,
                confidence=conf,
                rationale=f"{settings.universe} demo signal ({settings.broker_mode})",
            )
        )
    return out
