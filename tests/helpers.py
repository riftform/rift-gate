# Copyright 2026 Riftform LLC
# SPDX-License-Identifier: Apache-2.0
"""Shared fixtures: the worked-example actor contract and a small synthetic shared state."""
import datetime as dt
import pathlib

from rift_gate import load

ROOT = pathlib.Path(__file__).resolve().parent.parent
ACTOR = load(ROOT / "examples/contracts/refund-actor.contract.yaml")
NOW = dt.datetime(2026, 11, 2, 12, 0, tzinfo=dt.timezone.utc)
STATE = {
    "orders": {"O-1001": {"amount_usd": 120.0, "status": "delivered"}},
    "tickets": {"T-501": {"order": "O-1001", "reason": "damaged"}},
    "policy": {"P-refund-30d": {"window_days": 30}},
}


def at(minutes_ago: int) -> str:
    return (NOW - dt.timedelta(minutes=minutes_ago)).isoformat()
