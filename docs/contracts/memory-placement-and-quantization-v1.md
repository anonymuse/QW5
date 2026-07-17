# Memory placement and quantization feasibility v1

## Scope

This contract defines an M1 calculation and decision artifact. It does not quantize
weights, execute a model, validate model quality, or benchmark a kernel. The schemas
are
[`placement-evidence-graph.schema.json`](../../schemas/v1/placement-evidence-graph.schema.json)
and
[`placement-analysis.schema.json`](../../schemas/v1/placement-analysis.schema.json).

## Required inputs

Each analysis pins exact SHA-256 identities for:

- the model artifact manifest and tensor inventory;
- hardware inventories for A, B, and C;
- the relevant TB5 link summary or an explicit unavailable link input;
- the quantization layout specification;
- workload/state formulas and their source configuration;
- the gate-rule set, complete candidate-placement set, solver objective, and
  reserve/headroom policy as separate content-addressed artifacts;
- the analysis tool, QW5 commit, and dirty state; and
- every assumption or target reserve.

Each non-null input records `accepted`, `owner_approval_required`, or `rejected`.
Presence and a digest alone do not make an input decision-eligible.

The clean-node memory input conforms to
[`memory-baseline.schema.json`](../../schemas/v1/memory-baseline.schema.json). One
inventory snapshot is not a baseline. Each node requires an owner-approved plan,
ten-minute stabilization, 30 valid observations one minute apart, up to six retained
replacement attempts, and the nearest-rank fifth percentile of available bytes.
Thermal, pressure, power, Low Power Mode, clean-window status, invalid samples, and
errors remain in the artifact. The result records the actual monotonic stabilization
interval and validates every sample interval. It also carries the inventory's
`gpu.recommended_working_set_bytes` observation as separate Metal guidance; that value
is never treated as host available memory or substituted for the repeated baseline.
Fewer than 30 valid observations is not `COMPLETE`.

The primary evidence class is `ESTIMATED` for direct calculations or `SIMULATED` when
a named simulator models schedules or traffic. Measured inputs retain their own class
and do not relabel the output.

## Workload points

Analyze each model at batch size 1 and total context lengths 4,096, 32,768, and
262,144 tokens. Separate prefill high-water state from steady autoregressive decode.
For each point record prompt tokens, generated-token allowance, sequence count, cache
policy, and whether the point is a `TARGET` analysis condition rather than a supported
runtime capability.

Additional context or batch points require an explicit contract amendment. Results
are not interpolated beyond evaluated points without a labeled estimate and stated
method.

## Per-node budget

For each node calculate:

`os_reserve = physical_bytes - p05_available_baseline`

`placement_budget = physical_bytes - os_reserve - safety_reserve`

and

`headroom = placement_budget - sum(all_assigned_classes)`.

The equivalent second expression is
`placement_budget = p05_available_baseline - safety_reserve`; the OS reserve is not
subtracted twice. All terms are integer bytes and individually identified.
`safety_reserve` is an owner-approved `TARGET` frozen before analysis results are
visible. It is not inferred from aggregate physical memory or adjusted to make a
candidate fit.

Assigned classes include at minimum:

- resident source or quantized weights by tensor class;
- scale, zero-point, codebook, outlier, sparse, permutation, padding, and alignment
  metadata;
- embeddings, output head, and higher-precision exceptions;
- KV and recurrent state, router state, and per-layer persistent buffers;
- kernel scratch ranges, temporary reductions, command buffers, and allocator
  bookkeeping;
- transport send/receive rings for every concurrent message class;
- tokenizer/runtime code and control-plane state;
- artifact staging or promotion buffers actually required at runtime; and
- fragmentation allowance.

The v1 decision resolver requires exhaustive coverage of these machine-readable
memory classes before `GO`: `weights`, `quantization_metadata`, `kv_state`,
`recurrent_state`, `router_state`, `scratch`, `transport`, `allocator`, `control`,
`artifact_staging`, and `fragmentation`. A class may have zero bytes only when its
allocation cites a resolved architecture proof. More detailed tensor or runtime
classes roll up into exactly one of these decision classes without being discarded.

An unavailable scratch or state bound is represented by a declared low/high
sensitivity range. Zero is allowed only when the architecture proves the allocation
does not exist.

## Quantization candidate matrix

For each model evaluate:

1. the exact upstream representation;
2. concrete 8-, 6-, 5-, 4-, 3-, and 2-bit weight candidates only where a complete
   layout specification exists; and
3. mixed-precision candidates that state every tensor-class exception.

The pure parameter floor is recorded separately as `ESTIMATED` and may be used to
reject an impossible candidate early. A surviving floor must still include exact
metadata, padding, alignment, higher-precision tensors, state, scratch, and reserves.

For each candidate report source payload bytes, packed weight bytes, metadata bytes,
padding/alignment bytes, exception bytes, container overhead, and total bytes. The
components must reconcile exactly. If a transformed artifact exists, its measured file
size and hash are a separate input; the calculation reports any discrepancy rather
than replacing it.

## Pre-analysis contract freeze

A Sol-owned decision task must merge after the immutable tensor inventories and
before any analyzer implementation. It produces and validates these machine-readable
v1 artifacts and their schemas:

- `qw5.quantization-layout/v1`: model revision, candidate ID, eligible tensor set,
  packing word/order/endianness, bit width, group shape and axis, scale and zero-point
  dtypes/shapes/storage, padding/alignment, auxiliary storage, higher-precision
  exceptions, calibration identity when applicable, quality-evidence identity, and
  exact byte formulas;
- `qw5.formula-set/v1`: model revision/config digest, workload IDs, prefill/decode
  state formulas, checked integer operations and rounding, cache policy, scratch and
  persistent-buffer bounds, transport message formulas, allocator/fragmentation
  policy, safety-reserve target, and every unresolved input;
- `qw5.placement-gate-rule-set/v1`: gate IDs, applicability predicates,
  pass/fail/unresolved derivations, evidence requirements, and prohibited claims;
- `qw5.placement-candidate-set/v1`: every deterministic candidate and placement ID
  eligible for analysis;
- `qw5.placement-solver-objective/v1`: objective ordering and deterministic tie-breaks;
- `qw5.reserve-headroom-policy/v1`: owner-approved safety reserves, headroom formula,
  rounding, and rejection conditions;
- `qw5.text-subset-dependency/v1` for Qwen3.5 when proposed: complete-manifest digest,
  included/excluded tensors and files, loader and text-path dependency rules, proof
  status, unresolved dependencies, and prohibited claims; and
- model-specific gate rules that map each missing formula, layout, classification,
  quality input, or subset dependency to `passed`, `failed`, or `unresolved`.

Each artifact carries canonical identity, evidence class, positive and hostile
fixtures, and semantic validation. Only concrete candidates with complete layouts
enter the analyzer. A missing 8-, 6-, 5-, 4-, 3-, or 2-bit layout is reported as
`UNDETERMINED`; a bit-width label is never expanded by Terra into a format decision.

## Placement rules

- Every physical byte is assigned once. Shared storage uses one owner plus references.
- Per-node tensor assignments list exact tensor or deterministic tensor-set IDs.
- Node A may compute and own weights; no rule excludes it because it is control plane.
- Network edges name actual source, destination, message class, payload bytes,
  frequency model, and link-profile digest. Expert count is not packet count.
- Direct B-C traffic does not route through A unless a separate scenario explicitly
  evaluates a relay and labels it.
- Prefill and decode placements and traffic are separate.
- SSD is absent from the resident budget unless a separately identified promotion
  scenario accounts for latency, staging buffers, and measured cold-tier behavior.
- A node with negative headroom fails the placement even if aggregate headroom is
  positive.
- `text_subset_proven` is applicable only to `text_execution_subset`. A complete-
  artifact analysis records it as not applicable with a reason and no proof input.
- `transport_profile_available` is applicable exactly when a candidate has cross-node
  traffic. A network-free candidate records it as not applicable; a networked
  candidate requires an accepted link-summary input.

## Model-specific analyses

### Qwen3-Coder-Next

Evaluate single-node candidates on A, B, and C and distributed candidates using A+B,
A+C, B+C, and A+B+C. This enumerates feasibility; it does not assume the two M5 Max
nodes are faster. Tensor classes and state formulas come only from the pinned model
configuration and inventory.

A memory `GO` recommends the next correctness or artifact task. It does not claim a
working model or acceptable quantization quality.

### Qwen3.5-397B-A17B

Evaluate A+B+C for the complete upstream artifact. Evaluate a text-execution subset
only if the artifact contract's exclusion gate passes. Preserve the existing
**ESTIMATED** 99.25 GB two-bit language-parameter floor as a lower bound, then replace
it for decisions with concrete candidate totals.

Any candidate must expose per-node headroom after all runtime and operating-system
classes. A candidate that fits memory but lacks quality evidence, implementable
kernels, or bounded scratch remains `UNDETERMINED`.

## Decision record

Each scenario has:

- `decision_scope: m1_memory_placement`;
- outcome `GO`, `NO_GO`, or `UNDETERMINED`;
- applicable, passed, failed, unresolved, and not-applicable gate IDs;
- one reasoned evaluation for every gate, with a frozen rule ID and evidence-node IDs
  when applicable;
- exact evidence and assumption references;
- the next permitted task; and
- explicit claims that remain prohibited.

`GO` means only that the named next task is justified. Deployment feasibility remains
unproven until correctness, quality, kernels, transport, thermal behavior, and runtime
stability have their own evidence.

The required gate set is exhaustive. Applicable and not-applicable gates are disjoint
and exhaustive; applicable gates partition into passed, failed, and unresolved.
Applicability derives from component scope and network edges, never from the desired
outcome. Passed and failed evaluations require a frozen rule and resolved evidence
nodes. A not-applicable evaluation requires a machine-readable reason and must not
carry a rule or success evidence.

The outcome is recomputed rather than trusted from a producer assertion. `NO_GO`
follows from a failed gate or negative headroom. `UNDETERMINED` follows from unresolved
gates or any non-accepted input. `GO` requires every applicable gate passed, every
lineage input accepted, nonnegative headroom on every node, exhaustive memory-class
coverage, resolved quality evidence when that gate passes, and a non-null next task.
A not-applicable gate has a reason and cannot carry success evidence.

## Evidence-graph resolution

Every analysis references one canonical `qw5.placement-evidence-graph/v1` digest. The
graph binds the model/workload/candidate identity; every input role's schema, evidence
class, acceptance state, relative path, and digest; every gate's rule and evidence
nodes; every allocation's formula and evidence nodes; and the exhaustive memory-class
set. The graph carries the analysis identity fields rather than the analysis digest,
so the relationship is acyclic: the graph is frozen first and the analysis then binds
its digest.

Decision consumption is a bundle operation. The resolver recomputes the graph digest,
resolves every node by path, recomputes its canonical digest, validates its declared
schema and semantic rules, reconciles evidence classes and analysis projections, and
then recomputes placement arithmetic and gates. A standalone analysis is never
permitted to establish `GO`, even if its producer writes accepted inputs and passed
gates. Any unresolved path, digest, schema, semantic failure, gate projection,
allocation projection, or required evidence node blocks `GO`. Until M1-14 freezes the
remaining input schemas and registers deterministic evaluators for every passed gate
rule, a positive placement decision is therefore intentionally unavailable. Merely
adding a schema or producer-supplied rule ID does not register an evaluator; the
planning fixture remains `UNDETERMINED`.

## Acceptance and negative cases

The analysis must reject missing model, inventory, baseline, layout, formula, subset,
or link identities; aggregate-only memory; double-subtracted OS reserve; negative or
unreconciled byte components; duplicate storage assignment; omitted safety reserve;
implicit zero scratch; unknown tensor-class placement; packet counts multiplied by
expert count; combined prefill/decode rates; mutable model revision; quantization by
bit-width label alone; overlapping, incomplete, or vacuously not-applicable gate sets;
missing rule/candidate/objective/reserve lineage; a subset proof applied to a complete
artifact; network traffic without an accepted link summary; `GO` with negative
headroom, incomplete memory-class coverage, an unresolved evidence graph, unresolved
gates, or unaccepted lineage; producer-asserted `GO` outside the resolver; quality
inferred from size; and a capability claim derived from an estimated placement.
