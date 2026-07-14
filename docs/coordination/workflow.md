# Development workflow

## 1. Establish the task contract

Before implementation, record:

- objective and explicit non-goals;
- base revision and task branch;
- single owner and model routing appropriate to the work;
- owned paths, including shared generated files;
- frozen inputs, contracts, and dependencies;
- acceptance tests and publication checks;
- decisions or artifacts expected from the task.

If these are ambiguous or cross-cutting, the task routes to Sol and remains `proposed`
until the contract is coherent. Terra receives a separate task only after the contract,
inputs, paths, and acceptance tests are frozen. Luna receives a separate task only for
mechanical work with exact expected output.

## 2. Create one isolated line of work

Start from fetched, current `main`. Use exactly one `codex/<task-name>` branch, one
worktree, and one pull request. Confirm repository identity, status, remotes, and
existing changes before editing. Preserve unrelated work.

Follow-up fixes for a draft pull request stay on that task's branch and in that pull
request. A materially new objective requires a new task contract after the current
work is merged or intentionally closed.

## 3. Implement within owned paths

Update the active board before expanding scope. No parallel write work is allowed
unless explicitly authorized with disjoint paths. A single owner controls shared build
files, locks, schemas, coordination records, and generated indexes.

Default to clean-room, AI-authored implementation. Reference projects may inform
behavior and tests. Direct source adaptation begins only after a recorded licensing
and provenance decision.

## 4. Validate evidence and behavior

Run the acceptance checks plus change-appropriate formatting, build, unit,
correctness, and integration checks. For Zig foundation changes, the baseline is:

```console
zig fmt --check build.zig src
zig build
zig build test
zig build smoke
```

Benchmark and feasibility work must follow `docs/benchmarks/methodology.md`. A failure
or negative result is preserved when it changes an architecture decision.

## 5. Review the complete diff

Before commit, inspect every changed path for:

- unsupported present-tense capability, correctness, performance, feasibility,
  novelty, or priority claims;
- misuse of `MEASURED`, `SIMULATED`, `ESTIMATED`, or `TARGET`;
- duplicated or conflicting policy;
- copied or insufficiently attributed material;
- dependency, license, and provenance inconsistencies;
- credentials, secrets, personal data, hidden reasoning, or private transcripts;
- unrelated changes or destructive cleanup.

Sol performs final review for cross-cutting or integrated work.

## 6. Publish and hand off

Create a focused commit, push the task branch, and open one draft pull request. The
pull request states scope, rationale, impact, checks, known limits, open decisions, and
provenance. Move the board item to `review` and add the pull-request link. Merge,
branch deletion, and worktree deletion remain explicit human decisions.
