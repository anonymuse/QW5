# Thunderbolt 5 measurement protocol v1

## Scope and artifact chain

This protocol measures QW5-framed application traffic over persistent TCP connections
bound to verified direct Thunderbolt network routes. Results describe only the exact
recorded stack. They are not raw-link capacity, production-transport, inference, or
model-performance claims.

The machine-readable chain is:

- [`tb5-run-plan.schema.json`](../../schemas/v1/tb5-run-plan.schema.json) for the
  owner-approved 246-cell plan and local controls;
- [`tb5-route-proof.schema.json`](../../schemas/v1/tb5-route-proof.schema.json) for
  all six direct routes;
- [`tb5-measurement.schema.json`](../../schemas/v1/tb5-measurement.schema.json) for
  every raw cell result; and
- [`tb5-link-summary.schema.json`](../../schemas/v1/tb5-link-summary.schema.json) for
  the complete cell index and reconciled summaries.

All JSON identities use [`qw5-json-c14n-v1`](canonical-json-v1.md). The exact
handshake, payload generator, frame, digest trailer, acknowledgement, and golden bytes
are defined by [`qw5-tb5-wire/v1`](thunderbolt5-wire-v1.md).

## Preconditions

Before a run:

1. All three `qw5.hardware-inventory/v1` manifests pass schema, semantic, and public-
   safety validation and match the intended A/B/C aliases.
2. The six-entry route proof shows traffic bound directly to each pair's Thunderbolt
   route. The data plane never traverses node A as coordinator or a non-test route.
3. QW5 commit, clean-state flag, harness SHA-256, schema versions, OS builds,
   requested socket settings, inventory and route-proof digests, seed, order
   algorithm, thresholds, and local controls are frozen in an owner-approved run plan.
4. Every node uses the same harness and canonical plan digest. An out-of-band control
   barrier coordinates starts but never relays measured payloads.
5. Low Power Mode is off, power source is stable and recorded, and every node remains
   in nominal thermal state for five minutes before controls or network measurement.
6. No model, conversion, backup, update, or unrelated high-load job runs. Process
   checks stay local and only their public-safe pass/fail result is committed.

An unavailable route, dirty binary, plan mismatch, missing owner approval, or public-
safety failure blocks physical execution. It is not repaired inside a measurement run.

## Transport and exact framing

One worker and one persistent TCP connection serve each directed flow. `TCP_NODELAY`
is enabled; TLS and compression are disabled. For both endpoints of every flow, record
requested and effective send/receive buffers, `TCP_NODELAY`, address family,
congestion-control name when exposed, maximum segment size when exposed, and the
public route alias. Raw network addresses are forbidden.

The wire contract fixes a 96-byte untimed identity handshake, 64-byte data header,
payload, 32-byte SHA-256 trailer, and, in round-trip mode, 64-byte acknowledgement.
Header, payload, trailer, acknowledgement, and observed socket bytes are separate.
Deterministic payload bytes derive from seed, flow ID, payload size, and sequence by
the exact SHA-256 counter formula; payload generation occurs outside a timed latency
exchange.

The receiver credits a message only after frame identity, exact length, monotonic
sequence, deterministic bytes, and SHA-256 all pass. It records checksum count and
elapsed time. Integrity work stays inside the application path and is not silently
subtracted from throughput.

## Exact directed scenarios

The canonical flow IDs are `a-b`, `b-a`, `a-c`, `c-a`, `b-c`, and `c-b`. A scenario
ID is coupled to the following exact ordered flow set; it is not a free-form label.

| Scenario ID | Ordered concurrent directed flows |
| --- | --- |
| `solo-a-b` | `A>B` |
| `solo-b-a` | `B>A` |
| `solo-a-c` | `A>C` |
| `solo-c-a` | `C>A` |
| `solo-b-c` | `B>C` |
| `solo-c-b` | `C>B` |
| `duplex-a-b` | `A>B`, `B>A` |
| `duplex-a-c` | `A>C`, `C>A` |
| `duplex-b-c` | `B>C`, `C>B` |
| `fanout-a` | `A>B`, `A>C` |
| `fanout-b` | `B>A`, `B>C` |
| `fanout-c` | `C>A`, `C>B` |
| `fanin-a` | `B>A`, `C>A` |
| `fanin-b` | `A>B`, `C>B` |
| `fanin-c` | `A>C`, `B>C` |
| `cycle-a-b-c` | `A>B`, `B>C`, `C>A` |
| `cycle-a-c-b` | `A>C`, `C>B`, `B>A` |
| `all-directed` | all six in canonical flow order |

Every flow in a simultaneous scenario uses one payload size and the same barrier.
Ready acknowledgements precede release.

## Cell matrix and deterministic order

Streaming mode uses exactly these payload bytes:

`64`, `256`, `1,024`, `4,096`, `16,384`, `65,536`, `262,144`, `1,048,576`,
`4,194,304`, `16,777,216`, `67,108,864`, and `268,435,456`.

It covers all 18 scenarios, producing 216 cells. Round-trip mode covers only the six
solo scenarios and payloads `64`, `1,024`, `16,384`, `262,144`, and `4,194,304`,
producing 30 cells. The plan total is therefore 246, validated semantically rather
than trusted from a declared count.

Each canonical cell ID is `stream:<scenario>:<payload>` or
`round-trip:<scenario>:<payload>`. `sha256-keyed-sort-v1` orders cells by SHA-256 over
the big-endian 64-bit seed followed by the UTF-8 cell ID; digest ties break by cell ID.
The seed and resulting schedule index are committed before results exist. This
preregistered order prevents discretionary best-condition ordering.
Every cell result repeats the seed, and semantic validation recomputes that cell's
exact schedule index. The final link summary repeats the seed, contains cells in
schedule order, and validates every cell/index pair rather than checking only that
the integers 0 through 245 appear.

## Streaming repetitions

For every stream cell:

- retain three warm-up attempts, excluded only from sample statistics;
- run each warm-up for at least two seconds and one message per flow;
- target ten valid measurement attempts, each at least three seconds and one message
  per flow;
- permit at most twelve measurement attempts total, so no more than two replacements;
- continue fresh non-overlapping sequence ranges on persistent connections;
- idle five seconds between payloads and sixty seconds between scenarios, subject to
  the thermal rule; and
- retain warm-ups, invalid attempts, replacements, errors, and partial results.

For each flow, record source- and receiver-local monotonic start/end, messages,
logical payload, header, digest-trailer, acknowledgement and socket bytes, checksum
count/time, sequence range, copy observations, and errors. Counts reconcile to payload
size and sequence range. Streaming throughput is receiver-validated payload divided
by receiver-local elapsed time. Sender timing remains separate; clocks are never
subtracted across nodes.

## Round-trip repetitions

The receiver sends the fixed 64-byte acknowledgement only after full validation. For
the first four sizes, retain 100 warm-up exchanges and record 1,000 sequential
exchanges. For 4,194,304 bytes, retain 20 warm-ups and record 100 exchanges. Report
every source-local round-trip latency and its distribution. Never divide by two or
publish it as one-way latency.

The exchanges are stored as one warm-up batch and one measurement batch per cell,
with each exchange latency retained. Round-trip batches have no replacement policy:
an integrity/exchange failure makes the batch and cell `FAILED`; a timed connection
failure makes it `ABORTED`. Partial exchanges and errors remain raw evidence.

## Synchronization evidence

Monotonic clocks on different nodes are not directly comparable. V1 therefore uses
only `coordinator_receipt_surrogate`, measured on one coordinator monotonic clock:

1. Immediately before each simultaneous attempt, every worker completes 100 echo
   rounds on the persistent control channel; the coordinator retains every RTT and the
   maximum accepted RTT.
2. On release, each worker starts its data worker and immediately queues a `STARTED`
   acknowledgement. It records its local data-start-to-ack interval. The coordinator
   records every acknowledgement receipt and their maximum-minus-minimum skew.
3. The timer allowance is the sum of the recorded coordinator and participating-node
   monotonic resolutions. Let `rtt` be the maximum control RTT and `worker` the maximum
   local start-to-ack interval. The conservative uncertainty is
   `rtt + 2 * worker + timer_allowance`.
4. `start_skew_upper_bound = coordinator_receipt_skew + uncertainty`.

The raw calibration/receipt record is canonical and content-addressed; its SHA-256 and
all formula inputs are stored in the attempt. A valid attempt requires uncertainty at
or below 1 ms and the upper bound at or below 10 ms. Exceeding either invalidates the
attempt with the corresponding reason and permits a replacement within the stream
twelve-attempt limit. If calibration is unavailable or cannot meet the uncertainty
bound, the cell is `UNDETERMINED`, never simultaneous-link evidence. Solo flows mark
this synchronization `not_required`.

## Copy evidence and local controls

Each flow records six endpoint/stage observations: producer-to-send,
send-to-transport, and kernel/DMA/hardware at the source; transport-to-receive,
receive-to-consumer, and kernel/DMA/hardware at the destination. Every entry names the
endpoint, status, method, and, when available, count and bytes. Direct counts are
`MEASURED`; inferred values are `ESTIMATED` and stay separate; schema-fixture values
are `SIMULATED`. Kernel and hardware copies remain unavailable absent a direct
documented probe. Throughput never proves zero-copy.

Before network cells, each node runs buffer-copy, frame encode/decode, and SHA-256
controls for every stream payload with three retained warm-ups and ten recorded
repetitions. Binary, seed, byte counts, elapsed time, thermal state, and errors are
content-addressed. Controls may explain an application bottleneck but are never
subtracted from network results or used to relabel link contention.

## Error, retry, and thermal policy

- Checksum, frame identity, sequence, byte-count, route, skew, or premature-EOF
  failure invalidates and retains the attempt.
- One reconnect is permitted before a scenario begins. A timed connection failure
  aborts that scenario/payload cell.
- Timeouts, socket errors, invalid attempts, exclusions, and replacements remain in
  raw artifacts and in failure-rate counts.
- Fewer than ten valid stream measurements after twelve attempts yields `FAILED`.
- No payload reduction, path change, relay, checksum disablement, order change, or
  socket retuning is allowed inside a plan. Any such change creates a new plan digest.

Every attempt records beginning/end thermal state, Low Power Mode, power source, and
local monotonic observation times for every participating node. If a node leaves
nominal state, finish and retain the active attempt under its distinct thermal regime,
then pause new work for up to 15 minutes. Resume only after all nodes are nominal for
five continuous minutes; otherwise abort the cell. Results from different thermal or
power regimes are never pooled. Ambient and fan data remain explicitly unavailable
when no supported source exists.

## Artifact identity and summaries

Each result references the plan digest, schedule index, QW5 commit, harness digest,
three inventory digests, route-proof digest, exact scenario flow set, payload, mode,
seed, framing version, requested/effective socket settings, every warm-up and
measurement attempt, exclusions, and collection errors.

Per-flow and aggregate summaries report sample count, median, median absolute
deviation, p95, minimum, maximum, invalid attempts, and thermal regimes. The link
summary contains exactly 246 unique cell IDs and schedule indexes; coverage counts
reconcile to the raw measurement index. Per-flow values are never hidden by an
aggregate, and the best run is never the headline.

Summary arithmetic is exact integer arithmetic. Stream input samples are per-attempt
`floor(validated_payload_bytes * 1_000_000_000 / receiver_elapsed_ns)`; aggregate
throughput is the sum of concurrent per-flow values for that attempt. Round-trip input
samples are the retained source-local exchanges. Median is the middle value for odd
counts and the floor of the two-middle-value average for even counts; median absolute
deviation uses that same rule; p95 is nearest rank `ceil(0.95 * n)`. Wrong-mode
metrics contain zero samples and null statistics. The semantic validator recomputes
all per-flow and aggregate values.

## Acceptance and negative cases

Schema validation is necessary but insufficient. `tools/validate_contracts.py`
enforces scenario/flow coupling, complete plan coverage, route references, endpoint
and socket coverage, arithmetic byte/sequence/checksum reconciliation, synchronization
bounds, copy-stage coverage, attempt/summary/exclusion counts, cell outcome rules, and
link-summary cell/flow/schedule/metric consistency.

Harness tests must additionally reject wrong peers or routes, plan/identity mismatch,
corrupt or truncated frames, duplicate or regressing sequence, partial reads/writes,
socket byte mismatch, unreported retry, invalid sample credited to statistics,
cross-clock one-way latency, missing thermal evidence, unknown copy stage, raw network
identifier, and any golden-wire-vector mismatch.
