# ADR-0001: Model strategy

- **Status:** Accepted
- **Date:** 2026-07-14
- **Decision owners:** Project owner and bootstrap architecture task

## Context

QW5 needs an attainable correctness target before attempting a cluster-scale flagship.
The sequence must reflect current upstream architecture facts, memory pressure, and
the rule that public feasibility follows evidence.

During bootstrap, the official Hugging Face model cards were checked at these upstream
`main` revisions:

- `Qwen/Qwen3-Coder-Next`:
  [`a7fbcb5c0e12d62a448eaa0e260346bf5dcc0feb`](https://huggingface.co/Qwen/Qwen3-Coder-Next/tree/a7fbcb5c0e12d62a448eaa0e260346bf5dcc0feb)
- `Qwen/Qwen3.5-397B-A17B`:
  [`8472618112abcbd45acbcdc58436aff4233c23f7`](https://huggingface.co/Qwen/Qwen3.5-397B-A17B/tree/8472618112abcbd45acbcdc58436aff4233c23f7)

The cards agree with the approved handoff on the facts used below; no conflict was
found. These revisions pin the bootstrap's source-of-fact review, not future model
artifacts. Every downloaded artifact set must later pin its own exact revision and
content hashes in a reproducibility manifest.

## Decision

### First working target

**TARGET:** Implement text inference for `Qwen/Qwen3-Coder-Next` first. The checked
official card describes an Apache-2.0 causal language model with 80B total and 3B
activated parameters, 48 layers, a hybrid Gated DeltaNet/gated-attention layout, 512
experts with 10 activated and one shared expert, and a native 262,144-token context.

This target establishes tokenizer and prompt behavior, model loading, hybrid-attention
and MoE correctness, CPU references, Metal bring-up, single-node execution, and then
distributed execution. None of those capabilities exists at bootstrap.

### Flagship target

**TARGET:** Treat `Qwen/Qwen3.5-397B-A17B` as a text-first feasibility gate. The
checked official card describes an Apache-2.0 causal language model with a vision
encoder; its language model has 397B total and 17B activated parameters, 60 hybrid
layers, 512 experts with 10 routed plus one shared, a native 262,144-token context, and
extension up to 1,010,000 tokens.

Multimodal work follows verified text correctness. The model's vision capability is an
upstream architecture fact, not a current QW5 capability.

**ESTIMATED:** A two-bit floor for 397 billion language parameters is about 99.25 GB
using decimal bytes. This excludes quantization metadata, higher-precision tensors,
vision components, runtime state, scratch space, fragmentation, and operating-system
headroom. Therefore Qwen3.5-397B deployment is explicitly unproven.

### Deferred target

**TARGET:** Defer `Qwen3-Coder-480B-A35B-Instruct` until quantization and memory work
establishes adequate headroom. **ESTIMATED:** Its corresponding two-bit parameter
floor is about 120 GB before runtime overhead.

## Consequences

- Correctness and artifact identity work centers on Qwen3-Coder-Next first.
- Qwen3.5 architecture needs may inform interfaces, but may not distort the first
  implementation without an accepted contract.
- No model download or artifact generation is authorized by this ADR.
- Quantization quality, placement, usable context, throughput, and 397B feasibility
  remain open measurement gates.
- A change in upstream facts is recorded by a new ADR or superseding revision rather
  than silently rewriting results.
