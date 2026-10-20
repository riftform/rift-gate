# Copyright 2026 Riftform LLC
# SPDX-License-Identifier: Apache-2.0
"""Load and check boundary contracts.

A boundary contract is a small YAML document that says what one agent may do,
decide, read, write and delegate, what evidence an action needs, which actions
need independent verification, and when a person decides.
See spec/boundary-contract.md.
"""
from __future__ import annotations

import pathlib
import re
from typing import Any

import yaml

CONTRACT_ID = re.compile(r"^[a-z][a-z0-9_-]*/v\d+(\.\d+)?$")
_DURATION = re.compile(r"^\s*(\d+)\s*([smh])\s*$", re.IGNORECASE)


class ContractError(ValueError):
    """Raised when a contract is malformed."""


def load(path: str | pathlib.Path) -> dict[str, Any]:
    """Load one contract file and run basic structural checks."""
    data = yaml.safe_load(pathlib.Path(path).read_text(encoding="utf-8"))
    validate(data)
    return data


def validate(contract: Any) -> None:
    """Structural checks only. A contract that fails here must not be used."""
    if not isinstance(contract, dict):
        raise ContractError("contract must be a mapping")
    cid = contract.get("contract")
    if not isinstance(cid, str) or not CONTRACT_ID.match(cid):
        raise ContractError(f"contract id must look like 'name/v1' or 'name/v1.1', got {cid!r}")
    if not isinstance(contract.get("agent_id"), str):
        raise ContractError("agent_id is required")
    for section in ("capability", "authority"):
        if not isinstance(contract.get(section), dict):
            raise ContractError(f"'{section}' section is required")
    for key in ("tools",):
        if not isinstance(contract["capability"].get(key, []), list):
            raise ContractError("capability.tools must be a list")
    for key in ("decide", "never"):
        if not isinstance(contract["authority"].get(key, []), list):
            raise ContractError(f"authority.{key} must be a list")
    max_age = (contract.get("evidence") or {}).get("max_age")
    if max_age is not None:
        parse_duration_seconds(max_age)


def parse_duration_seconds(spec: Any) -> int:
    """Parse '30s', '5m', '2h' into seconds."""
    if not isinstance(spec, str):
        raise ContractError(f"duration must be a string like '5m', got {spec!r}")
    m = _DURATION.match(spec)
    if not m:
        raise ContractError(f"duration must look like '30s', '5m' or '2h', got {spec!r}")
    return int(m.group(1)) * {"s": 1, "m": 60, "h": 3600}[m.group(2).lower()]


def ref(contract: dict[str, Any], line: str) -> str:
    """The citation for one contract line, e.g. 'actor/v1.1#authority.never'."""
    return f"{contract['contract']}#{line}"
