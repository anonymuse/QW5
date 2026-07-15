# Active task board

Last updated: 2026-07-15

## Review

### M0 contract completion and M1 execution plan

- **State:** review
- **Owner:** Sol; single coherent architecture and contract task, no delegated or
  parallel writers
- **Base:** `main` at `c8e71bda5246c1e39b4d82ab416934b93280ff25`
- **Branch:** `codex/m1-contracts-and-measurement-plan`
- **Pull request:** [#3 — Complete M0 contracts and define the M1 execution plan](https://github.com/anonymuse/QW5/pull/3)
- **Objective:** Complete the M0 contract freeze assigned by `PROJECT_HANDOFF.md`,
  then define M1 entry and exit criteria, evidence and decision gates, the
  six-direction Thunderbolt 5 measurement protocol, model/tensor identity, placement
  and quantization-feasibility analysis, and an ordered follow-up pull-request plan.
- **Non-goals:** Model downloads, remote-node changes, physical cluster benchmarks,
  inference, quantization or Metal kernels, transport or distributed runtime
  implementation, model-feasibility claims, and edits to immutable merged provenance
  records.
- **Owned paths:** `docs/coordination/active-board.md`;
  `docs/coordination/m1-task-decomposition.md`;
  `docs/milestones/m1-feasibility-and-measurements.md`; `docs/contracts/`;
  `docs/architecture/README.md`; ADRs `0004` through `0007` under
  `docs/architecture/adr/`; `schemas/`; `fixtures/contracts/`;
  `tools/validate_contracts.py`; `requirements/contract-validation.txt`;
  `.github/workflows/ci.yml`; and this pull request's task-owned record under
  `docs/provenance/`.
- **Frozen inputs:** `PROJECT_HANDOFF.md`; accepted ADRs `0001` through `0003`;
  `docs/benchmarks/methodology.md`; `docs/hardware/topology.md`; owner-approved model
  sequence and declared three-node topology; model-card source revisions pinned by
  ADR-0001; JSON Schema draft 2020-12; SHA-256; and the owner-approved one-time
  exception for the missing immutable PR #1 provenance record.
- **Dependencies:** PR #1 and PR #2 merged. Contract validation adds only a pinned
  development/CI dependency; no production runtime dependency is added. External
  specifications and primary documentation are cited, not copied as implementation
  source.
- **Owner decision recorded:** On 2026-07-15 the owner selected the empirical
  coordinator-observed simultaneous-attempt inclusion rule (option 2). It is not a
  clock result, actual-start estimate, or one-way-timing claim.
- **Acceptance checks:** Fourteen machine-readable schemas pass draft 2020-12 meta-
  schema checks; positive fixtures pass schema and semantic validation; hostile
  mutations fail for their required error codes; the generated 108-control and
  246-cell bundles resolve every raw digest and projection; exact canonical, wire,
  TB5-evidence, and SafeTensors vectors reproduce;
  Markdown links resolve; existing Zig formatting, build, unit, smoke, and inventory
  checks pass; the complete diff passes evidence-label, unsupported-claim,
  privacy/secret, machine-identifier, attribution, provenance, and licensing review;
  focused commits include the required Codex co-author trailer; and one draft pull
  request documents decisions, open gates, routing, validation, and owner approvals.

## Ready

None. Follow-up M1 tasks become ready only after this planning pull request is
accepted and the project owner authorizes their stated external inputs or physical
access.

## Blocked

None.

## Recently completed

### M0 repository bootstrap and policy hardening

- **State:** done
- **Owner:** Sol; single coherent task, no delegated or parallel writers
- **Base:** `main` at `5e78a75fad3ee4150be12730ff8f0b24d67ba4a3`
- **Branch:** `codex/bootstrap-foundation`
- **Pull requests:** [#1 — Bootstrap QW5 project foundation](https://github.com/anonymuse/QW5/pull/1),
  merged as `6fcc41f1d945748a86e500012f624d2858afcb37` on 2026-07-14;
  [#2 — Bootstrap QW5 foundation and commit co-authorship policy](https://github.com/anonymuse/QW5/pull/2),
  merged as `c8e71bda5246c1e39b4d82ab416934b93280ff25` on 2026-07-14.
- **Outcome:** Established the repository bootstrap, policy, architecture and evidence
  boundaries, Zig 0.16.0 bootstrap and CI, conflict-resistant per-PR provenance
  policy, post-merge board reconciliation, inventory-command coverage, and the Codex
  commit co-authorship rule. The remaining M0 hardware/benchmark/model contract freeze
  is owned by PR #3; M1 implementation remains unstarted.
- **Known record exception:** PR #2 replaced the committed PR #1 provenance file with
  its own record. The project owner explicitly authorized M1 planning to proceed once
  without recreating or rewriting merged provenance; per-PR immutable records remain
  required for every future pull request.
