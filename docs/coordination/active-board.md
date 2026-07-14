# Active task board

Last updated: 2026-07-14

## Review

### Repository foundation

- **State:** review
- **Owner:** Sol; single coherent task, no delegated or parallel writers
- **Base:** `main` at `5e78a75fad3ee4150be12730ff8f0b24d67ba4a3`
- **Branch:** `codex/bootstrap-foundation`
- **Pull request:** [#2 — Bootstrap QW5 foundation and commit co-authorship policy](https://github.com/anonymuse/QW5/pull/2)
- **Objective:** Establish public repository policy, architecture records, evidence
  rules, Zig 0.16.0 bootstrap executable, read-only bootstrap inventory, and CI without
  implementing inference.
- **Non-goals:** Model downloads, tensor conversion, inference, Metal kernels,
  quantization, remote-node configuration, distributed transport, and performance
  claims.
- **Owned paths:** All paths created or modified by the bootstrap pull request. No
  other writer is authorized for this task.
- **Frozen inputs:** `PROJECT_HANDOFF.md`; owner-selected hardware and model sequence;
  official Qwen model cards identified by ADR-0001; Apache License 2.0; Zig 0.16.0;
  Apple-silicon `macos-15` CI runner.
- **Dependencies:** Zig standard library; pinned `actions/checkout` and
  `mlugg/setup-zig` actions for CI only.
- **Acceptance checks:** Formatting, build, unit tests, deterministic smoke test,
  inventory inspection, full diff review, instruction/claim/attribution/license scans,
  secret and private-data scan, focused commit, branch push, and draft pull request.

## Ready

None. M1 work must be decomposed and accepted after the foundation pull request is
reviewed.

## Blocked

None.

## Recently completed

None; this is the initial board.
