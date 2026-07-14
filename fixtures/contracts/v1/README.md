# Contract fixtures v1

The `*.valid.json` files are public-safe synthetic schema and semantic examples. They
are not target-cluster, model, transport, or feasibility evidence.

[`negative-cases.json`](negative-cases.json) defines deterministic, sometimes
multi-step mutations over the valid examples and the required schema or semantic
error code. They cover referential, arithmetic, coverage, status, synchronization,
storage, and gate invariants without copying large fixtures.

[`canonical-json-v1.vectors.json`](canonical-json-v1.vectors.json) and
[`tb5-wire-v1.vectors.json`](tb5-wire-v1.vectors.json) pin exact bytes and SHA-256.
The wire file also pins byte-exact corruptions and required parser error codes.
`tools/validate_contracts.py` rebuilds these independently and validates every schema,
positive fixture, and hostile mutation.
