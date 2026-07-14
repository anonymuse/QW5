# Coordination

This directory is the durable coordination source for QW5 work. It contains decisions
and task state that must survive a task transcript, tool session, or contributor
handoff.

- [`workflow.md`](workflow.md) defines the task lifecycle, scope contract, validation,
  and handoff rules.
- [`active-board.md`](active-board.md) records active ownership, branches, paths,
  dependencies, acceptance checks, and blockers.

Architecture belongs in ADRs, benchmark evidence belongs in reproducibility artifacts,
and AI-development disclosure uses the policy in `AI_PROVENANCE.md` plus task-owned
records under `docs/provenance/`. Coordination documents should link those records
rather than duplicate them.

Never place credentials, machine secrets, personal data, hidden reasoning, or private
task transcripts here. Record concise decisions and evidence sufficient for another
contributor to continue safely.

## Task states

- **proposed** — scope exists but ownership or inputs are not frozen.
- **ready** — objective, paths, inputs, dependencies, and acceptance checks are frozen.
- **active** — the named owner is writing within the declared paths.
- **review** — implementation and required local validation are complete.
- **blocked** — a named external decision or dependency prevents useful progress.
- **done** — the pull request is merged and durable follow-up state is recorded.

Only one task may own a path for writing at a time unless an explicit coordination
record proves the writes are disjoint.
