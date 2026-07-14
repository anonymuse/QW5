# QW5 agent instructions

These instructions apply to the entire repository. More specific `AGENTS.md` files may
narrow behavior for a subtree but may not relax the project boundaries below.

## Required startup reading

Before editing:

1. Read `README.md`, `PROJECT_HANDOFF.md`, this file, and
   `docs/coordination/README.md`.
2. Read `docs/coordination/workflow.md`, `docs/coordination/active-board.md`, and
   `docs/architecture/README.md`.
3. Read every ADR and domain document relevant to the task.
4. Inspect the current branch, status, remotes, tracked files, and existing changes.
5. Confirm the task starts from current `main` unless the owner explicitly specifies a
   different reviewed base.

`PROJECT_HANDOFF.md` is the approved project direction. If a current primary source
conflicts with it, stop before encoding the disputed fact, record the evidence, and
request a decision.

## Task and branch discipline

- Use one task, one `codex/<task-name>` branch, one worktree, and one pull request.
- Keep the pull request draft until its acceptance checks and provenance record are
  complete.
- Do not mix unrelated cleanup, speculative features, or drive-by refactors into a
  task.
- Do not delete a branch or worktree without explicit confirmation.
- Do not merge QW3 or QW4 Git history into QW5.

## Commit authorship

- Every Git commit created by Codex MUST include this trailer exactly:

  `Co-authored-by: OpenAI Codex <codex-ai@users.noreply.github.com>`

- Use this commit-message template:

  ```console
  git commit -m "Commit message" \
    -m "Co-authored-by: OpenAI Codex <codex-ai@users.noreply.github.com>"
  ```

- Do not use `--author` to add Codex as a co-author; `--author` changes the
  commit's primary author. Use it only when the owner explicitly requests a
  different primary author.
- Verify the trailer is present before handoff.

## Scope and path ownership

Every active task must state its objective, owned paths, inputs, dependencies, and
acceptance checks in the active board or linked specification. Edit only owned paths.
If necessary work falls outside them, update the durable scope before editing.

No parallel write work is allowed unless the task explicitly authorizes it and assigns
disjoint owned paths. Shared generated files, dependency locks, build definitions, and
coordination records require a single named owner.

## Project boundaries

- Default to clean-room, AI-authored reimplementation.
- QW3, QW4, DS4, llama.cpp, MLX, and other implementations are references and
  baselines, not source donors.
- Do not adapt non-AI-authored source without an explicit prior provenance and
  licensing decision.
- Do not make llama.cpp, MLX, PyTorch, Transformers, or another complete engine the
  QW5 production runtime.
- Do not download models, generate large artifacts, configure remote nodes, or run
  costly benchmarks unless the task expressly authorizes them.

## Validation and review

Run checks proportional to the change. Zig changes normally require:

```console
zig fmt --check build.zig src
zig build
zig build test
zig build smoke
```

Before publication, review the complete diff for unsupported claims, conflicting or
duplicate instructions, unattributed adaptation, license inconsistency, secrets,
personal data, and private task transcripts. Quantitative technical claims must use
the evidence labels defined in `README.md` and follow the benchmark methodology.
Correctness precedes optimization.

## Durable coordination state

Repository documents, not task transcripts, are the source of truth. Update the active
board when scope, ownership, dependencies, decisions, blockers, validation, or handoff
state changes. Record durable architecture decisions as ADRs and preserve benchmark
inputs and negative results under documented artifact conventions.

Do not publish private prompts, hidden reasoning, credentials, machine secrets,
personal data, or raw private task transcripts.

## Preserve-first cleanup

- Treat unknown or unrelated changes as owner data.
- Never discard, overwrite, mass-format, or stage unrelated work.
- Inspect before cleanup; prefer moving uncertain material to a clearly documented
  holding location over deletion.
- Never use destructive Git recovery commands without explicit owner approval.
- Preserve failed experiments and negative results when they inform project decisions.

## AI provenance

Every pull request must add or update its task-owned record at
`docs/provenance/pr-NNNN.md`, following the policy and template in
`AI_PROVENANCE.md`. The record contains the coding surface and model family, reasoning
setting only when verifiable, task objective, material human direction, materially
changed files, validation, review process, dependencies and external references,
adapted non-AI-authored material, and human interventions or decisions. Only the task
owner writes the record while its pull request is open; the record is immutable after
merge.

Separate claims about original QW5 work from dependencies, model weights, frameworks,
research, standards, and third-party material. Never claim a model or reasoning
setting that was not visible or otherwise verifiable.

## GPT-5.6 task routing

Model selection occurs when a separate task is launched; do not assume a running task
should switch among model variants.

- **Sol:** architecture, contracts, ambiguous or cross-cutting work, integration, hard
  debugging, benchmark interpretation, and final review.
- **Terra:** separate bounded implementation tasks after contracts, inputs, owned
  paths, and acceptance tests are frozen.
- **Luna:** separate mechanical or high-volume tasks with exact expected output.
- **Max:** deeper reasoning for one difficult task that benefits from unified context.
- **Ultra:** later multi-agent execution only when explicitly requested and when the
  work decomposes into independent bounded tasks. Ultra is not a stronger reasoning
  level.

Sol owns integration and final review when later tasks are split. Larger context or
more agents do not justify speculative architecture, overlapping writes, or unverified
claims.
