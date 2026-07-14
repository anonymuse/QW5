# ADR-0006: Memory fit is not deployment feasibility

- **Status:** Proposed for acceptance with the M1 planning pull request
- **Date:** 2026-07-14
- **Decision owners:** Project owner and M1 planning task

## Context

A parameter-count floor can be useful for prioritization, but it excludes packing,
scales, zero points, higher-precision tensors, state, scratch buffers, transport
buffers, fragmentation, operating-system headroom, and quality loss. Aggregate
physical memory also does not prove that a legal per-node placement exists.

Qwen3-Coder-Next and Qwen3.5-397B-A17B therefore require exact tensor inventories and
explicit placement budgets before M1 can advise later implementation.

## Decision

M1 separates four decisions:

1. **Artifact completeness:** immutable revision, complete file list, byte sizes, and
   hashes are verified.
2. **Representational size:** a concrete quantization layout, including metadata,
   padding, alignment, higher-precision exceptions, and transformed-artifact hashes,
   has an exact or reproducibly estimated size.
3. **Memory placement:** every resident weight, state, scratch, transport, staging,
   fragmentation, and operating-system reserve is assigned to a node for a declared
   workload, with nonnegative headroom on every node.
4. **Deployment feasibility:** correctness, quantization quality, required kernels,
   transport, thermal behavior, and runtime stability are demonstrated separately.

Passing an earlier decision does not imply a later one. M1 may issue `GO` only for the
scope `proceed to the next evidence task`. It may issue `CONDITIONAL_GO`, `NO_GO`, or
`UNDETERMINED` for a proposed memory placement. It may not claim that either model
runs, meets quality, or achieves a performance target.

The Qwen3.5 text-first analysis does not discard vision tensors merely because the
initial execution target is text. An exclusion is allowed only when the exact model
revision and a reviewed loader/execution dependency analysis prove the tensors are
not needed by the text path. Both the complete upstream artifact and any justified
text-execution subset remain identified.

Quantization candidates are concrete format specifications, not a bit-width label.
Each candidate records packing order, group shape and axis, scale and zero-point
dtypes, outlier policy, alignment, padding, per-tensor exceptions, calibration
identity where applicable, and output hashes when artifacts exist. Size evidence does
not substitute for quality evidence.

## Consequences

- The existing **ESTIMATED** 99.25 GB two-bit language-parameter floor for
  Qwen3.5-397B remains a lower-bound calculation, not a placement or capability claim.
- M1 can complete honestly with a negative or undetermined 397B gate.
- Per-node headroom, not aggregate 144 GB, controls placement acceptance.
- Missing kernel scratch or state bounds appear as sensitivity ranges or unresolved
  inputs; they are not set to zero.
