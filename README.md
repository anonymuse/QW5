# QW5

QW5 is a research engineering project building a Qwen-specific inference engine for a
heterogeneous Apple Silicon cluster. It will test whether model-aware tensor layouts,
sparse-expert scheduling, unified-memory management, custom Metal kernels, and
measured peer-to-peer transport can make frontier-class Qwen inference practical
across three directly connected Macs without adopting another complete inference
engine as the production runtime.

QW5 is currently at project-foundation stage. This repository does **not** yet contain
an inference engine, distributed inference, verified Qwen execution, performance
results, or a demonstrated deployment of a 397B model. It contains the project
contracts, initial architecture decisions, benchmark rules, a minimal Zig executable,
and a deterministic smoke test.

## Evidence labels

QW5 uses these labels consistently in public technical material:

- **MEASURED** — observed by a documented procedure on identified hardware and
  software, with raw artifacts retained.
- **SIMULATED** — produced by a named simulation and its declared assumptions, not by
  the target runtime on the target cluster.
- **ESTIMATED** — calculated or inferred from stated inputs and assumptions.
- **TARGET** — a desired capability, constraint, or threshold that has not yet been
  demonstrated.

An unlabeled implementation fact, such as a file path or command name, is not a
performance result. Quantitative results must carry one of the labels above.

## Direction and status

**TARGET:** QW5 will use Zig for host runtime, orchestration, transport, model loading,
artifact validation, and memory management, with custom Metal kernels for
performance-critical GPU operations. CPU reference kernels and measured CPU
participation are allowed. Focused dependencies and Python offline tooling are also
allowed.

The production runtime will not be llama.cpp, MLX, PyTorch, Transformers, or another
complete inference engine. Those projects may be correctness oracles, conversion
references, research inputs, and benchmark baselines.

The planned model sequence is:

1. **TARGET:** [`Qwen/Qwen3-Coder-Next`](https://huggingface.co/Qwen/Qwen3-Coder-Next)
   for the first end-to-end text implementation.
2. **TARGET:** text-first
   [`Qwen/Qwen3.5-397B-A17B`](https://huggingface.co/Qwen/Qwen3.5-397B-A17B)
   as the flagship feasibility gate; multimodal support follows verified text
   inference.
3. **TARGET:** defer `Qwen3-Coder-480B-A35B-Instruct` until memory and quantization
   results establish adequate headroom.

The upstream facts behind this sequence, including exact source revisions checked for
the bootstrap, are recorded in
[`ADR-0001`](docs/architecture/adr/0001-model-strategy.md).

## Initial cluster

- Node A: M5 Pro, 48 GB unified RAM, 1 TB SSD; logical control plane and eligible
  compute participant.
- Node B: M5 Max, 48 GB unified RAM, 1 TB SSD.
- Node C: M5 Max, 48 GB unified RAM, 1 TB SSD.
- Each node has a direct Thunderbolt 5 link to each other node.

These are owner-supplied configuration inputs, not benchmark results. Exact GPU
configuration, available memory, storage, operating-system build, link behavior,
thermal state, and bandwidth remain to be inventoried and **MEASURED**. See the
[`hardware topology`](docs/hardware/topology.md).

## Bootstrap executable

The supported toolchain is Zig **0.16.0**, verified against the local Apple-silicon
development environment and pinned in CI. The CI job runs on GitHub's Apple-silicon
`macos-15` runner.

```console
zig version
zig fmt --check build.zig src
zig build
zig build test
zig build smoke
zig build run -- inventory
```

`zig build smoke` checks a fixed output string. `inventory` is read-only and reports
only compiler-target metadata in the bootstrap schema; it does not claim to inventory
the three-node cluster. The complete probe is an M1 deliverable described in the
topology document.

## Working agreements

Start with [`PROJECT_HANDOFF.md`](PROJECT_HANDOFF.md) and [`AGENTS.md`](AGENTS.md).
Durable task state lives under [`docs/coordination`](docs/coordination/README.md), and
architecture decisions live under [`docs/architecture`](docs/architecture/README.md).
Benchmark publication must follow
[`docs/benchmarks/methodology.md`](docs/benchmarks/methodology.md).

QW5 is independent of QW3 and QW4. QW3 continues independently; QW4 remains a frozen
architectural artifact. Their Git histories and source are not being merged into QW5.
Clean-room, AI-authored reimplementation is the default. Any future source adaptation
requires an explicit provenance and licensing decision before it begins.

## License and authorship

QW5 is licensed under the [Apache License 2.0](LICENSE). This replaces the repository's
pre-bootstrap MIT selection as an explicit project-foundation decision.

Original QW5 code and documentation are intended to be AI-authored, human-directed,
publicly reviewed, and evidence-verified. Dependencies, model weights, frameworks,
research, standards, and any adapted third-party material are attributed separately.
See [`AI_PROVENANCE.md`](AI_PROVENANCE.md) and [`CONTRIBUTING.md`](CONTRIBUTING.md).
