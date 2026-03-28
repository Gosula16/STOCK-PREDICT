"""Structured audit log for broker actions (stdout + optional file). Never log secrets."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_audit = logging.getLogger("rentai.audit")
_audit.setLevel(logging.INFO)
_audit.propagate = False

_initialized = False


def setup_audit_logging(log_dir: str = "logs") -> None:
    global _initialized
    if _initialized:
        return
    _initialized = True

    fmt = logging.Formatter("%(message)s")
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    _audit.addHandler(sh)

    try:
        p = Path(log_dir)
        p.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(p / "audit.jsonl", encoding="utf-8")
        fh.setFormatter(fmt)
        _audit.addHandler(fh)
    except OSError:
        _audit.warning(
            json.dumps(
                {
                    "ts": datetime.now(UTC).isoformat(),
                    "event": "audit_file_skip",
                    "reason": "could_not_create_logs_dir",
                }
            )
        )


def audit_event(event: str, **fields: Any) -> None:
    payload = {
        "ts": datetime.now(UTC).isoformat(),
        "event": event,
        **fields,
    }
    _audit.info(json.dumps(payload, default=str))
