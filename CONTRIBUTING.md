# Contributing to QW5

QW5 is being completed as an evidence-first Apple-silicon inference architecture case
study and offline reference kit. The original home-cluster implementation is no longer
active. Read [`PROJECT_HANDOFF.md`](PROJECT_HANDOFF.md), [`AGENTS.md`](AGENTS.md), and
[ADR-0008](docs/architecture/adr/0008-portfolio-transition.md) before proposing work.

## Useful contributions

- Correct an architecture, Apple-platform, model, license, or attribution fact using a
  primary source.
- Improve the deterministic contract validator, synthetic walkthrough, fixtures, or
  documentation checks defined by the
  [portfolio completion plan](docs/portfolio/completion-plan.md).
- Add a clearly labeled case study showing how the design method applies to a local
  model deployment without claiming QW5 executed it.
- Improve accessibility, diagrams, navigation, reproducibility, or newcomer guidance.
- Report a privacy leak, unsupported claim, broken link, nondeterministic test, or
  discrepancy between a schema and its prose contract.

Inference implementation, model downloads, cluster access, physical benchmarking, and
new performance claims are out of scope unless the owner explicitly starts a new
program with a current ADR and budget.

## Choose a bounded task

Select the next dependency-ready item in
[`docs/portfolio/completion-plan.md`](docs/portfolio/completion-plan.md). Freeze its
objective, paths, inputs, dependencies, non-goals, and acceptance checks on the active
board. One task uses one `codex/<task-name>` branch, one worktree, and one pull request.
Parallel writers require explicit authorization and disjoint paths.

Architecture changes, integration, ambiguous claim decisions, and final review route
to Sol. Terra receives bounded code or documentation tasks after contracts and tests
are frozen. Luna receives exact mechanical work such as fixture expansion or link
normalization. Use the lowest-cost route that can satisfy the task's gates; do not use
agent count as a substitute for a precise contract.

## Build and test

Install Zig 0.16.0, the version pinned by `.zig-version` and CI. The merged foundation
checks are:

```console
zig fmt --check build.zig src
zig build
zig build test
zig build smoke
```

Contract and portfolio tasks add their exact offline validation commands as they land.
Do not weaken a check because target hardware is unavailable; use synthetic fixtures
or mark the claim untested.

## Claims and evidence

Use `MEASURED`, `SIMULATED`, `ESTIMATED`, and `TARGET` exactly as defined in
[`README.md`](README.md). Distinguish merged code from draft pull-request work and
current behavior from historical design. QW5 has no measured cluster result and no
inference capability. A build, fixture, plausible report, or third-party benchmark
cannot change that status.

## Authorship, dependencies, and source use

Follow [`AI_PROVENANCE.md`](AI_PROVENANCE.md) and create the task-owned pull-request
record it requires. Dependencies, model weights, frameworks, papers, standards,
generated oracle data, and third-party material must be attributed separately.
Studying a reference is not permission to copy it. Direct adaptation of
non-AI-authored source requires an explicit provenance and licensing decision first.

Never submit credentials, private hostnames or addresses, serial numbers, machine
paths, personal data, hidden reasoning, or private transcripts. Preserve unrelated
working-tree changes and failed experiments that affect a decision.

## License

Unless explicitly stated otherwise, contributions intentionally submitted for
inclusion in QW5 are provided under the repository's
[Apache License 2.0](LICENSE), consistent with Section 5 of that license.
