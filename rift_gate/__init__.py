# Copyright 2026 Riftform LLC
# SPDX-License-Identifier: Apache-2.0
"""rift-gate: check an AI agent's tool call against a written boundary contract before it runs."""
from .contracts import ContractError, load, validate
from .gate import Decision, GateResult, ToolCall, check, needs_verification

__all__ = ["ContractError", "Decision", "GateResult", "ToolCall", "check", "load",
           "needs_verification", "validate"]
__version__ = "0.1.0"
