# Copyright 2026 Riftform LLC
# SPDX-License-Identifier: Apache-2.0
import pytest

from rift_gate import ContractError, ToolCall, check, validate
from helpers import ACTOR, NOW, STATE, at


# --- forbidden ----------------------------------------------------------
def test_forbidden_tool_is_stopped_before_execution():
    d = check(ACTOR, ToolCall("payments.authorize", {"order": "O-1001", "amount_usd": 120}), STATE, NOW)
    assert not d.allowed
    assert d.decision == "stop"
    assert d.contract_ref == "actor/v1.1#authority.never"


def test_tool_outside_capability_is_stopped():
    d = check(ACTOR, ToolCall("orders.delete"), STATE, NOW)
    assert d.decision == "stop"
    assert d.contract_ref == "actor/v1.1#capability.tools"


