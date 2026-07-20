# Active task board

Last updated: 2026-07-19

## Active

None. The unavailable cluster is an intentional scope decision, not a blocker.

## Ready

None. The ordered portfolio queue lives in
[`docs/portfolio/completion-plan.md`](../portfolio/completion-plan.md) and begins only
after the current documentation package is published from a clean checkout of current
`main` as task `P00`.

## Blocked

None.

## Review

### Portfolio transition and completion plan

- **State:** review; documentation deliverables are complete in the clean,
  branch-aware checkout and draft-PR publication remains P00
- **Owner:** primary Codex task; single writer, no delegated or parallel writers
- **Base:** fetched remote `main` at
  `c8e71bda5246c1e39b4d82ab416934b93280ff25`
- **Branch:** `agent/portfolio-architecture-case-study`
- **Objective:** record the owner-approved end of the home-cluster implementation,
  reposition QW5 as an evidence-first Apple-silicon inference architecture case study,
  publish a flagship README, and create an execution-complete plan for lower-cost
  coding agents to finish the portfolio release.
- **Non-goals:** implementing inference, merging or closing pull requests, downloading
  models, accessing Apple hardware, configuring nodes, running physical benchmarks,
  claiming measured performance, or creating a release.
- **Owned paths:** `README.md`, `PROJECT_HANDOFF.md`, `AGENTS.md`, `CONTRIBUTING.md`,
  `docs/architecture/README.md`, ADRs `0001`–`0003` status annotations,
  `docs/architecture/adr/0008-portfolio-transition.md`,
  `docs/benchmarks/methodology.md` status annotation, `docs/hardware/topology.md`,
  `docs/portfolio/completion-plan.md`, and this board.
- **Frozen inputs:** the owner's 2026-07-19 pivot; merged PRs
  [#1](https://github.com/anonymuse/QW5/pull/1) and
  [#2](https://github.com/anonymuse/QW5/pull/2); draft PR
  [#3](https://github.com/anonymuse/QW5/pull/3) at
  `ad45675088a27c2e05ad7cd89e683bfb169fd4e7`; existing architecture, benchmark, and
  provenance policy; official upstream links cited by the README.
- **Dependencies:** documentation and existing source only; no model weights, remote
  machines, paid services, or new runtime dependencies.
- **Validation:** all 17 Markdown files have resolving local links and balanced code
  fences; changed-file whitespace checks pass; repository Markdown is valid UTF-8;
  privacy/secret/path scans found no candidate; current GitHub repository, PR, and
  PR #3 file-count state were inspected; external primary links used by the new
  narrative resolve. Zig checks were not run because `zig` is not available on the
  WSL execution PATH; no Zig source or build file changed.
- **Expected durable artifacts:** portfolio README, current handoff, transition ADR,
  historical-topology annotation, contributor/agent guardrails, and the portfolio
  completion plan.

### M0 contract completion and M1 planning

- **State:** review; historical cluster-program work pending the disposition decision
  in portfolio task `P01`
- **Owner:** original PR #3 task
- **Base:** `main` at `c8e71bda5246c1e39b4d82ab416934b93280ff25`
- **Branch:** `codex/m1-contracts-and-measurement-plan`
- **Pull request:** [#3 — Complete M0 contracts and define the M1 execution plan](https://github.com/anonymuse/QW5/pull/3)
- **Outcome:** a validated design package containing 16 schemas, 16 positive fixtures,
  87 hostile cases, four proposed ADRs, canonical evidence rules, a semantic validator,
  and a 16-task cluster measurement plan. It did not perform M1, access hardware,
  download models, or implement inference.
- **Disposition:** preserve the engineering work, curate it into the portfolio release,
  and close or supersede the obsolete execution queue without representing the draft
  as merged history. Exact steps and acceptance gates are defined by portfolio task
  `P01`.

## Recently completed

### Repository foundation

- **State:** done
- **Pull requests:** [#1 — Bootstrap QW5 project foundation](https://github.com/anonymuse/QW5/pull/1) and
  [#2 — Bootstrap QW5 foundation and commit co-authorship policy](https://github.com/anonymuse/QW5/pull/2)
- **Merge commit:** `c8e71bda5246c1e39b4d82ab416934b93280ff25`
- **Completed:** 2026-07-14
- **Outcome:** public policy, architecture records, evidence rules, Zig 0.16.0
  bootstrap executable, read-only compiler-target inventory, tests, and CI.
