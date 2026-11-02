# Security

rift-gate 0.1 is a research reference implementation, not a hardened security product. Its known gaps are listed in [spec/boundary-contract.md](spec/boundary-contract.md#known-gaps-in-v0).

## Known limitations of rift-gate 0.1

**Affected:** rift-gate 0.1.0 (tag `v0.1.0`, 25 October 2026) and the current `main` branch, which has the same gate code.

**rift-gate 0.1.0 should not be relied on as a production security enforcement boundary.** It is a research reference implementation. Internal testing in late October 2026 found cases where 0.1.0 allows a call that its contract says should be stopped or held:

- **Evidence freshness.** Some timestamps that do not establish a reliable evidence age are accepted as fresh, so `evidence.max_age` is not always enforced.
- **Human escalation.** Some missing, malformed or inconsistent amount inputs cause `escalation.human_above` not to be applied, so an action above the threshold can proceed without a person.
- **Contract validation.** `check()` does not validate the contract it is given. Some malformed contracts may be interpreted permissively. Others cause `check()` to raise an exception rather than return a hold. Callers must not treat an exception as authorization.
- **Delegation.** The `delegation.may_grant: none` restriction is not reliably enforced by v0.1.0. Delegation restrictions must not be relied upon as an independent security boundary.

Two statements in the 0.1 documentation are therefore not accurate for 0.1.0: that errors inside the gate always hold, and (in Technical Note 001) that malformed input always holds.

**Execution authority must stay outside the agent.** A rift-gate decision is advisory. A call is prevented only when the process that holds the tool credentials invokes the tool solely after the gate allows it. The agent must never hold those credentials or have any other path to the tool.

A corrected version is being tested. It has not been released, and this notice will be updated when it is.

## Reporting a vulnerability

If you find a way to get a forbidden, unverified or stale-evidence action past the gate, please report it privately through GitHub's **"Report a vulnerability"** button on this repository's **Security** tab, not as a public issue.

We will acknowledge reports and publish a fix and a note once one is available. A dedicated security contact address will be added here before any general (non-research) release.
