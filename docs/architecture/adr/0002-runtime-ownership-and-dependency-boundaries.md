# ADR-0002: Runtime ownership and dependency boundaries

- **Status:** Accepted
- **Date:** 2026-07-14

## Context

QW5 is intended to expose and investigate the hard systems work of Qwen inference on
Apple Silicon. Using a complete existing engine as the production executor would make
the central architecture and authorship claims misleading. Reimplementing every
supporting utility would also waste effort and increase risk.

## Decision

QW5 will own the production inference path:

- model loading, artifact manifests, tensor identity, layout, and validation;
- prefill and decode execution;
- KV-cache and recurrent-state management;
- hybrid attention, MoE routing, expert dispatch, and result reduction;
- quantized kernel execution;
- distributed scheduling, transport, placement, memory budgets, and telemetry.

Zig is the host language for runtime control, orchestration, transport, loading,
validation, and memory management. Custom Metal kernels implement performance-critical
GPU operations. CPU reference kernels establish correctness. CPU production work is
allowed only when correctness, useful overlap, or **MEASURED** performance justifies
it.

Focused third-party libraries and Apple frameworks are allowed when their surface is
narrow, license-compatible, attributed, pinned where material, and does not transfer a
QW5-owned runtime responsibility to a complete engine. Python is allowed for offline
inspection, conversion, calibration, oracle generation, analysis, and reproducibility
tooling; it is not the production executor.

llama.cpp, MLX, PyTorch, Transformers, vendor runtimes, and similar systems may be used
as correctness oracles, conversion references, behavioral research inputs, and
benchmarks. They may not become the QW5 production runtime.

Original QW5 work is Apache-2.0. Dependencies and external material are attributed
under their own licenses. Direct adaptation of non-AI-authored source requires an
explicit provenance and licensing decision before code is written; clean-room,
AI-authored implementation is the default.

## Consequences

- A dependency proposal must name the owned problem it solves, alternative considered,
  runtime surface, license, version or revision policy, and removal boundary.
- Oracle output and converted artifacts carry provenance and exact tool versions.
- Correctness may be compared with complete engines without linking or embedding them
  into production QW5.
- Negative results about custom implementation choices are publishable outcomes, not
  permission to obscure a change in runtime ownership.
