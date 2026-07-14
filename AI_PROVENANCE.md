# AI provenance

QW5 records enough public provenance to make its AI-authorship process reviewable
without publishing private task content. This file defines the policy and template;
it is not the mutable record for every pull request.

Do not include private prompts or transcripts, hidden reasoning, credentials, machine
secrets, personal data, or environment values that could identify or compromise a
machine. A concise summary of material human direction is sufficient.

## Storage and lifecycle

- Each pull request owns one record at `docs/provenance/pr-NNNN.md`, using its
  zero-padded pull-request number.
- The task owner may update that record while the pull request is open. No other
  concurrent task writes it.
- After merge, the record is immutable. A later correction is a separately reviewed,
  linked amendment rather than a rewrite of the original record.
- A repository-wide provenance index is optional and has one integration owner when
  a task explicitly authorizes updating it.

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
