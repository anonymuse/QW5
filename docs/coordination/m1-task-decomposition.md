# M1 ordered pull-request decomposition

This queue begins only after the M1 planning pull request is accepted and merged. Each
item is a separate branch, worktree, provenance record, and draft pull request from
then-current `main`. Merge in numeric order. A task may be split further by Sol, but
combining tasks requires an updated durable scope and owner approval.

No task may edit a v1 contract while implementing it. A discovered contract defect
returns to a separate Sol contract-amendment PR; implementation does not silently
reinterpret the schema.

## Routing summary

| Order | Task | Route | Readiness after planning acceptance |
| --- | --- | --- | --- |
| 01 | Public-safe hardware inventory probe | Terra / Medium | **First Terra-ready task** |
| 02 | Inventory fixture and negative-case expansion | Luna / Low | Ready after 01 |
| 03 | TB5 harness implementation and loopback validation | Terra / High | Ready after 01 |
| 04 | Three-node inventory capture | Terra / Medium | Permission-gated after 01–03 |
| 05 | TB5 solo-path capture | Terra / High | Physical-access-gated after 04 |
| 06 | TB5 simultaneous-link capture | Terra / High | Physical-access-gated after 05 |
| 07 | Immutable model revision and acquisition decision | Sol / High | Owner-decision-gated after 06 |
| 08 | Model manifest and tensor inspector | Terra / High | Ready after 07 |
| 09 | Qwen3-Coder-Next artifact and tensor manifests | Terra / High | Download-gated after 08 |
| 10 | Qwen3.5-397B-A17B artifact and tensor manifests | Terra / High | Storage/download-gated after 09 |
| 11 | Placement and quantization-size analyzer | Terra / High | Ready after 10 |
| 12 | Integrated M1 gate report | Sol / Extra High | Ready after all evidence tasks |

Only task 02 routes to Luna because it is exact, repetitive fixture expansion with no
design authority. Sol owns model selection, interpretation, architecture changes, and
final integration. No task uses Ultra or parallel agents.

## M1-01 — Public-safe hardware inventory probe

- **Objective:** Implement a read-only, mockable producer for
  `qw5.hardware-inventory/v1` and deterministic serialization without contacting
  remote nodes.
- **Recommended model and reasoning:** GPT-5.6 Terra, Medium. The contract and tests
  are frozen; the work is bounded platform integration with moderate API edge cases.
- **Owned paths:** `src/inventory/`, inventory-specific tests under `src/`,
  `fixtures/inventory/`, and the minimum required `src/main.zig`, `src/root.zig`, and
  `build.zig` wiring. The v1 schema and contract are read-only inputs.
- **Frozen inputs and contracts:** ADR-0004; hardware inventory v1 prose, schema, valid
  fixture, required fact IDs, deterministic order, and privacy denylist; Zig 0.16.0;
  public Apple APIs only.
- **Dependencies and merge order:** First after this planning PR. No M1 task may merge
  ahead of it.
- **Permissions or physical access:** Local read-only hardware/API access on one Apple
  silicon development Mac. No SSH, remote mutation, elevated privileges, or cluster
  capture.
- **Acceptance and negative tests:** Valid synthetic adapters emit the committed
  schema; identical in-memory inputs serialize byte-identically; unavailable and error
  facts survive; all required facts are present. Reject missing/duplicate facts,
  value-on-unavailable, source mismatch, serial/UUID/MAC/IP/hostname/path leakage,
  unsupported private API, malformed tool identity, and write attempts.
- **Durable artifacts:** Inventory module, mock source interfaces, deterministic unit
  fixtures, local dry-run instructions, and PR provenance.
- **Explicit non-goals:** Collecting A/B/C, configuring links, benchmarking, inferring
  unavailable facts, or changing the v1 contract.

This is the first task ready for GPT-5.6 Terra once the planning PR is accepted. It is
not executed by the planning task.

## M1-02 — Inventory fixture and negative-case expansion

- **Objective:** Mechanically expand the exact M1-01 adapter matrix across available,
  unavailable, error, redaction, and deterministic-order cases.
- **Recommended model and reasoning:** GPT-5.6 Luna, Low. Expected inputs and outputs
  are enumerated; the work is repetitive fixture generation with no architecture.
- **Owned paths:** New fixture files under `fixtures/inventory/` and their exact
  expected-failure index. No production source or schema edits.
- **Frozen inputs and contracts:** M1-01 source adapter list and serializer; v1 schema;
  a Sol-reviewed matrix naming each fixture, input, expected output digest, and failure
  keyword.
- **Dependencies and merge order:** Begins only after M1-01 merges; must merge before
  the probe is used on the cluster.
- **Permissions or physical access:** None. Synthetic data only.
- **Acceptance and negative tests:** Every matrix row has one fixture and expected
  digest; generated fixtures are deterministic; valid cases pass and negative cases
  fail the named rule. Reject missing rows, duplicate case IDs, invented hardware
  values, private identifiers, or changes outside owned fixtures.
- **Durable artifacts:** Exhaustive small adapter fixtures and expected-failure index.
- **Explicit non-goals:** New probes, schema design, API research, real hardware
  output, or interpretation.

## M1-03 — TB5 harness implementation and loopback validation

- **Objective:** Implement the v1 framed TCP harness, scenario planner, integrity,
  timing, copy telemetry, error retention, and artifact writer using loopback and
  injected transports only.
- **Recommended model and reasoning:** GPT-5.6 Terra, High. The protocol is frozen but
  concurrent framing, timing, backpressure, and failure handling require careful
  systems implementation.
- **Owned paths:** `src/bench/tb5/`, TB5-specific tests/fixtures, and minimal
  `build.zig`/CLI wiring. The v1 protocol and schema are read-only.
- **Frozen inputs and contracts:** ADR-0005; exact 18 scenarios, payload matrix,
  warm-up/repetition counts, TCP settings, 10 ms start-skew bound, SHA-256 framing,
  retry/error policy, thermal state machine, and result schema.
- **Dependencies and merge order:** After M1-02. It consumes inventory identities but
  does not require cluster output.
- **Permissions or physical access:** Local sockets only; no remote nodes or
  Thunderbolt route configuration.
- **Acceptance and negative tests:** Loopback validates all scenario plans and payload
  sizes without allocating all large payloads simultaneously; deterministic payload
  and framing vectors pass; partial reads/writes are handled. Reject wrong plan or
  peer, corrupt digest, duplicate/out-of-order sequence, truncated/oversized frame,
  timeout, start-skew violation, unreported retry, cross-clock one-way calculation,
  unknown copy layer, non-direct route proof, and private addresses in output.
- **Durable artifacts:** Harness, protocol vectors, injected-failure fixtures, result
  serializer, and operator dry-run guide.
- **Explicit non-goals:** Cluster measurement, transport selection beyond v1 TCP,
  performance claims, zero-copy claims, remote configuration, or production transport.

## M1-04 — Three-node inventory capture

- **Objective:** Run the accepted probe once per node under a documented stable
  collection regime and publish the three public-safe manifests plus a topology proof.
- **Recommended model and reasoning:** GPT-5.6 Terra, Medium. Execution is bounded by
  exact commands and schemas; unexpected API gaps are recorded, not redesigned.
- **Owned paths:** `artifacts/m1/inventory/` public manifests and capture report;
  task-owned provenance. Production source remains read-only unless a separate fix PR
  is accepted first.
- **Frozen inputs and contracts:** M1-01 binary digest, v1 schema, private alias map,
  capture checklist, QW5 commit, and public-safety scan.
- **Dependencies and merge order:** After M1-03 so the inventory can also support route
  preflight. Any probe defect returns to a separate Terra fix before capture resumes.
- **Permissions or physical access:** Project-owner approval for read-only SSH or
  physical console access to A, B, and C. No system setting, package, route, or remote
  node mutation without a separately authorized setup task.
- **Acceptance and negative tests:** Three manifests validate; required facts have
  available/unavailable/error states and sources; links resolve to two peer aliases;
  repeated serialization is stable; private scans pass. Reject alias ambiguity,
  version/hash mismatch, dirty binary, missing fact, raw dump, serial/UUID/MAC/IP,
  user/path leakage, or any write operation.
- **Durable artifacts:** Three inventory manifests, topology/route-proof manifest,
  raw-external artifact digests if needed, and a limitations report.
- **Explicit non-goals:** Benchmarking, improving node configuration, resolving
  unavailable facts by assumption, or declaring relative node performance.

## M1-05 — TB5 solo-path capture

- **Objective:** Execute streaming and round-trip modes for the six solo directed
  paths exactly as specified and publish raw manifests plus a non-interpretive summary.
- **Recommended model and reasoning:** GPT-5.6 Terra, High. The run is bounded but
  distributed synchronization, thermal pauses, and negative evidence require careful
  operational judgment.
- **Owned paths:** `artifacts/m1/tb5/solo/` manifests, summary, and task provenance.
  Harness and contracts are read-only.
- **Frozen inputs and contracts:** M1-03 harness digest; M1-04 inventories and route
  proof; v1 payloads, repetition counts, error policy, thermal rules, and preregistered
  scenario order/seed.
- **Dependencies and merge order:** After M1-04. Solo evidence must pass structural G2
  review before simultaneous testing.
- **Permissions or physical access:** Owner-approved exclusive cluster window, direct
  console or SSH access, already configured TB routes, stable power, and permission
  for the planned data volume. No route or OS mutation.
- **Acceptance and negative tests:** All solo cells reach ten valid attempts or retain
  a failed-cell artifact; route/checksum/sequence/byte/copy/error/thermal fields are
  complete; round-trip results are not divided by two. Reject relay/non-test route,
  missing cell, silent retry/exclusion, mixed thermal regimes, changed socket setting,
  insufficient attempt record, or headline best-run reporting.
- **Durable artifacts:** Content-addressed raw sample manifests, public-safe index,
  solo summary, failed-cell reports, and provenance.
- **Explicit non-goals:** Simultaneous traffic, placement interpretation, production
  transport claims, or model inference.

## M1-06 — TB5 simultaneous-link capture

- **Objective:** Execute pair-duplex, fan-out, fan-in, cycle, and all-directed
  scenarios and quantify per-flow contention without interpretation beyond the
  preregistered summary.
- **Recommended model and reasoning:** GPT-5.6 Terra, High. The scenario matrix is
  frozen; reliable multi-node concurrency and failure retention are the hard parts.
- **Owned paths:** `artifacts/m1/tb5/simultaneous/` manifests, summary, and provenance.
- **Frozen inputs and contracts:** Accepted solo result index; unchanged M1-03 harness
  and M1-04 inventory digests; exact v1 simultaneous scenarios and thresholds.
- **Dependencies and merge order:** After M1-05. A harness or route change invalidates
  comparability and requires a new plan rather than an in-place rerun.
- **Permissions or physical access:** Same owner-approved exclusive cluster access and
  data-volume permission as M1-05.
- **Acceptance and negative tests:** Every required simultaneous cell reaches the
  target or retains failure; all flows start within the bound; per-flow and aggregate
  summaries reconcile. Reject omitted slow flow, coordinator relay, mixed payload in
  one scenario, unrecorded start-skew replacement, pooled thermal regimes, changed
  binary/plan digest, or solo results relabeled as simultaneous.
- **Durable artifacts:** Raw simultaneous manifests, summary, contention table, failed
  scenarios, and provenance.
- **Explicit non-goals:** Scheduler design, causal controller-topology claims without
  evidence, or inference performance projection.

## M1-07 — Immutable model revision and acquisition decision

- **Objective:** Select the exact immutable revisions and file inclusion rules for
  both target models, or preserve ADR-0001 revisions, before any weights are fetched.
- **Recommended model and reasoning:** GPT-5.6 Sol, High. Revision choice is a
  cross-cutting architecture, reproducibility, licensing, and product decision.
- **Owned paths:** One new ADR if revisions or selection rules change;
  `artifacts/m1/models/acquisition-plan.json`; model acquisition checklist; provenance.
- **Frozen inputs and contracts:** ADR-0001 source revisions, current official model
  cards/configuration metadata, model manifest v1, project model sequence, runtime and
  security boundaries.
- **Dependencies and merge order:** After M1-06 so transport evidence exists before
  costly model acquisition; must merge before M1-08.
- **Permissions or physical access:** Network access for metadata-only inspection.
  Project-owner approval is required for any revision change, licensing implication,
  file selection, and later weight-download/storage budget. No weights in this task.
- **Acceptance and negative tests:** Full 40-character revisions resolve; file plan
  covers config, tokenizer/templates, license/notices, indexes, and intended shards;
  change rationale is reviewed. Reject mutable branch identity, shortened hash,
  provider cache ID as identity, remote code execution, missing license, unexplained
  vision exclusion, or silent model-sequence change.
- **Durable artifacts:** Accepted acquisition plan and, only if needed, a superseding
  ADR.
- **Explicit non-goals:** Weight downloads, tensor parsing, conversion, quantization,
  or feasibility claims.

## M1-08 — Model manifest and tensor inspector

- **Objective:** Implement offline, read-only file hashing and SafeTensors metadata
  inspection that emits both v1 contracts deterministically using miniature fixtures.
- **Recommended model and reasoning:** GPT-5.6 Terra, High. Contracts are frozen, but
  hostile input parsing, checked arithmetic, and semantic classification need careful
  implementation.
- **Owned paths:** `tools/model_inventory/`, its tests and miniature generated
  fixtures, and minimal task documentation. Model weights and schemas are read-only.
- **Frozen inputs and contracts:** Model/tensor v1 schemas; acquisition plan; pinned
  SafeTensors format reference or clean-room parser design; classification rules tied
  to exact pinned configurations.
- **Dependencies and merge order:** After M1-07.
- **Permissions or physical access:** No cluster access and no large model download.
  Synthetic miniature tensor files only; Python offline tooling is allowed.
- **Acceptance and negative tests:** Exact hashes and two-pass byte counts; parser does
  not execute model code or unsafe object deserialization; totals reconcile;
  serialization is deterministic. Reject oversized header, duplicate JSON/tensor key,
  unknown dtype, checked-arithmetic overflow, out-of-range/overlap/hole, malformed
  shape, duplicate path/name, hash mismatch, missing shard, absolute/private path, and
  unclassified tensor used as classified.
- **Durable artifacts:** Inspector, miniature fixtures, classification rules, and
  reproducibility command.
- **Explicit non-goals:** Real weights, conversion, quantization, model execution, or
  changing source semantics to match another runtime.

## M1-09 — Qwen3-Coder-Next artifact and tensor manifests

- **Objective:** Acquire the owner-approved immutable artifact into external storage,
  verify it twice, and publish complete model and tensor manifests.
- **Recommended model and reasoning:** GPT-5.6 Terra, High. The workflow is bounded,
  but large-artifact integrity and unexpected tensor classifications are consequential.
- **Owned paths:** `artifacts/m1/models/qwen3-coder-next/` public manifests, external
  raw-artifact index, limitations report, and provenance. Inspector is read-only.
- **Frozen inputs and contracts:** M1-07 revision/file plan; M1-08 inspector digest;
  model/tensor v1 schemas; external storage location supplied privately by owner.
- **Dependencies and merge order:** After M1-08.
- **Permissions or physical access:** Explicit owner approval for model download,
  network bandwidth, license terms, and sufficient external scratch storage. No
  cluster-node mutation is required.
- **Acceptance and negative tests:** Every planned file is present, exact-sized, and
  SHA-256 verified twice; no unexpected file; tensor ranges/totals reconcile;
  classification coverage is reported. Reject mutable resolution, partial shard,
  cache symlink as hash, download token/path leakage, missing license/template/index,
  duplicate/unknown tensor, or model execution.
- **Durable artifacts:** Public model manifest, tensor inventory, manifest digests,
  source-format totals, unresolved classifications, and external content-addressed
  location references.
- **Explicit non-goals:** Quantization, correctness inference, cluster placement,
  quality evaluation, or publishing weights in Git.

## M1-10 — Qwen3.5-397B-A17B artifact and tensor manifests

- **Objective:** Repeat the authorized artifact workflow for the complete flagship
  artifact and produce any text-execution subset only after its exclusion gate passes.
- **Recommended model and reasoning:** GPT-5.6 Terra, High. The process is frozen but
  artifact scale, vision/language boundaries, and storage reconciliation increase risk.
- **Owned paths:** `artifacts/m1/models/qwen3.5-397b-a17b/` public manifests, subset
  dependency report if applicable, limitations, and provenance.
- **Frozen inputs and contracts:** M1-07 revision/file plan; M1-08 inspector; v1
  contracts; complete-artifact-first rule from ADR-0006.
- **Dependencies and merge order:** After M1-09, so the smaller target validates the
  acquisition and inspection path first.
- **Permissions or physical access:** Separate owner approval for the much larger
  download, storage, time, and license review. No cluster mutation.
- **Acceptance and negative tests:** Same integrity gates as M1-09 plus complete
  language/vision totals; exclusions, if any, cite a reviewed execution dependency
  rule. Reject presumed text-only deletion, aggregate parameter count as inventory,
  missing vision file/tensor, storage double-counting, or a 2-bit floor presented as
  an artifact size.
- **Durable artifacts:** Complete model/tensor manifests, optional justified subset
  manifest, reconciliation tables, unresolved classifications, and external digests.
- **Explicit non-goals:** Conversion, quantization, inference, quality, or a claim that
  397B fits the cluster.

## M1-11 — Placement and quantization-size analyzer

- **Objective:** Implement checked, deterministic calculations for concrete layout
  size reconciliation, per-node budgets, allocations, sensitivity ranges, network
  edges, and v1 decision artifacts using synthetic inputs first.
- **Recommended model and reasoning:** GPT-5.6 Terra, High. Contracts and formulas are
  frozen, but byte-accounting correctness and combinatorial placement need rigorous
  tests.
- **Owned paths:** `tools/placement/`, synthetic fixtures/tests, formula-set manifests,
  and minimal documentation. Evidence schemas and raw M1 artifacts are read-only.
- **Frozen inputs and contracts:** ADR-0006; placement v1 schema; workload points;
  exact byte classes; node budget equation; packet semantics; prefill/decode split;
  approved quantization layout specifications.
- **Dependencies and merge order:** After M1-10 so the implementation can be checked
  against the manifest shapes without publishing interpreted results.
- **Permissions or physical access:** None beyond read-only access to committed M1
  public manifests. No model bytes needed if inventories are complete.
- **Acceptance and negative tests:** Checked arithmetic; all size components and node
  budgets reconcile; deterministic scenario enumeration; shared storage counted once;
  negative headroom fails. Reject aggregate-only fit, duplicate assignment, missing
  reserve, implicit zero scratch/state, bit-width-only layout, mixed evidence label,
  expert-as-packet multiplication, relay-by-default, combined prefill/decode, and GO
  when a required gate is unresolved.
- **Durable artifacts:** Analyzer, formula sets, synthetic placement fixtures, and
  reproducibility command.
- **Explicit non-goals:** Choosing the winning layout, quality claims, kernel
  implementation, quantized artifacts, inference, or final M1 interpretation.

## M1-12 — Integrated M1 gate report

- **Objective:** Run the accepted analysis, review all evidence adversarially, issue
  scoped decisions for both models, record architecture consequences, and close M1.
- **Recommended model and reasoning:** GPT-5.6 Sol, Extra High. This is cross-cutting
  interpretation and final integration where evidence conflicts and negative results
  must be handled coherently.
- **Owned paths:** `artifacts/m1/placement/`, the M1 gate report, new/superseding ADRs,
  board reconciliation, and provenance. Raw evidence and tools are read-only.
- **Frozen inputs and contracts:** Accepted outputs of M1-04 through M1-11; milestone
  gates G0–G6; model sequence; public-claims policy; owner-approved target reserve and
  quantization candidates.
- **Dependencies and merge order:** Last M1 task after all preceding PRs merge.
- **Permissions or physical access:** No new physical execution by default. Owner must
  approve target headroom/reserve policies, any model revision or subset decision,
  and the next post-M1 task. Missing evidence may require a separately scoped rerun PR.
- **Acceptance and negative tests:** Every input digest resolves; every required
  scenario has a gate outcome; per-node totals reconcile; MEASURED/SIMULATED/ESTIMATED/
  TARGET remain distinct; negative results and anomalies are retained. Reject cherry-
  picked link cells, best-run claims, aggregate-memory fit, unbounded scratch/state,
  size-as-quality, text subset without proof, capability language, or a GO broader
  than the named next task.
- **Durable artifacts:** Model-specific placement analyses, quantization-size tables,
  sensitivity ranges, integrated gate report, ADR consequences, completed board state,
  and next-task recommendation.
- **Explicit non-goals:** Inference, quantization kernels, Metal kernels, distributed
  execution, quality evaluation, model demonstration, or merging the report without
  project-owner review.
