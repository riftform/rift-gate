# Copyright 2026 Riftform LLC
# SPDX-License-Identifier: Apache-2.0
"""Run four synthetic tool calls through the gate and write one trace per call.

Everything here is synthetic: invented orders, tickets and timestamps. No model
is called. The traces in examples/traces/ were produced by this script.

    python examples/demo.py            # prints decisions, rewrites examples/traces/
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib

from rift_gate import ToolCall, check, load

HERE = pathlib.Path(__file__).resolve().parent
ACTOR = load(HERE / "contracts" / "refund-actor.contract.yaml")
NOW = dt.datetime(2026, 11, 2, 12, 0, tzinfo=dt.timezone.utc)
STATE = {
    "orders": {"O-1001": {"amount_usd": 120.0, "status": "delivered"}},
    "tickets": {"T-501": {"order": "O-1001", "reason": "arrived damaged"}},
    "policy": {"P-refund-30d": {"window_days": 30}},
}

CASES = {
    "forbidden-tool": ToolCall("payments.authorize", {"order": "O-1001", "amount_usd": 120}),
    "stale-evidence": ToolCall("refunds.propose", {"order": "O-1001"}, ["O-1001", "T-501"],
                               (NOW - dt.timedelta(minutes=12)).isoformat(), 120.0),
    "unknown-age-evidence": ToolCall("refunds.propose", {"order": "O-1001"}, ["O-1001", "T-501"], None, 120.0),
    "allowed-needs-verifier": ToolCall("refunds.propose", {"order": "O-1001"}, ["O-1001", "T-501"],
                                       (NOW - dt.timedelta(minutes=2)).isoformat(), 120.0),
}


def trace(name: str, call: ToolCall) -> list[dict]:
    run_id = f"synthetic-{name}"
    d = check(ACTOR, call, STATE, NOW)
    ts = NOW.isoformat().replace("+00:00", "Z")
    events = [{"ts": ts, "run_id": run_id, "seq": 0, "agent": "actor", "event": "action_submitted",
               "gate": None, "decision": None, "contract_ref": None,
               "detail": {"action": call.tool, "args": call.args, "evidence": call.evidence,
                          "observed_at": call.observed_at}, "latency_ms": 0}]
    for r in d.results:
        if r.decision == "not_invoked":
            continue
        events.append({"ts": ts, "run_id": run_id, "seq": len(events), "agent": "harness",
                       "event": "gate_check", "gate": r.gate, "decision": r.decision,
                       "contract_ref": r.contract_ref, "detail": r.detail, "latency_ms": 0})
    if d.allowed and d.needs_verification:
        events.append({"ts": ts, "run_id": run_id, "seq": len(events), "agent": "harness",
                       "event": "hold", "gate": "verification", "decision": "hold",
                       "contract_ref": "actor/v1.1#verification.required_for",
                       "detail": {"reason": "waiting for an independent verifier; not executed yet"},
                       "latency_ms": 0})
    return events


if __name__ == "__main__":
    out = HERE / "traces"
    out.mkdir(exist_ok=True)
    for name, call in CASES.items():
        events = trace(name, call)
        (out / f"{name}.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
        last = events[-1]
        print(f"{name:24s} {last['decision'] or '-':5s} {last['contract_ref']}")
