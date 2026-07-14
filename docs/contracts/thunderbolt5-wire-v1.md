# QW5 TB5 measurement wire format v1

## Scope

`qw5-tb5-wire/v1` is the exact test-harness framing consumed by the M1 TB5 protocol.
It is a measurement format, not the QW5 production transport. Multi-byte integers are
unsigned network-byte-order values. Every reserved field is zero on transmit and is
rejected when nonzero. Connections are persistent within a scenario.

## Connection handshake

The sender writes one 96-byte handshake before timed traffic. It is validated before
the ready barrier and is excluded from timed sample byte counts.

| Offset | Bytes | Field |
| ---: | ---: | --- |
| 0 | 4 | ASCII `QW5H` |
| 4 | 2 | version `1` |
| 6 | 2 | handshake length `96` |
| 8 | 32 | raw SHA-256 bytes of the canonical run plan |
| 40 | 16 | first 16 bytes of SHA-256 over the UTF-8 scenario ID |
| 56 | 16 | first 16 bytes of SHA-256 over the UTF-8 flow ID |
| 72 | 1 | source code: A=`1`, B=`2`, C=`3` |
| 73 | 1 | destination code: A=`1`, B=`2`, C=`3` |
| 74 | 2 | flags; v1 requires zero |
| 76 | 8 | plan seed |
| 84 | 8 | payload bytes per message |
| 92 | 4 | reserved zero |

The receiver rejects a self-flow, identity mismatch, wrong route-bound peer, unknown
node code, or changed plan parameters before acknowledging readiness.

## Deterministic payload

Let `BE64` and `BE16` be unsigned big-endian encodings. Let `flow` be the exact UTF-8
flow ID, whose v1 length fits `BE16`.

```text
key = SHA256(BE64(seed) || BE16(len(flow)) || flow || BE64(payload_bytes))
block[i] = SHA256(key || BE64(sequence) || BE64(i))
payload = truncate(block[0] || block[1] || ..., payload_bytes)
```

The sender constructs or selects this payload outside the timed latency interval. A
streaming implementation may reuse a prebuilt ring only when the selected bytes still
match the sequence-specific formula.

## Data frame

A frame is a 64-byte header, the exact payload, and a 32-byte SHA-256 trailer.

| Offset | Bytes | Field |
| ---: | ---: | --- |
| 0 | 4 | ASCII `QW5D` |
| 4 | 2 | version `1` |
| 6 | 2 | header length `64` |
| 8 | 2 | flags; bit 0 requests an acknowledgement, all other bits zero |
| 10 | 2 | reserved zero |
| 12 | 8 | sequence number |
| 20 | 8 | payload bytes |
| 28 | 16 | first 16 bytes of the run-plan SHA-256 |
| 44 | 16 | first 16 bytes of SHA-256 over the UTF-8 flow ID |
| 60 | 4 | reserved zero |

The trailer is SHA-256 over payload bytes only. The receiver credits a message only
after header identity, exact length, monotonic sequence, deterministic payload, and
trailer digest all pass. Header, payload, trailer, and socket byte counts remain
separate.

## Acknowledgement

Round-trip mode sets data-header flag bit 0. After validating the complete frame, the
receiver returns exactly 64 bytes:

| Offset | Bytes | Field |
| ---: | ---: | --- |
| 0 | 4 | ASCII `QW5A` |
| 4 | 2 | version `1` |
| 6 | 2 | acknowledgement length `64` |
| 8 | 2 | status: `0` success; any other value is a failed exchange |
| 10 | 2 | reserved zero |
| 12 | 8 | echoed sequence number |
| 20 | 8 | echoed payload bytes |
| 28 | 32 | echoed payload SHA-256 |
| 60 | 4 | reserved zero |

Streaming mode does not request or send acknowledgements. TCP setup, handshake, and
ready-barrier bytes are recorded at run level but excluded from per-attempt throughput.
No byte class is silently subtracted from observed socket bytes.

## Exact vectors and negative tests

[`tb5-wire-v1.vectors.json`](../../fixtures/contracts/v1/tb5-wire-v1.vectors.json)
pins one handshake, deterministic payload, data header, digest trailer, and
acknowledgement as exact hex plus component SHA-256. The same file pins exact mutated
bytes and required error codes for bad magic/version/node/flow/reserved fields, unknown
flags, truncation, extra bytes, payload/digest corruption, acknowledgement mismatch,
and plan mismatch. The contract validator independently rebuilds every golden byte and
materializes every mutation. Harness tests must additionally reject oversize
declarations, partial reads/writes, duplicate or regressing sequence, and any
acknowledgement that does not echo the validated frame.
