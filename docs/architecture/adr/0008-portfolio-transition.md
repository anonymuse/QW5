# ADR-0008: Conclude cluster implementation and publish the architecture case study

- **Status:** Accepted
- **Date:** 2026-07-19
- **Decision owner:** Project owner

## Context

QW5 began as a plan for a Qwen-specific inference engine spanning three heterogeneous
Apple-silicon Macs. The merged foundation established the thesis, runtime boundaries,
evidence vocabulary, benchmark discipline, three architecture decisions, a minimal
Zig utility, tests, and Apple-silicon CI. Draft pull request
[#3](https://github.com/anonymuse/QW5/pull/3) then designed a much deeper contract and
validation package for hardware inventory, Thunderbolt 5 measurement, model artifacts,
tensor inventories, placement, and quantization feasibility.

The physical program stopped before cluster measurement, model acquisition, inference,
Metal kernels, or distributed execution. The owner no longer intends to continue the
home-cluster program. Continuing the original M1–M5 implementation would therefore
spend time and money against an obsolete deployment decision.

The architecture work still demonstrates useful consulting capabilities: turning an
ambitious local-LLM idea into explicit system boundaries, evidence contracts, failure
gates, reproducibility rules, and an implementation sequence. Those artifacts can
also inform a future model-specific engine on one high-memory Apple-silicon machine,
with orchestration reconsidered only when a measured workload requires it.

The number `0008` preserves the public decision sequence: ADRs 0004–0007 already exist
in draft PR #3 even though they are not on merged `main` at the time of this decision.

## Decision

1. **Conclude the three-node implementation program.** QW5 will not execute its former
   M1–M5 cluster roadmap as the active project plan. No cluster hardware, model
   download, physical benchmark, kernel implementation, or inference runtime is
   required to complete the repository.
2. **Finish QW5 as a portfolio-grade architecture case study and reference kit.** The
   finished product will explain the original problem, the proposed architecture, the
   engineering artifacts produced, the gates that prevented unsupported claims, the
   decision to stop, and how the reusable methods apply to Apple-silicon deployments.
3. **Preserve provenance and state exactly.** Merged work, open draft work, synthetic
   fixtures, estimates, targets, and unimplemented aspirations remain visibly
   distinct. Curating PR #3 must retain its authorship record and review state; it may
   not be described as merged or executed retroactively.
4. **Make the case study runnable without specialized hardware.** The portfolio
   release should validate its schemas and fixtures and produce a deterministic,
   explicitly `SIMULATED` walkthrough from synthetic inputs. It must not fabricate
   cluster results or imply model compatibility.
5. **Treat a future inference engine as a new, separately authorized program.** Its
   default deployment order is one high-memory Mac first, model-specific correctness
   before optimization, and optional multi-node orchestration only after measurement.
   Model selection will be made at that future start from exact, then-current open-
   weight revisions rather than silently carrying QW5's 2026 targets forward.
6. **Retain the original architecture as a reference design.** ADRs 0001–0003 and the
   proposed ADRs/contracts in PR #3 remain technically useful historical decisions.
   They no longer authorize implementation or physical work.

## Portfolio completion boundary

QW5 is complete when:

- the README and case-study documents accurately distinguish outcomes from
  aspirations;
- the valuable PR #3 design assets have an explicit, provenance-preserving
  disposition;
- schemas, fixtures, semantic validation, the Zig bootstrap, and documentation checks
  run in CI from a clean checkout;
- a deterministic offline walkthrough demonstrates the evidence flow using only
  synthetic data labeled `SIMULATED`;
- an Apple-silicon cluster blueprint and a separate single-node future roadmap explain
  how the design can be reused;
- the repository has no active cluster-execution task, broken link, unsupported
  performance claim, private machine data, or ambiguous status; and
- a reviewed portfolio release records limitations and the intentional stop decision.

The detailed task sequence and acceptance gates live in
[`docs/portfolio/completion-plan.md`](../../portfolio/completion-plan.md).

## Consequences

- Stopping before hardware execution is a project outcome, not a benchmark failure.
- The repository showcases architecture, systems judgment, validation design, and
  responsible claim-making; it does not showcase a functioning inference engine.
- The former M1 task decomposition becomes historical source material. A smaller
  portfolio queue replaces it.
- No new quantitative claim can be promoted to `MEASURED` without the original
  methodology and identified hardware.
- A later single-node or clustered runtime requires a new ADR, current model and
  hardware inputs, an explicit budget, and a fresh execution plan.
