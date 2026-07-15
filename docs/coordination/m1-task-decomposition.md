# M1 ordered pull-request decomposition

This queue begins only after the M0 contract-completion and M1 planning pull request
is accepted and merged. Every item is a separate branch, worktree, provenance record,
and draft pull request from then-current `main`; merge in numeric order. An
implementation task cannot edit a frozen v1 contract. A defect returns to a separate
Sol amendment PR instead of being reinterpreted in code.

## Routing and readiness

| Order | Task | Route | Readiness |
| --- | --- | --- | --- |
| 01 | Public-safe hardware inventory probe | Terra / Medium | **First Terra-ready task after this PR** |
| 02 | Inventory adapter fixture expansion | Luna / Low | After 01 |
| 03 | TB5 harness and loopback validation | Terra / High | After 02 |
| 04 | Three-node inventory capture | Terra / Medium | Owner/access gated after 03 |
| 05 | Clean-node memory baseline capture | Terra / Medium | Owner/policy/access gated after 04 |
| 06 | Route proof and local application controls | Terra / High | Owner/access gated after 05 |
| 07 | TB5 solo-path capture | Terra / High | Owner/access gated after 06 |
| 08 | TB5 simultaneous capture and link summary | Terra / High | Owner/access gated after 07 |
| 09 | Immutable model acquisition decision | Sol / High | Owner decision after 08 |
| 10 | SafeTensors parser and model-classification freeze | Sol / High | After 09 |
| 11 | Model manifest and tensor inspector | Terra / High | After 10 |
| 12 | Qwen3-Coder-Next manifests | Terra / High | Download/storage gated after 11 |
| 13 | Qwen3.5-397B-A17B manifests | Terra / High | Separate download/storage gate after 12 |
| 14 | Layout, formula, reserve, subset, and placement freeze | Sol / Extra High | Owner decision after 13 |
| 15 | Placement and quantization-size analyzer | Terra / High | After 14 |
| 16 | Integrated M1 gate report | Sol / Extra High | After all evidence tasks |

Only task 02 uses Luna because it expands an exact reviewed matrix mechanically. Sol
owns architecture, identity/classification rules, formulas, layout selection,
interpretation, and integration. Terra receives bounded contracts and negative tests.
No task uses Ultra or parallel agents.

## M1-01 — Public-safe hardware inventory probe

- **Objective:** Implement a read-only, mockable `qw5.hardware-inventory/v1` producer
  and `qw5-json-c14n-v1` serializer without contacting remote nodes.
- **Recommended model and reasoning:** GPT-5.6 Terra, Medium; fact adapters and
  serialization are bounded by schemas, semantic rules, vectors, and privacy tests.
- **Owned paths:** `src/inventory/`, inventory tests/fixtures, and minimal
  `src/main.zig`, `src/root.zig`, and `build.zig` wiring; v1 contracts are read-only.
- **Frozen inputs and contracts:** ADR-0004, hardware schema/prose, canonical vectors,
  semantic validator error codes, required fact/source/link sets, Zig 0.16.0, public
  Apple APIs only.
- **Dependencies and merge order:** First after this PR; no later M1 task merges first.
- **Permissions or physical access:** Read-only local Apple-silicon API access; no
  SSH, elevation, remote mutation, or cluster capture.
- **Acceptance and negative tests:** Mock adapters cover available/unavailable/error;
  canonical bytes match vectors; semantic validation passes. Reject wrong fact type or
  unit, duplicate/dangling source, self/partial peer set, malformed error state,
  nondeterminism, forbidden identifiers, private API, or write attempt.
- **Durable artifacts:** Probe module, mock boundaries, canonical serializer, unit
  fixtures, dry-run guide, and provenance.
- **Explicit non-goals:** A/B/C capture, link benchmarking, inferred facts, route
  setup, or v1 contract edits.

This is the first task ready for GPT-5.6 Terra after this planning PR is accepted. It
is not executed in PR #3 and no kickoff prompt is part of this PR.

## M1-02 — Inventory adapter fixture expansion

- **Objective:** Expand the accepted adapter matrix mechanically across status,
  redaction, source, peer, ordering, and serializer cases.
- **Recommended model and reasoning:** GPT-5.6 Luna, Low; inputs, expected canonical
  bytes/digests, and error codes are enumerated by Sol and M1-01.
- **Owned paths:** `fixtures/inventory/` and its expected-result index only.
- **Frozen inputs and contracts:** M1-01 adapter list/serializer, v1 schemas,
  validator, and Sol-reviewed fixture matrix.
- **Dependencies and merge order:** After 01; before any cluster use.
- **Permissions or physical access:** None; synthetic data only.
- **Acceptance and negative tests:** Every matrix row exists exactly once and matches
  expected bytes or failure code; reject missing/duplicate rows, invented hardware,
  private identifiers, or edits outside fixtures.
- **Durable artifacts:** Exhaustive small adapter fixtures and digest/failure index.
- **Explicit non-goals:** Source changes, new probes, real output, API research, or
  interpretation.

## M1-03 — TB5 harness and loopback validation

- **Objective:** Implement `qw5-tb5-wire/v1`, the exact 246-cell planner, loopback
  harness, raw local controls/index, raw empirical-inclusion evidence, measurement
  index, raw attempt writer, and result/link-summary serializers using injected
  transports.
- **Recommended model and reasoning:** GPT-5.6 Terra, High; concurrent I/O and failure
  retention are difficult, but framing, payload generation, plan, routes, statuses,
  and arithmetic are frozen.
- **Owned paths:** `src/bench/tb5/`, TB5 tests/fixtures/operator dry-run docs, and
  minimal CLI/build wiring; contract files remain read-only.
- **Frozen inputs and contracts:** ADRs 0005 and 0007; run-plan, route-proof, local-
  control/index, synchronization-evidence, measurement/index, and link-summary
  schemas; exact wire/canonical/TB5 vectors; public Network framework route procedure;
  scenario maps, payloads, counts, keyed order, empirical 1 ms/10 ms inclusion
  thresholds, deterministic stream stop/caps/final-frame rule, generation and
  verification timing, application buffers, sockets, copies, errors, and thermal
  state machine.
- **Dependencies and merge order:** After 02; before all physical captures.
- **Permissions or physical access:** Local loopback/injected sockets only; no remote
  nodes, route changes, or Thunderbolt claims.
- **Acceptance and negative tests:** Rebuild all exact vectors; generate 246 unique
  cells; partial reads/writes and backpressure work. Reject bad handshake/header/ack,
  reserved bits, corrupt/truncated/extra bytes, identity/route mismatch, sequence
  regression, byte/checksum/copy/count mismatch, malformed or insufficient empirical
  evidence, unsupported timing claim, unretained retry, cap-shortened sample, partial
  final frame, cross-clock latency, private address, dirty physical identity,
  incomplete indexes, all-complete/zero-sample summary, raw-summary disagreement, and
  digest non-resolution.
- **Durable artifacts:** Harness, planner, control runner, injected-failure fixtures,
  serializers, loopback report, and provenance.
- **Explicit non-goals:** Cluster execution, transport selection, production runtime,
  zero-copy or bandwidth claims, and contract redesign.

## M1-04 — Three-node inventory capture

- **Objective:** Execute the accepted probe once on A, B, and C and publish three
  public-safe manifests; record unavailable facts rather than redesigning adapters.
- **Recommended model and reasoning:** GPT-5.6 Terra, Medium; exact binary, commands,
  contracts, and failure behavior bound the operational task.
- **Owned paths:** `artifacts/m1/inventory/`, capture report, and provenance.
- **Frozen inputs and contracts:** M1-01 binary digest, M1-02 fixtures, private alias
  map, hardware v1, canonical profile, capture checklist, and clean QW5 commit.
- **Dependencies and merge order:** After 03; probe defects require a separate fix PR.
- **Permissions or physical access:** Owner-approved read-only SSH or console on all
  nodes; no setting, package, route, or file mutation beyond approved artifact output.
- **Acceptance and negative tests:** Three manifests validate; facts and two peers are
  explicit; repeated serialization is identical; public scan passes. Reject alias or
  digest mismatch, dirty binary, raw dump, partial peer set, private identifier, or
  remote write.
- **Durable artifacts:** Three inventories, digest index, limitations, and provenance.
- **Explicit non-goals:** Memory-baseline sampling, benchmark, tuning, or performance
  comparison.

## M1-05 — Clean-node memory baseline capture

- **Objective:** Run the dedicated preregistered `qw5.memory-baseline/v1` plan on each
  node and derive the fifth-percentile available baseline and observed OS reserve.
- **Recommended model and reasoning:** GPT-5.6 Terra, Medium; the policy, statistic,
  validity rules, and artifact arithmetic are frozen.
- **Owned paths:** `artifacts/m1/memory-baseline/`, sampling report, and provenance.
- **Frozen inputs and contracts:** M1-04 inventories; owner-approved ten-minute
  stabilization, 30 valid one-minute samples, maximum 36 attempts, thermal/power/
  clean-window criteria, nearest-rank p05 rule, and schema/validator.
- **Dependencies and merge order:** After 04; before route controls or placement.
- **Permissions or physical access:** Owner-approved exclusive read-only window on A,
  B, and C; process verification may not kill jobs or alter system settings.
- **Acceptance and negative tests:** All attempts retained; summary counts, p05, min,
  max, physical bytes, and OS reserve reconcile; actual stabilization/cadence validate;
  Metal working-set guidance remains separate. Reject one-shot baseline, unstable
  physical identity, invalid sample credited, changed cadence, fewer than 30 valid
  samples marked complete, or safety reserve invented from results.
- **Durable artifacts:** Three raw baseline manifests, summary/index, limitations, and
  provenance.
- **Explicit non-goals:** Selecting safety reserve, freeing memory, rebooting/tuning
  nodes, model allocation, or feasibility claims.

## M1-06 — Route proof and local application controls

- **Objective:** Publish the six direct-route proofs and run buffer-copy, framing, and
  SHA-256 controls on all nodes before network measurement.
- **Recommended model and reasoning:** GPT-5.6 Terra, High; execution is frozen but
  route binding, thermal pauses, and negative evidence require care.
- **Owned paths:** `artifacts/m1/tb5/preflight/`, control artifacts/index, and
  provenance.
- **Frozen inputs and contracts:** M1-03 binary, M1-04 inventories, M1-05 baselines,
  route-proof and local-control/index schemas, exact public Network framework
  interface/local-endpoint binding and current-path/peer-handshake checks, canonical
  plan template, public denylist.
- **Dependencies and merge order:** After 05; before solo capture.
- **Permissions or physical access:** Owner-approved exclusive access and already
  configured routes; no route, address, socket-default, or OS mutation.
- **Acceptance and negative tests:** Six routes validate required interface/local
  endpoint, ready/current path, expected interface use, public-safe endpoint match,
  no path update, peer handshake, and no relay; all 108 node/payload/control artifacts
  resolve through the canonical index. Reject missing direction/cell, relay or non-
  test path, path update, raw interface/address, digest or binary mismatch, dirty
  producer, silent control subtraction, pooled regimes, or control relabeled as link
  evidence.
- **Durable artifacts:** Route proof, local-control raw index/summary, limitations,
  plan inputs, and provenance.
- **Explicit non-goals:** Network throughput cells, tuning, causal hardware claims, or
  production transport decisions.

## M1-07 — TB5 solo-path capture

- **Objective:** Execute stream and round-trip cells for all six solo directions under
  one approved plan and publish raw attempts plus a solo coverage report.
- **Recommended model and reasoning:** GPT-5.6 Terra, High; matrix and thresholds are
  frozen, while distributed operation and failure retention are consequential.
- **Owned paths:** `artifacts/m1/tb5/solo/` and provenance.
- **Frozen inputs and contracts:** M1-03 harness, M1-06 route/control digests,
  owner-approved seed/order/socket/thermal/data-volume plan and exact v1 rules.
- **Dependencies and merge order:** After 06; structural solo review before 08.
- **Permissions or physical access:** Owner-approved exclusive cluster window and
  bounded data volume; no route/OS mutation.
- **Acceptance and negative tests:** Every solo cell has ten valid attempts or a
  retained terminal status; round-trip latency stays round trip; bytes, sequences,
  checksums, copies, errors, exclusions, sockets, and thermal regimes reconcile.
  Stream source stopping, 3-second target, 30-second/32-GiB caps, final-frame
  announcement, generation/verification timing, and peak application buffers match
  the plan. Reject missing cell, cap-shortened valid sample, partial final frame,
  best-run headline, silent retry, changed plan, mixed regime, relay, or one-way latency.
- **Durable artifacts:** Content-addressed solo attempts, index, summary, failures,
  and provenance.
- **Explicit non-goals:** Simultaneous traffic, placement interpretation, inference,
  or raw-link claims.

## M1-08 — TB5 simultaneous capture and link summary

- **Objective:** Execute duplex, fan-in/out, cycle, and all-directed cells and publish
  the complete 246-cell link summary with per-flow contention visible.
- **Recommended model and reasoning:** GPT-5.6 Terra, High; empirical-inclusion
  evidence, content-addressed reconciliation, and failure preservation are bounded but
  consequential.
- **Owned paths:** `artifacts/m1/tb5/simultaneous/`, final link summary/index, and
  provenance.
- **Frozen inputs and contracts:** Accepted solo index, unchanged harness/plan/route/
  inventory/control digests, exact scenario sets, raw empirical evidence schema,
  preregistered 1 ms control-RTT and 10 ms coordinator-observed thresholds, status
  rules, measurement index, and summary reconciliation contract.
- **Dependencies and merge order:** After 07; any input change creates a new plan.
- **Permissions or physical access:** Same owner-approved exclusive access and volume
  authorization as 07.
- **Acceptance and negative tests:** Every cell has a terminal artifact; each valid
  simultaneous attempt has qualifying raw empirical evidence; all 246 paths/digests
  resolve and identity/status/metrics/exclusions/errors/thermal fields reconcile.
  Complete stream cells have ten flow/aggregate throughput samples; complete round-
  trip cells have exactly 1,000 or 100 latency samples. Reject unsupported timing
  claims, invalid evidence credited, missing evidence not undetermined, zero-sample
  complete cells, raw-summary disagreement, omitted slow flow, relay, missing warmup/
  invalid attempt, pooled regimes, or aggregate hiding per-flow values.
- **Durable artifacts:** Simultaneous raw artifacts, 246-cell link summary, contention
  table, failed/undetermined cells, and provenance.
- **Explicit non-goals:** Causal controller-topology inference, scheduler design,
  model projection, or transport optimization.

## M1-09 — Immutable model acquisition decision

- **Objective:** Select exact revisions and complete file-inclusion/license/storage
  plans for both models without downloading weights.
- **Recommended model and reasoning:** GPT-5.6 Sol, High; revision, licensing, model
  sequence, security, cost, and public identity are owner-facing architecture choices.
- **Owned paths:** acquisition-plan artifact/checklist, one ADR only if direction
  changes, and provenance.
- **Frozen inputs and contracts:** ADR-0001 revisions, official metadata/model cards,
  model-manifest v1, security/runtime boundaries, and complete-artifact-first rule.
- **Dependencies and merge order:** After 08; before classification or downloads.
- **Permissions or physical access:** Metadata-only network access; owner approval for
  revision, license, selection, later bandwidth/storage, and any model-sequence change.
- **Acceptance and negative tests:** Full 40-hex revisions resolve; canonical revision
  listings and frozen expected path sets cover config, tokenizers/templates,
  licenses/notices, indexes, and shards. Reject mutable identity, a file table that
  differs from the expected paths, cache/ETag identity, remote code, missing license,
  unexplained vision exclusion, or silent thesis change.
- **Durable artifacts:** Approved acquisition plan, canonical immutable-revision
  listings with frozen expected path sets, and decision record.
- **Explicit non-goals:** Weights, parsing, conversion, quantization, or feasibility.

## M1-10 — SafeTensors parser and model-classification freeze

- **Objective:** Accept the immutable SafeTensors parser profile and freeze versioned
  classification rules plus hostile miniature examples for both exact revisions
  before implementing the generic inspector.
- **Recommended model and reasoning:** GPT-5.6 Sol, High; mapping names/configuration
  to language, vision, hybrid layer, router, expert, state, and head semantics is a
  model-specific interpretation decision.
- **Owned paths:** accepted parser-profile decision record,
  `artifacts/m1/models/classification-rules/`, rule schemas/fixtures, supporting
  contract amendment if required, and provenance.
- **Frozen inputs and contracts:** M1-09 revisions/file plan, immutable SafeTensors
  format commit, parser-profile schema/limits/dtypes/vectors, official configuration
  metadata, tensor v1 vocabulary, complete-vs-subset boundary.
- **Dependencies and merge order:** After 09; before 11.
- **Permissions or physical access:** Metadata-only network access; no weights or
  model code execution. Owner decides any semantic ambiguity affecting model scope.
- **Acceptance and negative tests:** Parser profile retains scalar `[]`, strict UTF-8,
  duplicate-member rejection, limits, checked arithmetic/offsets, and exact dtype set;
  rules specify precedence, captures, expected classes, revision/config digest,
  unresolved behavior, and examples. Reject mutable format reference, duplicate JSON
  member, scalar byte/offset mismatch, unsupported dtype, overflow, ambiguous rule
  overlap, silent fallback, unknown name forced classified, or vision exclusion.
- **Durable artifacts:** Accepted parser profile, two rule sets, schema, fixtures,
  coverage report, provenance.
- **Explicit non-goals:** Parser implementation, weight download, placement, or
  changing the model sequence.

## M1-11 — Model manifest and tensor inspector

- **Objective:** Implement offline two-pass hashing and hostile-input SafeTensors
  metadata inspection that emits both v1 artifacts canonically.
- **Recommended model and reasoning:** GPT-5.6 Terra, High; parsing is delicate but
  file roles, classification rules, ranges, totals, and error codes are frozen.
- **Owned paths:** `tools/model_inventory/`, miniature fixtures/tests, reproducibility
  docs, and provenance; schemas/rules are read-only.
- **Frozen inputs and contracts:** Model/tensor v1, M1-09 acquisition plan and expected
  path sets, M1-10 accepted parser profile/rules, canonical profile, immutable
  SafeTensors format commit, exact raw vectors, and semantic validator behavior.
- **Dependencies and merge order:** After 10; before real artifacts.
- **Permissions or physical access:** None; generated miniature files only, no large
  downloads, remote code, or unsafe deserialization.
- **Acceptance and negative tests:** Two passes reconcile; completeness is derived;
  file/layer/expert totals and storage coverage reconcile. Reject duplicate JSON/key/
  tensor/path, oversized header, unknown dtype, overflow, reversed/out-of-range/
  overlap/hole, shape/byte mismatch, missing shard, private path, hash mismatch,
  rule ambiguity, or unclassified-as-classified.
- **Durable artifacts:** Inspector, miniature hostile corpus, deterministic command,
  coverage report, and provenance.
- **Explicit non-goals:** Real weights, execution, conversion, quantization, or runtime
  source adaptation.

## M1-12 — Qwen3-Coder-Next manifests

- **Objective:** Acquire the approved immutable artifact externally, verify it twice,
  and publish complete model/tensor manifests.
- **Recommended model and reasoning:** GPT-5.6 Terra, High; workflow is frozen but
  large-artifact integrity and unexpected classification require careful stops.
- **Owned paths:** `artifacts/m1/models/qwen3-coder-next/` and provenance.
- **Frozen inputs and contracts:** M1-09 plan, M1-10 rules, M1-11 binary, public
  contracts, private owner-supplied external storage.
- **Dependencies and merge order:** After 11; smaller target validates the path first.
- **Permissions or physical access:** Explicit owner approval for license, bandwidth,
  download, time, and storage; no cluster mutation.
- **Acceptance and negative tests:** Every planned byte is present and twice verified;
  no unexpected file; ranges/totals/classification reconcile. Reject mutable or
  partial artifact, cache symlink identity, secret/path leakage, missing license/
  template/index, unknown tensor, or model execution.
- **Durable artifacts:** Public manifests/digests, totals, unresolved classifications,
  external content index, limitations, provenance.
- **Explicit non-goals:** Quantization, inference, quality, placement, or Git weights.

## M1-13 — Qwen3.5-397B-A17B manifests

- **Objective:** Repeat the accepted workflow for the complete language/vision
  artifact; do not create a text subset yet.
- **Recommended model and reasoning:** GPT-5.6 Terra, High; frozen workflow with
  greater scale and storage risk.
- **Owned paths:** `artifacts/m1/models/qwen3.5-397b-a17b/` and provenance.
- **Frozen inputs and contracts:** Same accepted inputs as 12, with flagship revision,
  rules, complete-artifact-first requirement, and separate storage plan.
- **Dependencies and merge order:** After 12; before any subset/layout/formula work.
- **Permissions or physical access:** Separate owner approval for license, download,
  bandwidth, time, and sufficient external storage.
- **Acceptance and negative tests:** All integrity/tensor gates from 12 plus complete
  language/vision totals. Reject implicit vision exclusion, aggregate-only total,
  duplicate physical storage, estimated bytes relabeled measured, or partial artifact.
- **Durable artifacts:** Complete public manifests, totals, unresolved classifications,
  external index, limitations, provenance.
- **Explicit non-goals:** Text subset, quantization, execution, placement, or quality.

## M1-14 — Layout, formula, reserve, subset, and placement freeze

- **Objective:** Decide and validate machine-readable quantization layouts, formula
  set, safety reserve/headroom policy, candidate placements/solver objective,
  model-specific gates, and any Qwen3.5 text-subset dependency proof.
- **Recommended model and reasoning:** GPT-5.6 Sol, Extra High; these cross-cutting
  choices determine what calculations mean and cannot be delegated to an analyzer.
- **Owned paths:** schemas/fixtures and accepted artifacts for
  `quantization-layout/v1`, `formula-set/v1`, `text-subset-dependency/v1`,
  `placement-gate-rule-set/v1`, `placement-candidate-set/v1`,
  `placement-solver-objective/v1`, `reserve-headroom-policy/v1`, one ADR if direction
  changes, and provenance.
- **Frozen inputs and contracts:** M1-05 baselines, M1-08 link summary, M1-12/13 exact
  tensors/configs, placement v1, evidence labels, owner-approved target reserve and
  candidate list.
- **Dependencies and merge order:** After 13; must merge before 15.
- **Permissions or physical access:** No cluster or weights required. Owner approval
  is mandatory for safety reserve, headroom rule, quantization candidates, solver
  objective, text-subset rule, and any material model/runtime boundary change.
- **Acceptance and negative tests:** Every formula has checked units/rounding and
  source fields; layouts reconcile metadata/padding/exceptions; placements enumerate
  allowed node sets; applicability plus passed/failed/unresolved/not-applicable gates
  are exhaustive/disjoint; subset exclusions have dependency proof or remain
  unresolved. Reject missing lineage, vacuous not-applicable gates, network traffic
  without link evidence, bit labels alone, zero scratch by omission,
  result-tuned reserve, expert-count-as-packets, implicit vision removal, unknown
  tensor class, or quality inferred from size.
- **Durable artifacts:** Accepted schemas, positive/hostile fixtures, formula/layout/
  subset/gate/placement artifacts, owner decision record, provenance.
- **Explicit non-goals:** Analyzer code, quantized artifacts, quality evaluation,
  kernels, inference, or changing project thesis without a stop decision.

## M1-15 — Placement and quantization-size analyzer

- **Objective:** Implement the exact accepted integer calculations and enumerations for
  both models and workload points; emit `qw5.placement-analysis/v1` artifacts.
- **Recommended model and reasoning:** GPT-5.6 Terra, High; formulas, layouts,
  candidates, gates, solver objective, and expected vectors are frozen by 14.
- **Owned paths:** `tools/placement_analysis/`, tests/fixtures, reproducibility docs,
  generated analysis artifacts, and provenance; frozen contracts are read-only.
- **Frozen inputs and contracts:** All M1-14 artifacts plus immutable baseline/link/
  model/tensor digests and exact workload matrix.
- **Dependencies and merge order:** After 14; before integration.
- **Permissions or physical access:** None; offline metadata only, no weights required.
- **Acceptance and negative tests:** Checked integer arithmetic reproduces golden
  cases; sizes, allocations, budgets, headroom, edges, and gates reconcile for each
  model/context/phase/candidate. Reject missing identity, duplicate assignment,
  double OS reserve, formula/layout drift, negative headroom passed, gate overlap/gap,
  unresolved `GO`, implicit interpolation, or capability language.
- **Durable artifacts:** Analyzer, tests, per-scenario analyses, reconciliation report,
  and provenance.
- **Explicit non-goals:** Quantization, inference, quality, kernels, scheduler,
  optimization, or deployment claim.

## M1-16 — Integrated M1 gate report

- **Objective:** Audit the complete evidence graph and issue scoped model/placement
  outcomes plus the next permitted task, if any.
- **Recommended model and reasoning:** GPT-5.6 Sol, Extra High; cross-domain evidence,
  negative results, owner decisions, and public claims require architecture judgment.
- **Owned paths:** final M1 report/index, consequential ADRs, milestone/board
  reconciliation, and provenance.
- **Frozen inputs and contracts:** Accepted outputs 01–15, PROJECT_HANDOFF, ADRs,
  benchmark methodology, milestone gates, and evidence vocabulary.
- **Dependencies and merge order:** Last; no missing predecessor is waived.
- **Permissions or physical access:** None unless owner separately requests a narrowly
  scoped evidence check; owner approves/rejects the recommended post-M1 action.
- **Acceptance and negative tests:** Every input digest resolves; 246 link cells and
  both model analyses trace to raw evidence; gate sets reconcile; limitations and
  failures remain prominent. Reject missing lineage, mixed evidence classes,
  aggregate-memory shortcut, best-run selection, unresolved `GO`, quality/performance
  inference, or thesis/model/runtime/license change without owner decision.
- **Durable artifacts:** Integrated gate report, evidence index, decisions/open
  questions, board transition, ADRs where required, and provenance.
- **Explicit non-goals:** Inference implementation, kernels, quantized artifact
  creation, transport/runtime code, PR merge, or unapproved follow-on execution.
