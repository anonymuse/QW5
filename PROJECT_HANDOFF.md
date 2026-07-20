# QW5 Project Handoff

## Current mandate

QW5 is being completed as a portfolio-grade architecture case study and offline
reference kit for evidence-first local LLM inference on Apple silicon. The owner ended
the original three-Mac home-cluster implementation on 2026-07-19. That decision is
recorded in
[`ADR-0008`](docs/architecture/adr/0008-portfolio-transition.md).

Repository: <https://github.com/anonymuse/QW5>

The active objective is not to finish the inference engine. It is to turn the high-
quality design, validation, and governance work already produced into a coherent,
runnable, honest consulting showpiece. The exact remaining queue is
[`docs/portfolio/completion-plan.md`](docs/portfolio/completion-plan.md).

## Finished-product definition

The QW5 portfolio release should let a technical buyer, engineering leader, or local-
AI practitioner understand three things quickly:

1. how a frontier-model deployment on Apple silicon can be decomposed into artifact,
   memory, compute, transport, correctness, and evidence problems;
2. what QW5 actually designed and validated before the physical program stopped; and
3. how the same methods can guide either a high-memory single Mac or a future cluster.

The finished product consists of:

- a flagship README and navigable architecture case study;
- the merged Zig foundation and its deterministic tests;
- a curated, provenance-preserving version of the PR #3 contracts, schemas, fixtures,
  semantic validator, and proposed decisions;
- an offline, deterministic walkthrough using synthetic artifacts labeled
  `SIMULATED`;
- reusable Apple-silicon cluster and single-node blueprints;
- reproducibility, claim, privacy, and authorship policies; and
- a reviewed release that clearly states limitations and the intentional stop.

It is not a working model server, a benchmark result, or proof that the proposed
three-node placement was feasible.

## Evidence and repository state

| Surface | State | What it proves |
| --- | --- | --- |
| PR [#1](https://github.com/anonymuse/QW5/pull/1) | Merged | Foundation policy, architecture, evidence method, Zig bootstrap, tests, and CI were established. |
| PR [#2](https://github.com/anonymuse/QW5/pull/2) | Merged | Codex co-authorship and provenance policy were completed. |
| PR [#3](https://github.com/anonymuse/QW5/pull/3) | Open draft at `ad45675088a27c2e05ad7cd89e683bfb169fd4e7` | A substantial M0/M1 design and contract package exists and passed its documented synthetic validation. It was not merged or executed. |
| Three-node hardware inventory | Not performed | No node fact is `MEASURED` by QW5. |
| Thunderbolt 5 characterization | Not performed | QW5 has no link, latency, throughput, copy-count, or concurrency result. |
| Model acquisition and tensor inventory | Not performed | QW5 did not download, inspect, convert, or quantify the target model artifacts. |
| Inference runtime | Not implemented | QW5 cannot load a model, generate a token, serve an API, or execute Metal kernels. |
| Portfolio release | Planned | Completion means the reference kit and synthetic walkthrough meet the gates in the completion plan. |

Quantitative statements use the repository labels exactly:

- **MEASURED** — observed through a documented procedure on identified hardware and
  software with raw evidence retained;
- **SIMULATED** — produced by a named simulation with explicit assumptions;
- **ESTIMATED** — calculated or inferred from stated inputs;
- **TARGET** — desired but not demonstrated.

Fixture validation does not become hardware measurement. A third-party result does
not become a QW5 result. A model card does not establish local feasibility.

## Original project thesis

QW5 asked whether a model-specific runtime could make a frontier-class sparse Qwen
model practical across a heterogeneous Apple-silicon cluster by owning the hard parts:

- immutable model and tensor identity;
- tensor-aware mixed quantization;
- unified-memory and scratch budgeting;
- hybrid attention and sparse mixture-of-experts execution;
- measurement-driven expert and state placement;
- custom Metal kernels with CPU correctness references;
- direct peer transport over a full Thunderbolt 5 mesh;
- separate prefill and decode performance models; and
- reproducible correctness, quality, transport, memory, power, and thermal evidence.

The original runtime boundary put orchestration, loading, validation, memory,
transport, and telemetry in Zig and performance-critical operations in custom Metal.
MLX, llama.cpp, PyTorch, Transformers, and other complete engines were permitted as
oracles, conversion references, and baselines rather than as an undisclosed production
executor.

The historical target sequence was Qwen3-Coder-Next for correctness followed by a
text-first Qwen3.5-397B-A17B feasibility gate. ADR-0001 pins the source facts reviewed
at bootstrap. These are preserved design inputs, not current implementation promises.

## What was built

### Merged foundation

- Apache-2.0 project, contribution, agent, and AI-provenance policies.
- A defensible public evidence vocabulary and benchmark methodology.
- Architecture records for model sequencing, runtime ownership, and measurement-
  before-placement.
- A declared three-node topology and public-safe inventory design.
- A Zig 0.16.0 executable with deterministic `smoke` and limited compiler-target
  `inventory` commands.
- Unit tests, a smoke test, pinned Apple-silicon CI, and focused dependency boundaries.

### Draft contract and validation package

PR #3 contains work worth preserving even though the hardware program ended:

- 16 JSON Schemas and 16 positive fixtures;
- 87 committed hostile cases plus bundle-level negative tests;
- canonical JSON identity and content-addressed evidence graphs;
- public-safe hardware and memory-baseline contracts;
- a 246-cell application-path TB5 measurement design and exact wire vectors;
- empirical simultaneous-attempt inclusion rules that avoid unsupported clock claims;
- model acquisition, SafeTensors parsing, tensor inventory, quantization, placement,
  and fail-closed feasibility contracts;
- a versioned semantic validator with pinned CI-only dependencies; and
- four proposed ADRs plus a 16-task M1 decomposition.

Those artifacts demonstrate architecture and validation depth. They do not demonstrate
runtime behavior. Portfolio task `P01` defines their exact disposition.

## Architecture outcomes

The strongest outcomes are decisions and controls that transfer beyond this one
topology:

- **Memory fit is not deployment feasibility.** Weight bytes are only one part of a
  legal allocation; metadata, higher-precision tensors, state, scratch, transport,
  fragmentation, OS headroom, quality, kernels, and stability remain separate gates.
- **Aggregate RAM is not a placement.** Each node needs a complete, nonnegative budget
  for a declared workload.
- **Transport standards are not application results.** Link marketing rates cannot
  replace route proof, message framing, checksums, copy observations, latency
  distributions, concurrency tests, and error retention.
- **Coordinator is a logical role, not a mandatory relay.** Data paths should follow
  measured topology and workload cost.
- **Prefill and decode are different systems problems.** Combining them into one token
  rate hides compute, memory, state, and transport behavior.
- **Identity precedes optimization.** Model revisions, files, tensors, transformed
  artifacts, fixtures, and results need immutable lineage before comparison.
- **Missing evidence fails closed.** `UNDETERMINED` is better than a marketable but
  unsupported `GO`.
- **A disciplined stop is a valid outcome.** Ending the physical program before
  expensive execution preserved useful IP without manufacturing success claims.

## Reuse paths

### Apple-silicon cluster engagements

Use QW5 as a discovery and architecture framework:

1. inventory each node with public-safe, source-attributed facts;
2. establish clean memory baselines and operating headroom;
3. characterize every directed peer path alone and under concurrency;
4. pin exact model artifacts and build a semantic tensor inventory;
5. define concrete quantization layouts and quality gates;
6. model prefill and decode separately;
7. solve per-node placement from measured profiles;
8. implement the smallest correctness path before custom optimization; and
9. publish raw evidence, limitations, and negative results with the recommendation.

The historical topology document and PR #3 contracts are design templates. They must
be adapted to the client's actual chips, OS, fabric, security policy, workload, model,
and budget.

### Future single-machine engine

The owner's likely next implementation is a model-specific engine on one high-memory
Apple-silicon machine, potentially with 128 GB or more unified memory. That future
program should begin separately and in this order:

1. select one exact, then-current model revision and workload;
2. prove artifact completeness, legal memory headroom, and a realistic quantization;
3. establish tokenizer, prompt, logit, and short-generation correctness against pinned
   oracles;
4. build a readable single-node CPU/reference path and then Metal kernels;
5. add the local API, telemetry, long-context behavior, and agent demonstration;
6. measure power, thermals, prefill, decode, quality, and stability; and
7. add orchestration only if one machine fails a measured business requirement.

The model-specific approach is intentionally narrow. Projects such as
[antirez/ds4](https://github.com/antirez/ds4) illustrate why a focused implementation
can make different tradeoffs from a universal runtime. DS4 is a reference and
inspiration, not a source donor or QW5 result.

## Open-weight context

Model turnover is now faster than a long custom-runtime program. Recent families such
as [Moonshot AI's Kimi models](https://huggingface.co/moonshotai/models),
[Thinking Machines' Inkling](https://huggingface.co/thinkingmachines/Inkling), and
[Qwen 3.5](https://huggingface.co/Qwen/Qwen3.5-397B-A17B) reinforce the value of a
stable deployment method with replaceable model adapters.

QW5 does not claim support for those models. “Open-weight” is used deliberately:
weight availability, source availability, license terms, redistribution rights,
runtime support, and local feasibility are separate checks. Every future engagement
must repeat them for the exact revision under consideration.

## Project relationships and source boundaries

- QW5 remains independent of QW3 and QW4; their Git histories are not merged.
- QW3, QW4, DS4, MLX, llama.cpp, and similar projects may be studied as references or
  baselines.
- Clean-room, AI-authored implementation remains the default for original QW5 code.
- Direct adaptation of non-AI-authored source requires a prior licensing and
  provenance decision.
- Dependencies, weights, frameworks, research, standards, and adapted material are
  attributed separately from original QW5 work.

## Agent routing and cost control

Use the lowest-cost agent that can meet a frozen task contract:

- **Sol:** source-of-truth reconciliation, architecture or claim decisions,
  cross-cutting integration, and final adversarial review;
- **Terra:** bounded implementation, validator, CI, and documentation tasks with exact
  inputs, owned paths, and acceptance tests;
- **Luna:** deterministic fixture expansion, link normalization, inventory tables,
  and other mechanical work with exact expected output.

Most portfolio work is intentionally Terra- or Luna-sized. Do not use expensive model
or multi-agent modes to compensate for unclear scope. One task uses one branch,
worktree, provenance record, and draft pull request. Sol owns the three integration
gates defined by the completion plan.

## Non-negotiable boundaries

- Do not resume the historical M1–M5 cluster queue.
- Do not access or configure remote nodes.
- Do not download model weights or large artifacts.
- Do not fabricate measurements or promote synthetic data to `MEASURED`.
- Do not claim an inference engine, model compatibility, deployment, benchmark, or
  performance result that is not present and reproducible.
- Do not merge, close, or rewrite PR #3 without the explicit disposition step in
  portfolio task `P01`.
- Do not expose credentials, serial numbers, addresses, hostnames, usernames, personal
  paths, private prompts, hidden reasoning, or raw private transcripts.

## Completion and publication

Execute portfolio tasks `P00` through `P10` in dependency order. Each task freezes its
scope on the active board, updates provenance, runs its stated checks, and opens a
focused draft PR. The repository is complete only when the release definition and
global gates in
[`docs/portfolio/completion-plan.md`](docs/portfolio/completion-plan.md) pass and the
owner approves publication.
