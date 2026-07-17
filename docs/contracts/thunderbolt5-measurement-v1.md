# Thunderbolt 5 measurement protocol v1

## Scope and evidence chain

This protocol measures QW5-framed application traffic over persistent TCP connections
bound to verified direct Thunderbolt network routes. It does not measure raw-link
capacity and does not establish inference, model, kernel, or production-transport
performance.

The machine-readable chain is:

- [`tb5-run-plan.schema.json`](../../schemas/v1/tb5-run-plan.schema.json): the
  owner-approved 246-cell schedule and resource policy;
- [`tb5-route-proof.schema.json`](../../schemas/v1/tb5-route-proof.schema.json): the
  six public-safe direct-route results;
- [`tb5-local-control.schema.json`](../../schemas/v1/tb5-local-control.schema.json)
  and [`tb5-local-control-index.schema.json`](../../schemas/v1/tb5-local-control-index.schema.json):
  the 108 node/payload/control observations and their digest resolver;
- [`tb5-synchronization-evidence.schema.json`](../../schemas/v1/tb5-synchronization-evidence.schema.json):
  the raw empirical inclusion evidence for one simultaneous attempt;
- [`tb5-measurement.schema.json`](../../schemas/v1/tb5-measurement.schema.json) and
  [`tb5-measurement-index.schema.json`](../../schemas/v1/tb5-measurement-index.schema.json):
  every raw cell plus the frozen relative-path/digest resolver; and
- [`tb5-link-summary.schema.json`](../../schemas/v1/tb5-link-summary.schema.json):
  the reconciled 246-cell projection.

Every digest is SHA-256 over [`qw5-json-c14n-v1`](canonical-json-v1.md) bytes. The
handshake, deterministic payload generator, frame, checksum trailer, acknowledgement,
and exact vectors are [`qw5-tb5-wire/v1`](thunderbolt5-wire-v1.md).

The identity graph is deliberately acyclic. The preregistered plan contains only
inputs known before collection and never names a local-control or measurement output.
Each local control binds the plan digest; the local-control index binds the plan and
all 108 control digests. Each raw measurement and the measurement index bind both the
plan and local-control-index digests; the measurement index then binds all 246 raw
cell digests. The link summary binds the plan, local-control index, and measurement
index. Bundle validation recomputes each canonical digest and every projection across
that complete graph.

## Preconditions

Before physical collection:

1. Three `qw5.hardware-inventory/v1` artifacts pass schema, semantic, and public-
   safety validation and identify only A/B/C aliases.
2. The route proof passes for all six directions. No measured data path may use the
   coordinator as a relay or use an unapproved interface.
3. The owner approves the plan seed/order, route and inventory digests, clean QW5
   commit, harness digest, socket request, thermal policy, 32 GiB per-flow stream cap,
   30-second attempt cap, and all other `TARGET` settings.
4. Every node uses the same clean harness and canonical plan digest. The control plane
   coordinates work but never relays measured payloads.
5. Low Power Mode is off; power is stable and recorded; every participating node is
   nominal for five continuous minutes before collection.
6. Model work, conversion, backup, update, and unrelated high-load jobs are absent.

A dirty producer or identity, plan mismatch, route failure, missing approval, or
public-safety failure blocks collection. Physical `MEASURED` artifacts with a dirty
QW5 identity are rejected by semantic validation.

## Direct-route selection and evidence

M1-03 must use public Network framework APIs rather than a shell route heuristic:

1. Resolve the owner-mapped private Thunderbolt interface as an
   [`NWInterface`](https://developer.apple.com/documentation/network/nwinterface).
2. Set
   [`NWParameters.requiredInterface`](https://developer.apple.com/documentation/network/nwparameters/requiredinterface)
   and
   [`NWParameters.requiredLocalEndpoint`](https://developer.apple.com/documentation/network/nwparameters/requiredlocalendpoint)
   before creating the TCP connection.
3. Wait for `NWConnection` ready state; inspect
   [`NWConnection.currentPath`](https://developer.apple.com/documentation/network/nwconnection/currentpath),
   its status, local endpoint, remote endpoint, and whether it uses the required
   interface. Monitor path updates through the entire connection.
4. Complete the QW5 identity handshake directly with the expected peer and verify the
   peer alias, plan digest, flow, payload, and route alias.

A direction passes only when the required interface and local endpoint were applied,
the ready/current path uses that interface, public-safe endpoint comparisons match the
owner mapping, no path change occurs, and the expected peer completes the handshake.
The public artifact records API names, aliases, booleans, statuses, and digests; it
never records raw interface names/indexes, addresses, hostnames, or ports. The owner
may retain private raw routing details outside Git and expose only a salted content
digest. Failure of any condition is `direct_verified: false` and blocks physical data
for that direction.

## Transport, framing, and buffers

Each directed flow has one worker and one persistent TCP connection. `TCP_NODELAY` is
enabled; TLS and compression are disabled. Both endpoints retain requested and
effective send/receive buffers, address family, congestion-control observation,
maximum-segment observation, and the public route alias. TCP interpretation follows
[RFC 9293](https://www.rfc-editor.org/rfc/rfc9293.html).

The wire contract fixes a 96-byte untimed identity handshake, 64-byte data header,
payload, 32-byte SHA-256 trailer, and a 64-byte acknowledgement in round-trip mode.
Header, payload, trailer, acknowledgement, and observable socket bytes remain
separate. The receiver credits a frame only after identity, exact length, monotonic
sequence, deterministic payload, and SHA-256 validation.

Each active flow uses exactly one preallocated application send-payload buffer and
one receive-payload buffer. Each raw cell records bytes per buffer, active-flow count,
and the exact peak application payload-buffer total; semantic validation recomputes
that total as `2 * payload_bytes * active_flow_count`.
Transport/framework/kernel storage is recorded separately when observable and is
never inferred from these two buffers.

## Directed scenarios and matrix

Canonical flows are `a-b`, `b-a`, `a-c`, `c-a`, `b-c`, and `c-b`.

| Scenario | Ordered simultaneous flows |
| --- | --- |
| `solo-a-b`, `solo-b-a`, `solo-a-c`, `solo-c-a`, `solo-b-c`, `solo-c-b` | the named direction |
| `duplex-a-b`, `duplex-a-c`, `duplex-b-c` | both directions on the named pair |
| `fanout-a`, `fanout-b`, `fanout-c` | both outbound directions from the named node |
| `fanin-a`, `fanin-b`, `fanin-c` | both inbound directions to the named node |
| `cycle-a-b-c` | `a-b`, `b-c`, `c-a` |
| `cycle-a-c-b` | `a-c`, `c-b`, `b-a` |
| `all-directed` | all six in canonical order |

Streaming tests all 18 scenarios at `64`, `256`, `1,024`, `4,096`, `16,384`,
`65,536`, `262,144`, `1,048,576`, `4,194,304`, `16,777,216`, `67,108,864`, and
`268,435,456` bytes: 216 cells. Round trip tests the six solo scenarios at `64`,
`1,024`, `16,384`, `262,144`, and `4,194,304` bytes: 30 cells. Total: 246.

Cell IDs are `stream:<scenario>:<payload>` and
`round-trip:<scenario>:<payload>`. `sha256-keyed-sort-v1` sorts by SHA-256 of the
big-endian u64 seed followed by UTF-8 cell ID, with cell ID breaking digest ties.
Semantic validation recomputes every schedule index.

## Streaming attempt rule

Each stream cell retains three warm-ups, each targeting at least two seconds and one
complete message per flow. It then seeks ten valid recorded attempts with no more
than twelve attempts total.

For a recorded attempt:

1. The source endpoint is the controlling endpoint. All workers are ready before the
   coordinator releases the attempt.
2. Payload generation begins inside the retained source interval. Receiver comparison
   and SHA-256 complete inside the retained receiver interval. Their cost is not
   removed from throughput.
3. The target is three seconds. The source stops at the first complete-frame boundary
   at or after the target, unless 30 seconds or 32 GiB of logical payload per flow is
   reached first.
4. If either cap is reached before the three-second target, the attempt is invalid and
   retained. A cap never silently shortens a valid attempt.
5. The source announces the final sequence on the control channel. The receiver ends
   only after fully reading and validating that exact frame. EOF, timeout, or a final
   partial frame invalidates and retains the attempt.

Connections keep fresh non-overlapping sequence ranges. The run idles five seconds
between payloads and 60 seconds between scenarios, subject to the thermal rule.
Streaming throughput is receiver-validated logical payload divided by receiver-local
elapsed time. Sender and receiver clocks are never subtracted. Validation requires
both retained endpoint intervals to meet the two-second warm-up or three-second sample
target and rejects any interval or logical-payload total above the frozen cap.

## Round-trip rule

The first four round-trip payload sizes retain 100 warm-up exchanges and 1,000
recorded exchanges. The 4 MiB cell retains 20 warm-ups and 100 recorded exchanges.
Before each timer starts, the source generates the payload/frame in its preallocated
buffer. The timed interval includes send, receiver read, deterministic comparison,
SHA-256, and acknowledgement. The source retains every source-local round-trip value.
Results are never divided by two or relabeled as one-way latency.

One failed integrity/exchange makes the batch `FAILED`; a timed connection failure
makes it `ABORTED`. Partial exchanges and errors remain durable evidence.

## Empirical simultaneous-attempt inclusion

Different-node monotonic clocks are not comparable. V1 therefore does not estimate
actual start-time separation. It uses `coordinator_observed_window_v1`, an empirical
quality score used only to include or exclude a simultaneous attempt:

1. Immediately before release, every participant completes exactly 100 echo rounds
   over the persistent control channel. Every RTT is retained.
2. On release, each worker starts its data worker and queues `STARTED`. It records its
   worker-local start-to-ack interval. The coordinator records all ack receipts on its
   single monotonic clock.
3. `pre_attempt_control_rtt_max_ns` is the maximum retained RTT.
   `worker_start_to_ack_max_ns` is the maximum worker-local interval.
   `timer_resolution_allowance_ns` is coordinator resolution plus the largest worker
   resolution. `coordinator_receipt_spread_ns` is latest minus earliest coordinator
   receipt.
4. `coordinator_observed_start_window_ns` is receipt spread + maximum RTT + twice the
   maximum worker interval + the timer-resolution allowance.

This value is solely an empirical attempt-inclusion score. It is never an actual-start
estimate, start-skew bound, clock proof, or one-way-delay claim. An attempt is included
only when maximum control RTT is at most 1 ms and the coordinator-observed window is
at most 10 ms. Missing, malformed, or error evidence invalidates the attempt. If no
simultaneous recorded attempt qualifies, the cell is `UNDETERMINED`. Solo attempts
use `not_required`.

The raw record retains clocks by API identifier and units, all 100 RTTs per
participant, release/receipt values, worker intervals, resolutions, derived values,
decision, reasons, errors, and canonical digest. The measurement references that
digest. Bundle validation resolves it, recomputes the canonical digest, and reconciles
plan, cell, scenario, attempt, method, raw-derived fields, and inclusion decision to
the attempt projection. The validator also recomputes every maximum, spread,
allowance, score, and decision.

## Copy observations and local controls

Every flow records producer-to-send, send-to-transport, and kernel/DMA/hardware at the
source plus transport-to-receive, receive-to-consumer, and kernel/DMA/hardware at the
destination. Direct counts are `MEASURED`; derived counts are `ESTIMATED`; fixture
counts are `SIMULATED`; unavailable layers remain unavailable. Throughput never proves
zero-copy.

Before network cells, every node runs three controls at every stream payload: raw
buffer copy, frame plus verification, and deterministic generation plus SHA-256. That
is 3 nodes x 12 payloads x 3 controls = 108 indexed artifacts. Each retains three
warm-ups and ten recorded durations, buffer counts/peak bytes, timing scope, plan and
producer identity, and errors. The index resolves each relative path to its canonical
digest. Controls are matching cost context only; they are never subtracted from
network measurements.

Each control also records one exact node-local regime identity over its observation
interval: thermal state, Low Power Mode, and power source at both boundaries. A
`COMPLETE` control cannot cross any of those boundaries. The control index and every
control resolve to the same preregistered plan; the plan never points back to the
post-run index.

A complete control has exactly three warm-ups, ten recorded durations, and no error.
A failed, aborted, or undetermined control retains every completed duration and at
least one structured error; it remains in the 108-entry index and cannot be normalized
to an empty successful result.

## Thermal, failures, and retries

- Checksum, identity, sequence, bytes, route, empirical-inclusion, timeout, or partial-
  frame failure invalidates and retains the attempt.
- One reconnect is allowed before a scenario starts. A timed connection failure
  aborts that cell.
- No payload reduction, route change, relay, checksum disablement, schedule change, or
  socket retuning is allowed inside a plan.
- Every attempt retains start/end thermal state, Low Power Mode, power source, and
  node-local observation times.
- A valid attempt has exactly one stable `(thermal state, Low Power Mode, power
  source)` tuple per active node. Start/end changes invalidate the attempt.
- When a node leaves nominal state, finish and retain the current attempt, pause up to
  15 minutes, and resume only after all participating nodes are nominal for five
  continuous minutes. Otherwise abort the cell.
- One cell summary may cover only one complete per-node regime identity. An attempt
  from a different thermal, Low Power Mode, or power-source regime cannot remain a
  valid member of that summary; it is retained with an exclusion reason. Regimes are
  not pooled even if their thermal-state labels match.

## Measurement index and link summary

The measurement index has exactly 246 unique cell IDs, relative paths, and digests.
The link summary records the index digest. For every cell, validation must resolve the
path, recompute the raw canonical digest, and reconcile cell identity, mode, scenario,
payload, status, ordered flow set, metrics, exclusions, errors, and exact per-node
regime identities.
Coverage is recomputed from the reconciled statuses.

`COMPLETE` has an evidentiary meaning:

- stream: exactly ten throughput samples per flow and ten aggregate samples; latency
  is empty;
- round trip through 256 KiB: exactly 1,000 latency samples per flow; throughput and
  aggregate are empty; and
- 4 MiB round trip: exactly 100 latency samples per flow; throughput and aggregate are
  empty.

`FAILED`, `ABORTED`, and `UNDETERMINED` cells retain whatever valid partial metrics,
exclusions, errors, and regime identities exist. They are never converted to empty
successful-looking records.

Integer summary arithmetic is fixed: per-attempt stream rate is
`floor(validated_payload_bytes * 1_000_000_000 / receiver_elapsed_ns)`; simultaneous
aggregate is the sum of its per-flow rates. Median is the middle value or floor of the
two middle values' average; median absolute deviation uses the same rule; p95 is
nearest rank `ceil(0.95 * n)`.

## Required hostile tests

In addition to schema/meta-schema, canonical, wire, and link checks, validation rejects:

- an all-`COMPLETE` summary with zero samples;
- an index digest, path, raw digest, identity, status, metric, exclusion, error, or
  regime projection that disagrees;
- a run plan that points at a post-run local-control index, a local control that binds
  a different plan, or any unresolved path/digest in the complete evidence graph;
- pooling attempts or controls across thermal, Low Power Mode, or power-source
  regimes;
- an unsupported timing-bound field or a derived empirical score that does not
  reconcile;
- insufficient empirical evidence credited to a simultaneous cell;
- a dirty physical `MEASURED` artifact;
- incomplete 108-control or 246-measurement indexes;
- route/peer mismatch, relay, path update, corrupt/truncated frame, sequence regression,
  byte mismatch, hidden retry, cross-clock subtraction, missing thermal evidence,
  unknown copy stage, and private machine/network identity.
