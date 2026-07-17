# QW5 canonical JSON byte profile v1

## Purpose

`qw5-json-c14n-v1` defines the only byte representation used when a QW5 JSON
artifact is hashed, signed, compared byte-for-byte, or referenced by SHA-256. It is a
small deterministic subset of JSON chosen so every M1 producer can implement it
without depending on map iteration order or language-specific float formatting.

Human-readable schema fixtures may be indented for review. Before their content is
used as an artifact identity, it must be parsed and serialized with this profile.
Production M1 producers write the canonical bytes directly.

## Accepted data model

- Input is one JSON value encoded as UTF-8. A byte-order mark is forbidden.
- Objects, arrays, strings, integers, booleans, and `null` are accepted.
- Object member names are unique. A parser must reject duplicate names before
  constructing a map.
- Every string and member name is valid Unicode scalar text in Normalization Form C
  (NFC). A producer rejects non-NFC input; it does not silently normalize identities.
- Numbers are base-10 integers in the inclusive range
  `-9223372036854775808` through `18446744073709551615`. Fractions, exponents,
  negative zero, NaN, and infinities are forbidden.

The individual artifact schema may impose a smaller integer range.

## Exact serialization

1. Encode the value as UTF-8 with no BOM, leading bytes, trailing whitespace, or
   trailing newline.
2. Emit object members in ascending Unicode scalar-value order of their member names.
   Array order is preserved.
3. Emit no insignificant whitespace. Separators are exactly `,` and `:`.
4. Emit integers as the shortest decimal form: `0`, or an optional `-` followed by a
   nonzero digit and remaining digits. A leading `+` is forbidden.
5. Emit `true`, `false`, and `null` exactly as shown.
6. Delimit strings with `"`. Escape quotation mark and reverse solidus as `\"` and
   `\\`. Use the short escapes `\b`, `\f`, `\n`, `\r`, and `\t`. Encode every other
   U+0000 through U+001F control character as lowercase `\u00xx`. Do not escape `/`
   or any other Unicode scalar value; encode it directly as UTF-8.

SHA-256 is computed over exactly these bytes. A parent index stores the digest; the
artifact never embeds a digest of itself.

## Validation vectors and failures

[`canonical-json-v1.vectors.json`](../../fixtures/contracts/v1/canonical-json-v1.vectors.json)
contains source values, exact canonical UTF-8 hex, and expected SHA-256 digests.
`tools/validate_contracts.py` independently reconstructs and verifies every vector.
The validator also rejects duplicate names, non-NFC strings, floating-point numbers,
out-of-range integers, a BOM, and trailing bytes.

Any change to the accepted data model, ordering, escaping, newline rule, or integer
range creates a new profile version. It must not reinterpret a v1 digest.

## References

- [RFC 8259: The JavaScript Object Notation (JSON) Data Interchange Format](https://www.rfc-editor.org/info/rfc8259/)
- [Unicode Standard Annex #15: Unicode Normalization Forms](https://unicode.org/reports/tr15/)
