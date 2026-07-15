# ADR-0005: Thunderbolt 5 application-path measurement

- **Status:** Proposed for acceptance with the M0 contract-completion and M1 planning pull request
- **Date:** 2026-07-14
- **Decision owners:** Project owner and M0 contract-completion/M1 planning task

## Context

The declared full mesh does not establish effective application throughput, latency,
concurrency, copy count, routing, or error behavior. Controller marketing rates do not
answer those questions. Cross-node clock subtraction also cannot produce defensible
one-way latency in this protocol.

QW5 needs transport evidence that matches the production boundary closely enough to
guide later scheduling while remaining implementable and auditable on macOS.

## Decision

M1 first measures framed application payloads over one persistent TCP connection per
directed flow, explicitly bound and route-verified to the direct Thunderbolt network
path for the node pair. TCP is a measurement transport, not a permanent production
transport decision. TLS and compression are disabled for this protocol and the actual
socket settings are recorded. TCP behavior is interpreted according to
[RFC 9293](https://www.rfc-editor.org/info/rfc9293/).

The protocol measures all six directed paths alone and in the simultaneous scenarios
defined by `docs/contracts/thunderbolt5-measurement-v1.md`. Application bytes, framed
wire bytes, checksum work, retries, errors, observable copies, and unavailable copy
layers remain separate. No data flow is allowed to relay through node A or a non-test
network path.

Streaming throughput is timed independently at each endpoint using its monotonic
clock. Request/acknowledgement tests report measured round-trip latency. They do not
divide by two or publish one-way latency. One-way timing is outside this ADR and would
require a separate architecture decision and measurement contract.

Every message uses a deterministic payload and SHA-256 integrity check. Checksum time
is recorded because integrity cost is part of the measured application path; it is not
silently subtracted. A checksum, sequence, route, or byte-count mismatch invalidates
the sample and is preserved as negative evidence.

The run is a machine-readable, owner-approved 246-cell plan with a preregistered seed
and deterministic keyed order. The exact v1 wire format and golden bytes are frozen
before harness implementation. Local buffer-copy, framing, and SHA-256 controls are
measured separately and never silently subtracted or relabeled as link capacity.

Simultaneous-attempt inclusion follows ADR-0007. It uses a same-coordinator empirical
observation and never interprets different-node clocks as a common timebase. Missing
or insufficient evidence makes the cell `UNDETERMINED`.

## Consequences

- M1 claims application-path behavior for the recorded stack, not raw Thunderbolt 5
  signaling capacity.
- Simultaneous tests use one worker per directed flow and a start barrier; their
  eligibility is determined by the empirical rule in ADR-0007.
- Warm-ups, invalid attempts, replacements, per-endpoint timestamps, socket bytes,
  copy evidence, exclusions, and thermal regimes remain in raw artifacts.
- Kernel and hardware copy counts may remain unavailable. QW5 reports only observable
  copies and never infers zero-copy from throughput.
- A later transport can be evaluated by a new protocol revision or a separately
  identified transport profile without rewriting M1 results.
