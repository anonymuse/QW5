# ADR-0003: Measurement before placement

- **Status:** Historical reference; implementation authority superseded by ADR-0008
- **Date:** 2026-07-14

> [!NOTE]
> The measurement discipline remains reusable, but QW5 did not perform the planned
> inventory or link/kernel measurements. See
> [ADR-0008](0008-portfolio-transition.md).

## Context

The initial cluster is heterogeneous and fully connected, but declared chip names and
link standards do not determine effective kernel throughput, transfer latency,
concurrency, copy count, thermal behavior, or usable memory. A hard-coded placement
based on marketing specifications would turn untested assumptions into architecture.

## Decision

Placement decisions require reproducible measurements of relevant kernels, memory
behavior, and every physical link before being accepted.

- Node A is the logical control plane and may own weights and computation.
- The M5 Pro participates whenever correctness, overlap, or **MEASURED** system
  performance supports it.
- Nodes B and C are expected to carry more heavy computation, but this is a hypothesis,
  not a fixed rule.
- Direct peer-to-peer communication is preferred over coordinator relay when
  **MEASURED** link and copy behavior supports it.
- A packet is accounted for by actual message and destination, not multiplied by an
  abstract count of activated experts.
- Prefill and autoregressive decode use separate performance models, traces, and
  placement conclusions.
- SSD starts as a cold artifact and promotion tier. Continuous active-weight streaming
  is not assumed without separate evidence.
- CPU participation requires correctness, useful overlap, or **MEASURED** performance
  justification.

Simulations and estimates may prioritize experiments, but must be labeled and may not
be presented as cluster results. Text-first Qwen3.5-397B feasibility remains open until
artifact sizes, headroom, kernels, links, placement, and quality are jointly tested.

## Required measurement inputs

- exact node hardware, OS build, available memory and storage, power state, and thermal
  context;
- A-B, A-C, and B-C links in both directions, alone and concurrently;
- payload size, transport, synchronization, checksum, copy count, and error behavior;
- kernel throughput and working-set behavior by node and tensor class;
- routing traces, quantization sensitivity, placement size, and network cost;
- prompt, prefill, decode, sampling, and run-to-run variation.

## Consequences

- Early schedulers must accept measured profiles rather than encode permanent chip
  rankings.
- Placement proposals state the evidence revision and assumptions they consume.
- Results that reject peer transfer, CPU work, SSD use, a quantization, or 397B
  feasibility are retained and published when they affect decisions.
