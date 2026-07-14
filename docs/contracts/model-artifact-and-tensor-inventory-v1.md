# Model artifact and tensor inventory contracts v1

## Purpose

These contracts identify exactly which upstream bytes and tensors an M1 analysis
consumes. They cover `Qwen/Qwen3-Coder-Next` and
`Qwen/Qwen3.5-397B-A17B`; they do not authorize a download or select a new revision.

The schemas are
[`model-artifact-manifest.schema.json`](../../schemas/v1/model-artifact-manifest.schema.json)
and [`tensor-inventory.schema.json`](../../schemas/v1/tensor-inventory.schema.json).

## Immutable model identity

A model manifest records:

- repository provider and exact repository ID;
- a full 40-character immutable revision resolved before acquisition;
- the originally requested reference, if any, as non-authoritative context;
- acquisition tool name, version, executable or package digest, QW5 commit, and dirty
  flag;
- repository license files and SHA-256 identities;
- every consumed file's relative POSIX path, role, exact byte size, SHA-256, media
  type, upstream object identity when available, and acquisition status; and
- explicit included and excluded path rules plus unexpected-file detection.

Branches such as `main`, tags, cache directory names, ETags, or filenames are not
immutable identity. Hugging Face's download API accepts full commit revisions; the M1
acquisition task must pass the full revision and verify every resulting file. See the
[Hugging Face download guide](https://huggingface.co/docs/huggingface_hub/guides/download).

The manifest includes configuration, generation configuration when consumed,
tokenizer files, special-token maps, chat or prompt templates, license and notices,
weight index files, and every weight shard used by the tensor inventory. Missing or
extra files fail completeness until reviewed.

## File and manifest hashing

SHA-256 is computed by streaming exact bytes from a read-only artifact. Symlink target
text, cache paths, and provider ETags are never substituted for content hashes. A
second independent pass verifies byte count and hash before the manifest is accepted.
The manifest is serialized in deterministic key and path order. A parent gate report
records the manifest's exact-byte digest.

## Tensor inventory

The inventory references one model manifest by SHA-256 and records parser identity,
source format, byte order, deterministic ordering rule, and every parsed tensor. Each
tensor contains:

- exact tensor name and source-file relative path;
- dtype spelling from the source plus normalized dtype;
- ordered shape, element count, stored bytes, and data byte range;
- component (`language`, `vision`, or `unclassified`);
- semantic class such as embedding, normalization, attention, recurrent state,
  router, routed expert, shared expert, output head, vision, or unclassified;
- layer, expert, and shard indices when derivable from the pinned configuration;
- storage identity and an explicit alias reference when the format permits sharing;
- source quantization metadata, or `none` when the tensor is not quantized; and
- classification status and rule ID so a naming heuristic is never presented as an
  upstream semantic fact.

Integer element counts and byte sizes are recomputed with checked arithmetic. Source
format ranges must be within the file and obey the format's overlap, hole, alignment,
and endianness rules. For SafeTensors, M1 follows the documented header, dtype, shape,
and data-offset semantics and pins the parser dependency or clean-room parser revision.
The [SafeTensors format description](https://github.com/huggingface/safetensors#format)
is a reference, not source donated to QW5.

Totals are emitted by file, component, semantic class, normalized dtype, layer, and
expert class. Every total must reconcile to the tensor list. File container overhead
is reported separately from tensor payload bytes.

## Quantization metadata

For an upstream or transformed quantized tensor, record all applicable fields:

- scheme name and version;
- weight bit width and signedness;
- packing word size, element order, endianness, block alignment, and padding bytes;
- group shape, grouping axis, and group count;
- scale dtype, shape, bytes, and storage reference;
- zero-point presence, dtype, shape, bytes, and storage reference;
- codebook, outlier, sparse-mask, permutation, or auxiliary tensor identities;
- source tensor SHA-256 and output tensor/artifact SHA-256;
- higher-precision exception rule;
- calibration dataset/artifact digest, tool revision, parameters, and seed when an
  artifact was calibrated; and
- quality-evidence references, kept separate from size metadata.

A label such as `2-bit` or `4-bit` without these fields is only a theoretical
candidate. It cannot be used for an exact placement decision.

## Reproducibility and safety

The producer records exact command parameters after removing local paths and secrets,
dependency versions, locale, and ordering rule. No Python object deserialization or
remote model code is required to inspect SafeTensors metadata. Any task proposing such
execution needs separate security and provenance review.

The public manifest contains no download token, cache location, username, hostname,
or local path. Large model bytes remain outside Git. Model licenses and notices are
identified as upstream material; they are not described as AI-authored QW5 content.

## Model-specific requirements

### Qwen3-Coder-Next

Use the owner-approved immutable revision. Reconcile every tensor against its pinned
configuration, including hybrid attention/recurrent layers, router, routed experts,
shared experts, embeddings, normalization, and output head. Unknown or variant names
remain `unclassified` and block any placement that depends on their semantic role.

### Qwen3.5-397B-A17B

Inventory language and vision components from the complete artifact. Produce a full
artifact total first. A text-execution subset is a separate, linked manifest whose
exclusions cite a reviewed dependency rule. Weight tying or shared storage is counted
once physically and represented explicitly; it is not guessed from equal shapes or
names.

## Acceptance and negative cases

Tests must reject a mutable revision, truncated hash, absolute path, missing consumed
file, hash/size mismatch, duplicate file path, duplicate tensor name, unknown dtype,
shape/element mismatch, out-of-range or overlapping storage, missing quantization
metadata, non-reconciling totals, unclassified tensor used by a class-dependent
placement, excluded vision tensor without a dependency rule, and private download or
machine data.
