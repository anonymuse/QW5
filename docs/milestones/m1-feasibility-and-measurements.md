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

1. This M0 contract-completion and M1 planning pull request is accepted and merged,
   including ADRs 0004 through 0007, exact-byte vectors, v1 contracts, and the
   repository semantic validator.
2. The active task is created from then-current `main` with disjoint owned paths,
   frozen inputs, acceptance tests, and a task-owned provenance record.
3. CI passes draft 2020-12 meta-validation, positive fixtures, semantic invariants,
   hostile mutations, the generated 108-control and 246-cell evidence bundles, and
   exact canonical/wire/TB5/SafeTensors vectors.
4. The project owner separately approves any remote-node access, model download,
   external scratch storage, or costly benchmark required by that task.
5. Stable public aliases A, B, and C are mapped privately to the intended machines;
   no private mapping is committed.
6. The M1 task records the exact QW5 commit and has no unrelated dirty changes.
7. Any selected model revision is a full immutable commit. A change from the source
   revisions reviewed by ADR-0001 receives explicit Sol review and owner approval.
8. Before physical cluster work, the owner approves the memory-baseline plan and the
   TB5 plan's seed/order, socket request, empirical-inclusion and thermal thresholds,
   local controls, stream duration/byte caps, expected data volume, exclusive window,
   and access method.
9. Before placement results are consumed, the owner approves the safety-reserve and
   headroom policy, concrete quantization candidates, model-specific formulas/gates,
   and any Qwen3.5 text-subset dependency rule.

Failure of an entry criterion blocks only the dependent task. It is not permission to
substitute a declared or estimated value.

## Required deliverables

1. **Inventory tooling and node manifests:** one v1 public-safe inventory for A, B,
   and C plus source/error records for every required fact.
2. **Memory baselines:** one preregistered repeated clean-node baseline for A, B, and
   C, preserving all samples, invalid observations, and reserve derivation.
3. **Topology proof:** a public-safe mapping of the three direct pair links and the
   route-verification artifact used by the benchmark, without network identifiers.
4. **Thunderbolt application-path evidence:** owner-approved run plan, exact wire
   vectors, three-node local controls, all six directed solo paths and every required
   simultaneous scenario, with raw attempts, local-control and measurement indexes,
   and a raw-reconciled 246-cell summary.
5. **Model artifact manifests:** complete immutable file identities for both selected
   model revisions, including canonical revision listings, frozen expected paths,
   tokenizer, configuration, templates, licenses, weight indexes, and weight files
   consumed by analysis.
6. **Tensor inventories:** an accepted SafeTensors parser profile, deterministic
   tensor-level metadata, and revision-specific classification rules, with unresolved
   classifications explicit.
7. **Pre-analysis decisions:** accepted quantization layouts, formula set, gate-rule
   set, safety-reserve/headroom policy, complete placement-candidate set, solver
   objective, and any text-subset dependency proof.
8. **Placement analyses:** per-node budgets and assignments for both models across the
   declared workload matrix, preserving assumptions and sensitivity ranges.
9. **Gate report:** one decision per model and placement scenario, limitations,
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

All schemas, semantic rules, exact vectors, task boundaries, and applicable owner
permissions are accepted. Failure blocks execution.

### G1 — Inventory completeness

Each required fact is `available`, `unavailable`, or `error` with a source. Node and
link identity are unambiguous using public aliases. Each node also has 30 accepted
clean-node memory samples with validated stabilization/cadence, separately recorded
Metal working-set guidance, and a reconciled fifth-percentile baseline. Missing facts
or an incomplete baseline make dependent calculations `UNDETERMINED`.

### G2 — Link evidence validity

Every one of the 246 cells has the planned valid sample count or a preserved failed,
aborted, or undetermined report. Route proof, local controls, byte/sequence/checksum
reconciliation, requested/effective sockets, endpoint timing, copy evidence, errors,
and thermal conditions are present. Seed-derived schedule indexes reconcile for every
cell. Every summary cell resolves through the frozen measurement index and reconciles
identity, status, metrics, exclusions, errors, and thermal regimes to raw evidence.
Simultaneous attempts use the ADR-0007 empirical rule: maximum pre-attempt control RTT
at most 1 ms and coordinator-observed score at most 10 ms. The score is not an
actual-start or one-way-timing result. Every included attempt resolves its raw
synchronization digest and projection. Stream targets, caps, and application-buffer
totals reconcile. A failed cell is not silently dropped.

### G3 — Artifact and tensor completeness

Both models have immutable revisions, two matching hash passes for every consumed
file, canonical revision-listing digests, exact expected-path/file-table equality,
derived completeness, revision-specific classification rules, and deterministic tensor
inventories. The parser profile is pinned to an immutable upstream format reference;
scalar `shape: []`, safety limits, exact supported dtypes, strict UTF-8, duplicate-
member rejection, and checked offsets/arithmetic are tested. File, layer, expert,
dtype, class, and storage totals reconcile. Duplicate names, reversed/out-of-range/
overlapping/holed storage, unknown dtypes, or missing files fail the gate.

### G4 — Representational-size gate

Each candidate quantization is a Sol-approved concrete layout whose weight, metadata,
padding, alignment, and higher-precision exception bytes reconcile. Formula-set,
reserve/headroom, gate-rule, candidate-set, solver-objective, and applicable text-
subset inputs are immutable and accepted before analyzer implementation. A parameter-
count floor cannot pass this gate.

### G5 — Per-node placement gate

For each workload scenario, all weights, state, scratch ranges, transport buffers,
staging, fragmentation, and operating-system reserve are assigned. Headroom is
nonnegative on every node under the declared rule. Aggregate-memory fit alone fails.

### G6 — Model recommendation

For each model, Sol issues one scoped result:

- `GO`: evidence supports the named next task only;
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

- deliverables 1 through 9 exist with immutable identities;
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
