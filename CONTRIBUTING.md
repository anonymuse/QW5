# Contributing to QW5

QW5 welcomes review, experiments, documentation, and implementation that respect its
clean-room and evidence-first boundaries. Read `PROJECT_HANDOFF.md` and `AGENTS.md`
before proposing work.

## Choose a bounded task

Open or select work with a concrete objective, owned paths, frozen inputs and
contracts, dependencies, and acceptance checks. Record active ownership in
`docs/coordination/active-board.md`. One task uses one `codex/<task-name>` branch, one
worktree, and one pull request. Parallel writers require explicit authorization and
disjoint paths.

Architecture, contracts, ambiguous cross-cutting changes, integration, difficult
debugging, benchmark interpretation, and final review route to Sol. Terra is for
separate bounded implementation after contracts and tests are frozen. Luna is for
separate mechanical work with exact output. Max is a reasoning choice for one hard
task. Ultra is a later multi-agent execution mode, not a stronger reasoning level, and
must be explicitly requested for independently decomposable work.

## Build and test

Install Zig 0.16.0, the version pinned by `.zig-version` and CI. For Zig changes, run:

```console
zig fmt --check build.zig src
zig build
zig build test
zig build smoke
```

Document additional correctness, benchmark, schema, or artifact checks in the pull
request. A benchmark result is not reviewable unless it follows
`docs/benchmarks/methodology.md`.

## Claims and evidence

Use `MEASURED`, `SIMULATED`, `ESTIMATED`, and `TARGET` exactly as defined in
`README.md`. Distinguish current capability from intent. Preserve negative results and
do not claim correctness, performance, feasibility, novelty, or priority without
reviewable evidence.

## Authorship, dependencies, and source use

Original QW5 code and documentation should be AI-authored, human-directed, publicly
reviewed, and evidence-verified. Follow `AI_PROVENANCE.md` and record the required
pull-request provenance in the task-owned `docs/provenance/pr-NNNN.md` file.

Dependencies, model weights, frameworks, papers, standards, generated oracle data,
and third-party material must be attributed separately. Studying a reference is not
permission to copy it. Direct adaptation of non-AI-authored source requires an
explicit provenance and licensing decision before implementation.

Never submit credentials, machine secrets, private transcripts, hidden reasoning, or
personal data. Preserve unrelated working-tree changes and request clarification
instead of deleting uncertain files.

## License

Unless explicitly stated otherwise, contributions intentionally submitted for
inclusion in QW5 are provided under the repository's Apache License 2.0, consistent
with Section 5 of that license.
