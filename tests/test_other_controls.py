# Copyright 2026 Riftform LLC
# SPDX-License-Identifier: Apache-2.0
import pytest

from rift_gate import ContractError, ToolCall, check, validate
from helpers import ACTOR, NOW, STATE, at


# --- delegation and escalation -------------------------------------------------
def test_delegating_more_than_own_authority_is_stopped():
    d = check(ACTOR, ToolCall("tasks.delegate", {"grant": ["refunds.propose", "payments.authorize"]}), STATE, NOW)
    assert d.decision == "stop"
    assert d.contract_ref == "actor/v1.1#delegation.may_grant"


def test_delegating_a_subset_passes():
    d = check(ACTOR, ToolCall("tasks.delegate", {"grant": ["refunds.propose"]}), STATE, NOW)
    assert d.allowed


def test_large_refund_goes_to_a_person():
    call = ToolCall("refunds.propose", evidence=["O-1001"], observed_at=at(1), amount_usd=7500)
    d = check(ACTOR, call, STATE, NOW)
    assert d.decision == "hold"
    assert d.contract_ref == "actor/v1.1#escalation.human_above"


# --- fail closed ---------------------------------------------------------------
def test_gate_error_holds_instead_of_passing():
    broken = dict(ACTOR, evidence={"required_for": ["refunds.propose"], "max_age": "five minutes"})
    call = ToolCall("refunds.propose", evidence=["O-1001"], observed_at=at(1), amount_usd=120)
    d = check(broken, call, STATE, NOW)
    assert not d.allowed and d.decision == "hold"


def test_malformed_contract_is_rejected_at_load():
    with pytest.raises(ContractError):
        validate({"contract": "actor", "agent_id": "actor", "capability": {}, "authority": {}})
