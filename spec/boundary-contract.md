# Boundary contract format, v0

A boundary contract is a short YAML document attached to one agent. It is written by the person or team responsible for the agent, and it is checked by the gate **before** any tool call executes. A prompt can ask an agent to behave; a contract is enforced whether or not the agent agrees.

Status: **v0**. This is the format used in Riftform's RIFT research prototype, published as-is so others can read, run and test it. It will change. Machine-readable schema: [`boundary-contract.schema.json`](boundary-contract.schema.json).

## Sections

| Section | Field | Meaning | Enforced by rift-gate 0.1 |
|---|---|---|---|
| `contract` | | Identifier and version, e.g. `actor/v1.1`. Every stop or hold cites `<contract>#<section.field>` | ✅ cited |
| `agent_id` | | The agent this contract governs | |
| `capability` | `tools` | Every tool the agent may call. Anything not listed is stopped | ✅ boundary |
| `authority` | `decide` | Actions the agent may decide on its own | ✅ via delegation |
| | `never` | Actions stopped even if the tool is reachable | ✅ boundary |
| `state` | `read`, `write` | Shared-state collections the agent may read and write | Documented, not enforced (your state layer should) |
| `delegation` | `may_grant` | `subset_of_own`: a grant may include only actions in the agent's own `authority.decide`. `none`: no delegation | ✅ boundary (`subset_of_own`) |
| `evidence` | `required_for` | Actions that must cite evidence | ✅ evidence |
| | `must_resolve_in` | `shared_state`: every cited ID must exist in shared state | ✅ evidence |
| | `max_age` | Maximum age of the cited evidence (`30s`, `5m`, `2h`). Age is now minus `observed_at`, the time the agent read it. **Evidence of unknown age is held, not passed** | ✅ evidence |
| `verification` | `required_for` | Actions that need an independent verifier before they execute | ✅ reported as `needs_verification` |
| | `timeout`, `independence` | How long to wait; on which axes the verifier must differ from the actor (model provider, context, evidence retrieval, state snapshot, verification policy) | Documented; the verifier is yours to run |
| `escalation` | `human_above` | Thresholds above which a person decides (e.g. `refund_usd: 5000`) | ✅ escalation (`refund_usd`) |
| | `on_unresolved`, `on_verifier_timeout`, `on_disagreement_with_actor` | What happens when things don't resolve. `hold` throughout | Gate errors hold |
| `fallback` | `protected` | What must stay protected if cooperation breaks down | Documented |

## Decisions

- **pass**: the check applied and was satisfied.
- **stop**: the call is refused; the cited line says why.
- **hold**: the call does not execute until something resolves (a person, a verifier, or fresh evidence).
- **not_invoked**: the check does not apply to this tool.

## Design rules

1. **Fail closed.** Malformed input, unknown evidence age and errors inside the gate all hold.
2. **Cite the line.** Every stop or hold names the contract line, so a failure can be attributed.
3. **The gate never branches on who is asking or why.** Same call, same contract, same state, same answer.
4. **The verifier reads the world itself.** It never checks the actor's reasoning, only the actor's proposed action against its own read.

## Known gaps in v0

- `state.read`/`state.write`, `fallback` and verifier independence are declared but not enforced by this package.
- `escalation.human_above` supports only `refund_usd`, the example domain's unit.
- `observed_at` is asserted by the agent or harness. A dishonest harness can lie about it.
- Contracts are not signed. Anyone who can edit the YAML can change the limits.
