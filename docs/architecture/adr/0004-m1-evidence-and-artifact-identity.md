# ADR-0004: M1 evidence and artifact identity

- **Status:** Proposed for acceptance with the M0 contract-completion and M1 planning pull request
- **Date:** 2026-07-14
- **Decision owners:** Project owner and M0 contract-completion/M1 planning task

## Context

M1 combines hardware observations, transport measurements, upstream model files,
tensor metadata, calculations, and decision reports. A path name or mutable upstream
branch cannot prove which inputs produced a result. A single report can also become
misleading if measured inputs, simulations, estimates, and targets lose their labels.

The repository needs contracts that are reviewable without publishing credentials,
serial numbers, network addresses, home paths, or other machine-specific identifiers.

## Decision

M1 machine-readable contracts use JSON Schema draft 2020-12 and carry an explicit
`schema` identifier. A breaking semantic or structural change creates a new schema
major version; an existing version is not silently redefined.

Every durable artifact records:

- its role, schema version, creation time, producing tool identity, QW5 commit, and
  dirty-state flag;
- exactly one primary evidence class: `MEASURED`, `SIMULATED`, `ESTIMATED`, or
  `TARGET`;
- SHA-256 identities for every consumed artifact and for the exact bytes of every
  produced file when referenced by another artifact;
- stable public aliases such as nodes A, B, and C instead of private machine or
  network identifiers;
- explicit `unavailable` and `error` states rather than invented defaults; and
- declared assumptions and exclusions where the artifact is simulated or estimated.

An artifact may cite inputs from other evidence classes, but it does not inherit or
upgrade their class. In particular, a placement calculation that consumes measured
inventory remains `ESTIMATED` or `SIMULATED`; a desired threshold remains `TARGET`;
and a schema fixture is never published as a cluster measurement.

SHA-256 for JSON artifacts is computed over the exact `qw5-json-c14n-v1` bytes: UTF-8
without BOM or trailing newline, NFC text, unique member names sorted by Unicode scalar
value, minimal fixed escaping, no whitespace, and integer-only numbers in the declared
range. Non-JSON files are hashed as exact raw bytes. A manifest does not contain a
self-referential digest; its parent index, report, or sidecar records the digest.
Exact canonicalization and wire vectors pin expected bytes and hashes.

Draft 2020-12 structure is one validation layer. Versioned repository semantic
validation additionally enforces uniqueness by stable ID, referential integrity,
coverage matrices, arithmetic reconciliation, storage ranges, status transitions,
and decision-gate logic. Positive fixtures and mutation-based hostile vectors run in
CI with pinned validation dependencies.

## Public-safety boundary

Committed artifacts must not contain serial numbers, hardware UUIDs, MAC addresses,
raw IP addresses, usernames, hostnames, home or mount paths, credentials, tokens, or
unredacted command output. A private operator mapping may associate node aliases with
machines during collection, but it is neither an M1 input nor a committed artifact.

## Consequences

- Contract schemas and public-safe examples live under `schemas/` and
  `fixtures/contracts/`.
- Contract semantics live in the versioned repository validator and cannot be
  reinterpreted independently by a later producer.
- Large raw outputs may live in content-addressed external storage, referenced by a
  committed public-safe manifest.
- Missing data can make a gate `undetermined`; it may not be replaced with a marketing
  specification or owner recollection.
- Schema examples carry `artifact_role: schema_fixture` and synthetic labels so they
  cannot be mistaken for target-cluster evidence.

## References

- [JSON Schema draft 2020-12](https://json-schema.org/draft/2020-12/json-schema-core)
- [NIST FIPS 180-4 Secure Hash Standard](https://csrc.nist.gov/pubs/fips/180-4/upd1/final)
