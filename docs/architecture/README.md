# Architecture

QW5 is the design for a custom, Qwen-specific inference runtime on a heterogeneous
Apple Silicon cluster. It is currently a set of accepted boundaries and open
feasibility gates, not a working inference system.

## Non-negotiable invariants

- Correctness precedes optimization.
- Each model input is identified by repository, exact revision, and verified artifact
  hashes before execution or publication.
- Physical-link and kernel measurements precede placement decisions.
- Node A is the logical control plane, not a mandatory relay or compute exclusion.
- M5 Pro compute participation is allowed and decided by measurement.
- Direct peer-to-peer mesh communication is preferred when measurements support it.
- Prefill and decode have separate performance models and reports.
- SSD begins as a cold artifact and promotion tier, not an assumption of continuous
  active-weight streaming.
- CPU participation requires correctness, overlap, or measured-performance
  justification.
- Text-first Qwen3.5-397B feasibility remains an open gate.
- Negative and failed results that affect decisions are preserved and published.

## Runtime shape

Zig owns host control, model loading, artifact validation, memory management,
orchestration, transport, telemetry, and execution planning. Custom Metal kernels own
performance-critical GPU operations. CPU reference kernels establish correctness and
may participate in production only with evidence. Python is an offline tool for model
inspection, conversion, calibration, oracle generation, and analysis.

QW5 owns model and tensor identity, layouts, prefill and decode, KV and recurrent
state, MoE routing and dispatch, quantized execution, distributed scheduling,
transport, memory budgets, and telemetry. Complete external engines are references,
oracles, and baselines rather than production runtime components.

Distributed protocols will keep layer or recurrent-state transfer, expert dispatch,
expert results, control commands, telemetry, and artifact/model negotiation as
distinct message classes. The design will not assume all traffic relays through Node
A.

## Decision records

- [`ADR-0001: Model strategy`](adr/0001-model-strategy.md)
- [`ADR-0002: Runtime ownership and dependency boundaries`](adr/0002-runtime-ownership-and-dependency-boundaries.md)
- [`ADR-0003: Measurement before placement`](adr/0003-measurement-before-placement.md)
- [`ADR-0004: M1 evidence and artifact identity`](adr/0004-m1-evidence-and-artifact-identity.md)
- [`ADR-0005: Thunderbolt 5 application-path measurement`](adr/0005-thunderbolt5-application-path-measurement.md)
- [`ADR-0006: Memory fit is not deployment feasibility`](adr/0006-memory-fit-is-not-deployment-feasibility.md)

## Foundation decisions

The original QW5 project is licensed under Apache License 2.0. This supersedes the
pre-bootstrap MIT file. Dependencies and adapted material retain their own licenses
and attribution; replacing the project license does not relicense third-party work.

The toolchain baseline is Zig 0.16.0. Toolchain updates require an intentional change,
local and CI validation, and documentation of material language or runtime effects.
