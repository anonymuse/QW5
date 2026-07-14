# Benchmark methodology

QW5 benchmarks exist to test correctness and architecture decisions, not to manufacture
a favorable headline. No performance result is valid without a reproducible record.

## Evidence classes

- **MEASURED:** Observed by the documented procedure on identified hardware and
  software. Raw outputs and run metadata are retained.
- **SIMULATED:** Produced by a named simulator from declared inputs and assumptions.
  It is not target-cluster runtime behavior.
- **ESTIMATED:** Calculated or inferred from stated inputs and assumptions, including
  theoretical storage floors.
- **TARGET:** A desired threshold or capability that has not been demonstrated.

Do not combine classes in a chart or table without labeling each series or value. A
simulation calibrated with measurements remains `SIMULATED` unless the displayed value
itself was observed.

## Correctness gate

Correctness precedes optimization. A performance result must identify the correctness
test, oracle or independently generated fixture, tolerance, sampling configuration,
and outcome that permits the benchmark. Qwen correctness is not inferred from a build,
smoke test, plausible text, or agreement with a single unpinned runtime.

Small schemas, correctness fixtures, reproducibility manifests, and reviewed benchmark
artifacts belong in source control. Large raw data uses a content-addressed external
location referenced by a committed manifest.

## Required identity record

Every published run records:

- QW5 commit and dirty-state flag;
- model repository, exact immutable revision, and hashes for every artifact consumed;
- tokenizer, prompt template, and special-token identity;
- quantization scheme and parameters by tensor class;
- dependency, oracle, converter, compiler, and operating-system versions;
- node chip, memory, GPU configuration, storage state, power mode, and thermal context;
- physical topology and the exact link-profile artifact used for placement;
- configuration and schema versions plus command or harness identity.

Secrets, personal paths, serial numbers, and other machine-identifying private data are
excluded or safely normalized.

## Workload description

Record dataset or prompt hashes, context length, prompt tokens, generated tokens,
batching, concurrency, seed, sampling values, stop conditions, warmup, repetitions, and
cache state. Separate at minimum:

- prefill latency and prompt-token throughput;
- time to first token;
- autoregressive decode inter-token latency and generated-token throughput;
- end-to-end latency, reported only in addition to the separated phases.

Prefill and decode require separate performance models. Do not average them into one
rate that hides their different compute, memory, state, and transport behavior.

## Cluster and transport record

Record placement by tensor and state class, memory allocated and available on each
node, message class, source and actual destination, payload bytes, checksums, copy
counts, synchronization, retries, and link concurrency. Measure A-B, A-C, and B-C in
both directions, first alone and then under representative simultaneous traffic.

Node A's control role does not imply a required data relay. CPU time, GPU time, transfer
time, waiting, and overlap should be attributable where the platform permits.

## Baselines and comparison

Name the baseline engine, exact revision, model artifact, quantization, hardware,
context, sampling, warmup, and invocation. Prefer identical artifacts and workload;
otherwise list every known mismatch. Report a baseline as evidence, not as part of the
QW5 production runtime.

## Repetition and reporting

Choose warmup and repetitions before inspecting favorable results. Retain individual
runs and report sample count, median, dispersion, and relevant tails rather than only
the best run. Document exclusions with reasons. Record thermal or power changes when
available and never silently mix materially different regimes.

## Negative results and publication

Preserve failures, regressions, and infeasible placements when they inform an ADR or
gate. A report states limitations, anomalies, and unverified hypotheses. Qwen3.5-397B
deployment, long-context behavior, quality at a quantization, distributed scaling, and
performance advantage remain open until separate evidence supports each claim.
