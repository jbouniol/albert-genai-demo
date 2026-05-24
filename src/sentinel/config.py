"""Project-wide constants. Models per agent + thresholds."""
from __future__ import annotations

MODELS: dict[str, str] = {
    "collector": "gpt-4o-mini",
    "analyzer": "gpt-4o",
    "scorer": "gpt-4o",
    "communicator": "gpt-4o-mini",
}

THRESHOLDS: dict[str, float] = {
    "watch": 0.30,
    "monitor": 0.50,
    "alert": 0.65,
    "high_alert": 0.80,
}

HITL_TRIGGER: float = THRESHOLDS["alert"]
