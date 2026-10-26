# rift-gate

**Written limits for AI agents, checked before a tool runs.**

rift-gate is a minimal reference implementation of a pre-execution gate for tool-using AI agents. Each agent gets a short, machine-readable **boundary contract**: what it may do, what it may hand to others, what evidence an action needs, and when a person decides. rift-gate checks every proposed tool call against that contract **before the tool executes**, and every stop or hold names the contract line responsible.

## The problem

Rules about what an agent may do often live in prompts or application logic rather than in an independently enforceable boundary. A hidden instruction on a web page, or a confused model, can talk an agent past them, and the owner finds out afterwards from a log, if at all. rift-gate puts the rules in a contract that is checked outside the model.

## What exists in v0.1

| Included | Where |
|---|---|
| Boundary-contract format v0 (prose and JSON Schema) | [`spec/boundary-contract.md`](spec/boundary-contract.md), [`spec/boundary-contract.schema.json`](spec/boundary-contract.schema.json) |
| Trace-event schema | [`spec/trace_event.schema.json`](spec/trace_event.schema.json) |
| Minimal enforcement gate with fail-closed defaults | [`rift_gate/gate.py`](rift_gate/gate.py), [`rift_gate/contracts.py`](rift_gate/contracts.py) |
| Two worked contracts: a refund actor and its independent verifier | [`examples/contracts/`](examples/contracts/) |
| A demo that writes four synthetic traces | [`examples/demo.py`](examples/demo.py), [`examples/traces/`](examples/traces/) |
| 15 unit tests | [`tests/`](tests/) |
| Architecture notes and diagram | [`docs/architecture.md`](docs/architecture.md) |

## Install

Requires Python 3.10 or newer. From a clone of this repository:

```
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[test]"
```

## Run the demo

```
python examples/demo.py
```

Expected output (the demo uses a fixed clock, so it is the same every time):

```
forbidden-tool           stop  actor/v1.1#authority.never
stale-evidence           stop  actor/v1.1#evidence.max_age
unknown-age-evidence     hold  actor/v1.1#evidence.max_age
allowed-needs-verifier   hold  actor/v1.1#verification.required_for
```

It rewrites `examples/traces/*.jsonl`; `git diff` should show no change.

## Run the tests

```
python -m pytest
```

15 tests: forbidden tool, tool outside capability, stale evidence, unknown-age evidence (four variants), fabricated and missing evidence, delegation overreach and subset, human escalation threshold, gate error, malformed contract.

## What a boundary contract looks like

An excerpt of [`examples/contracts/refund-actor.contract.yaml`](examples/contracts/refund-actor.contract.yaml):

```yaml
contract: actor/v1.1
capability:
  tools: [orders.read, refunds.propose, tasks.delegate]
authority:
  decide: [refunds.propose]
  never: [payments.authorize, customer.modify]
delegation:
  may_grant: subset_of_own
evidence:
  required_for: [refunds.propose]
  must_resolve_in: shared_state
  max_age: 5m
verification:
  required_for: [refunds.propose]
escalation:
  human_above: { refund_usd: 5000 }
  on_unresolved: hold
```

## What happens before a tool executes

```python
from rift_gate import ToolCall, check, load

contract = load("examples/contracts/refund-actor.contract.yaml")
state = {"orders": {"O-1001": {"amount_usd": 120.0}}}

d = check(contract, ToolCall("payments.authorize", {"order": "O-1001"}), state)
d.allowed        # False
d.decision       # "stop"
d.contract_ref   # "actor/v1.1#authority.never"
```

| Check | Contract lines | Result |
|---|---|---|
| Tool not allowed, or explicitly forbidden | `capability.tools`, `authority.never` | stop |
| Delegating more authority than the agent has | `delegation.may_grant` | stop |
| Missing or unknown evidence IDs | `evidence.required_for`, `evidence.must_resolve_in` | stop |
| Amount above a human threshold | `escalation.human_above` | hold |
| Action needs an independent verifier | `verification.required_for` | allowed, with `needs_verification = True` |
| Any error inside the gate | `escalation.on_unresolved` | hold |

Your code calls the tool only when `d.allowed` is true and any required verification has confirmed. rift-gate does not run tools or verifiers itself.

## Stale or unknown evidence

Evidence age is the current time minus `observed_at`, the time the agent read the cited state. Older than `evidence.max_age`: **stop**. If `observed_at` is missing, unparseable or has no timezone, the age cannot be measured, and the gate **holds** rather than passing. Unmeasurable age is treated as not fresh.

## Not implemented yet

- A verifier. rift-gate only reports that one is needed.
- Tool-protocol adapters (for example MCP).
- Enforcement of the `state` and `fallback` sections, and of verifier independence.
- Escalation thresholds other than `refund_usd`.
- Signed contracts, or protection against a harness that misreports `observed_at`.

See [spec/boundary-contract.md](spec/boundary-contract.md#known-gaps-in-v0).

## What was tested, and what was not

There are two different kinds of evidence here. Do not read one as the other.

**This repository (public, 0.1).** The 15 unit tests above pass against the included cases. They show that the code does what this README says on those inputs. They do not establish general effectiveness against real agents.

**Riftform's research prototype (private).** The gate logic here is extracted from a larger, private research prototype: one actor agent and one independent verifier on a toy refund desk, seven failure scenarios, 76 citable runs. 35 used scripted agents and 41 used two locally hosted open models from different developers (Qwen 2.5 7B acting, Llama 3 8B verifying), with predictions written down before every run. With the real models, a forbidden payment call was blocked before execution in 4 of 4 runs and stale evidence was stopped in 4 of 4. Ten unplanned findings were each attributed to the responsible component.

Limits of that prototype evidence:

- No comparison baselines were run, so it does not show this approach beats any alternative.
- One actor and one verifier, in a toy refund domain.
- Repeated runs used a fixed temperature and seed: they are reproducibility checks, not independent samples.
- Three planned claims were not reached with real models.
- The prototype found a fail-open in its own freshness check: evidence of unknown age passed. The fix (hold on unknown age, as in this package) has so far been verified only by unit tests.
- This package is not the whole experimental system. The prototype's run records, model outputs and ledgers are not published here.

## What is planned next

Proposed work, not yet funded or built: contract format v1 with examples beyond the refund desk; a hardened enforcement library 1.0; an adapter for MCP tool calls; reproducible attack tests anyone can run; and a release write-up.

## Differences from the research prototype

- The prototype's deliberately weakened test variants are not included; only the full-control logic is.
- Evidence IDs resolve against any top-level collection in the state you pass in, not a fixed list.
- Malformed durations are rejected when a contract loads, and errors inside the gate hold rather than raise.
- Timestamps without a timezone count as unknown age.

## Contributing and security

See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## License

Apache-2.0. See [LICENSE](LICENSE). Copyright 2026 Riftform LLC.

## Technical notes

- [Technical Note 001: Fail closed when you can't tell how old the evidence is](docs/technical-notes/001-evidence-freshness-fail-closed.md)
