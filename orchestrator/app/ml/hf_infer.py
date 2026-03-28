"""Optional Hugging Face Inference API (sentiment / FinBERT-style). Token from env only."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def _best_label(payload: Any) -> tuple[str | None, float | None]:
    """Normalize HF classification payloads (FinBERT, etc.)."""
    if payload is None:
        return None, None
    rows = payload
    if isinstance(payload, list) and payload and isinstance(payload[0], list):
        rows = payload[0]
    if not isinstance(rows, list) or not rows:
        return None, None
    best: tuple[str | None, float | None] = (None, None)
    for item in rows:
        if not isinstance(item, dict):
            continue
        label = item.get("label")
        score = item.get("score")
        if label is None or score is None:
            continue
        try:
            s = float(score)
        except (TypeError, ValueError):
            continue
        if best[1] is None or s > best[1]:
            best = (str(label), s)
    return best


def infer_text_sentiment(token: str, model: str, text: str) -> tuple[str | None, float | None]:
    """POST to HF Inference API. Returns (label, score) or (None, None) on failure."""
    if not text.strip():
        return None, None
    url = f"https://api-inference.huggingface.co/models/{model}"
    try:
        with httpx.Client(timeout=45.0) as client:
            r = client.post(
                url,
                json={"inputs": text[:2000]},
                headers={"Authorization": f"Bearer {token}"},
            )
        if r.status_code != 200:
            logger.warning(
                "HF inference HTTP %s for model %s: %s",
                r.status_code,
                model,
                (r.text or "")[:300],
            )
            return None, None
        return _best_label(r.json())
    except Exception:
        logger.exception("HF inference request failed")
        return None, None


def sentiment_to_bias(label: str | None) -> float:
    """Map FinBERT-style labels to a small confidence nudge."""
    if not label:
        return 0.0
    u = label.lower()
    if "positive" in u:
        return 0.06
    if "negative" in u:
        return -0.06
    return 0.0
