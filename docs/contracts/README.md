# M1 contracts

These contracts define the evidence QW5 must collect before M1 can make placement
decisions. They do not implement probes, download models, execute benchmarks, or claim
model feasibility.

## Contract set

- [`canonical-json-v1.md`](canonical-json-v1.md) freezes exact JSON bytes for every
  artifact identity and supplies independent hash vectors.
- [`hardware-inventory-v1.md`](hardware-inventory-v1.md) defines public-safe node and
  link facts and the unavailable/error model.
- [`thunderbolt5-measurement-v1.md`](thunderbolt5-measurement-v1.md) freezes the six
  directed paths, simultaneous scenarios, payloads, timing, integrity, copy, error,
  and thermal rules.
- [`thunderbolt5-wire-v1.md`](thunderbolt5-wire-v1.md) freezes exact handshake,
  payload-generation, frame, digest-trailer, and acknowledgement bytes.
- [`model-artifact-and-tensor-inventory-v1.md`](model-artifact-and-tensor-inventory-v1.md)
  defines immutable upstream identity, file hashes, tensor metadata, and quantization
  metadata.
- [`memory-placement-and-quantization-v1.md`](memory-placement-and-quantization-v1.md)
  defines the two-model feasibility analysis and decision vocabulary.

The contract set includes 14 v1 schemas: hardware inventory, clean-node memory
baseline, TB5 run plan, route proof, raw local control, local-control index, raw
synchronization evidence, raw measurement, measurement index, link summary, model
manifest, SafeTensors parser profile, tensor inventory, and placement analysis.

The corresponding JSON Schemas are under [`../../schemas/v1`](../../schemas/v1), with
public-safe synthetic examples and negative fixtures under
[`../../fixtures/contracts/v1`](../../fixtures/contracts/v1).

## Versioning

Each instance has a `schema` value in the form `qw5.<contract>/v1`. A breaking field,
unit, identity, evidence, canonical-byte, or semantic change requires `v2`. Additive
fields may be proposed only when old readers remain correct; schemas reject unknown
properties by default so an additive change still receives review and coordinated
reader updates.

The contract version is independent of the producing tool version. Both are recorded.
An artifact is never silently rewritten under the same digest or schema identity.

## Common identity and evidence rules

- Digests are lowercase, 64-character SHA-256 values over the exact
  `qw5-json-c14n-v1` bytes for JSON artifacts and exact raw bytes for non-JSON files.
- QW5 commits and immutable Hugging Face revisions are full 40-character hexadecimal
  object IDs.
- Timestamps use UTC RFC 3339 with a `Z` suffix.
- Byte quantities are integer bytes. Rates use bytes per second. Durations use integer
  nanoseconds unless the field explicitly names another unit.
- Each artifact has one primary evidence class. Mixed-class reports label every input
  and output separately.
- `MEASURED` means the target value was observed by the recorded procedure.
  `SIMULATED`, `ESTIMATED`, and `TARGET` never become measured because they consume a
  measured input.
- Schema fixtures use synthetic node, model, and digest values and set
  `artifact_role` to `schema_fixture`.

## Public-safety rules

Committed instances use node aliases A, B, and C. They exclude serial numbers,
hardware UUIDs, MAC addresses, IP addresses, hostnames, usernames, home paths, mount
paths, credentials, tokens, and unredacted system-profiler or registry dumps. Source
records name the command or API and its version without including private arguments or
raw output. Large raw artifacts stay outside Git in content-addressed storage and are
referenced by a reviewed public-safe manifest.

## Validation rule

Every schema must validate against the draft 2020-12 meta-schema. Every example must
pass its declared schema and semantic validator. Each negative mutation names the
required schema or semantic error and must be rejected. Exact canonical, TB5
wire/evidence, and SafeTensors vectors must reproduce their bytes, canonical digests,
projections, and named hostile failures. CI installs the pinned validation-only
dependencies from `requirements/contract-validation.txt` and runs
`tools/validate_contracts.py`; syntax-only parsing is insufficient.
