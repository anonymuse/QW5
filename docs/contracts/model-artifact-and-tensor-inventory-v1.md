# Model artifact and tensor inventory contracts v1

## Purpose

These contracts identify exactly which upstream bytes and tensors an M1 analysis
consumes. They cover `Qwen/Qwen3-Coder-Next` and
`Qwen/Qwen3.5-397B-A17B`; they do not authorize a download or select a new revision.

The schemas are
[`model-artifact-manifest.schema.json`](../../schemas/v1/model-artifact-manifest.schema.json)
and [`tensor-inventory.schema.json`](../../schemas/v1/tensor-inventory.schema.json).
SafeTensors parsing is further frozen by
[`safetensors-parser-profile.schema.json`](../../schemas/v1/safetensors-parser-profile.schema.json).
Both use [`qw5-json-c14n-v1`](canonical-json-v1.md) for artifact identity and require
schema plus repository semantic validation.

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

Before acquisition, Sol captures the immutable revision listing as a canonical
artifact, records its SHA-256, and freezes the sorted `expected_paths` selected from
that listing. The manifest file table must match that expected set exactly. Include
and exclude patterns explain the selection but cannot substitute for the explicit
path set or change after file results are visible.

## File and manifest hashing

SHA-256 is computed by streaming exact bytes from a read-only artifact. Symlink target
text, cache paths, and provider ETags are never substituted for content hashes. Every
verified file contains two ordered pass records, each with pass number, byte count,
SHA-256, and completion time. Both passes must match the accepted file identity; a
boolean assertion that a second pass happened is insufficient. The manifest uses
canonical bytes and path order. A parent gate report records its digest.

`complete` is derived, never self-asserted: every selected file is `verified`, every
selected component has its required role, missing/unexpected/error lists are empty,
the file table equals the frozen expected paths, both hash passes reconcile, and
verified file/byte totals equal the file table. An
incomplete or error manifest remains durable negative evidence but cannot pass G3.

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

An empty shape `[]` is a scalar: its element count is one and its stored bytes equal
one element of the declared dtype. A dimension containing zero is an empty tensor and
has zero elements; it is not a scalar. Integer element counts and byte sizes are
recomputed with checked arithmetic. Source
format ranges must be within the file and obey the format's overlap, hole, alignment,
and endianness rules. For SafeTensors, M1 follows the documented header, dtype, shape,
and data-offset semantics and pins the parser dependency or clean-room parser revision.
The [SafeTensors format description](https://github.com/safetensors/safetensors/blob/6eb4dc9a28ebce297606e0f4836bbf28839cacef/README.md#format)
is a reference, not source donated to QW5.

## SafeTensors parser profile

The Sol-owned v1 profile precedes any Terra parser task. It pins upstream commit
`6eb4dc9a28ebce297606e0f4836bbf28839cacef` and accepts exactly `BOOL`, `U8`, `I8`,
`U16`, `I16`, `F16`, `BF16`, `U32`, `I32`, `F32`, `U64`, `I64`, and `F64`.
Sub-byte and FP8 encodings are rejected in v1 rather than guessed.

QW5's safety limits are contract policy, not claims about upstream SafeTensors:

- maximum header: 16 MiB;
- maximum tensor records: 1,000,000;
- maximum rank: 16;
- maximum dimension: signed 64-bit maximum; and
- maximum shape product/element count: unsigned 64-bit maximum, with checked
  multiplication and checked dtype-byte multiplication.

The parser reads the little-endian u64 header length, rejects a truncated/oversized
header, requires strict UTF-8 and an object beginning with `{`, permits only ASCII
space padding, and rejects duplicate JSON members at every nesting level. Every tensor
record has only `dtype`, `shape`, and `data_offsets`; offsets must be ordered, in
bounds, contiguous, non-overlapping, and collectively cover the data buffer. Dtype,
shape, byte length, and range length reconcile exactly. The raw
[`safetensors-parser-v1.vectors.json`](../../fixtures/contracts/v1/safetensors-parser-v1.vectors.json)
includes a positive scalar plus duplicate-member, scalar-byte, unsupported-dtype, and
header-limit hostiles.

Source files record container, header, and data-section bytes. Totals are emitted by
file, component, semantic class, normalized dtype, layer, and expert class. Every
count and byte total is recomputed from the tensor list. Tensor names and owning
storage IDs are unique; dtype normalization, shape product, stored bytes, range
length, file bounds, overlap, hole, and full data-section coverage are checked with
bounded integer arithmetic. File container overhead remains separate from payload.
An alias names one owning tensor and repeats its exact file, dtype, shape, range, and
storage identity. Logical tensor/element counts include aliases; physical byte totals
and byte breakdowns count only owners.

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

Before the generic inspector becomes a Terra task, a separate Sol task accepts the
parser profile and freezes one versioned classification-rule artifact per immutable
model revision. Each rule names
the exact configuration field or tensor-name pattern, output component/semantic
class, permitted layer/expert captures, precedence, and negative examples. Rules must
be exhaustive or leave tensors explicitly `unclassified`; the inspector cannot invent
model semantics while implementing the parser.

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
file, hash/size mismatch on either pass, duplicate file path, false completeness,
duplicate tensor name, unknown dtype, shape/element/byte mismatch, reversed,
out-of-range, overlapping, or holed storage, duplicate SafeTensors JSON members,
unsupported dtype, oversized or malformed header, scalar byte/range mismatch, checked-
arithmetic overflow, missing quantization metadata,
non-reconciling file/layer/expert totals, unclassified tensor used by a class-dependent
placement, excluded vision tensor without a dependency rule, and private download or
machine data. Hostile miniature vectors exercise these invariants without model
weights or unsafe deserialization.
