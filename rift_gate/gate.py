# Copyright 2026 Riftform LLC
# SPDX-License-Identifier: Apache-2.0
"""Pre-execution gate: check one proposed tool call against a boundary contract.

The gate runs BEFORE the tool executes. Each check returns a GateResult that
names the contract line responsible, so every stop or hold can be attributed.

Checks, in order:
  boundary    the tool is in capability.tools, not in authority.never, and any
              delegation grants only a subset of the agent's own authority.decide
  evidence    for actions in evidence.required_for: every cited ID exists in
              shared state, and the evidence is no older than evidence.max_age.
              Evidence whose age cannot be measured is HELD, not passed.
  escalation  amounts above escalation.human_above go to a person (hold)

Separately, needs_verification() says whether an independent verifier must
confirm the action before it executes. This package does not run the verifier.

Extracted from the gate logic of Riftform's RIFT research prototype (harness
v1.1). Differences from the prototype are listed in README.md.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any

from .contracts import parse_duration_seconds, ref

PASS, STOP, HOLD, NOT_INVOKED = "pass", "stop", "hold", "not_invoked"


@dataclass(frozen=True)
class GateResult:
    gate: str                       # boundary | evidence | escalation
    decision: str                   # pass | stop | hold | not_invoked
    contract_ref: str | None        # e.g. "actor/v1.1#authority.never"
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolCall:
    tool: str
    args: dict[str, Any] = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)   # IDs the agent cites
    observed_at: str | None = None   # ISO-8601 time the agent read the cited state
    amount_usd: float | None = None  # for escalation thresholds


@dataclass(frozen=True)
class Decision:
    allowed: bool                   # True only if every check passed or did not apply
    decision: str                   # pass | stop | hold
    contract_ref: str | None        # the line responsible for a stop or hold
    results: tuple[GateResult, ...]
    needs_verification: bool


# ---------- helpers ----------------------------------------------------------
def _parse_time(raw: Any) -> dt.datetime | None:
    if not isinstance(raw, str):
        return None
    try:
        t = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else None   # naive times are not measurable


def _max_age_seconds(contract: dict) -> int | None:
    spec = (contract.get("evidence") or {}).get("max_age")
    return None if spec is None else parse_duration_seconds(spec)


def _resolves(evidence_id: str, state: dict) -> bool:
    return any(isinstance(coll, dict) and evidence_id in coll for coll in state.values())


# ---------- checks -----------------------------------------------------------
def boundary(contract: dict, call: ToolCall) -> GateResult:
    authority = contract.get("authority") or {}
    tools = (contract.get("capability") or {}).get("tools") or []
    if call.tool in (authority.get("never") or []):
        return GateResult("boundary", STOP, ref(contract, "authority.never"),
                          {"tool": call.tool, "reason": "listed in authority.never"})
    if call.tool not in tools:
        return GateResult("boundary", STOP, ref(contract, "capability.tools"),
                          {"tool": call.tool, "reason": "not in capability.tools"})
    if call.tool == "tasks.delegate":
        own = set(authority.get("decide") or [])
        grant = set(call.args.get("grant") or [])
        overreach = sorted(grant - own)
        if overreach:
            return GateResult("boundary", STOP, ref(contract, "delegation.may_grant"),
                              {"tool": call.tool, "grant": sorted(grant),
                               "own_authority_decide": sorted(own), "overreach": overreach,
                               "reason": "grant not a subset of delegator's own authority"})
    return GateResult("boundary", PASS, ref(contract, "capability.tools"), {"tool": call.tool})


def evidence(contract: dict, call: ToolCall, state: dict, now: dt.datetime | None = None) -> GateResult:
    ev = contract.get("evidence") or {}
    if call.tool not in (ev.get("required_for") or []):
        return GateResult("evidence", NOT_INVOKED, None)
    if not call.evidence:
        return GateResult("evidence", STOP, ref(contract, "evidence.required_for"),
                          {"reason": "action requires cited evidence; none given"})
    unresolved = [e for e in call.evidence if not _resolves(e, state)]
    if unresolved:
        return GateResult("evidence", STOP, ref(contract, "evidence.must_resolve_in"),
                          {"unresolved": unresolved})
    max_age = _max_age_seconds(contract)
    if max_age is not None:
        observed = _parse_time(call.observed_at)
        if observed is None:
            return GateResult("evidence", HOLD, ref(contract, "evidence.max_age"),
                              {"observed_at": call.observed_at, "max_age_seconds": max_age,
                               "reason": "evidence age unknown; unmeasurable age is not fresh"})
        now = now or dt.datetime.now(dt.timezone.utc)
        age = (now - observed).total_seconds()
        if age > max_age:
            return GateResult("evidence", STOP, ref(contract, "evidence.max_age"),
                              {"observed_at": call.observed_at, "age_seconds": int(age),
                               "max_age_seconds": max_age, "reason": "evidence is stale"})
    return GateResult("evidence", PASS, ref(contract, "evidence.required_for"),
                      {"resolved": list(call.evidence), "observed_at": call.observed_at})


def escalation(contract: dict, call: ToolCall) -> GateResult:
    thresholds = (contract.get("escalation") or {}).get("human_above") or {}
    threshold = thresholds.get("refund_usd")
    if call.tool != "refunds.propose" or threshold is None or call.amount_usd is None:
        return GateResult("escalation", NOT_INVOKED, None)
    if call.amount_usd > threshold:
        return GateResult("escalation", HOLD, ref(contract, "escalation.human_above"),
                          {"amount_usd": call.amount_usd, "threshold_usd": threshold})
    return GateResult("escalation", PASS, ref(contract, "escalation.human_above"),
                      {"amount_usd": call.amount_usd, "threshold_usd": threshold})


def needs_verification(contract: dict, tool: str) -> bool:
    return tool in ((contract.get("verification") or {}).get("required_for") or [])


# ---------- the gate ---------------------------------------------------------
def check(contract: dict, call: ToolCall, state: dict, now: dt.datetime | None = None) -> Decision:
    """Run every check in order and stop at the first stop or hold.

    Fails closed: any exception inside a check is returned as a hold that cites
    escalation.on_unresolved rather than letting the call through.
    """
    results: list[GateResult] = []
    try:
        for step in (lambda: boundary(contract, call),
                     lambda: evidence(contract, call, state, now),
                     lambda: escalation(contract, call)):
            r = step()
            results.append(r)
            if r.decision in (STOP, HOLD):
                return Decision(False, r.decision, r.contract_ref, tuple(results),
                                needs_verification(contract, call.tool))
    except Exception as exc:  # noqa: BLE001  (fail closed by design)
        r = GateResult("boundary", HOLD, ref(contract, "escalation.on_unresolved"),
                       {"reason": f"gate error: {type(exc).__name__}"})
        results.append(r)
        return Decision(False, HOLD, r.contract_ref, tuple(results), True)
    return Decision(True, PASS, None, tuple(results), needs_verification(contract, call.tool))
