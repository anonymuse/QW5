# Thunderbolt 5 measurement protocol v1

## Scope

This protocol measures QW5-framed application traffic over persistent TCP connections
bound to verified direct Thunderbolt network routes. Results describe only the exact
recorded stack. They are not raw-link capacity, production-transport, inference, or
model-performance claims.

The result schema is
[`tb5-measurement.schema.json`](../../schemas/v1/tb5-measurement.schema.json).

## Preconditions

Before a run:

1. All three `qw5.hardware-inventory/v1` manifests pass validation and match the
   intended A/B/C aliases.
2. Each pair has a route proof showing traffic is bound directly to that pair's
   Thunderbolt route. The data plane must not traverse node A as coordinator or any
   non-test interface.
3. QW5 commit, harness executable SHA-256, schema version, OS build, socket settings,
   and inventory digests are frozen in the run plan.
4. Nodes use the same harness and plan digest. A control barrier coordinates starts
   but never relays measured payloads.
5. Low Power Mode is off. Power source is stable and recorded. Each node reports the
   nominal thermal state continuously for five minutes before baseline measurement.
6. No model, conversion, backup, update, or unrelated high-load job runs on the nodes.
   Process lists are checked locally; they are not published.

## Framing and transport

One worker and one persistent TCP connection are used per directed flow. TCP_NODELAY
is enabled. TLS and compression are disabled. Requested and effective send/receive
buffer sizes, congestion-control name when exposed, address family, maximum segment
size when exposed, and route aliases are recorded. Raw addresses are excluded.

Each message has a fixed protocol header containing protocol version, run/scenario
identifier hashes, stream ID, sequence number, payload bytes, flags, and the expected
SHA-256 payload digest. Integers use network byte order. Header bytes and payload bytes
are counted separately. The deterministic payload is generated from the plan seed,
stream ID, payload size, and sequence number; generation occurs before a timed latency
operation or uses a prebuilt ring for streaming.

The receiver validates frame length, identity, monotonic sequence, and SHA-256 before
crediting bytes. It reports checksum computation time separately. Checksumming remains
inside the measured application path and is not silently subtracted from throughput.

## Directed paths and concurrency scenarios

The six directed paths are `A>B`, `B>A`, `A>C`, `C>A`, `B>C`, and `C>B`. Execute these
18 scenarios in the listed order unless a preregistered randomized order and seed are
stored in the plan:

| ID | Concurrent directed flows | Purpose |
| --- | --- | --- |
| `solo-a-b` | `A>B` | Solo direction |
| `solo-b-a` | `B>A` | Solo direction |
| `solo-a-c` | `A>C` | Solo direction |
| `solo-c-a` | `C>A` | Solo direction |
| `solo-b-c` | `B>C` | Solo direction |
| `solo-c-b` | `C>B` | Solo direction |
| `duplex-a-b` | `A>B`, `B>A` | Pair full duplex |
| `duplex-a-c` | `A>C`, `C>A` | Pair full duplex |
| `duplex-b-c` | `B>C`, `C>B` | Pair full duplex |
| `fanout-a` | `A>B`, `A>C` | Shared sender |
| `fanout-b` | `B>A`, `B>C` | Shared sender |
| `fanout-c` | `C>A`, `C>B` | Shared sender |
| `fanin-a` | `B>A`, `C>A` | Shared receiver |
| `fanin-b` | `A>B`, `C>B` | Shared receiver |
| `fanin-c` | `A>C`, `B>C` | Shared receiver |
| `cycle-a-b-c` | `A>B`, `B>C`, `C>A` | Three-node directed cycle |
| `cycle-a-c-b` | `A>C`, `C>B`, `B>A` | Reverse cycle |
| `all-directed` | all six | Full-mesh stress |

All flows in a simultaneous scenario use the same payload size and start barrier.
Ready acknowledgements precede the barrier. A measured start skew above 10 ms
invalidates that repetition; at most two replacement attempts are allowed and all
attempts are retained.

## Payloads and modes

Streaming mode uses this exact ordered byte matrix:

`64`, `256`, `1,024`, `4,096`, `16,384`, `65,536`, `262,144`, `1,048,576`,
`4,194,304`, `16,777,216`, `67,108,864`, and `268,435,456`.

For every scenario and payload:

- perform three unreported warm-up samples;
- each warm-up lasts at least two seconds and completes at least one message;
- perform ten reported repetitions;
- each reported repetition lasts at least three seconds and completes at least one
  message per flow;
- use a fresh sequence range without reconnecting between valid repetitions; and
- idle for five seconds between payload sizes and sixty seconds between scenarios,
  subject to the thermal rule below.

The endpoint records monotonic start/end, messages, logical payload bytes, header
bytes, socket bytes when exposed, checksum count/time, sequence range, and errors for
each repetition. Throughput is calculated from receiver-validated payload bytes and
receiver-local elapsed time. Sender results are reported separately; cross-clock
subtraction is forbidden.

Round-trip mode runs only for the six solo paths with payloads `64`, `1,024`, `16,384`,
`262,144`, and `4,194,304` bytes. The receiver returns a fixed-size acknowledgement
after validation. For the first four sizes, run 100 warm-up exchanges and 1,000
recorded sequential exchanges. For 4,194,304 bytes, run 20 warm-ups and 100 recorded
exchanges. Report source-local round-trip latency; do not divide it into one-way
latency. Acknowledgement bytes are counted separately.

## Copies and synchronization

For each endpoint and repetition, record observable application copies by named stage:

- deterministic producer to send buffer;
- send buffer to transport submission when observable;
- transport receive to receive buffer when observable;
- receive buffer to checksum/consumer when a distinct copy occurs.

Each stage has `available`, `unavailable`, or `error`, count, bytes, observation method,
and whether the value is counted or inferred. Inferred values are `ESTIMATED` and are
not combined with measured copy counts. Kernel, DMA, controller, and hardware copies
remain unavailable unless a documented probe directly observes them. Throughput is
never used as evidence of zero-copy.

The coordinator records barrier readiness, release time, and per-node start receipt.
Wall-clock synchronization is used only to correlate artifacts. Timed intervals use
endpoint-local monotonic clocks.

## Error and retry policy

- Checksum, frame identity, sequence, byte-count, route, or premature-EOF failure
  invalidates the repetition.
- A connection setup failure permits one reconnect before the scenario begins. A
  connection failure in a timed repetition aborts that scenario/payload cell.
- Timeouts, socket errors, invalid samples, and replacement attempts remain in raw
  artifacts. They are not excluded from failure-rate reporting.
- The valid sample target is ten. If it is not reached within twelve attempts, the
  cell fails G2 and is reported as negative evidence.
- No automatic payload reduction, path change, relay, checksum disablement, or socket
  retuning is allowed inside a plan. Such a change creates a new plan digest.

## Thermal and power policy

Record thermal state, Low Power Mode, power source, and monotonic observation times at
the beginning and end of every repetition. If any node leaves nominal thermal state,
finish and retain the active repetition as a distinct thermal regime, then pause new
measurement for up to 15 minutes. Resume only after all nodes are nominal continuously
for five minutes. Otherwise abort the remaining scenario and record the failure.

Ambient temperature and fan data are recorded when available. Their absence is
explicit and does not invite an estimate. Results from different thermal or power
regimes are never pooled.

## Artifact identity and reporting

Each result references the plan digest, QW5 commit, harness digest, three inventory
digests, route-proof digest, scenario, payload, mode, seed, socket configuration,
sample records, exclusions, and collection errors. Raw artifacts are content-addressed.

Summaries report per directed flow and aggregate scenario values without hiding
per-flow contention. For latency and throughput report sample count, median, median
absolute deviation or another preregistered dispersion statistic, p95, minimum,
maximum, invalid attempts, and thermal regimes. The best run is never the headline.

## Acceptance and negative cases

The harness tests must reject a wrong peer alias, non-direct route, inconsistent plan
digest, missing flow, duplicate sequence, corrupt checksum, truncated frame, byte-count
mismatch, start skew above the bound, unreported retry, unknown copy layer, raw network
identifier in a public artifact, non-monotonic endpoint timestamps, and one-way latency
derived from unsynchronized clocks.
