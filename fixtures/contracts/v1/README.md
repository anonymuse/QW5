# Contract fixtures v1

The `*.valid.json` files are public-safe synthetic schema and semantic examples. They
are not target-cluster, model, transport, or feasibility evidence.

[`negative-cases.json`](negative-cases.json) defines deterministic, sometimes
multi-step mutations over the valid examples and the required schema or semantic
error code. They cover referential, arithmetic, coverage, status, synchronization,
storage, and gate invariants without copying large fixtures.

[`canonical-json-v1.vectors.json`](canonical-json-v1.vectors.json),
[`tb5-wire-v1.vectors.json`](tb5-wire-v1.vectors.json),
[`tb5-evidence-v1.vectors.json`](tb5-evidence-v1.vectors.json), and
[`safetensors-parser-v1.vectors.json`](safetensors-parser-v1.vectors.json) pin exact
bytes or canonical artifact digests and named hostile outcomes. The wire file also
pins byte-exact corruptions and required parser error codes.
The TB5 evidence vectors additionally pin raw synchronization-to-attempt digest and
field reconciliation plus acyclic plan, local-control, control-index, measurement,
measurement-index, and summary resolution. The model fixtures pair a frozen
acquisition plan with its exact manifest projection; placement fixtures pair an
`UNDETERMINED` analysis with its evidence graph. SafeTensors vectors retain valid
string-map `__metadata__` and reject non-string or nested metadata values.
`tools/validate_contracts.py` rebuilds these independently and validates every schema,
positive fixture, and hostile mutation.
