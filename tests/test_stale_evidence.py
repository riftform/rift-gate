# Copyright 2026 Riftform LLC
# SPDX-License-Identifier: Apache-2.0
import pytest

from rift_gate import ContractError, ToolCall, check, validate
from helpers import ACTOR, NOW, STATE, at


# --- stale and unknown-age evidence -------------------------------------------
def test_stale_evidence_is_stopped():
    call = ToolCall("refunds.propose", evidence=["O-1001", "T-501"], observed_at=at(12), amount_usd=120)
    d = check(ACTOR, call, STATE, NOW)
    assert d.decision == "stop"
    assert d.contract_ref == "actor/v1.1#evidence.max_age"


def test_fresh_evidence_passes_and_requires_verification():
    call = ToolCall("refunds.propose", evidence=["O-1001", "T-501"], observed_at=at(2), amount_usd=120)
    d = check(ACTOR, call, STATE, NOW)
    assert d.allowed and d.decision == "pass"
    assert d.needs_verification


@pytest.mark.parametrize("observed_at", [None, "", "yesterday", "2026-11-02T11:58:00"])  # last: no timezone
def test_unknown_age_evidence_is_held_not_passed(observed_at):
    call = ToolCall("refunds.propose", evidence=["O-1001"], observed_at=observed_at, amount_usd=120)
    d = check(ACTOR, call, STATE, NOW)
    assert d.decision == "hold"
    assert d.contract_ref == "actor/v1.1#evidence.max_age"


def test_fabricated_evidence_is_stopped():
    call = ToolCall("refunds.propose", evidence=["O-9999"], observed_at=at(1), amount_usd=120)
    d = check(ACTOR, call, STATE, NOW)
    assert d.decision == "stop"
    assert d.contract_ref == "actor/v1.1#evidence.must_resolve_in"


def test_missing_evidence_is_stopped():
    d = check(ACTOR, ToolCall("refunds.propose", observed_at=at(1), amount_usd=120), STATE, NOW)
    assert d.decision == "stop"
    assert d.contract_ref == "actor/v1.1#evidence.required_for"


