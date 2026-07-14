# AI provenance

QW5 records enough public provenance to make its AI-authorship process reviewable
without publishing private task content. Each pull request adds or updates a record
using the template below.

Do not include private prompts or transcripts, hidden reasoning, credentials, machine
secrets, personal data, or environment values that could identify or compromise a
machine. A concise summary of material human direction is sufficient.

## Pull-request record template

- **Date and pull request:**
- **Coding surface and model family:**
- **Reasoning setting:** Record only when visible or otherwise verifiable; otherwise
  write `not verifiable`.
- **Task objective:**
- **Material human direction:**
- **Files generated or materially changed:**
- **Tests and checks performed:**
- **Review process:**
- **Dependencies and external references:** Include versions or immutable revisions
  where material.
- **Adapted non-AI-authored source:** State `none` or identify the source, license,
  decision record, and affected paths.
- **Human interventions or decisions:**

## Bootstrap foundation record

- **Date and pull request:** 2026-07-14; draft pull request for
  `codex/bootstrap-foundation`.
- **Coding surface and model family:** Codex desktop; GPT-5.6 Sol, visible in the task
  interface.
- **Reasoning setting:** Extra High, visible in the task interface.
- **Task objective:** Establish the public QW5 repository foundation without
  implementing inference.
- **Material human direction:** The project owner supplied the QW5 handoff, runtime
  boundaries, initial three-node topology, model sequence, evidence requirements,
  Apache-2.0 selection, task-routing policy, bootstrap scope, and publication checks.
- **Files generated or materially changed:** Root project policy and contribution
  files; coordination, architecture, benchmark, and hardware documents; three ADRs;
  Zig build and source files; CI; toolchain pin; and ignore rules.
- **Tests and checks performed:** Zig formatting, build, unit tests, deterministic
  smoke test, inventory command inspection, full diff review, policy duplication and
  claim scans, license/provenance review, and secret/private-data scan.
- **Review process:** Single-task implementation followed by a complete diff review
  against the approved handoff and current primary model sources; draft pull request
  retained for public human review.
- **Dependencies and external references:** Zig 0.16.0 and its standard library;
  GitHub-hosted `macos-15`; immutable revisions of `actions/checkout` and
  `mlugg/setup-zig`; official Qwen Hugging Face model cards at the revisions recorded
  in ADR-0001; official Zig and GitHub runner documentation.
- **Adapted non-AI-authored source:** No implementation source adapted. `LICENSE` is
  the standard Apache License 2.0 text. GitHub Actions uses the published interfaces
  of attributed third-party actions.
- **Human interventions or decisions:** The owner selected the project direction,
  hardware inputs, target models, Apache-2.0 license, branch and publication workflow,
  and single-Sol execution policy.
