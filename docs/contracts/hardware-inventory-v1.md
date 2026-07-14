# Hardware inventory contract v1

## Purpose

`qw5.hardware-inventory/v1` records facts QW5 probed on one node. It does not repeat
the owner-declared chip, memory, storage, or topology as if they were observations.
The operator supplies only the public alias A, B, or C; the private alias-to-machine
mapping remains outside the artifact.

The JSON Schema is
[`hardware-inventory.schema.json`](../../schemas/v1/hardware-inventory.schema.json).
Artifact identity uses [`qw5-json-c14n-v1`](canonical-json-v1.md). The schema binds
every required fact ID to its exact value type and unit; the repository semantic
validator enforces uniqueness, references, peer coverage, and route relationships
that JSON Schema cannot express portably.

## Artifact identity

The artifact records its role, evidence class, collection interval, tool name/version
and executable SHA-256, QW5 commit and dirty flag, node alias, source table, ordered
fact table, collection errors, and applied redactions. A production capture uses
`artifact_role: inventory` and `evidence_class: MEASURED`; the repository example is a
synthetic `schema_fixture`.

Each fact has:

- a stable `fact_id` from the table below;
- `status` equal to `available`, `unavailable`, or `error`;
- a typed `value` and `unit` only when available;
- a `source_ref` naming a read-only API or command in the source table;
- a UTC observation timestamp; and
- an error code/message safe for publication when the status is `error`.

An unavailable fact is not an error when the platform exposes no supported public
source. Neither state receives a fallback value.

## Required facts

The probe emits every fact ID exactly once and sorts facts by `fact_id`.

| Fact ID | Type and unit | Why it is required |
| --- | --- | --- |
| `clock.monotonic_name` | string, `none` | Identifies the benchmark clock |
| `clock.monotonic_resolution_ns` | integer, `ns` | Bounds timer resolution |
| `clock.sync_method` | string, `none` | Describes wall-clock coordination |
| `clock.sync_uncertainty_ns` | integer, `ns` | Prevents unsupported one-way timing |
| `cpu.efficiency_core_count` | integer, `count` | Separates heterogeneous CPU capacity |
| `cpu.logical_core_count` | integer, `count` | Records scheduler-visible CPUs |
| `cpu.performance_core_count` | integer, `count` | Separates heterogeneous CPU capacity |
| `cpu.physical_core_count` | integer, `count` | Records physical CPU capacity |
| `gpu.core_count` | integer, `count` | Avoids inferring GPU configuration from chip name |
| `gpu.device_count` | integer, `count` | Detects the execution-device set |
| `gpu.device_name` | string, `none` | Identifies the public Metal device class |
| `gpu.has_unified_memory` | boolean, `none` | Verifies the exposed memory model |
| `gpu.recommended_working_set_bytes` | integer, `bytes` | Records the API's current allocation guidance |
| `hardware.model_identifier` | string, `none` | Public Apple model class; never a serial number |
| `memory.available_bytes` | integer, `bytes` | Captures collection-time availability |
| `memory.page_bytes` | integer, `bytes` | Supports alignment and allocation analysis |
| `memory.physical_bytes` | integer, `bytes` | Verifies installed physical memory |
| `memory.pressure_level` | string, `none` | Names the collection-time pressure regime |
| `os.build` | string, `none` | Pins the operating-system build |
| `os.kernel_release` | string, `none` | Pins the kernel environment |
| `os.product_version` | string, `none` | Records the public macOS version |
| `power.low_power_mode` | boolean, `none` | Detects a known performance regime |
| `power.source` | string, `none` | Distinguishes AC, battery, UPS, or unavailable |
| `soc.name` | string, `none` | Verifies the SoC reported by a supported source |
| `storage.available_important_bytes` | integer, `bytes` | Bounds space QW5 may responsibly use |
| `storage.internal` | boolean, `none` | Distinguishes the declared internal cold tier |
| `storage.total_bytes` | integer, `bytes` | Verifies storage capacity |
| `thermal.state` | string, `none` | Captures the platform thermal regime |
| `thunderbolt.controller_count` | integer, `count` | Supports contention interpretation |
| `tool.zig_version` | string, `none` | Pins the host toolchain |

`clock.sync_uncertainty_ns`, GPU core count, memory pressure, power source, and
Thunderbolt controller count may be unavailable on a supported public interface. They
remain required records precisely so their absence cannot disappear.

## Link routes

The `links` array has one entry for each direct peer visible from the node. It is
sorted by `peer_alias` and contains:

- peer alias and a local public route alias such as `A-B`;
- `status`: `available`, `unavailable`, or `error`;
- whether the route is active and direct according to the recorded source;
- public-safe controller and port aliases assigned by the probe for that capture;
- negotiated rate, width, generation, and lane details only when a public source
  exposes them, each with its own status and source;
- a source reference and observation time.

Raw interface names may be retained locally for execution but are normalized to the
route alias before publication. MAC addresses, IP addresses, registry paths, serials,
and hardware UUIDs are forbidden.

## Sources and determinism

A source entry records a stable ID, kind (`api` or `command`), public name, provider,
API/command version when known, and a sanitized invocation description. The probe
must prefer stable public APIs. If it uses a command, it captures exit status and
parses only the required fields; raw dumps are not committed.

The expected implementation sources include Foundation `ProcessInfo` for operating
and thermal/power context, Metal device properties for exposed GPU facts, read-only
volume capacity APIs for storage, and supported system calls or IOKit queries for
hardware and Thunderbolt facts. The implementation task must test each adapter behind
a mockable source boundary. API choice does not authorize private frameworks.

Relevant Apple documentation includes
[`ProcessInfo`](https://developer.apple.com/documentation/foundation/processinfo),
[`isLowPowerModeEnabled`](https://developer.apple.com/documentation/foundation/processinfo/islowpowermodeenabled),
and [checking volume storage capacity](https://developer.apple.com/documentation/foundation/checking-volume-storage-capacity).

Sources sort by `source_id`; fact members serialize in canonical member-name order;
links by `peer_alias`; errors by `code`. Collection timestamps and live availability
values are expected to vary, but repeated serialization of the same in-memory record
must produce identical canonical bytes. Duplicate source IDs and dangling
`source_ref` values fail semantic validation even when the source objects differ in
other fields.

`links` has exactly the other two node aliases, never the collecting node. Its route
alias is the sorted physical pair (`A-B`, `A-C`, or `B-C`). If link enumeration itself
cannot run safely, `links` is empty and `collection_errors` contains the public-safe
failure; a partial peer set is invalid. An `error` link or optional observation carries
an error object, while an `unavailable` state does not.

## Acceptance and negative cases

A valid production inventory must:

- contain all required fact IDs exactly once;
- include exactly two peer-link records for the declared three-node mesh or an
  explicit top-level collection error;
- use only public aliases;
- provide sources for every available or failed observation;
- report no forbidden field or raw private identifier;
- pass the v1 schema and privacy scan; and
- pass `tools/validate_contracts.py`, including schema and semantic validation.

Tests must reject a missing required fact, duplicate fact ID, available fact without a
value, unavailable fact with an invented value, invalid unit/type pair, unknown node
alias, private identifier field, malformed digest, dirty flag omission, and
non-deterministic duplicate source ID.
