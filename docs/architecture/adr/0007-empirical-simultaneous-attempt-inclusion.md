# ADR-0007: Empirical simultaneous-attempt inclusion

- **Status:** Proposed for acceptance with the M0 contract-completion and M1 planning pull request
- **Date:** 2026-07-15
- **Decision owners:** Project owner and M0 contract-completion/M1 planning task

## Context

QW5 needs a deterministic rule for deciding whether simultaneous-flow attempts are
comparable enough to retain. Node-local monotonic clocks do not share an established
timebase. A coordinator's receipt times plus control-channel observations cannot
establish the participants' actual data-start separation.

The first-pass contract named a conservative timing result, but the available inputs
did not justify that interpretation. The project owner selected an empirical surrogate
instead of adding a clock-synchronization system to M1.

## Decision

M1 uses `coordinator_observed_window_v1` only as an empirical attempt-inclusion score.
Immediately before each simultaneous attempt, every participant contributes exactly
100 retained control RTT observations. After release, the coordinator records all
`STARTED` acknowledgement receipts on its one monotonic clock; workers record their
local data-start-to-ack intervals and clock resolution.

The score is:

`receipt spread + maximum control RTT + 2 * maximum worker start-to-ack interval + timer-resolution allowance`

where the allowance is the coordinator resolution plus the largest participating
worker resolution. Every input and derived term is retained in a canonical raw
`qw5.tb5-synchronization-evidence/v1` artifact and linked from the attempt by SHA-256.

An attempt qualifies only when maximum pre-attempt control RTT is at most 1 ms and the
coordinator-observed score is at most 10 ms. The score is not an estimate of actual
start separation and cannot support cross-node subtraction or one-way latency.
Malformed, unavailable, or error evidence invalidates the attempt. A simultaneous cell
with no qualifying recorded evidence is `UNDETERMINED`.

## Consequences

- M1 does not add clock synchronization, PTP, or another time-transfer system.
- The 1 ms and 10 ms values are preregistered empirical inclusion thresholds, not
  hardware capability claims.
- Validator vectors recompute every raw term and reject legacy or unsupported timing
  claim fields.
- Any future actual-start or one-way-timing claim needs a new ADR, protocol version,
  primary-source analysis, and evidence model.
