# Technical Note 001: Fail closed when you can't tell how old the evidence is

*Riftform · Version 1.0 · 25 October 2026 · Applies to rift-gate 0.1 (release v0.1.0, commit `6d9fae7`)*

## Abstract

Tool-using agents often act on state they read earlier. A pre-execution gate can refuse an action whose supporting evidence is too old, but only if it can measure the evidence's age. This note describes how rift-gate 0.1 treats evidence whose age **cannot** be measured: it holds the call rather than passing it. That rule exists because our own earlier prototype got it wrong: its freshness check let evidence of unknown age through. We describe the failure, the correction, and what the correction does and does not establish.

## 1. The problem

An agent reads an order, a ticket or a balance, reasons for a while, then proposes an action that depends on what it read. If the underlying state changed in the meantime, the action can be wrong even when the agent's reasoning was sound.

rift-gate expresses a freshness limit as one line in an agent's boundary contract. From the example refund-actor contract in this repository:

```yaml
evidence:
  required_for: [refunds.propose]
  must_resolve_in: shared_state
  max_age: 5m
```

Evidence age is the current time minus `observed_at`, the time the agent read the cited state. The gate checks this **before the tool executes**.

## 2. Three cases, not two

It is tempting to treat freshness as a yes/no question: younger than `max_age` passes, older stops. There is a third case.

| Evidence | Decision | Cites |
|---|---|---|
| Age known and within `max_age` | Continues to the next check | n/a |
| Age known and greater than `max_age` | **stop** ("evidence is stale") | `evidence.max_age` |
| Age **unknown**: `observed_at` missing, empty, unparseable, or a timestamp without a timezone | **hold** ("evidence age unknown; unmeasurable age is not fresh") | `evidence.max_age` |

A timestamp without a timezone is treated as unknown because it can be read as more than one moment, and so as more than one age.

The repository demo shows the third case directly:

```
unknown-age-evidence     hold  actor/v1.1#evidence.max_age
```

## 3. Why hold, and not pass or stop

**Not pass.** If unknown age passes, then the easiest way to get past a freshness limit is to omit the timestamp, whether through a bug in the harness, a malformed tool result or a confused model. A limit that disappears when its input is missing is not a limit.

**Not stop.** Unknown age is not proof that the evidence is stale; often it is a plumbing problem. A *hold* means the call does not execute until something resolves it: fresh evidence, a verifier, or a person. That keeps the action from running without silently discarding a possibly legitimate request.

This follows the contract format's first design rule: **fail closed**. Malformed input, unknown evidence age and errors inside the gate all hold. Every hold names the contract line responsible, so the cause can be attributed afterwards.

## 4. The failure we observed

rift-gate's gate logic was extracted from a larger, private research prototype: one actor agent and one independent verifier on a toy refund desk. In the research prototype, evidence whose age could not be established was allowed to pass the freshness check. That was a fail-open. rift-gate 0.1 changes the behavior: if `observed_at` is missing, unparseable, or lacks a timezone, the evidence is treated as having unknown age and the action is held rather than passed.

## 5. The correction in rift-gate 0.1

In rift-gate 0.1 the evidence check, after confirming the cited evidence exists in shared state, does this:

1. If the contract sets `evidence.max_age`, parse `observed_at`.
2. If it cannot be parsed into a timezone-aware time, return **hold**, citing `evidence.max_age`.
3. Otherwise compute the age; if it exceeds `max_age`, return **stop**, citing `evidence.max_age`.

The repository's tests cover the stale case (stop), the fresh case (allowed, with verification still required by the contract), and four unknown-age variants: missing, empty, unparseable, and no timezone (all hold).

## 6. What this does and does not establish

- **Verified only by unit tests.** The correction is checked by the unit tests in this repository. It has not been re-run against real models.
- **The harness can lie.** `observed_at` is asserted by the agent or harness. A harness that reports a false time defeats this check; the gate cannot detect it. Signed or independently stamped observation times are not part of 0.1.
- **Toy domain.** The prototype had one actor and one verifier on a refund desk. There were no comparison baselines, and repeated runs were reproducibility checks, not independent samples.
- **Not a safety guarantee.** This is one fail-closed rule in a minimal reference implementation, not production software.

## 7. Try it

From a clone of this repository (Python 3.10+):

```
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[test]"
python examples/demo.py
python -m pytest
```

Look for the `unknown-age-evidence  hold` line in the demo output and `test_unknown_age_evidence_is_held_not_passed` in the tests.

---

Riftform LLC — applied intelligence research and systems. https://riftform.com/ · Code: Apache-2.0.

## Source map (every claim → public material in this repository)

| Claim | Source |
|---|---|
| Contract excerpt (`required_for`, `must_resolve_in`, `max_age: 5m`) | `README.md` §"What a boundary contract looks like"; `examples/contracts/refund-actor.contract.yaml` |
| Age = now − `observed_at`; checked before the tool executes | `README.md` §"Stale or unknown evidence"; `spec/boundary-contract.md` (evidence `max_age` row) |
| Stale → stop "evidence is stale"; unknown → hold "evidence age unknown; unmeasurable age is not fresh"; both cite `evidence.max_age` | `rift_gate/gate.py`, evidence check (lines ~112–124) |
| Missing, unparseable or no-timezone `observed_at` = unknown age | `README.md` §"Stale or unknown evidence"; `tests/test_stale_evidence.py` (parametrized: `None`, `""`, `"yesterday"`, no-timezone timestamp) |
| Demo line `unknown-age-evidence hold actor/v1.1#evidence.max_age` | `README.md` §"Run the demo" |
| Fail closed: malformed input, unknown age and gate errors hold; cite the line | `spec/boundary-contract.md` §"Design rules" 1–2 |
| Prototype: one actor, one verifier, toy refund desk; unplanned findings attributed | `README.md` §"What was tested, and what was not" |
| Prototype's freshness check let evidence of unknown age pass (a fail-open); 0.1 holds instead; fix verified only by unit tests | `README.md` limits list ("found a fail-open in its own freshness check: evidence of unknown age passed"); `rift_gate/gate.py` (`_parse_time()` returns None for unusable timestamps → evidence check returns HOLD); `spec/boundary-contract.md` ("Evidence of unknown age is held, not passed") |
| `observed_at` can be misreported by the harness; contracts not signed | `spec/boundary-contract.md` §"Known gaps in v0"; `README.md` §"Not implemented yet" |
| No baselines; fixed temperature/seed repeats not independent samples | `README.md` limits list |
| Install/demo/test commands | `README.md` §§"Install", "Run the demo", "Run the tests" |
