# M1 feasibility and measurements

- **Status:** Proposed contract; no M1 execution has begun
- **Decision owner:** Sol for architecture, interpretation, and final integration
- **Implementation routing:** Only the accepted, bounded tasks in
  [`../coordination/m1-task-decomposition.md`](../coordination/m1-task-decomposition.md)

## Objective

M1 will replace hardware, link, artifact-size, and placement assumptions with
reviewable evidence for `Qwen/Qwen3-Coder-Next` and
`Qwen/Qwen3.5-397B-A17B`. Its product is a set of trustworthy inputs and scoped
go/no-go decisions for later work, not inference or a cluster capability claim.

## Entry criteria

All criteria must hold before physical or model-artifact execution begins:

1. This planning pull request is accepted and merged, including ADRs 0004 through
   0006 and all v1 contracts.
2. The active task is created from then-current `main` with disjoint owned paths,
   frozen inputs, acceptance tests, and a task-owned provenance record.
3. Schemas pass draft 2020-12 meta-validation; valid and negative fixtures behave as
   documented.
4. The project owner separately approves any remote-node access, model download,
   external scratch storage, or costly benchmark required by that task.
5. Stable public aliases A, B, and C are mapped privately to the intended machines;
   no private mapping is committed.
6. The M1 task records the exact QW5 commit and has no unrelated dirty changes.
7. Any selected model revision is a full immutable commit. A change from the source
   revisions reviewed by ADR-0001 receives explicit Sol review and owner approval.

Failure of an entry criterion blocks only the dependent task. It is not permission to
substitute a declared or estimated value.

## Required deliverables

1. **Inventory tooling and node manifests:** one v1 public-safe inventory for A, B,
   and C plus source/error records for every required fact.
2. **Topology proof:** a public-safe mapping of the three direct pair links and the
   route-verification artifact used by the benchmark, without network identifiers.
3. **Thunderbolt application-path evidence:** all six directed solo paths and every
   required simultaneous scenario, with raw per-sample artifacts and a reviewed
   summary.
4. **Model artifact manifests:** complete immutable file identities for both selected
   model revisions, including tokenizer, configuration, templates, licenses, weight
   indexes, and weight files consumed by analysis.
5. **Tensor inventories:** deterministic tensor-level metadata and semantic
   classification, with unresolved classifications explicit.
6. **Quantization candidates:** concrete storage layouts and reproducible size
   calculations; transformed artifacts and quality results are separate evidence and
   are not required to exist merely to evaluate a theoretical candidate.
7. **Placement analyses:** per-node budgets and assignments for both models across the
   declared workload matrix, preserving assumptions and sensitivity ranges.
8. **Gate report:** one decision per model and placement scenario, limitations,
   negative results, unresolved questions, and a recommendation for the next task.

## Evidence requirements

Every deliverable follows [`../benchmarks/methodology.md`](../benchmarks/methodology.md)
and ADR-0004. Published summaries link exact input digests and retain individual
samples. Exclusions are declared before summary statistics are calculated. Median,
dispersion, tails, sample count, failures, and thermal/power regimes are reported;
best-run-only reporting is prohibited.

The evidence classes remain separate:

| Class | M1 examples | Forbidden interpretation |
| --- | --- | --- |
| `MEASURED` | Probed memory bytes; file hashes; receiver bytes and duration | Does not prove a model runs |
| `SIMULATED` | Placement or traffic simulator output | Is not target-cluster runtime behavior |
| `ESTIMATED` | Quantized byte calculation; state or scratch sensitivity range | Is not measured allocation or quality |
| `TARGET` | Required headroom or acceptance threshold | Is not an achieved result |

## Decision gates

### G0 — Contract readiness

All schemas, fixtures, task boundaries, and owner permissions are accepted. Failure
blocks execution.

### G1 — Inventory completeness

Each required fact is `available`, `unavailable`, or `error` with a source. Node and
link identity are unambiguous using public aliases. Missing facts needed by a later
calculation make that calculation `UNDETERMINED`.

### G2 — Link evidence validity

Every solo and simultaneous cell required by the v1 protocol has the planned valid
sample count or a preserved failure report. Route proof, byte counts, sequence,
checksums, timing, copy telemetry, errors, and thermal conditions are present. A failed
cell is not silently dropped.

### G3 — Artifact and tensor completeness

Both models have immutable revisions, complete consumed-file SHA-256 identities, and
deterministic tensor inventories. The tensor byte totals reconcile exactly to indexed
storage ranges. Duplicate names, overlaps, holes where the source format forbids them,
unknown dtypes, or missing files fail the gate.

### G4 — Representational-size gate

Each candidate quantization is a concrete layout whose weight, metadata, padding,
alignment, and higher-precision exception bytes reconcile. A parameter-count floor
may prioritize work but cannot pass this gate.

### G5 — Per-node placement gate

For each workload scenario, all weights, state, scratch ranges, transport buffers,
staging, fragmentation, and operating-system reserve are assigned. Headroom is
nonnegative on every node under the declared rule. Aggregate-memory fit alone fails.

### G6 — Model recommendation

For each model, Sol issues one scoped result:

- `GO`: evidence supports the named next task only;
- `CONDITIONAL_GO`: named evidence remains before the next task can complete;
- `NO_GO`: the proposed placement fails a stated constraint; or
- `UNDETERMINED`: required evidence is unavailable or contradictory.

No M1 result states that inference, quality, throughput, or long-context operation has
been demonstrated.

## Required workload matrix

Both models are analyzed for batch size 1 at minimum at 4,096, 32,768, and 262,144
total context tokens, with prefill and decode state separated. These are analysis
points, not supported-context claims. Additional points require a new declared input.
KV, recurrent state, routing buffers, transport buffers, and scratch are calculated
from the exact pinned architecture configuration or left unresolved; they are never
inferred from a different model.

Qwen3.5 analysis includes the complete upstream artifact. A text-execution subset is
an additional scenario only after a reviewed dependency analysis proves each excluded
vision tensor is not needed by the text path.

## Exit criteria

M1 is complete when:

- deliverables 1 through 8 exist with immutable identities;
- gates G0 through G6 have explicit outcomes for both models;
- all required checks and public-safety scans pass;
- negative and invalid results are retained;
- accepted architectural consequences are recorded in ADRs;
- the board is reconciled and no M1 task remains ambiguously active; and
- the project owner approves or rejects the recommended next physical or
  implementation step.

M1 may exit successfully with `NO_GO` or `UNDETERMINED` for Qwen3.5-397B. Honest
infeasibility is a valid milestone result.

## Open questions preserved for evidence

- Which relevant GPU and Thunderbolt properties are exposed by stable public APIs on
  the actual macOS build?
- Can kernel/hardware copy activity be observed with sufficient fidelity, or must it
  remain unavailable?
- Which exact upstream revisions will the owner authorize for artifact acquisition?
- Which concrete quantization layouts deserve later quality evaluation?
- What scratch and state bounds will later kernels require?
- Does any simultaneous-link pattern expose shared-controller or thermal contention?

None of these questions is answered by this planning contract.
