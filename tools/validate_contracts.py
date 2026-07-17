#!/usr/bin/env python3
"""Validate QW5 contract schemas, fixtures, semantic invariants, and exact vectors."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import struct
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas" / "v1"
FIXTURE_DIR = ROOT / "fixtures" / "contracts" / "v1"
I64_MIN = -(1 << 63)
U64_MAX = (1 << 64) - 1
FORMAT_CHECKER = FormatChecker()


@FORMAT_CHECKER.checks("date-time")
def is_qw5_datetime(value: object) -> bool:
    if not isinstance(value, str):
        return True
    if len(value) < 20 or value[10:11] != "T" or not value.endswith("Z") or "," in value:
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0

SCHEMA_FILES = {
    "qw5.hardware-inventory/v1": "hardware-inventory.schema.json",
    "qw5.memory-baseline/v1": "memory-baseline.schema.json",
    "qw5.model-acquisition-plan/v1": "model-acquisition-plan.schema.json",
    "qw5.model-artifact-manifest/v1": "model-artifact-manifest.schema.json",
    "qw5.placement-analysis/v1": "placement-analysis.schema.json",
    "qw5.placement-evidence-graph/v1": "placement-evidence-graph.schema.json",
    "qw5.safetensors-parser-profile/v1": "safetensors-parser-profile.schema.json",
    "qw5.tb5-link-summary/v1": "tb5-link-summary.schema.json",
    "qw5.tb5-local-control-index/v1": "tb5-local-control-index.schema.json",
    "qw5.tb5-local-control/v1": "tb5-local-control.schema.json",
    "qw5.tb5-measurement/v1": "tb5-measurement.schema.json",
    "qw5.tb5-measurement-index/v1": "tb5-measurement-index.schema.json",
    "qw5.tb5-route-proof/v1": "tb5-route-proof.schema.json",
    "qw5.tb5-run-plan/v1": "tb5-run-plan.schema.json",
    "qw5.tb5-synchronization-evidence/v1": "tb5-synchronization-evidence.schema.json",
    "qw5.tensor-inventory/v1": "tensor-inventory.schema.json",
}

FLOW = {
    "a-b": ("A", "B", "A-B"),
    "b-a": ("B", "A", "A-B"),
    "a-c": ("A", "C", "A-C"),
    "c-a": ("C", "A", "A-C"),
    "b-c": ("B", "C", "B-C"),
    "c-b": ("C", "B", "B-C"),
}
SCENARIOS = {
    "solo-a-b": ("a-b",),
    "solo-b-a": ("b-a",),
    "solo-a-c": ("a-c",),
    "solo-c-a": ("c-a",),
    "solo-b-c": ("b-c",),
    "solo-c-b": ("c-b",),
    "duplex-a-b": ("a-b", "b-a"),
    "duplex-a-c": ("a-c", "c-a"),
    "duplex-b-c": ("b-c", "c-b"),
    "fanout-a": ("a-b", "a-c"),
    "fanout-b": ("b-a", "b-c"),
    "fanout-c": ("c-a", "c-b"),
    "fanin-a": ("b-a", "c-a"),
    "fanin-b": ("a-b", "c-b"),
    "fanin-c": ("a-c", "b-c"),
    "cycle-a-b-c": ("a-b", "b-c", "c-a"),
    "cycle-a-c-b": ("a-c", "c-b", "b-a"),
    "all-directed": ("a-b", "b-a", "a-c", "c-a", "b-c", "c-b"),
}
SCENARIO_ORDER = tuple(SCENARIOS)
SOLO_SCENARIOS = SCENARIO_ORDER[:6]
STREAM_PAYLOADS = (64, 256, 1024, 4096, 16384, 65536, 262144, 1048576,
                   4194304, 16777216, 67108864, 268435456)
ROUND_TRIP_PAYLOADS = (64, 1024, 16384, 262144, 4194304)
ALL_GATES = {
    "artifact_complete", "tensor_reconciled", "layout_complete",
    "memory_baseline_accepted", "memory_nonnegative", "quality_available",
    "scratch_bounded", "state_bounded", "transport_profile_available",
    "text_subset_proven",
}
REQUIRED_MEMORY_CLASSES = {
    "allocator", "artifact_staging", "control", "fragmentation", "kv_state",
    "quantization_metadata", "recurrent_state", "router_state", "scratch",
    "transport", "weights",
}
# M1-14 must freeze and register deterministic rule evaluators before any positive
# placement decision can pass bundle validation. Schema presence alone is not a rule
# evaluation and a producer-supplied rule_id is never trusted.
PLACEMENT_GATE_RULE_EVALUATORS: frozenset[str] = frozenset()
DTYPES = {
    "BOOL": ("bool8", 1), "U8": ("uint8", 1), "I8": ("int8", 1),
    "U16": ("uint16", 2), "I16": ("int16", 2), "F16": ("float16", 2),
    "BF16": ("bfloat16", 2), "U32": ("uint32", 4), "I32": ("int32", 4),
    "F32": ("float32", 4), "U64": ("uint64", 8), "I64": ("int64", 8),
    "F64": ("float64", 8),
}


class JsonInputError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Issue:
    code: str
    pointer: str
    message: str


def issue(code: str, pointer: str, message: str) -> Issue:
    return Issue(code, pointer, message)


def duplicate_guard(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise JsonInputError("CANON_DUPLICATE_KEY", f"duplicate object member {key!r}")
        result[key] = value
    return result


def reject_float(token: str) -> Any:
    raise JsonInputError("CANON_NON_INTEGER", f"non-integer JSON number {token!r}")


def reject_constant(token: str) -> Any:
    raise JsonInputError("CANON_NON_INTEGER", f"non-finite JSON number {token!r}")


def load_json(path: Path) -> Any:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=duplicate_guard,
            parse_float=reject_float,
            parse_constant=reject_constant,
        )
        check_canonical_value(value)
        return value
    except JsonInputError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise JsonInputError("JSON_PARSE", f"{path}: {exc}") from exc


def check_canonical_value(value: Any) -> None:
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        if not I64_MIN <= value <= U64_MAX:
            raise JsonInputError("CANON_INTEGER_RANGE", f"integer out of v1 range: {value}")
        return
    if isinstance(value, str):
        if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise JsonInputError("CANON_INVALID_SCALAR", "string contains a Unicode surrogate")
        if unicodedata.normalize("NFC", value) != value:
            raise JsonInputError("CANON_NON_NFC", f"string is not NFC: {value!r}")
        return
    if isinstance(value, list):
        for item in value:
            check_canonical_value(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise JsonInputError("CANON_KEY_TYPE", "object member name is not text")
            check_canonical_value(key)
            check_canonical_value(item)
        return
    raise JsonInputError("CANON_TYPE", f"unsupported value type: {type(value).__name__}")


def encode_string(value: str) -> str:
    escapes = {
        '"': '\\"', "\\": "\\\\", "\b": "\\b", "\f": "\\f",
        "\n": "\\n", "\r": "\\r", "\t": "\\t",
    }
    parts = ['"']
    for char in value:
        if char in escapes:
            parts.append(escapes[char])
        elif ord(char) < 0x20:
            parts.append(f"\\u{ord(char):04x}")
        else:
            parts.append(char)
    parts.append('"')
    return "".join(parts)


def canonical_text(value: Any) -> str:
    check_canonical_value(value)
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if type(value) is int:
        return str(value)
    if isinstance(value, str):
        return encode_string(value)
    if isinstance(value, list):
        return "[" + ",".join(canonical_text(item) for item in value) + "]"
    return "{" + ",".join(
        encode_string(key) + ":" + canonical_text(value[key]) for key in sorted(value)
    ) + "}"


def parse_canonical_source(raw: bytes) -> Any:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise JsonInputError("CANON_BOM", "UTF-8 byte-order mark is forbidden")
    if not raw or raw[:1] in b" \t\r\n":
        raise JsonInputError("CANON_NON_CANONICAL", "leading whitespace or an empty source is forbidden")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise JsonInputError("CANON_UTF8", str(exc)) from exc
    decoder = json.JSONDecoder(
        object_pairs_hook=duplicate_guard,
        parse_float=reject_float,
        parse_constant=reject_constant,
    )
    try:
        value, end = decoder.raw_decode(text)
    except JsonInputError:
        raise
    except json.JSONDecodeError as exc:
        raise JsonInputError("JSON_PARSE", str(exc)) from exc
    if end != len(text):
        raise JsonInputError("CANON_TRAILING_BYTES", "bytes follow the JSON value")
    check_canonical_value(value)
    if canonical_text(value).encode("utf-8") != raw:
        raise JsonInputError("CANON_NON_CANONICAL", "source is not the canonical v1 encoding")
    return value


def ptr(parts: Any) -> str:
    encoded = [str(part).replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(encoded) if encoded else "/"


def schema_issues(instance: Any, schema: Any) -> list[Issue]:
    validator = Draft202012Validator(schema, format_checker=FORMAT_CHECKER)
    return [
        issue(f"SCHEMA_{error.validator.upper()}", ptr(error.absolute_path), error.message)
        for error in sorted(
            validator.iter_errors(instance),
            key=lambda item: tuple(str(part) for part in item.absolute_path),
        )
    ]


def ids_unique(values: list[str]) -> bool:
    return len(values) == len(set(values))


def semantic_hardware(data: dict[str, Any]) -> list[Issue]:
    out: list[Issue] = []
    sources = [row["source_id"] for row in data["sources"]]
    if not ids_unique(sources):
        out.append(issue("HW_SOURCE_ID_UNIQUE", "/sources", "source_id values must be unique"))
    if sources != sorted(sources):
        out.append(issue("HW_SOURCE_ORDER", "/sources", "sources must be sorted by source_id"))
    source_set = set(sources)
    for fact_id, fact in data["facts"].items():
        if fact["source_ref"] not in source_set:
            out.append(issue("HW_SOURCE_REFERENCE", f"/facts/{fact_id}/source_ref", "unknown source_ref"))
    optional_units = {
        "negotiated_rate": ("bits_per_second", int),
        "negotiated_width": ("count", int),
        "negotiated_generation": ("none", str),
        "negotiated_lanes": ("count", int),
    }
    node = data["node_alias"]
    expected_peers = sorted({"A", "B", "C"} - {node})
    links = data["links"]
    if links:
        peers = [row["peer_alias"] for row in links]
        if peers != expected_peers:
            out.append(issue("HW_LINK_PEERS", "/links", f"expected peers {expected_peers}, got {peers}"))
        for index, link in enumerate(links):
            base = f"/links/{index}"
            if link["peer_alias"] == node:
                out.append(issue("HW_LINK_SELF", base + "/peer_alias", "self-link is forbidden"))
            expected_route = "-".join(sorted((node, link["peer_alias"])))
            if link["route_alias"] != expected_route:
                out.append(issue("HW_ROUTE_ALIAS", base + "/route_alias", f"expected {expected_route}"))
            if link["source_ref"] not in source_set:
                out.append(issue("HW_SOURCE_REFERENCE", base + "/source_ref", "unknown source_ref"))
            for name, (unit, value_type) in optional_units.items():
                observation = link[name]
                if observation["source_ref"] not in source_set:
                    out.append(issue("HW_SOURCE_REFERENCE", base + f"/{name}/source_ref", "unknown source_ref"))
                if observation["status"] == "available":
                    if observation["unit"] != unit or type(observation["value"]) is not value_type:
                        out.append(issue("HW_LINK_OBSERVATION_TYPE", base + f"/{name}", f"expected {value_type.__name__}/{unit}"))
    return out


def required_model_components(model_role: str) -> list[str]:
    components = ["configuration", "language", "license", "tokenizer"]
    if model_role == "flagship_target":
        components.append("vision")
    return components


def model_component_coverage(files: list[dict[str, Any]]) -> set[str]:
    covered: set[str] = set()
    for row in files:
        if row.get("status", "verified") != "verified":
            continue
        role = row["role"]
        components = set(row["components"])
        if role in {"configuration", "generation_configuration"} and "configuration" in components:
            covered.add("configuration")
        if role == "weight_shard":
            covered.update(components & {"language", "vision"})
        if role in {"license", "notice"} and "license" in components:
            covered.add("license")
        if role in {"tokenizer", "tokenizer_configuration", "special_tokens", "prompt_template"} and "tokenizer" in components:
            covered.add("tokenizer")
    return covered


def semantic_model_acquisition_plan(data: dict[str, Any]) -> list[Issue]:
    out: list[Issue] = []
    fixture_role = data["artifact_role"] == "schema_fixture"
    if fixture_role != (data["model_role"] == "schema_fixture"):
        out.append(issue("MODEL_PLAN_ROLE", "/model_role", "schema-fixture and production model roles cannot be mixed"))
    expected_provider = "fixture" if fixture_role else "huggingface"
    if data["repository"]["provider"] != expected_provider:
        out.append(issue("MODEL_PLAN_PROVIDER", "/repository/provider", f"expected {expected_provider}"))
    if data["approval_status"] == "approved" and data["producer"]["dirty"]:
        out.append(issue("MODEL_PLAN_DIRTY", "/approval_status", "an approved acquisition plan requires a clean producer"))
    expected_repository = {
        "first_working_target": "Qwen/Qwen3-Coder-Next",
        "flagship_target": "Qwen/Qwen3.5-397B-A17B",
    }.get(data["model_role"])
    if expected_repository is not None and data["repository"]["repository_id"] != expected_repository:
        out.append(issue("MODEL_PLAN_REPOSITORY", "/repository/repository_id", f"expected {expected_repository}"))
    required_components = required_model_components(data["model_role"])
    if data["required_components"] != required_components:
        out.append(issue("MODEL_PLAN_COMPONENTS", "/required_components", f"expected {required_components}"))
    expected_files = data["expected_files"]
    paths = [row["path"] for row in expected_files]
    if paths != sorted(paths) or not ids_unique(paths):
        out.append(issue("MODEL_PLAN_PATH_ORDER", "/expected_files", "expected file paths must be unique and sorted"))
    for index, row in enumerate(expected_files):
        if row["components"] != sorted(row["components"]):
            out.append(issue("MODEL_PLAN_FILE_COMPONENT_ORDER", f"/expected_files/{index}/components", "file components must be sorted"))
        if not set(row["components"]).issubset(set(required_components)):
            out.append(issue("MODEL_PLAN_FILE_COMPONENT", f"/expected_files/{index}/components", "file component is outside the required model-role set"))
    missing = set(required_components) - model_component_coverage(expected_files)
    if missing:
        out.append(issue("MODEL_PLAN_ROLE_COVERAGE", "/expected_files", f"missing required component bytes/metadata: {sorted(missing)}"))
    return out


def semantic_model(data: dict[str, Any]) -> list[Issue]:
    out: list[Issue] = []
    fixture_role = data["artifact_role"] == "schema_fixture"
    if fixture_role != (data["selection"]["model_role"] == "schema_fixture"):
        out.append(issue("MODEL_ROLE", "/selection/model_role", "schema-fixture and production model roles cannot be mixed"))
    expected_provider = "fixture" if fixture_role else "huggingface"
    if data["repository"]["provider"] != expected_provider:
        out.append(issue("MODEL_PROVIDER", "/repository/provider", f"expected {expected_provider}"))
    files = data["files"]
    paths = [row["path"] for row in files]
    if not ids_unique(paths):
        out.append(issue("MODEL_FILE_PATH_UNIQUE", "/files", "file paths must be unique"))
    if paths != sorted(paths):
        out.append(issue("MODEL_FILE_ORDER", "/files", "files must be sorted by path"))
    expected_paths = data["selection"]["expected_paths"]
    if expected_paths != sorted(expected_paths) or not ids_unique(expected_paths):
        out.append(issue("MODEL_EXPECTED_PATH_ORDER", "/selection/expected_paths", "expected paths must be unique and sorted"))
    if paths != expected_paths:
        out.append(issue("MODEL_EXPECTED_PATHS", "/files", "file table must exactly match the frozen expected path set"))
    components = data["selection"]["components"]
    required_components = required_model_components(data["selection"]["model_role"])
    if components != required_components:
        out.append(issue("MODEL_ROLE_COMPONENTS", "/selection/components", f"expected {required_components}"))
    for index, row in enumerate(files):
        if row["components"] != sorted(row["components"]):
            out.append(issue("MODEL_FILE_COMPONENT_ORDER", f"/files/{index}/components", "file components must be sorted"))
        if not set(row["components"]).issubset(set(components)):
            out.append(issue("MODEL_FILE_COMPONENT", f"/files/{index}/components", "file component is outside the selected model-role set"))
    missing_components = set(required_components) - model_component_coverage(files)
    if missing_components:
        out.append(issue("MODEL_ROLE_COVERAGE", "/files", f"missing verified component bytes/metadata: {sorted(missing_components)}"))
    for index, row in enumerate(files):
        if row["status"] != "verified":
            continue
        passes = row["verification_passes"]
        if [item["pass_index"] for item in passes] != [1, 2]:
            out.append(issue("MODEL_HASH_PASS_ORDER", f"/files/{index}/verification_passes", "hash passes must be 1 then 2"))
        if len(passes) == 2 and passes[1]["completed_at"] < passes[0]["completed_at"]:
            out.append(issue("MODEL_HASH_PASS_TIME", f"/files/{index}/verification_passes", "second pass completion precedes first pass"))
        for pass_index, check in enumerate(passes):
            if check["size_bytes"] != row["size_bytes"] or check["sha256"] != row["sha256"]:
                out.append(issue("MODEL_HASH_PASS_MISMATCH", f"/files/{index}/verification_passes/{pass_index}", "verification pass differs from accepted file identity"))
    verified = [row for row in files if row["status"] == "verified"]
    missing = sorted(row["path"] for row in files if row["status"] == "missing")
    completeness = data["completeness"]
    if completeness["verified_file_count"] != len(verified):
        out.append(issue("MODEL_VERIFIED_COUNT", "/completeness/verified_file_count", "verified count does not reconcile"))
    if completeness["verified_total_bytes"] != sum(row["size_bytes"] for row in verified):
        out.append(issue("MODEL_VERIFIED_BYTES", "/completeness/verified_total_bytes", "verified bytes do not reconcile"))
    if completeness["missing_paths"] != missing:
        out.append(issue("MODEL_MISSING_PATHS", "/completeness/missing_paths", "missing paths do not reconcile"))
    if completeness["unexpected_paths"] != sorted(data["unexpected_files"]):
        out.append(issue("MODEL_UNEXPECTED_PATHS", "/completeness/unexpected_paths", "unexpected paths do not reconcile"))
    if completeness["status"] == "complete":
        if len(verified) != len(files) or missing or data["unexpected_files"] or completeness["errors"]:
            out.append(issue("MODEL_COMPLETE_STATUS", "/completeness/status", "complete requires all files verified and no missing, unexpected, or error entries"))
    return out


def validate_model_evidence_bundle(
    plan: dict[str, Any],
    manifest: dict[str, Any],
) -> list[Issue]:
    out: list[Issue] = []
    plan_issues = validate_instance(plan, "qw5.model-acquisition-plan/v1")
    manifest_issues = validate_instance(manifest, "qw5.model-artifact-manifest/v1")
    out.extend(plan_issues)
    out.extend(manifest_issues)
    if any(item.code.startswith("SCHEMA_") for item in plan_issues + manifest_issues):
        return out
    plan_digest = canonical_digest(plan)
    if manifest["selection"]["acquisition_plan_sha256"] != plan_digest:
        out.append(issue("MODEL_PLAN_DIGEST", "/selection/acquisition_plan_sha256", "manifest does not resolve to the canonical acquisition plan"))
    plan_repository = plan["repository"]
    manifest_repository = manifest["repository"]
    if (
        plan_repository["provider"] != manifest_repository["provider"]
        or plan_repository["repository_id"] != manifest_repository["repository_id"]
        or plan_repository["immutable_revision"] != manifest_repository["immutable_revision"]
    ):
        out.append(issue("MODEL_PLAN_REPOSITORY", "/repository", "manifest repository identity differs from the resolved acquisition plan"))
    selection = manifest["selection"]
    if selection["model_role"] != plan["model_role"]:
        out.append(issue("MODEL_PLAN_ROLE", "/selection/model_role", "manifest model role differs from the acquisition plan"))
    if selection["revision_listing_sha256"] != plan["revision_listing_sha256"]:
        out.append(issue("MODEL_PLAN_REVISION_LISTING", "/selection/revision_listing_sha256", "revision-listing identity differs from the acquisition plan"))
    expected_paths = [row["path"] for row in plan["expected_files"]]
    if selection["components"] != plan["required_components"] or selection["expected_paths"] != expected_paths:
        out.append(issue("MODEL_PLAN_SELECTION", "/selection", "manifest component/path projection differs from the acquisition plan"))
    if manifest["included_patterns"] != plan["included_patterns"] or manifest["excluded_patterns"] != plan["excluded_patterns"]:
        out.append(issue("MODEL_PLAN_PATTERNS", "/included_patterns", "manifest selection patterns differ from the acquisition plan"))
    manifest_projection = [
        {"path": row["path"], "role": row["role"], "components": row["components"]}
        for row in manifest["files"]
    ]
    if manifest_projection != plan["expected_files"]:
        out.append(issue("MODEL_PLAN_FILE_TABLE", "/files", "manifest paths, roles, or components differ from the acquisition plan"))
    if (
        manifest["artifact_role"] == "model_artifact_manifest"
        and manifest["completeness"]["status"] == "complete"
        and (
            plan["artifact_role"] != "model_acquisition_plan"
            or plan["approval_status"] != "approved"
            or plan["producer"]["dirty"]
        )
    ):
        out.append(issue("MODEL_PLAN_APPROVAL", "/selection/acquisition_plan_sha256", "a production complete manifest requires a clean owner-approved production acquisition plan"))
    return out


def product(values: list[int]) -> int:
    result = 1
    for value in values:
        result *= value
    return result


def semantic_tensor(data: dict[str, Any]) -> list[Issue]:
    out: list[Issue] = []
    source_rows = data["source_files"]
    source_paths = [row["path"] for row in source_rows]
    if not ids_unique(source_paths):
        out.append(issue("TENSOR_SOURCE_FILE_UNIQUE", "/source_files", "source file paths must be unique"))
    source = {row["path"]: row for row in source_rows}
    for index, row in enumerate(source_rows):
        if row["header_bytes"] + row["data_bytes"] != row["size_bytes"]:
            out.append(issue("TENSOR_FILE_RECONCILIATION", f"/source_files/{index}", "header plus data bytes must equal file bytes"))
    tensors = data["tensors"]
    names = [row["name"] for row in tensors]
    tensor_by_name = {row["name"]: row for row in tensors}
    if not ids_unique(names):
        out.append(issue("TENSOR_NAME_UNIQUE", "/tensors", "tensor names must be unique"))
    if names != sorted(names):
        out.append(issue("TENSOR_NAME_ORDER", "/tensors", "tensors must be sorted by name"))
    storage_ids = [row["storage_id"] for row in tensors if row["alias_of"] is None]
    if not ids_unique(storage_ids):
        out.append(issue("TENSOR_STORAGE_UNIQUE", "/tensors", "owning storage IDs must be unique"))
    ranges: dict[str, list[tuple[int, int, int]]] = defaultdict(list)
    by_component: Counter[str] = Counter()
    by_dtype: Counter[str] = Counter()
    by_semantic: Counter[str] = Counter()
    by_layer: Counter[str] = Counter()
    by_expert: Counter[str] = Counter()
    by_file: dict[str, dict[str, int]] = defaultdict(lambda: {"tensor_count": 0, "element_count": 0, "tensor_payload_bytes": 0})
    expected_unclassified: list[str] = []
    for index, row in enumerate(tensors):
        base = f"/tensors/{index}"
        if row["source_file"] not in source:
            out.append(issue("TENSOR_SOURCE_REFERENCE", base + "/source_file", "unknown source file"))
            continue
        normalized, width = DTYPES[row["source_dtype"]]
        if row["normalized_dtype"] != normalized:
            out.append(issue("TENSOR_DTYPE_NORMALIZATION", base + "/normalized_dtype", f"expected {normalized}"))
        elements = product(row["shape"])
        if row["element_count"] != elements:
            out.append(issue("TENSOR_ELEMENT_COUNT", base + "/element_count", "shape product does not match element count"))
        expected_bytes = elements * width
        if row["stored_bytes"] != expected_bytes:
            out.append(issue("TENSOR_STORED_BYTES", base + "/stored_bytes", "dtype width times element count does not match stored bytes"))
        start, end = row["data_offsets"]
        if start > end:
            out.append(issue("TENSOR_RANGE_ORDER", base + "/data_offsets", "range start exceeds end"))
        if end - start != row["stored_bytes"]:
            out.append(issue("TENSOR_RANGE_SIZE", base + "/data_offsets", "range length does not match stored bytes"))
        if end > source[row["source_file"]]["data_bytes"]:
            out.append(issue("TENSOR_RANGE_BOUNDS", base + "/data_offsets", "range exceeds source data section"))
        if row["alias_of"] is None:
            ranges[row["source_file"]].append((start, end, index))
        else:
            owner = tensor_by_name.get(row["alias_of"])
            if owner is None or owner["alias_of"] is not None or owner["name"] == row["name"]:
                out.append(issue("TENSOR_ALIAS_REFERENCE", base + "/alias_of", "alias must reference one owning tensor"))
            elif any(row[field] != owner[field] for field in (
                "source_file", "source_dtype", "normalized_dtype", "shape",
                "element_count", "stored_bytes", "data_offsets", "storage_id",
            )):
                out.append(issue("TENSOR_ALIAS_IDENTITY", base, "alias storage identity differs from its owner"))
        classification = row["classification"]
        is_unclassified = classification["status"] != "classified" or row["semantic_class"] == "unclassified" or row["component"] == "unclassified"
        if is_unclassified:
            expected_unclassified.append(row["name"])
        if classification["status"] == "classified" and not classification["rule_id"]:
            out.append(issue("TENSOR_CLASSIFICATION_RULE", base + "/classification/rule_id", "classified tensor requires a rule ID"))
        if classification["status"] == "unclassified" and classification["rule_id"] is not None:
            out.append(issue("TENSOR_CLASSIFICATION_RULE", base + "/classification/rule_id", "unclassified tensor must not claim a rule"))
        amount = row["stored_bytes"] if row["alias_of"] is None else 0
        by_component[row["component"]] += amount
        by_dtype[row["normalized_dtype"]] += amount
        by_semantic[row["semantic_class"]] += amount
        by_layer["none" if row["layer_index"] is None else str(row["layer_index"])] += amount
        expert_key = "none" if row["expert_index"] is None else f"expert-{row['expert_index']}"
        by_expert[expert_key] += amount
        totals = by_file[row["source_file"]]
        totals["tensor_count"] += 1
        totals["element_count"] += row["element_count"]
        totals["tensor_payload_bytes"] += amount
    for path in source_paths:
        file_ranges = ranges[path]
        cursor = 0
        for start, end, index in sorted(file_ranges):
            if start < cursor:
                out.append(issue("TENSOR_RANGE_OVERLAP", f"/tensors/{index}/data_offsets", "storage range overlaps a prior tensor"))
            elif start > cursor and data["format"]["range_policy"] == "contiguous_no_overlap":
                out.append(issue("TENSOR_RANGE_HOLE", f"/tensors/{index}/data_offsets", "storage range leaves an undeclared hole"))
            cursor = max(cursor, end)
        if data["format"]["range_policy"] == "contiguous_no_overlap" and cursor != source[path]["data_bytes"]:
            out.append(issue("TENSOR_RANGE_COVERAGE", "/tensors", f"ranges for {path} do not cover its data section"))
    totals = data["totals"]
    expected_scalar = {
        "tensor_count": len(tensors),
        "element_count": sum(row["element_count"] for row in tensors),
        "tensor_payload_bytes": sum(row["stored_bytes"] for row in tensors if row["alias_of"] is None),
        "container_overhead_bytes": sum(row["header_bytes"] for row in source_rows),
    }
    for name, expected in expected_scalar.items():
        if totals[name] != expected:
            out.append(issue("TENSOR_TOTAL_RECONCILIATION", f"/totals/{name}", f"expected {expected}"))
    expected_maps = {
        "by_component": dict(by_component), "by_dtype": dict(by_dtype),
        "by_semantic_class": dict(by_semantic), "by_layer": dict(by_layer),
        "by_expert_class": dict(by_expert),
    }
    for name, expected in expected_maps.items():
        if totals[name] != expected:
            out.append(issue("TENSOR_TOTAL_RECONCILIATION", f"/totals/{name}", f"expected {expected}"))
    expected_by_file = {}
    for path in source_paths:
        values = by_file[path]
        expected_by_file[path] = {**values, "container_overhead_bytes": source[path]["header_bytes"]}
    if totals["by_file"] != expected_by_file:
        out.append(issue("TENSOR_TOTAL_RECONCILIATION", "/totals/by_file", f"expected {expected_by_file}"))
    if data["unclassified_tensors"] != sorted(expected_unclassified):
        out.append(issue("TENSOR_UNCLASSIFIED_RECONCILIATION", "/unclassified_tensors", "unclassified list does not match tensor classifications"))
    return out


def semantic_noop(data: dict[str, Any]) -> list[Issue]:
    del data
    return []


def semantic_sync_evidence(data: dict[str, Any]) -> list[Issue]:
    out: list[Issue] = []
    participants = data["participants"]
    flow_ids = [row["flow_id"] for row in participants]
    if not ids_unique(flow_ids):
        out.append(issue("TB_SYNC_FLOW_UNIQUE", "/participants", "participant flow IDs must be unique"))
    expected_flows = SCENARIOS[data["scenario_id"]]
    if tuple(flow_ids) != expected_flows or data["cell_id"].split(":")[1] != data["scenario_id"]:
        out.append(issue("TB_SYNC_CELL_IDENTITY", "/participants", "cell, scenario, and participant flows must agree"))
    for index, row in enumerate(participants):
        if row["flow_id"] not in FLOW or row["worker_node"] != FLOW[row["flow_id"]][0]:
            out.append(issue("TB_SYNC_WORKER_MAPPING", f"/participants/{index}", "worker node must be the directed-flow source"))
    receipts = [row["coordinator_ack_receipt_ns"] for row in participants]
    if any(value < data["coordinator"]["release_monotonic_ns"] for value in receipts):
        out.append(issue("TB_SYNC_RECEIPT_ORDER", "/participants", "ack receipt precedes coordinator release"))
    expected_rtt = max(value for row in participants for value in row["pre_attempt_control_rtt_ns"])
    expected_worker = max(row["worker_start_to_ack_ns"] for row in participants)
    expected_allowance = data["coordinator"]["clock_resolution_ns"] + max(
        row["worker_clock_resolution_ns"] for row in participants
    )
    expected_spread = max(receipts) - min(receipts)
    expected_window = expected_spread + expected_rtt + 2 * expected_worker + expected_allowance
    derived = data["derived"]
    expected = {
        "pre_attempt_control_rtt_max_ns": expected_rtt,
        "worker_start_to_ack_max_ns": expected_worker,
        "timer_resolution_allowance_ns": expected_allowance,
        "coordinator_receipt_spread_ns": expected_spread,
        "coordinator_observed_start_window_ns": expected_window,
    }
    for name, value in expected.items():
        if derived[name] != value:
            out.append(issue("TB_SYNC_RECONCILIATION", f"/derived/{name}", f"expected {value}"))
    expected_reasons = []
    if expected_rtt > 1_000_000:
        expected_reasons.append("SYNC_CONTROL_RTT_EXCEEDED")
    if expected_window > 10_000_000:
        expected_reasons.append("SYNC_OBSERVED_WINDOW_EXCEEDED")
    expected_decision = "included" if not expected_reasons and not data["errors"] else "excluded"
    if data["errors"]:
        expected_decision = "undetermined"
        expected_reasons.append("SYNC_EVIDENCE_ERROR")
    if derived["inclusion_decision"] != expected_decision or derived["reasons"] != expected_reasons:
        out.append(issue("TB_SYNC_DECISION", "/derived", f"expected {expected_decision} with {expected_reasons}"))
    if data["artifact_role"] == "synchronization_evidence" and data["producer"]["dirty"]:
        out.append(issue("TB_MEASURED_DIRTY", "/producer/dirty", "physical measured synchronization evidence requires a clean producer"))
    return out


def validate_sync_reference(
    cell_id: str,
    plan_sha256: str,
    attempt: dict[str, Any],
    raw: dict[str, Any],
) -> list[Issue]:
    out: list[Issue] = []
    sync = attempt["synchronization"]
    actual_digest = canonical_digest(raw)
    if sync["evidence_sha256"] != actual_digest:
        out.append(issue("TB_SYNC_EVIDENCE_DIGEST", "/synchronization/evidence_sha256", "raw canonical digest differs from the attempt reference"))
    if (
        raw["plan_sha256"] != plan_sha256
        or raw["cell_id"] != cell_id
        or raw["scenario_id"] != cell_id.split(":")[1]
        or raw["attempt_id"] != attempt["attempt_id"]
    ):
        out.append(issue("TB_SYNC_EVIDENCE_IDENTITY", "/synchronization/evidence_sha256", "raw plan, cell, scenario, or attempt identity differs"))
    expected_projection = {
        "status": "available",
        "method": raw["method"],
        "calibration_rounds": len(raw["participants"][0]["pre_attempt_control_rtt_ns"]),
        "coordinator_receipt_spread_ns": raw["derived"]["coordinator_receipt_spread_ns"],
        "pre_attempt_control_rtt_max_ns": raw["derived"]["pre_attempt_control_rtt_max_ns"],
        "worker_start_to_ack_max_ns": raw["derived"]["worker_start_to_ack_max_ns"],
        "timer_resolution_allowance_ns": raw["derived"]["timer_resolution_allowance_ns"],
        "coordinator_observed_start_window_ns": raw["derived"]["coordinator_observed_start_window_ns"],
        "evidence_sha256": actual_digest,
    }
    if sync != expected_projection:
        out.append(issue("TB_SYNC_EVIDENCE_PROJECTION", "/synchronization", "attempt synchronization projection differs from raw evidence"))
    if raw["derived"]["inclusion_decision"] != "included":
        required_reasons = set(raw["derived"]["reasons"])
        if attempt["valid"] or not required_reasons.issubset(set(attempt["invalid_reasons"])):
            out.append(issue("TB_SYNC_EVIDENCE_DECISION", "/synchronization", "excluded or undetermined raw evidence must invalidate the attempt with its reasons"))
    return out


def semantic_local_control(data: dict[str, Any]) -> list[Issue]:
    out: list[Issue] = []
    expected_scope = {
        "buffer_copy": "copy_only",
        "framing": "frame_and_verify",
        "sha256": "generate_and_sha256",
    }[data["control_id"]]
    if data["buffer_policy"]["timing_scope"] != expected_scope:
        out.append(issue("TB_CONTROL_TIMING_SCOPE", "/buffer_policy/timing_scope", f"expected {expected_scope}"))
    expected_peak = 2 * data["payload_bytes"]
    if data["buffer_policy"]["peak_application_buffer_bytes"] < expected_peak:
        out.append(issue("TB_CONTROL_BUFFER_BOUND", "/buffer_policy/peak_application_buffer_bytes", f"expected at least {expected_peak}"))
    regime = data["regime"]
    if regime["node"] != data["node"]:
        out.append(issue("TB_CONTROL_REGIME_NODE", "/regime/node", "regime node must match the control node"))
    if regime["observation_end_monotonic_ns"] < regime["observation_start_monotonic_ns"]:
        out.append(issue("TB_CONTROL_REGIME_TIME", "/regime", "regime observation interval regresses"))
    stable = (
        regime["start_thermal_state"] == regime["end_thermal_state"]
        and regime["start_low_power_mode"] == regime["end_low_power_mode"]
        and regime["start_power_source"] == regime["end_power_source"]
    )
    if data["status"] == "COMPLETE" and not stable:
        out.append(issue(
            "TB_CONTROL_REGIME_TRANSITION",
            "/regime",
            "a complete local control must retain one exact thermal, low-power, and power-source regime",
        ))
    if data["artifact_role"] == "local_control" and data["producer"]["dirty"]:
        out.append(issue("TB_MEASURED_DIRTY", "/producer/dirty", "physical measured local controls require a clean producer"))
    return out


def expected_local_control_keys() -> set[tuple[str, str, int]]:
    return {
        (control, node, payload)
        for node in ("A", "B", "C")
        for payload in STREAM_PAYLOADS
        for control in ("buffer_copy", "framing", "sha256")
    }


def ordered_local_control_keys() -> list[tuple[str, str, int]]:
    return [
        (control, node, payload)
        for node in ("A", "B", "C")
        for payload in STREAM_PAYLOADS
        for control in ("buffer_copy", "framing", "sha256")
    ]


def semantic_local_control_index(data: dict[str, Any]) -> list[Issue]:
    out: list[Issue] = []
    entries = data["entries"]
    keys = [(row["control_id"], row["node"], row["payload_bytes"]) for row in entries]
    paths = [row["relative_path"] for row in entries]
    digests = [row["sha256"] for row in entries]
    if not ids_unique(keys) or not ids_unique(paths) or not ids_unique(digests):
        out.append(issue("TB_CONTROL_INDEX_UNIQUE", "/entries", "control identities, paths, and digests must each be unique"))
    if data["artifact_role"] == "local_control_index":
        if set(keys) != expected_local_control_keys():
            out.append(issue("TB_CONTROL_INDEX_COVERAGE", "/entries", "physical index must cover all 108 node/payload/control cells"))
        if keys != ordered_local_control_keys():
            out.append(issue("TB_CONTROL_INDEX_ORDER", "/entries", "physical index must use node, payload, then declared control order"))
        if data["producer"]["dirty"]:
            out.append(issue("TB_MEASURED_DIRTY", "/producer/dirty", "physical measured local-control index requires a clean producer"))
    return out


def semantic_measurement_index(data: dict[str, Any]) -> list[Issue]:
    out: list[Issue] = []
    entries = data["entries"]
    cell_ids = [row["cell_id"] for row in entries]
    paths = [row["relative_path"] for row in entries]
    digests = [row["sha256"] for row in entries]
    if not ids_unique(cell_ids) or not ids_unique(paths) or not ids_unique(digests):
        out.append(issue("TB_MEASUREMENT_INDEX_UNIQUE", "/entries", "cell IDs, paths, and digests must each be unique"))
    if data["artifact_role"] == "measurement_index":
        if set(cell_ids) != required_cell_ids():
            out.append(issue("TB_MEASUREMENT_INDEX_COVERAGE", "/entries", "physical index must cover all 246 cells"))
        if cell_ids != scheduled_cell_ids(data["plan_seed"]):
            out.append(issue("TB_MEASUREMENT_INDEX_ORDER", "/entries", "physical index must use the seed-derived schedule order"))
        if data["producer"]["dirty"]:
            out.append(issue("TB_MEASURED_DIRTY", "/producer/dirty", "physical measured index requires a clean producer"))
    return out


def semantic_placement_evidence_graph(data: dict[str, Any]) -> list[Issue]:
    out: list[Issue] = []
    nodes = data["nodes"]
    node_ids = [row["node_id"] for row in nodes]
    paths = [row["relative_path"] for row in nodes]
    if not ids_unique(node_ids) or not ids_unique(paths):
        out.append(issue("PLACEMENT_GRAPH_NODE_UNIQUE", "/nodes", "evidence node IDs and paths must be unique"))
    node_set = set(node_ids)
    input_roles = [
        row["role"] for row in nodes
        if row["role"] not in {"quality_evidence", "allocation_evidence", "gate_evidence"}
    ]
    if not ids_unique(input_roles):
        out.append(issue("PLACEMENT_GRAPH_INPUT_ROLE_UNIQUE", "/nodes", "each placement input role must occur at most once"))
    nodes_by_id = {row["node_id"]: row for row in nodes}
    required_roles_by_passed_gate = {
        "artifact_complete": {"model_manifest"},
        "tensor_reconciled": {"tensor_inventory"},
        "layout_complete": {"quantization_layout"},
        "memory_baseline_accepted": {"memory_baseline_a", "memory_baseline_b", "memory_baseline_c"},
        "memory_nonnegative": {"reserve_headroom_policy"},
        "quality_available": {"quality_evidence"},
        "scratch_bounded": {"formula_set"},
        "state_bounded": {"formula_set"},
        "transport_profile_available": {"link_summary"},
        "text_subset_proven": {"text_subset_dependency"},
    }
    gates = data["gate_resolutions"]
    gate_ids = [row["gate_id"] for row in gates]
    if set(gate_ids) != ALL_GATES or not ids_unique(gate_ids):
        out.append(issue("PLACEMENT_GRAPH_GATE_COVERAGE", "/gate_resolutions", "graph must resolve every gate exactly once"))
    for index, row in enumerate(gates):
        missing = set(row["evidence_node_ids"]) - node_set
        if missing:
            out.append(issue("PLACEMENT_GRAPH_NODE_REFERENCE", f"/gate_resolutions/{index}/evidence_node_ids", f"unknown nodes {sorted(missing)}"))
        if row["disposition"] in {"passed", "failed"} and (row["rule_id"] is None or not row["evidence_node_ids"]):
            out.append(issue("PLACEMENT_GRAPH_GATE_EVIDENCE", f"/gate_resolutions/{index}", "passed or failed gate requires a rule and resolved evidence nodes"))
        if row["disposition"] == "not_applicable" and (row["rule_id"] is not None or row["evidence_node_ids"]):
            out.append(issue("PLACEMENT_GRAPH_GATE_EVIDENCE", f"/gate_resolutions/{index}", "not-applicable gate cannot carry a rule or success evidence"))
        referenced = [nodes_by_id[node_id] for node_id in row["evidence_node_ids"] if node_id in nodes_by_id]
        if row["disposition"] in {"passed", "failed"} and any(
            node["acceptance_status"] != "accepted" for node in referenced
        ):
            out.append(issue("PLACEMENT_GRAPH_GATE_ACCEPTANCE", f"/gate_resolutions/{index}/evidence_node_ids", "passed or failed gate evidence must be accepted"))
        if row["disposition"] == "passed":
            roles = {node["role"] for node in referenced}
            required_roles = required_roles_by_passed_gate[row["gate_id"]]
            if not required_roles.issubset(roles):
                out.append(issue(
                    "PLACEMENT_GRAPH_GATE_BINDING",
                    f"/gate_resolutions/{index}/evidence_node_ids",
                    f"passed {row['gate_id']} gate requires evidence roles {sorted(required_roles)}",
                ))
    allocations = data["allocation_resolutions"]
    allocation_ids = [row["allocation_id"] for row in allocations]
    if not ids_unique(allocation_ids):
        out.append(issue("PLACEMENT_GRAPH_ALLOCATION_UNIQUE", "/allocation_resolutions", "allocation resolutions must be unique"))
    for index, row in enumerate(allocations):
        references = set(row["evidence_node_ids"])
        if row["zero_bytes_proof_node_id"] is not None:
            references.add(row["zero_bytes_proof_node_id"])
        missing = references - node_set
        if missing:
            out.append(issue("PLACEMENT_GRAPH_NODE_REFERENCE", f"/allocation_resolutions/{index}", f"unknown nodes {sorted(missing)}"))
        accepted_references = [nodes_by_id[node_id] for node_id in references if node_id in nodes_by_id]
        if any(node["acceptance_status"] != "accepted" for node in accepted_references):
            out.append(issue("PLACEMENT_GRAPH_ALLOCATION_ACCEPTANCE", f"/allocation_resolutions/{index}", "allocation evidence and zero-byte proofs must be accepted"))
    allocation_classes = {row["memory_class"] for row in allocations}
    passed_gates = {row["gate_id"] for row in gates if row["disposition"] == "passed"}
    if "scratch_bounded" in passed_gates and "scratch" not in allocation_classes:
        out.append(issue("PLACEMENT_GRAPH_GATE_BINDING", "/allocation_resolutions", "passed scratch gate requires a scratch allocation resolution"))
    if "state_bounded" in passed_gates and not {"kv_state", "recurrent_state", "router_state"}.issubset(allocation_classes):
        out.append(issue("PLACEMENT_GRAPH_GATE_BINDING", "/allocation_resolutions", "passed state gate requires KV, recurrent, and router state allocation resolutions"))
    if set(data["required_memory_classes"]) != REQUIRED_MEMORY_CLASSES:
        out.append(issue("PLACEMENT_GRAPH_MEMORY_CLASSES", "/required_memory_classes", "required memory classes are not exhaustive"))
    return out


def semantic_placement(data: dict[str, Any], allow_resolved_go: bool = False) -> list[Issue]:
    out: list[Issue] = []
    inputs = data["inputs"]
    expected_input_schemas = {
        "model_manifest": "qw5.model-artifact-manifest/v1",
        "tensor_inventory": "qw5.tensor-inventory/v1",
        "link_summary": "qw5.tb5-link-summary/v1",
        "quantization_layout": "qw5.quantization-layout/v1",
        "formula_set": "qw5.formula-set/v1",
        "text_subset_dependency": "qw5.text-subset-dependency/v1",
        "gate_rule_set": "qw5.placement-gate-rule-set/v1",
        "placement_candidate_set": "qw5.placement-candidate-set/v1",
        "solver_objective": "qw5.placement-solver-objective/v1",
        "reserve_headroom_policy": "qw5.reserve-headroom-policy/v1",
    }
    for name, expected_schema in expected_input_schemas.items():
        record = inputs[name]
        if record is not None and record["schema"] != expected_schema:
            out.append(issue("PLACEMENT_INPUT_SCHEMA", f"/inputs/{name}/schema", f"expected {expected_schema}"))
    for name, expected_schema in (
        ("hardware_inventory", "qw5.hardware-inventory/v1"),
        ("memory_baseline", "qw5.memory-baseline/v1"),
    ):
        for node, record in inputs[name].items():
            if record["schema"] != expected_schema:
                out.append(issue("PLACEMENT_INPUT_SCHEMA", f"/inputs/{name}/{node}/schema", f"expected {expected_schema}"))
    if data["quantization_candidate"]["layout_spec_sha256"] != inputs["quantization_layout"]["sha256"]:
        out.append(issue("PLACEMENT_LAYOUT_IDENTITY", "/quantization_candidate/layout_spec_sha256", "layout digest differs from input identity"))
    if data["model"]["component_scope"] == "text_execution_subset" and inputs["text_subset_dependency"] is None:
        out.append(issue("PLACEMENT_TEXT_SUBSET_PROOF", "/inputs/text_subset_dependency", "text subset requires a dependency proof"))
    if data["model"]["component_scope"] != "text_execution_subset" and inputs["text_subset_dependency"] is not None:
        out.append(issue("PLACEMENT_TEXT_SUBSET_APPLICABILITY", "/inputs/text_subset_dependency", "non-subset analysis must not claim a text-subset proof"))
    size = data["size_reconciliation"]
    expected_total = sum(size[name] for name in (
        "packed_weight_bytes", "quantization_metadata_bytes", "padding_alignment_bytes",
        "higher_precision_exception_bytes", "container_overhead_bytes",
    ))
    if size["total_bytes"] != expected_total:
        out.append(issue("PLACEMENT_SIZE_RECONCILIATION", "/size_reconciliation/total_bytes", f"expected {expected_total}"))
    allocations = data["allocations"]
    allocation_ids = [row["allocation_id"] for row in allocations]
    if not ids_unique(allocation_ids):
        out.append(issue("PLACEMENT_ALLOCATION_UNIQUE", "/allocations", "allocation IDs must be unique"))
    by_node: Counter[str] = Counter()
    for index, row in enumerate(allocations):
        by_node[row["node"]] += row["bytes"]
        if row["range"] is not None:
            low = row["range"]["low_bytes"]
            high = row["range"]["high_bytes"]
            if low > high or not low <= row["bytes"] <= high:
                out.append(issue("PLACEMENT_RANGE", f"/allocations/{index}/range", "range must contain the selected byte value"))
        if row["bytes"] == 0 and row["zero_bytes_proof_node_id"] is None:
            out.append(issue("PLACEMENT_ZERO_BYTES_PROOF", f"/allocations/{index}/zero_bytes_proof_node_id", "a zero-byte class requires a resolved architecture proof"))
        if row["bytes"] != 0 and row["zero_bytes_proof_node_id"] is not None:
            out.append(issue("PLACEMENT_ZERO_BYTES_PROOF", f"/allocations/{index}/zero_bytes_proof_node_id", "a nonzero allocation cannot cite a zero-byte proof"))
    budgets = data["node_budgets"]
    nodes = [row["node"] for row in budgets]
    if not ids_unique(nodes):
        out.append(issue("PLACEMENT_NODE_UNIQUE", "/node_budgets", "node budgets must be unique"))
    if nodes != ["A", "B", "C"]:
        out.append(issue("PLACEMENT_NODE_COVERAGE", "/node_budgets", "node budgets must cover A, B, and C in order"))
    headrooms: list[int] = []
    for index, row in enumerate(budgets):
        base = f"/node_budgets/{index}"
        if row["physical_bytes"] - row["baseline_available_bytes"] != row["os_reserve_bytes"]:
            out.append(issue("PLACEMENT_OS_RESERVE_FORMULA", base + "/os_reserve_bytes", "physical minus baseline available must equal observed OS reserve"))
        expected_budget = row["baseline_available_bytes"] - row["safety_reserve_bytes"]
        if row["placement_budget_bytes"] != expected_budget:
            out.append(issue("PLACEMENT_BUDGET_FORMULA", base + "/placement_budget_bytes", f"expected {expected_budget}"))
        if row["allocated_bytes"] != by_node[row["node"]]:
            out.append(issue("PLACEMENT_ALLOCATION_RECONCILIATION", base + "/allocated_bytes", f"expected {by_node[row['node']]}"))
        expected_headroom = row["placement_budget_bytes"] - row["allocated_bytes"]
        if row["headroom_bytes"] != expected_headroom:
            out.append(issue("PLACEMENT_HEADROOM_FORMULA", base + "/headroom_bytes", f"expected {expected_headroom}"))
        headrooms.append(row["headroom_bytes"])
    if set(by_node) - set(nodes):
        out.append(issue("PLACEMENT_ALLOCATION_NODE", "/allocations", "allocation refers to a node without a budget"))
    for index, edge in enumerate(data["network_edges"]):
        if edge["source"] == edge["destination"]:
            out.append(issue("PLACEMENT_NETWORK_SELF_EDGE", f"/network_edges/{index}", "network edge must cross nodes"))
        if inputs["link_summary"] is None:
            out.append(issue("PLACEMENT_LINK_INPUT", f"/network_edges/{index}", "network edge requires a link summary input"))
        elif edge["link_summary_sha256"] != inputs["link_summary"]["sha256"]:
            out.append(issue("PLACEMENT_LINK_IDENTITY", f"/network_edges/{index}/link_summary_sha256", "link digest differs from input identity"))
    decision = data["decision"]
    required = set(decision["required_gates"])
    applicable = set(decision["applicable_gates"])
    passed = set(decision["passed_gates"])
    failed = set(decision["failed_gates"])
    unresolved = set(decision["unresolved_gates"])
    not_applicable = set(decision["not_applicable_gates"])
    if required != ALL_GATES:
        out.append(issue("PLACEMENT_GATE_REQUIRED_SET", "/decision/required_gates", "required gate set is not exhaustive"))
    partitions = (passed, failed, unresolved, not_applicable)
    if any(partitions[i] & partitions[j] for i in range(len(partitions)) for j in range(i + 1, len(partitions))):
        out.append(issue("PLACEMENT_GATE_DISJOINT", "/decision", "passed, failed, unresolved, and not-applicable gates must be disjoint"))
    if passed | failed | unresolved | not_applicable != required or applicable != passed | failed | unresolved:
        out.append(issue("PLACEMENT_GATE_COVERAGE", "/decision", "applicable and not-applicable partitions must exhaust every required gate"))
    evaluations = decision["gate_evaluations"]
    evaluation_ids = [row["gate_id"] for row in evaluations]
    if set(evaluation_ids) != ALL_GATES or not ids_unique(evaluation_ids):
        out.append(issue("PLACEMENT_GATE_EVALUATION_COVERAGE", "/decision/gate_evaluations", "one evaluation is required for every gate"))
    expected_dispositions = {
        **{gate: "passed" for gate in passed},
        **{gate: "failed" for gate in failed},
        **{gate: "unresolved" for gate in unresolved},
        **{gate: "not_applicable" for gate in not_applicable},
    }
    for index, row in enumerate(evaluations):
        if row["disposition"] != expected_dispositions.get(row["gate_id"]):
            out.append(issue("PLACEMENT_GATE_EVALUATION", f"/decision/gate_evaluations/{index}", "evaluation disagrees with gate partition"))
        if row["disposition"] in {"passed", "failed"} and (row["rule_id"] is None or not row["evidence_node_ids"]):
            out.append(issue("PLACEMENT_GATE_EVIDENCE", f"/decision/gate_evaluations/{index}", "passed or failed gate requires a rule and evidence nodes"))
        if row["disposition"] == "not_applicable" and (row["rule_id"] is not None or row["evidence_node_ids"]):
            out.append(issue("PLACEMENT_GATE_EVIDENCE", f"/decision/gate_evaluations/{index}", "not-applicable gate cannot carry a rule or success evidence"))
    text_subset = data["model"]["component_scope"] == "text_execution_subset"
    expected_not_applicable: set[str] = set()
    if text_subset:
        if "text_subset_proven" not in applicable or "text_subset_proven" in not_applicable:
            out.append(issue("PLACEMENT_TEXT_SUBSET_APPLICABILITY", "/decision", "text-subset gate is applicable only to text-subset analyses"))
    else:
        expected_not_applicable.add("text_subset_proven")
        if "text_subset_proven" not in not_applicable:
            out.append(issue("PLACEMENT_TEXT_SUBSET_APPLICABILITY", "/decision/not_applicable_gates", "complete/non-subset analysis must mark text-subset proof not applicable"))
    networked = bool(data["network_edges"])
    if networked:
        if inputs["link_summary"] is None or "transport_profile_available" not in applicable:
            out.append(issue("PLACEMENT_TRANSPORT_APPLICABILITY", "/decision", "networked candidates require an applicable transport gate and link summary"))
    else:
        expected_not_applicable.add("transport_profile_available")
        if inputs["link_summary"] is not None or "transport_profile_available" not in not_applicable:
            out.append(issue("PLACEMENT_TRANSPORT_APPLICABILITY", "/decision", "network-free candidates must mark transport not applicable and omit link summary"))
    if not_applicable != expected_not_applicable:
        out.append(issue("PLACEMENT_GATE_APPLICABILITY", "/decision/not_applicable_gates", f"expected only {sorted(expected_not_applicable)}"))
    nonnegative = bool(headrooms) and min(headrooms) >= 0
    if nonnegative and "memory_nonnegative" not in passed:
        out.append(issue("PLACEMENT_MEMORY_GATE", "/decision", "nonnegative headroom must pass the memory gate"))
    if not nonnegative and "memory_nonnegative" in passed:
        out.append(issue("PLACEMENT_MEMORY_GATE", "/decision/passed_gates", "negative headroom cannot pass the memory gate"))
    lineage_records = [
        inputs["model_manifest"], inputs["tensor_inventory"], inputs["quantization_layout"],
        inputs["formula_set"], inputs["gate_rule_set"], inputs["placement_candidate_set"],
        inputs["solver_objective"], inputs["reserve_headroom_policy"],
        *inputs["hardware_inventory"].values(), *inputs["memory_baseline"].values(),
    ]
    lineage_records.extend(record for record in (inputs["link_summary"], inputs["text_subset_dependency"]) if record is not None)
    lineage_accepted = all(record["acceptance_status"] == "accepted" for record in lineage_records)
    if failed or not nonnegative:
        expected_outcome = "NO_GO"
    elif unresolved or not lineage_accepted:
        expected_outcome = "UNDETERMINED"
    else:
        expected_outcome = "GO"
    if decision["outcome"] != expected_outcome:
        out.append(issue("PLACEMENT_OUTCOME_DERIVATION", "/decision/outcome", f"expected {expected_outcome} from accepted lineage, gate outcomes, and headroom"))
    if decision["outcome"] == "GO" and (applicable != passed or not lineage_accepted or decision["next_permitted_task"] is None):
        out.append(issue("PLACEMENT_GO_GATES", "/decision/outcome", "GO requires every applicable gate passed, accepted lineage, nonnegative headroom, and a next task"))
    if decision["outcome"] == "GO":
        allocation_classes = {row["class"] for row in allocations}
        if allocation_classes != REQUIRED_MEMORY_CLASSES:
            out.append(issue("PLACEMENT_MEMORY_CLASS_COVERAGE", "/allocations", f"GO requires all memory classes; missing {sorted(REQUIRED_MEMORY_CLASSES - allocation_classes)}"))
        if "quality_available" in passed and data["quantization_candidate"]["quality_evidence_sha256"] is None:
            out.append(issue("PLACEMENT_QUALITY_EVIDENCE", "/quantization_candidate/quality_evidence_sha256", "a passed quality gate requires an identified quality artifact"))
        if not allow_resolved_go:
            out.append(issue(
                "PLACEMENT_GO_REQUIRES_RESOLVED_GRAPH",
                "/decision/outcome",
                "GO is accepted only through materialized placement-evidence-graph resolution",
            ))
    return out


def placement_input_roles(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    inputs = data["inputs"]
    roles: dict[str, dict[str, Any]] = {
        "model_manifest": inputs["model_manifest"],
        "tensor_inventory": inputs["tensor_inventory"],
        "hardware_inventory_a": inputs["hardware_inventory"]["A"],
        "hardware_inventory_b": inputs["hardware_inventory"]["B"],
        "hardware_inventory_c": inputs["hardware_inventory"]["C"],
        "memory_baseline_a": inputs["memory_baseline"]["A"],
        "memory_baseline_b": inputs["memory_baseline"]["B"],
        "memory_baseline_c": inputs["memory_baseline"]["C"],
        "quantization_layout": inputs["quantization_layout"],
        "formula_set": inputs["formula_set"],
        "gate_rule_set": inputs["gate_rule_set"],
        "placement_candidate_set": inputs["placement_candidate_set"],
        "solver_objective": inputs["solver_objective"],
        "reserve_headroom_policy": inputs["reserve_headroom_policy"],
    }
    if inputs["link_summary"] is not None:
        roles["link_summary"] = inputs["link_summary"]
    if inputs["text_subset_dependency"] is not None:
        roles["text_subset_dependency"] = inputs["text_subset_dependency"]
    return roles


def validate_placement_evidence_bundle(
    analysis: dict[str, Any],
    graph: dict[str, Any],
    artifacts_by_path: dict[str, dict[str, Any]],
) -> list[Issue]:
    out: list[Issue] = []
    graph_issues = validate_instance(graph, "qw5.placement-evidence-graph/v1")
    analysis_schema = load_json(SCHEMA_DIR / SCHEMA_FILES["qw5.placement-analysis/v1"])
    analysis_structural = schema_issues(analysis, analysis_schema)
    out.extend(graph_issues)
    out.extend(analysis_structural)
    if graph_issues or analysis_structural:
        return out
    graph_digest = canonical_digest(graph)
    if analysis["evidence_graph_sha256"] != graph_digest:
        out.append(issue("PLACEMENT_GRAPH_DIGEST", "/evidence_graph_sha256", "analysis does not reference the canonical evidence graph"))
    expected_identity = {
        "repository_id": analysis["model"]["repository_id"],
        "immutable_revision": analysis["model"]["immutable_revision"],
        "component_scope": analysis["model"]["component_scope"],
        "phase": analysis["workload"]["phase"],
        "context_tokens": analysis["workload"]["context_tokens"],
        "candidate_id": analysis["quantization_candidate"]["candidate_id"],
    }
    if graph["analysis_identity"] != expected_identity:
        out.append(issue("PLACEMENT_GRAPH_IDENTITY", "/evidence_graph_sha256", "evidence graph identifies a different analysis"))
    nodes_by_id = {row["node_id"]: row for row in graph["nodes"]}
    nodes_by_role = {row["role"]: row for row in graph["nodes"] if row["role"] not in {"quality_evidence", "allocation_evidence", "gate_evidence"}}
    expected_inputs = placement_input_roles(analysis)
    if set(nodes_by_role) != set(expected_inputs):
        out.append(issue("PLACEMENT_GRAPH_INPUT_COVERAGE", "/evidence_graph_sha256", "evidence graph input roles do not match analysis inputs"))
    for role, record in expected_inputs.items():
        node = nodes_by_role.get(role)
        if node is None:
            continue
        projection = {
            "sha256": node["sha256"],
            "schema": node["schema"],
            "evidence_class": node["evidence_class"],
            "acceptance_status": node["acceptance_status"],
        }
        if projection != record:
            out.append(issue("PLACEMENT_GRAPH_INPUT_PROJECTION", "/inputs", f"graph node for {role} differs from the analysis input"))
    graph_gates = {
        row["gate_id"]: {
            "gate_id": row["gate_id"],
            "disposition": row["disposition"],
            "rule_id": row["rule_id"],
            "evidence_node_ids": row["evidence_node_ids"],
        }
        for row in graph["gate_resolutions"]
    }
    for index, evaluation in enumerate(analysis["decision"]["gate_evaluations"]):
        projection = {
            "gate_id": evaluation["gate_id"],
            "disposition": evaluation["disposition"],
            "rule_id": evaluation["rule_id"],
            "evidence_node_ids": evaluation["evidence_node_ids"],
        }
        if graph_gates.get(evaluation["gate_id"]) != projection:
            out.append(issue("PLACEMENT_GRAPH_GATE_PROJECTION", f"/decision/gate_evaluations/{index}", "analysis gate differs from its evidence-graph resolution"))
    graph_allocations = {row["allocation_id"]: row for row in graph["allocation_resolutions"]}
    for index, allocation in enumerate(analysis["allocations"]):
        projection = {
            "allocation_id": allocation["allocation_id"],
            "memory_class": allocation["class"],
            "formula_id": allocation["formula_id"],
            "evidence_node_ids": allocation["evidence_node_ids"],
            "zero_bytes_proof_node_id": allocation["zero_bytes_proof_node_id"],
        }
        if graph_allocations.get(allocation["allocation_id"]) != projection:
            out.append(issue("PLACEMENT_GRAPH_ALLOCATION_PROJECTION", f"/allocations/{index}", "allocation differs from its evidence-graph resolution"))
    if set(graph_allocations) != {row["allocation_id"] for row in analysis["allocations"]}:
        out.append(issue("PLACEMENT_GRAPH_ALLOCATION_COVERAGE", "/allocations", "graph and analysis allocation IDs differ"))
    unresolved_nodes: set[str] = set()
    resolved_artifacts_by_id: dict[str, dict[str, Any]] = {}
    for index, node in enumerate(graph["nodes"]):
        if node["acceptance_status"] != "accepted":
            unresolved_nodes.add(node["node_id"])
        artifact = artifacts_by_path.get(node["relative_path"])
        if artifact is None:
            unresolved_nodes.add(node["node_id"])
            out.append(issue("PLACEMENT_GRAPH_NODE_RESOLUTION", f"/nodes/{index}/relative_path", "evidence node path did not resolve"))
            continue
        if canonical_digest(artifact) != node["sha256"]:
            unresolved_nodes.add(node["node_id"])
            out.append(issue("PLACEMENT_GRAPH_NODE_DIGEST", f"/nodes/{index}/sha256", "resolved artifact digest differs from the graph node"))
        schema_id = artifact.get("schema")
        if schema_id != node["schema"] or schema_id not in SCHEMA_FILES:
            unresolved_nodes.add(node["node_id"])
            out.append(issue("PLACEMENT_GRAPH_NODE_SCHEMA", f"/nodes/{index}/schema", "resolved artifact schema is unavailable or differs from the graph node"))
            continue
        artifact_issues = validate_instance(artifact, schema_id)
        if artifact_issues:
            unresolved_nodes.add(node["node_id"])
            out.extend(artifact_issues)
        else:
            resolved_artifacts_by_id[node["node_id"]] = artifact
        if artifact.get("evidence_class") != node["evidence_class"]:
            unresolved_nodes.add(node["node_id"])
            out.append(issue("PLACEMENT_GRAPH_NODE_EVIDENCE_CLASS", f"/nodes/{index}/evidence_class", "resolved artifact evidence class differs from the graph node"))
    manifest_node = nodes_by_role.get("model_manifest")
    tensor_node = nodes_by_role.get("tensor_inventory")
    if manifest_node is not None and tensor_node is not None:
        manifest_artifact = resolved_artifacts_by_id.get(manifest_node["node_id"])
        tensor_artifact = resolved_artifacts_by_id.get(tensor_node["node_id"])
        if manifest_artifact is not None and tensor_artifact is not None:
            if tensor_artifact["model_manifest_sha256"] != manifest_node["sha256"]:
                unresolved_nodes.add(tensor_node["node_id"])
                out.append(issue("PLACEMENT_GRAPH_MODEL_LINEAGE", "/inputs/tensor_inventory", "tensor inventory does not bind the resolved model manifest"))
            expected_model_identity = {
                "repository_id": manifest_artifact["repository"]["repository_id"],
                "immutable_revision": manifest_artifact["repository"]["immutable_revision"],
            }
            if tensor_artifact["model"] != expected_model_identity or analysis["model"]["repository_id"] != expected_model_identity["repository_id"] or analysis["model"]["immutable_revision"] != expected_model_identity["immutable_revision"]:
                unresolved_nodes.update({manifest_node["node_id"], tensor_node["node_id"]})
                out.append(issue("PLACEMENT_GRAPH_MODEL_LINEAGE", "/model", "analysis, manifest, and tensor inventory model identities differ"))
    if graph_gates["artifact_complete"]["disposition"] == "passed" and manifest_node is not None:
        manifest_artifact = resolved_artifacts_by_id.get(manifest_node["node_id"])
        if manifest_artifact is not None and manifest_artifact["completeness"]["status"] != "complete":
            unresolved_nodes.add(manifest_node["node_id"])
            out.append(issue("PLACEMENT_GRAPH_GATE_DERIVATION", "/decision/gate_evaluations", "artifact_complete cannot pass for an incomplete manifest"))
    if graph_gates["memory_baseline_accepted"]["disposition"] == "passed":
        for role in ("memory_baseline_a", "memory_baseline_b", "memory_baseline_c"):
            node = nodes_by_role.get(role)
            artifact = resolved_artifacts_by_id.get(node["node_id"]) if node is not None else None
            if artifact is not None and artifact["summary"]["status"] != "COMPLETE":
                unresolved_nodes.add(node["node_id"])
                out.append(issue("PLACEMENT_GRAPH_GATE_DERIVATION", "/decision/gate_evaluations", f"memory_baseline_accepted cannot pass for incomplete {role}"))
    out.extend(semantic_placement(analysis, allow_resolved_go=True))
    if analysis["decision"]["outcome"] == "GO":
        unresolved_rule_ids = sorted({
            row["rule_id"] or "<missing>"
            for row in analysis["decision"]["gate_evaluations"]
            if row["disposition"] == "passed" and row["rule_id"] not in PLACEMENT_GATE_RULE_EVALUATORS
        })
        if unresolved_rule_ids:
            out.append(issue(
                "PLACEMENT_GO_UNRESOLVED_RULE",
                "/decision/gate_evaluations",
                f"GO requires registered deterministic gate evaluators; unresolved rules {unresolved_rule_ids}",
            ))
    if analysis["decision"]["outcome"] == "GO" and unresolved_nodes:
        out.append(issue("PLACEMENT_GO_UNRESOLVED_GRAPH", "/decision/outcome", f"GO has unresolved evidence nodes {sorted(unresolved_nodes)}"))
    if analysis["decision"]["outcome"] == "GO" and "quality_available" in analysis["decision"]["passed_gates"]:
        quality_nodes = [
            nodes_by_id[node_id]
            for node_id in graph_gates["quality_available"]["evidence_node_ids"]
            if node_id in nodes_by_id and nodes_by_id[node_id]["role"] == "quality_evidence"
        ]
        if not quality_nodes or analysis["quantization_candidate"]["quality_evidence_sha256"] not in {row["sha256"] for row in quality_nodes}:
            out.append(issue("PLACEMENT_QUALITY_EVIDENCE", "/quantization_candidate/quality_evidence_sha256", "quality identity does not resolve through the quality gate"))
    return out


def validate_flow_definition(row: dict[str, Any], pointer: str) -> list[Issue]:
    expected = FLOW.get(row["flow_id"])
    if expected is None:
        return [issue("TB_FLOW_ID", pointer + "/flow_id", "unknown directed flow")]
    if (row["source"], row["destination"], row["route_alias"]) != expected:
        return [issue("TB_FLOW_MAPPING", pointer, f"expected source, destination, route {expected}")]
    return []


def validate_scenario(row: dict[str, Any], pointer: str = "/scenario") -> list[Issue]:
    out: list[Issue] = []
    expected = SCENARIOS[row["scenario_id"]]
    actual = tuple(flow["flow_id"] for flow in row["flows"])
    if actual != expected:
        out.append(issue("TB_SCENARIO_FLOW_SET", pointer + "/flows", f"expected {expected}, got {actual}"))
    for index, flow in enumerate(row["flows"]):
        out.extend(validate_flow_definition(flow, pointer + f"/flows/{index}"))
    return out


def semantic_tb_plan(data: dict[str, Any]) -> list[Issue]:
    out: list[Issue] = []
    matrix = data["matrix"]
    if tuple(matrix["scenario_order"]) != SCENARIO_ORDER:
        out.append(issue("TB_PLAN_SCENARIO_ORDER", "/matrix/scenario_order", "scenario order differs from v1"))
    scenarios = matrix["scenarios"]
    ids = [row["scenario_id"] for row in scenarios]
    if tuple(ids) != SCENARIO_ORDER:
        out.append(issue("TB_PLAN_SCENARIO_COVERAGE", "/matrix/scenarios", "scenario definitions must appear once in v1 order"))
    for index, row in enumerate(scenarios):
        out.extend(validate_scenario(row, f"/matrix/scenarios/{index}"))
    count = len(SCENARIOS) * len(STREAM_PAYLOADS) + len(SOLO_SCENARIOS) * len(ROUND_TRIP_PAYLOADS)
    if matrix["planned_cell_count"] != count:
        out.append(issue("TB_PLAN_CELL_COUNT", "/matrix/planned_cell_count", f"expected {count}"))
    if data["producer"]["qw5_commit"] != data["identity"]["qw5_commit"] or data["producer"]["dirty"] != data["identity"]["dirty"]:
        out.append(issue("TB_PLAN_IDENTITY_RECONCILIATION", "/identity", "producer and plan QW5 identities must match"))
    if data["approval_status"] == "approved" and (data["identity"]["dirty"] or data["producer"]["dirty"]):
        out.append(issue("TB_PLAN_DIRTY", "/approval_status", "approved plans require clean producer and harness identities"))
    return out


def semantic_route(data: dict[str, Any]) -> list[Issue]:
    out: list[Issue] = []
    if data["artifact_role"] == "route_proof" and data["producer"]["dirty"]:
        out.append(issue("TB_MEASURED_DIRTY", "/producer/dirty", "physical measured route proof requires a clean producer"))
    routes = data["routes"]
    ids = [row["flow_id"] for row in routes]
    if tuple(ids) != tuple(FLOW):
        out.append(issue("TB_ROUTE_COVERAGE", "/routes", "route proof must contain all six flows in v1 order"))
    for index, row in enumerate(routes):
        out.extend(validate_flow_definition(row, f"/routes/{index}"))
    return out


def expected_copy_keys(flow_id: str) -> set[tuple[str, str]]:
    source, destination, _ = FLOW[flow_id]
    return {
        (source, "producer_to_send"), (source, "send_to_transport"),
        (source, "kernel_dma_hardware"), (destination, "transport_to_receive"),
        (destination, "receive_to_consumer"), (destination, "kernel_dma_hardware"),
    }


def integer_median(values: list[int]) -> int:
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) // 2


def expected_metric(values: list[int], unit: str) -> dict[str, Any]:
    if not values:
        return {
            "sample_count": 0, "median": None, "median_absolute_deviation": None,
            "p95": None, "minimum": None, "maximum": None, "unit": unit,
        }
    ordered = sorted(values)
    median = integer_median(ordered)
    return {
        "sample_count": len(ordered),
        "median": median,
        "median_absolute_deviation": integer_median([abs(value - median) for value in ordered]),
        "p95": ordered[math.ceil(0.95 * len(ordered)) - 1],
        "minimum": ordered[0],
        "maximum": ordered[-1],
        "unit": unit,
    }


def canonical_cell_ids() -> list[str]:
    return [
        *(f"stream:{scenario}:{payload}" for scenario in SCENARIO_ORDER for payload in STREAM_PAYLOADS),
        *(f"round-trip:{scenario}:{payload}" for scenario in SOLO_SCENARIOS for payload in ROUND_TRIP_PAYLOADS),
    ]


def scheduled_cell_ids(seed: int) -> list[str]:
    prefix = struct.pack("!Q", seed)
    return sorted(
        canonical_cell_ids(),
        key=lambda cell_id: (hashlib.sha256(prefix + cell_id.encode("utf-8")).digest(), cell_id),
    )


def semantic_tb_measurement(data: dict[str, Any]) -> list[Issue]:
    out = validate_scenario(data["scenario"])
    if data["producer"]["qw5_commit"] != data["identity"]["qw5_commit"] or data["producer"]["dirty"] != data["identity"]["dirty"]:
        out.append(issue("TB_MEASUREMENT_IDENTITY_RECONCILIATION", "/identity", "producer and measurement QW5 identities must match"))
    if data["artifact_role"] == "measurement" and data["evidence_class"] == "MEASURED" and (data["identity"]["dirty"] or data["producer"]["dirty"]):
        out.append(issue("TB_MEASURED_DIRTY", "/identity/dirty", "physical MEASURED TB5 evidence requires clean producer and QW5 identities"))
    scenario_id = data["scenario"]["scenario_id"]
    flow_ids = SCENARIOS[scenario_id]
    simultaneous = len(flow_ids) > 1
    buffers = data["application_buffers"]
    expected_buffer_projection = {
        "bytes_per_buffer": data["payload_bytes"],
        "active_flow_count": len(flow_ids),
        "peak_application_payload_buffer_bytes": 2 * data["payload_bytes"] * len(flow_ids),
    }
    if any(buffers[name] != value for name, value in expected_buffer_projection.items()):
        out.append(issue(
            "TB_APPLICATION_BUFFER_RECONCILIATION", "/application_buffers",
            f"expected {expected_buffer_projection}",
        ))
    mode_id = "round-trip" if data["mode"] == "round_trip" else "stream"
    expected_cell_id = f"{mode_id}:{scenario_id}:{data['payload_bytes']}"
    if data["cell_id"] != expected_cell_id:
        out.append(issue("TB_CELL_IDENTITY", "/cell_id", f"expected {expected_cell_id}"))
    schedule = scheduled_cell_ids(data["plan_seed"])
    if expected_cell_id in schedule:
        expected_schedule_index = schedule.index(expected_cell_id)
        if data["schedule_index"] != expected_schedule_index:
            out.append(issue("TB_SCHEDULE_INDEX", "/schedule_index", f"expected {expected_schedule_index}"))
    if data["mode"] == "round_trip" and scenario_id not in SOLO_SCENARIOS:
        out.append(issue("TB_ROUND_TRIP_SCOPE", "/mode", "round-trip mode is limited to solo scenarios"))
    expected_socket_keys = {(flow_id, endpoint) for flow_id in flow_ids for endpoint in FLOW[flow_id][:2]}
    actual_socket_keys = {(row["flow_id"], row["endpoint"]) for row in data["socket_settings"]}
    if actual_socket_keys != expected_socket_keys or len(actual_socket_keys) != len(data["socket_settings"]):
        out.append(issue("TB_SOCKET_COVERAGE", "/socket_settings", "requested/effective socket settings must cover both endpoints of every flow exactly once"))
    attempts = data["attempts"]
    attempt_ids = [row["attempt_id"] for row in attempts]
    if not ids_unique(attempt_ids):
        out.append(issue("TB_ATTEMPT_ID_UNIQUE", "/attempts", "attempt IDs must be unique"))
    phases = [row["phase"] for row in attempts]
    if "measurement" in phases and "warmup" in phases[phases.index("measurement"):]:
        out.append(issue("TB_ATTEMPT_PHASE_ORDER", "/attempts", "all warm-ups must precede measurement attempts"))
    phase_indexes: dict[str, list[int]] = defaultdict(list)
    previous_sequence: dict[str, int] = {}
    flow_rates: dict[str, list[int]] = defaultdict(list)
    flow_latencies: dict[str, list[int]] = defaultdict(list)
    aggregate_rates: list[int] = []
    valid_regime_by_node: dict[str, tuple[str, bool, str | None]] = {}
    for attempt_index, attempt in enumerate(attempts):
        base = f"/attempts/{attempt_index}"
        phase_indexes[attempt["phase"]].append(attempt["attempt_index"])
        expected_prefix = "warmup-" if attempt["phase"] == "warmup" else "sample-"
        if not attempt["attempt_id"].startswith(expected_prefix):
            out.append(issue("TB_ATTEMPT_PHASE_ID", base + "/attempt_id", "attempt ID prefix disagrees with phase"))
        sync = attempt["synchronization"]
        if simultaneous:
            if sync["status"] != "available":
                if attempt["valid"]:
                    out.append(issue("TB_SYNC_EVIDENCE", base + "/synchronization", "simultaneous valid attempt requires synchronization evidence"))
            else:
                expected_window = (
                    sync["coordinator_receipt_spread_ns"]
                    + sync["pre_attempt_control_rtt_max_ns"]
                    + 2 * sync["worker_start_to_ack_max_ns"]
                    + sync["timer_resolution_allowance_ns"]
                )
                if sync["coordinator_observed_start_window_ns"] != expected_window:
                    out.append(issue("TB_SYNC_RECONCILIATION", base + "/synchronization/coordinator_observed_start_window_ns", f"expected {expected_window}"))
                rtt_exceeded = sync["pre_attempt_control_rtt_max_ns"] > data["scenario"]["maximum_pre_attempt_control_rtt_ns"]
                window_exceeded = sync["coordinator_observed_start_window_ns"] > data["scenario"]["maximum_coordinator_observed_start_window_ns"]
                if rtt_exceeded and (attempt["valid"] or "SYNC_CONTROL_RTT_EXCEEDED" not in attempt["invalid_reasons"]):
                    out.append(issue("TB_SYNC_CONTROL_RTT", base + "/synchronization/pre_attempt_control_rtt_max_ns", "pre-attempt control RTT above 1 ms must invalidate the retained attempt"))
                if window_exceeded and (attempt["valid"] or "SYNC_OBSERVED_WINDOW_EXCEEDED" not in attempt["invalid_reasons"]):
                    out.append(issue("TB_SYNC_OBSERVED_WINDOW", base + "/synchronization/coordinator_observed_start_window_ns", "coordinator-observed window above 10 ms must invalidate the retained attempt"))
        elif sync["status"] != "not_required":
            out.append(issue("TB_SOLO_SYNC", base + "/synchronization", "solo attempt must mark cross-flow synchronization not required"))
        active_nodes = sorted({node for flow_id in flow_ids for node in FLOW[flow_id][:2]})
        thermal_nodes = [row["node"] for row in attempt["thermal"]]
        if thermal_nodes != active_nodes:
            out.append(issue("TB_THERMAL_COVERAGE", base + "/thermal", f"expected nodes {active_nodes}"))
        attempt_regime: dict[str, tuple[str, bool, str | None]] = {}
        for thermal_index, thermal in enumerate(attempt["thermal"]):
            if thermal["end_monotonic_ns"] < thermal["start_monotonic_ns"]:
                out.append(issue("TB_THERMAL_TIME", base + f"/thermal/{thermal_index}", "thermal timestamps regress"))
            if attempt["valid"]:
                stable = (
                    thermal["start_state"] == thermal["end_state"]
                    and thermal["start_low_power_mode"] == thermal["end_low_power_mode"]
                    and thermal["start_power_source"] == thermal["end_power_source"]
                )
                if not stable:
                    out.append(issue(
                        "TB_REGIME_TRANSITION",
                        base + f"/thermal/{thermal_index}",
                        "a valid attempt cannot cross a thermal, low-power, or power-source regime",
                    ))
                attempt_regime[thermal["node"]] = (
                    thermal["start_state"],
                    thermal["start_low_power_mode"],
                    thermal["start_power_source"],
                )
        if attempt["phase"] == "measurement" and attempt["valid"]:
            if not valid_regime_by_node:
                valid_regime_by_node = attempt_regime
            elif attempt_regime != valid_regime_by_node:
                out.append(issue(
                    "TB_REGIME_MIXED",
                    base + "/thermal",
                    "valid measurement attempts in one cell must share one exact per-node regime identity",
                ))
        sample_ids = tuple(row["flow_id"] for row in attempt["flows"])
        if sample_ids != flow_ids:
            out.append(issue("TB_ATTEMPT_FLOW_SET", base + "/flows", f"expected {flow_ids}, got {sample_ids}"))
        for flow_index, sample in enumerate(attempt["flows"]):
            sample_base = base + f"/flows/{flow_index}"
            messages = sample["messages"]
            if attempt["valid"] and sample["errors"]:
                out.append(issue("TB_VALID_FLOW_ERRORS", sample_base + "/errors", "valid attempts cannot contain flow errors"))
            if attempt["valid"] and messages < 1:
                out.append(issue("TB_VALID_MESSAGES", sample_base + "/messages", "valid attempt must contain at least one message"))
            expected_counts = {
                "logical_payload_bytes": messages * data["payload_bytes"],
                "header_bytes": messages * 64,
                "digest_trailer_bytes": messages * 32,
                "ack_bytes": messages * (64 if data["mode"] == "round_trip" else 0),
                "checksum_count": messages,
            }
            for name, expected in expected_counts.items():
                if sample[name] != expected:
                    out.append(issue("TB_BYTE_RECONCILIATION", sample_base + f"/{name}", f"expected {expected}"))
            if messages > 0 and sample["sequence_last"] - sample["sequence_first"] + 1 != messages:
                out.append(issue("TB_SEQUENCE_RANGE", sample_base, "sequence range does not match message count"))
            if sample["flow_id"] in previous_sequence and sample["sequence_first"] <= previous_sequence[sample["flow_id"]]:
                out.append(issue("TB_SEQUENCE_MONOTONIC", sample_base + "/sequence_first", "sequence range overlaps or regresses"))
            previous_sequence[sample["flow_id"]] = sample["sequence_last"]
            expected_socket_bytes = sum(expected_counts[name] for name in (
                "logical_payload_bytes", "header_bytes", "digest_trailer_bytes", "ack_bytes"
            ))
            for name in ("source_socket_bytes", "receiver_socket_bytes"):
                observation = sample[name]
                if observation["status"] == "available" and observation["value"] != expected_socket_bytes:
                    out.append(issue("TB_SOCKET_BYTE_RECONCILIATION", sample_base + f"/{name}/value", f"expected {expected_socket_bytes}"))
            source_elapsed = sample["source_monotonic_end_ns"] - sample["source_monotonic_start_ns"]
            receiver_elapsed = sample["receiver_monotonic_end_ns"] - sample["receiver_monotonic_start_ns"]
            if attempt["valid"] and (source_elapsed <= 0 or receiver_elapsed <= 0):
                out.append(issue("TB_ENDPOINT_TIME", sample_base, "valid endpoint intervals must be positive"))
            if data["mode"] == "stream" and attempt["valid"]:
                minimum = 2000000000 if attempt["phase"] == "warmup" else 3000000000
                if source_elapsed < minimum or receiver_elapsed < minimum:
                    out.append(issue("TB_STREAM_DURATION", sample_base, f"source and receiver intervals must be at least {minimum} ns"))
                if sample["round_trip_ns"]:
                    out.append(issue("TB_STREAM_LATENCY", sample_base + "/round_trip_ns", "stream mode cannot report round-trip exchanges"))
            if data["mode"] == "stream" and (
                source_elapsed > 30_000_000_000
                or receiver_elapsed > 30_000_000_000
                or sample["logical_payload_bytes"] > 34_359_738_368
            ):
                out.append(issue(
                    "TB_STREAM_CAP", sample_base,
                    "stream interval or logical payload exceeds the frozen 30-second/32-GiB per-flow cap",
                ))
            if data["mode"] == "round_trip" and attempt["valid"]:
                expected_exchanges = (20 if data["payload_bytes"] == 4194304 else 100) if attempt["phase"] == "warmup" else (100 if data["payload_bytes"] == 4194304 else 1000)
                if messages != expected_exchanges or len(sample["round_trip_ns"]) != expected_exchanges:
                    out.append(issue("TB_ROUND_TRIP_COUNT", sample_base, f"expected {expected_exchanges} exchanges and latency records"))
            copy_keys = {(row["endpoint"], row["stage"]) for row in sample["copies"]}
            expected_keys = expected_copy_keys(sample["flow_id"])
            if copy_keys != expected_keys or len(copy_keys) != len(sample["copies"]):
                out.append(issue("TB_COPY_COVERAGE", sample_base + "/copies", f"expected copy observations {sorted(expected_keys)}"))
            for copy_index, copy_row in enumerate(sample["copies"]):
                if copy_row["status"] == "available":
                    allowed_evidence = (
                        {"SIMULATED"}
                        if data["artifact_role"] == "schema_fixture"
                        else {"MEASURED", "ESTIMATED"}
                    )
                    if copy_row["evidence_class"] not in allowed_evidence:
                        out.append(issue(
                            "TB_COPY_EVIDENCE_CLASS",
                            sample_base + f"/copies/{copy_index}/evidence_class",
                            f"expected one of {sorted(allowed_evidence)}",
                        ))
                    expected_copy_bytes = copy_row["count"] * data["payload_bytes"]
                    if copy_row["count"] not in {0, messages} or copy_row["bytes"] != expected_copy_bytes:
                        out.append(issue("TB_COPY_RECONCILIATION", sample_base + f"/copies/{copy_index}", f"expected count 0 or {messages} and bytes count*{data['payload_bytes']}"))
            if attempt["phase"] == "measurement" and attempt["valid"]:
                if data["mode"] == "stream" and receiver_elapsed > 0:
                    flow_rates[sample["flow_id"]].append(sample["logical_payload_bytes"] * 1000000000 // receiver_elapsed)
                elif data["mode"] == "round_trip":
                    flow_latencies[sample["flow_id"]].extend(sample["round_trip_ns"])
        if attempt["phase"] == "measurement" and attempt["valid"] and data["mode"] == "stream":
            aggregate_rates.append(sum(
                sample["logical_payload_bytes"] * 1000000000
                // (sample["receiver_monotonic_end_ns"] - sample["receiver_monotonic_start_ns"])
                for sample in attempt["flows"]
                if sample["receiver_monotonic_end_ns"] > sample["receiver_monotonic_start_ns"]
            ))
    for phase, indexes in phase_indexes.items():
        if indexes != list(range(1, len(indexes) + 1)):
            out.append(issue("TB_ATTEMPT_INDEX", "/attempts", f"{phase} attempt indexes must be contiguous from 1"))
    warmups = [row for row in attempts if row["phase"] == "warmup"]
    measurements = [row for row in attempts if row["phase"] == "measurement"]
    valid_measurements = [row for row in measurements if row["valid"]]
    invalid_measurements = [row for row in measurements if not row["valid"]]
    summary = data["summary"]
    expected_summary_counts = {
        "warmup_attempts": len(warmups), "measurement_attempts": len(measurements),
        "valid_measurement_attempts": len(valid_measurements),
        "invalid_measurement_attempts": len(invalid_measurements),
        "replacement_attempts": max(0, len(measurements) - 10),
    }
    for name, expected in expected_summary_counts.items():
        if summary[name] != expected:
            out.append(issue("TB_SUMMARY_COUNT", f"/summary/{name}", f"expected {expected}"))
    expected_summary_flows = tuple(row["flow_id"] for row in summary["flow_summaries"])
    if expected_summary_flows != flow_ids:
        out.append(issue("TB_SUMMARY_FLOW_SET", "/summary/flow_summaries", f"expected {flow_ids}"))
    for index, row in enumerate(summary["flow_summaries"]):
        expected_throughput = expected_metric(flow_rates[row["flow_id"]], "bytes_per_second")
        expected_latency = expected_metric(flow_latencies[row["flow_id"]], "ns")
        if row["valid_attempts"] != len(valid_measurements) or row["invalid_attempts"] != len(invalid_measurements):
            out.append(issue("TB_FLOW_SUMMARY_COUNT", f"/summary/flow_summaries/{index}", "flow attempt counts do not reconcile"))
        if row["throughput"] != expected_throughput:
            out.append(issue("TB_FLOW_SUMMARY_METRIC", f"/summary/flow_summaries/{index}/throughput", f"expected {expected_throughput}"))
        if row["round_trip_latency"] != expected_latency:
            out.append(issue("TB_FLOW_SUMMARY_METRIC", f"/summary/flow_summaries/{index}/round_trip_latency", f"expected {expected_latency}"))
    expected_aggregate = expected_metric(aggregate_rates, "bytes_per_second")
    if summary["aggregate_throughput"] != expected_aggregate:
        out.append(issue("TB_AGGREGATE_SUMMARY", "/summary/aggregate_throughput", f"expected {expected_aggregate}"))
    expected_regimes = [
        {
            "node": node,
            "thermal_state": values[0],
            "low_power_mode": values[1],
            "power_source": values[2],
        }
        for node, values in sorted(valid_regime_by_node.items())
    ]
    if summary["regime_identities"] != expected_regimes:
        out.append(issue("TB_REGIME_SUMMARY", "/summary/regime_identities", f"expected {expected_regimes}"))
    invalid_ids = {row["attempt_id"] for row in attempts if not row["valid"]}
    excluded_ids = {row["attempt_id"] for row in data["exclusions"]}
    if invalid_ids != excluded_ids or len(excluded_ids) != len(data["exclusions"]):
        out.append(issue("TB_EXCLUSION_RECONCILIATION", "/exclusions", "exclusions must reference every invalid attempt exactly once"))
    status = summary["cell_status"]
    if status == "COMPLETE":
        stream_complete = data["mode"] == "stream" and len(warmups) == 3 and all(row["valid"] for row in warmups) and len(valid_measurements) == 10
        round_trip_complete = data["mode"] == "round_trip" and len(warmups) == 1 and warmups[0]["valid"] and len(measurements) == 1 and len(valid_measurements) == 1
        if not (stream_complete or round_trip_complete):
            out.append(issue("TB_COMPLETE_STATUS", "/summary/cell_status", "complete cell does not meet the mode-specific warm-up and measurement counts"))
    if status == "FAILED":
        invalid_warmup = any(not row["valid"] for row in warmups)
        stream_failed = data["mode"] == "stream" and (invalid_warmup or (len(measurements) == 12 and len(valid_measurements) < 10))
        round_trip_failed = data["mode"] == "round_trip" and (invalid_warmup or (len(measurements) == 1 and not valid_measurements))
        if not (stream_failed or round_trip_failed):
            out.append(issue("TB_FAILED_STATUS", "/summary/cell_status", "failed cell does not meet the mode-specific terminal rule"))
    if status == "ABORTED" and not data["errors"]:
        out.append(issue("TB_ABORT_STATUS", "/summary/cell_status", "aborted cell requires a retained run error"))
    def synchronization_qualifies(attempt: dict[str, Any]) -> bool:
        sync = attempt["synchronization"]
        return (
            sync["status"] == "available"
            and sync["pre_attempt_control_rtt_max_ns"] <= data["scenario"]["maximum_pre_attempt_control_rtt_ns"]
            and sync["coordinator_observed_start_window_ns"] <= data["scenario"]["maximum_coordinator_observed_start_window_ns"]
        )

    no_qualifying_sync = simultaneous and bool(measurements) and not any(
        synchronization_qualifies(attempt) for attempt in measurements
    )
    if no_qualifying_sync and status not in {"UNDETERMINED", "ABORTED"}:
        out.append(issue("TB_SYNC_CELL_OUTCOME", "/summary/cell_status", "a simultaneous cell with no qualifying empirical synchronization record must be UNDETERMINED unless a terminal run error aborted it"))
    if status == "UNDETERMINED" and not no_qualifying_sync:
        out.append(issue("TB_UNDETERMINED_STATUS", "/summary/cell_status", "undetermined simultaneous cell requires recorded attempts with no qualifying empirical synchronization record"))
    return out


def semantic_memory(data: dict[str, Any]) -> list[Issue]:
    out: list[Issue] = []
    samples = data["samples"]
    indexes = [row["attempt_index"] for row in samples]
    if indexes != list(range(1, len(samples) + 1)):
        out.append(issue("MEMORY_SAMPLE_INDEX", "/samples", "sample indexes must be contiguous from 1"))
    stabilization = data["stabilization"]
    observed_stabilization = stabilization["end_monotonic_ns"] - stabilization["start_monotonic_ns"]
    if observed_stabilization < 0 or stabilization["observed_duration_ns"] != observed_stabilization:
        out.append(issue("MEMORY_STABILIZATION_RECONCILIATION", "/stabilization", "stabilization duration must equal end minus start"))
    for index, sample in enumerate(samples):
        if sample["available_bytes"] > sample["physical_bytes"]:
            out.append(issue("MEMORY_AVAILABLE_BOUNDS", f"/samples/{index}/available_bytes", "available bytes cannot exceed physical bytes"))
        if index == 0:
            if sample["monotonic_ns"] < stabilization["end_monotonic_ns"]:
                out.append(issue("MEMORY_STABILIZATION_ORDER", f"/samples/{index}/monotonic_ns", "sampling began before stabilization ended"))
        elif sample["monotonic_ns"] - samples[index - 1]["monotonic_ns"] < data["policy"]["sample_interval_ns"]:
            out.append(issue("MEMORY_SAMPLE_INTERVAL", f"/samples/{index}/monotonic_ns", "samples are closer than the frozen interval"))
    valid = [row for row in samples if row["valid"]]
    summary = data["summary"]
    expected_counts = (len(samples), len(valid), len(samples) - len(valid))
    actual_counts = (summary["attempted_samples"], summary["accepted_samples"], summary["rejected_samples"])
    if actual_counts != expected_counts:
        out.append(issue("MEMORY_SUMMARY_COUNT", "/summary", f"expected counts {expected_counts}"))
    physical = {row["physical_bytes"] for row in samples}
    if len(physical) != 1 or summary["physical_bytes"] not in physical:
        out.append(issue("MEMORY_PHYSICAL_STABILITY", "/summary/physical_bytes", "physical bytes must remain constant"))
    if valid:
        values = sorted(row["available_bytes"] for row in valid)
        rank = max(1, math.ceil(0.05 * len(values)))
        p05 = values[rank - 1]
        expected = {
            "p05_available_bytes": p05,
            "minimum_available_bytes": values[0],
            "maximum_available_bytes": values[-1],
            "observed_os_reserve_bytes": summary["physical_bytes"] - p05,
        }
        for name, value in expected.items():
            if summary[name] != value:
                out.append(issue("MEMORY_SUMMARY_RECONCILIATION", f"/summary/{name}", f"expected {value}"))
    else:
        for name in ("p05_available_bytes", "minimum_available_bytes", "maximum_available_bytes", "observed_os_reserve_bytes"):
            if summary[name] is not None:
                out.append(issue("MEMORY_EMPTY_SUMMARY", f"/summary/{name}", "summary statistics require a valid sample"))
    if summary["status"] == "COMPLETE":
        if len(valid) != 30 or data["errors"]:
            out.append(issue("MEMORY_COMPLETE_STATUS", "/summary/status", "complete baseline requires 30 valid samples and no errors"))
        if data["policy"]["approval_status"] != "approved" or data["producer"]["dirty"]:
            out.append(issue("MEMORY_PLAN_APPROVAL", "/policy/approval_status", "complete baseline requires prior owner approval and a clean producer"))
        if stabilization["observed_duration_ns"] < data["policy"]["stabilization_duration_ns"]:
            out.append(issue("MEMORY_STABILIZATION_MINIMUM", "/stabilization/observed_duration_ns", "complete baseline requires the frozen stabilization duration"))
    if summary["status"] == "UNDETERMINED" and (len(samples) != data["policy"]["maximum_attempts"] or len(valid) >= data["policy"]["planned_valid_samples"]):
        out.append(issue("MEMORY_UNDETERMINED_STATUS", "/summary/status", "undetermined requires exhausted attempts without enough valid samples"))
    if summary["status"] == "ABORTED" and not data["errors"]:
        out.append(issue("MEMORY_ABORT_STATUS", "/summary/status", "aborted baseline requires a retained error"))
    return out


def required_cell_ids() -> set[str]:
    return set(canonical_cell_ids())


def semantic_link_summary(data: dict[str, Any]) -> list[Issue]:
    out: list[Issue] = []
    if data["artifact_role"] == "link_summary" and data["producer"]["dirty"]:
        out.append(issue("TB_MEASURED_DIRTY", "/producer/dirty", "physical measured link summary requires a clean producer"))
    cells = data["cells"]
    ids = [row["cell_id"] for row in cells]
    if set(ids) != required_cell_ids() or not ids_unique(ids):
        out.append(issue("TB_SUMMARY_CELL_COVERAGE", "/cells", "summary must contain every v1 cell exactly once"))
    indexes = [row["schedule_index"] for row in cells]
    if set(indexes) != set(range(246)) or not ids_unique(indexes):
        out.append(issue("TB_SUMMARY_SCHEDULE_COVERAGE", "/cells", "schedule indexes must cover 0 through 245"))
    expected_schedule = {cell_id: index for index, cell_id in enumerate(scheduled_cell_ids(data["plan_seed"]))}
    for index, row in enumerate(cells):
        if row["schedule_index"] != expected_schedule.get(row["cell_id"]):
            out.append(issue("TB_SUMMARY_SCHEDULE_INDEX", f"/cells/{index}/schedule_index", "schedule index does not match plan seed"))
    if indexes != sorted(indexes):
        out.append(issue("TB_SUMMARY_SCHEDULE_ORDER", "/cells", "cells must be serialized in schedule order"))
    measurement_hashes = [row["measurement_sha256"] for row in cells]
    if not ids_unique(measurement_hashes):
        out.append(issue("TB_SUMMARY_MEASUREMENT_IDENTITY", "/cells", "each cell must reference a distinct result artifact"))
    empty_throughput = expected_metric([], "bytes_per_second")
    empty_latency = expected_metric([], "ns")
    for index, row in enumerate(cells):
        base = f"/cells/{index}"
        mode_label, scenario_id, payload_text = row["cell_id"].split(":")
        expected_mode = "round_trip" if mode_label == "round-trip" else "stream"
        if row["mode"] != expected_mode or row["scenario_id"] != scenario_id or row["payload_bytes"] != int(payload_text):
            out.append(issue("TB_SUMMARY_CELL_IDENTITY", base, "mode, scenario, or payload disagrees with cell ID"))
        flow_ids = tuple(item["flow_id"] for item in row["flow_summaries"])
        expected_flows = SCENARIOS.get(scenario_id)
        if expected_flows is None:
            out.append(issue("TB_SUMMARY_CELL_IDENTITY", base + "/scenario_id", "unknown scenario in cell ID"))
        elif flow_ids != expected_flows:
            out.append(issue("TB_SUMMARY_FLOW_SET", base + "/flow_summaries", f"expected {expected_flows}"))
        metrics = [
            *(item["throughput"] for item in row["flow_summaries"]),
            *(item["round_trip_latency"] for item in row["flow_summaries"]),
            row["aggregate_throughput"],
        ]
        for metric_index, metric in enumerate(metrics):
            values = [metric[name] for name in ("median", "median_absolute_deviation", "p95", "minimum", "maximum")]
            if (metric["sample_count"] == 0 and any(value is not None for value in values)) or (
                metric["sample_count"] > 0 and any(value is None for value in values)
            ):
                out.append(issue("TB_SUMMARY_METRIC_SHAPE", base, f"metric {metric_index} statistics disagree with sample count"))
            if metric["sample_count"] > 0 and all(value is not None for value in values) and not (
                metric["minimum"] <= metric["median"] <= metric["maximum"]
                and metric["minimum"] <= metric["p95"] <= metric["maximum"]
            ):
                out.append(issue("TB_SUMMARY_METRIC_ORDER", base, f"metric {metric_index} order is invalid"))
        if row["mode"] == "stream":
            if any(item["round_trip_latency"] != empty_latency for item in row["flow_summaries"]):
                out.append(issue("TB_SUMMARY_WRONG_MODE_METRIC", base + "/flow_summaries", "stream cells cannot report round-trip latency"))
        else:
            if any(item["throughput"] != empty_throughput for item in row["flow_summaries"]) or row["aggregate_throughput"] != empty_throughput:
                out.append(issue("TB_SUMMARY_WRONG_MODE_METRIC", base, "round-trip cells cannot report throughput"))
        if row["aggregate_throughput"]["unit"] != "bytes_per_second":
            out.append(issue("TB_SUMMARY_METRIC_UNIT", base + "/aggregate_throughput/unit", "aggregate throughput unit must be bytes_per_second"))
        for flow_index, flow in enumerate(row["flow_summaries"]):
            if flow["throughput"]["unit"] != "bytes_per_second" or flow["round_trip_latency"]["unit"] != "ns":
                out.append(issue("TB_SUMMARY_METRIC_UNIT", base + f"/flow_summaries/{flow_index}", "flow metric units are fixed"))
        regime_nodes = [item["node"] for item in row["regime_identities"]]
        if regime_nodes != sorted(regime_nodes) or not ids_unique(regime_nodes):
            out.append(issue("TB_SUMMARY_REGIME_ORDER", base + "/regime_identities", "regime identities must be unique and sorted by node"))
        if row["status"] == "COMPLETE":
            if row["mode"] == "stream":
                expected_count = 10
                if row["aggregate_throughput"]["sample_count"] != expected_count or any(
                    flow["throughput"]["sample_count"] != expected_count
                    or flow["round_trip_latency"]["sample_count"] != 0
                    for flow in row["flow_summaries"]
                ):
                    out.append(issue("TB_SUMMARY_COMPLETE_EVIDENCE", base, "complete stream cell requires ten per-flow and aggregate throughput samples and no latency samples"))
            else:
                expected_count = 100 if row["payload_bytes"] == 4_194_304 else 1000
                if row["aggregate_throughput"]["sample_count"] != 0 or any(
                    flow["throughput"]["sample_count"] != 0
                    or flow["round_trip_latency"]["sample_count"] != expected_count
                    for flow in row["flow_summaries"]
                ):
                    out.append(issue("TB_SUMMARY_COMPLETE_EVIDENCE", base, f"complete round-trip cell requires {expected_count} latency samples per flow and no throughput samples"))
            if row["errors"]:
                out.append(issue("TB_SUMMARY_COMPLETE_ERRORS", base + "/errors", "complete cell cannot retain a terminal cell error"))
    counts = Counter(row["status"].lower() + "_cells" for row in cells)
    coverage = data["coverage"]
    for key in ("complete_cells", "failed_cells", "aborted_cells", "undetermined_cells"):
        if coverage[key] != counts[key]:
            out.append(issue("TB_SUMMARY_STATUS_RECONCILIATION", f"/coverage/{key}", f"expected {counts[key]}"))
    return out


def canonical_digest(data: Any) -> str:
    return hashlib.sha256(canonical_text(data).encode("utf-8")).hexdigest()


def validate_tb5_evidence_bundle(
    summary: dict[str, Any],
    plan: dict[str, Any],
    local_control_index: dict[str, Any],
    local_controls_by_path: dict[str, dict[str, Any]],
    measurement_index: dict[str, Any],
    raw_by_path: dict[str, dict[str, Any]],
    synchronization_by_digest: dict[str, dict[str, Any]] | None = None,
) -> list[Issue]:
    out: list[Issue] = []
    synchronization_by_digest = synchronization_by_digest or {}
    root_issues: list[Issue] = []
    for artifact, schema_id in (
        (summary, "qw5.tb5-link-summary/v1"),
        (plan, "qw5.tb5-run-plan/v1"),
        (local_control_index, "qw5.tb5-local-control-index/v1"),
        (measurement_index, "qw5.tb5-measurement-index/v1"),
    ):
        root_issues.extend(validate_instance(artifact, schema_id))
    out.extend(root_issues)
    if any(item.code.startswith("SCHEMA_") for item in root_issues):
        return out
    plan_digest = canonical_digest(plan)
    if summary["plan_sha256"] != plan_digest:
        out.append(issue("TB_GRAPH_PLAN_DIGEST", "/plan_sha256", "canonical run-plan digest does not match the link summary"))
    if summary["plan_seed"] != plan["seed"]:
        out.append(issue("TB_GRAPH_PLAN_SEED", "/plan_seed", "link-summary seed differs from the resolved run plan"))
    control_index_digest = canonical_digest(local_control_index)
    if summary["local_control_index_sha256"] != control_index_digest:
        out.append(issue(
            "TB_GRAPH_CONTROL_INDEX_DIGEST",
            "/local_control_index_sha256",
            "canonical local-control-index digest does not match the link summary",
        ))
    if local_control_index["plan_sha256"] != plan_digest:
        out.append(issue("TB_GRAPH_CONTROL_PLAN", "/local_control_index_sha256", "local-control index does not reference the resolved run plan"))
    control_keys: set[tuple[str, str, int]] = set()
    for entry_index, entry in enumerate(local_control_index["entries"]):
        raw_control = local_controls_by_path.get(entry["relative_path"])
        pointer = f"/local_control_index_sha256/entries/{entry_index}"
        if raw_control is None:
            out.append(issue("TB_GRAPH_CONTROL_RESOLUTION", pointer, "local-control index path did not resolve"))
            continue
        raw_issues = validate_instance(raw_control, "qw5.tb5-local-control/v1")
        out.extend(raw_issues)
        if any(item.code.startswith("SCHEMA_") for item in raw_issues):
            continue
        raw_digest = canonical_digest(raw_control)
        if raw_digest != entry["sha256"]:
            out.append(issue("TB_GRAPH_CONTROL_DIGEST", pointer + "/sha256", "local-control canonical digest differs from its index entry"))
        if raw_control["plan_sha256"] != plan_digest:
            out.append(issue("TB_GRAPH_CONTROL_PLAN", pointer, "local control does not reference the resolved run plan"))
        expected_key = (entry["control_id"], entry["node"], entry["payload_bytes"])
        actual_key = (raw_control["control_id"], raw_control["node"], raw_control["payload_bytes"])
        if actual_key != expected_key:
            out.append(issue("TB_GRAPH_CONTROL_IDENTITY", pointer, "local-control identity differs from its index entry"))
        control_keys.add(actual_key)
    if set(local_controls_by_path) != {row["relative_path"] for row in local_control_index["entries"]}:
        out.append(issue("TB_GRAPH_CONTROL_COVERAGE", "/local_control_index_sha256", "control resolver and index path sets differ"))
    if len(local_control_index["entries"]) == 108 and control_keys != expected_local_control_keys():
        out.append(issue("TB_GRAPH_CONTROL_COVERAGE", "/local_control_index_sha256", "resolved controls do not cover the exact 108-cell matrix"))
    if canonical_digest(measurement_index) != summary["measurement_index_sha256"]:
        out.append(issue("TB_SUMMARY_INDEX_DIGEST", "/measurement_index_sha256", "canonical index digest does not match the summary"))
    if (
        measurement_index["plan_sha256"] != plan_digest
        or measurement_index["local_control_index_sha256"] != control_index_digest
        or measurement_index["plan_seed"] != plan["seed"]
    ):
        out.append(issue("TB_SUMMARY_INDEX_PLAN", "/measurement_index_sha256", "index plan identity differs from summary"))
    by_cell = {row["cell_id"]: row for row in measurement_index["entries"]}
    if len(by_cell) != len(measurement_index["entries"]) or set(by_cell) != {row["cell_id"] for row in summary["cells"]}:
        out.append(issue("TB_SUMMARY_INDEX_COVERAGE", "/measurement_index_sha256", "index must resolve every summary cell exactly once"))
        return out
    indexed_measurement_paths = {row["relative_path"] for row in measurement_index["entries"]}
    if set(raw_by_path) != indexed_measurement_paths:
        out.append(issue("TB_SUMMARY_INDEX_COVERAGE", "/measurement_index_sha256", "measurement resolver and index path sets differ"))
    for cell_index, cell in enumerate(summary["cells"]):
        base = f"/cells/{cell_index}"
        entry = by_cell[cell["cell_id"]]
        raw = raw_by_path.get(entry["relative_path"])
        if raw is None:
            out.append(issue("TB_SUMMARY_MEASUREMENT_RESOLUTION", base + "/measurement_sha256", "index path did not resolve"))
            continue
        raw_issues = validate_instance(raw, "qw5.tb5-measurement/v1")
        out.extend(raw_issues)
        if any(item.code.startswith("SCHEMA_") for item in raw_issues):
            continue
        digest = canonical_digest(raw)
        if digest != entry["sha256"] or digest != cell["measurement_sha256"]:
            out.append(issue("TB_SUMMARY_MEASUREMENT_DIGEST", base + "/measurement_sha256", "raw canonical digest, index digest, and cell digest differ"))
        expected_identity = {
            "qw5_commit": plan["identity"]["qw5_commit"],
            "dirty": plan["identity"]["dirty"],
            "plan_sha256": plan_digest,
            "harness_sha256": plan["identity"]["harness_sha256"],
            "route_proof_sha256": plan["identity"]["route_proof_sha256"],
            "inventory_sha256": plan["identity"]["inventory_sha256"],
            "local_control_index_sha256": control_index_digest,
        }
        if raw["identity"] != expected_identity or raw["plan_seed"] != plan["seed"]:
            out.append(issue("TB_GRAPH_MEASUREMENT_IDENTITY", base, "raw measurement does not bind the resolved plan and local-control index"))
        projected_flows = [
            {
                "flow_id": row["flow_id"],
                "throughput": row["throughput"],
                "round_trip_latency": row["round_trip_latency"],
            }
            for row in raw["summary"]["flow_summaries"]
        ]
        projected = {
            "cell_id": raw["cell_id"],
            "schedule_index": raw["schedule_index"],
            "mode": raw["mode"],
            "scenario_id": raw["scenario"]["scenario_id"],
            "payload_bytes": raw["payload_bytes"],
            "status": raw["summary"]["cell_status"],
            "measurement_sha256": digest,
            "flow_summaries": projected_flows,
            "aggregate_throughput": raw["summary"]["aggregate_throughput"],
            "regime_identities": raw["summary"]["regime_identities"],
            "exclusions": raw["exclusions"],
            "errors": raw["errors"],
        }
        if projected != cell:
            out.append(issue("TB_SUMMARY_RAW_RECONCILIATION", base, "summary cell disagrees with its raw measurement projection"))
        for attempt_index, attempt in enumerate(raw["attempts"]):
            sync = attempt["synchronization"]
            if sync["status"] != "available":
                continue
            sync_raw = synchronization_by_digest.get(sync["evidence_sha256"])
            if sync_raw is None:
                out.append(issue(
                    "TB_SYNC_EVIDENCE_RESOLUTION",
                    base + f"/attempts/{attempt_index}/synchronization/evidence_sha256",
                    "synchronization digest did not resolve to a raw artifact",
                ))
                continue
            sync_issues = validate_instance(sync_raw, "qw5.tb5-synchronization-evidence/v1")
            out.extend(sync_issues)
            if not sync_issues:
                out.extend(validate_sync_reference(raw["cell_id"], raw["identity"]["plan_sha256"], attempt, sync_raw))
    return out


SEMANTIC_VALIDATORS: dict[str, Callable[[dict[str, Any]], list[Issue]]] = {
    "qw5.hardware-inventory/v1": semantic_hardware,
    "qw5.memory-baseline/v1": semantic_memory,
    "qw5.model-acquisition-plan/v1": semantic_model_acquisition_plan,
    "qw5.model-artifact-manifest/v1": semantic_model,
    "qw5.placement-analysis/v1": semantic_placement,
    "qw5.placement-evidence-graph/v1": semantic_placement_evidence_graph,
    "qw5.safetensors-parser-profile/v1": semantic_noop,
    "qw5.tb5-link-summary/v1": semantic_link_summary,
    "qw5.tb5-local-control-index/v1": semantic_local_control_index,
    "qw5.tb5-local-control/v1": semantic_local_control,
    "qw5.tb5-measurement/v1": semantic_tb_measurement,
    "qw5.tb5-measurement-index/v1": semantic_measurement_index,
    "qw5.tb5-route-proof/v1": semantic_route,
    "qw5.tb5-run-plan/v1": semantic_tb_plan,
    "qw5.tb5-synchronization-evidence/v1": semantic_sync_evidence,
    "qw5.tensor-inventory/v1": semantic_tensor,
}


def validate_instance(data: Any, schema_id: str) -> list[Issue]:
    schema = load_json(SCHEMA_DIR / SCHEMA_FILES[schema_id])
    structural = schema_issues(data, schema)
    if structural:
        return structural
    return SEMANTIC_VALIDATORS[schema_id](data)


def decode_pointer(pointer: str) -> list[str]:
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        raise ValueError(f"invalid JSON pointer {pointer!r}")
    return [part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")]


def pointer_get(document: Any, pointer: str) -> Any:
    value = document
    for part in decode_pointer(pointer):
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def pointer_parent(document: Any, pointer: str) -> tuple[Any, str]:
    parts = decode_pointer(pointer)
    if not parts:
        raise ValueError("root mutation is not supported")
    value = document
    for part in parts[:-1]:
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value, parts[-1]


def apply_operation(document: Any, operation: dict[str, Any]) -> None:
    kind = operation["op"]
    parent, key = pointer_parent(document, operation["path"])
    if kind == "copy":
        value = copy.deepcopy(pointer_get(document, operation["from"]))
    else:
        value = copy.deepcopy(operation.get("value"))
    if isinstance(parent, list):
        if kind == "remove":
            parent.pop(int(key))
        elif kind in {"add", "copy"}:
            parent.append(value) if key == "-" else parent.insert(int(key), value)
        elif kind == "replace":
            parent[int(key)] = value
        else:
            raise ValueError(f"unsupported operation {kind}")
    else:
        if kind == "remove":
            del parent[key]
        elif kind in {"add", "copy", "replace"}:
            parent[key] = value
        else:
            raise ValueError(f"unsupported operation {kind}")


def verify_canonical_vectors() -> int:
    failures = 0
    vectors = load_json(FIXTURE_DIR / "canonical-json-v1.vectors.json")
    vector_ids = [row.get("vector_id") for row in vectors.get("valid_vectors", []) + vectors.get("invalid_sources", [])]
    if vectors.get("schema") != "qw5.canonical-json-vectors/v1" or not ids_unique(vector_ids):
        print("FAIL canonical vectors: schema ID missing or vector IDs are not unique")
        failures += 1
    for row in vectors["valid_vectors"]:
        raw = canonical_text(row["value"]).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        if raw.hex() != row["canonical_utf8_hex"] or digest != row["sha256"]:
            print(f"FAIL canonical vector {row['vector_id']}: bytes or digest mismatch")
            failures += 1
    for row in vectors["invalid_sources"]:
        try:
            parse_canonical_source(bytes.fromhex(row["source_utf8_hex"]))
        except JsonInputError as exc:
            if exc.code != row["expected_error"]:
                print(f"FAIL canonical negative {row['vector_id']}: expected {row['expected_error']}, got {exc.code}")
                failures += 1
        else:
            print(f"FAIL canonical negative {row['vector_id']}: source was accepted")
            failures += 1
    return failures


def wire_parts(inputs: dict[str, Any]) -> dict[str, bytes]:
    plan = bytes.fromhex(inputs["plan_sha256"])
    scenario = inputs["scenario_id"].encode("utf-8")
    flow = inputs["flow_id"].encode("utf-8")
    nodes = {"A": 1, "B": 2, "C": 3}
    scenario_digest = hashlib.sha256(scenario).digest()[:16]
    flow_digest = hashlib.sha256(flow).digest()[:16]
    seed = inputs["seed"]
    payload_bytes = inputs["payload_bytes"]
    sequence = inputs["sequence"]
    handshake = (
        b"QW5H" + struct.pack("!HH", 1, 96) + plan + scenario_digest + flow_digest
        + struct.pack("!BBHQQI", nodes[inputs["source"]], nodes[inputs["destination"]], 0, seed, payload_bytes, 0)
    )
    key = hashlib.sha256(struct.pack("!QH", seed, len(flow)) + flow + struct.pack("!Q", payload_bytes)).digest()
    payload = b"".join(
        hashlib.sha256(key + struct.pack("!QQ", sequence, index)).digest()
        for index in range((payload_bytes + 31) // 32)
    )[:payload_bytes]
    trailer = hashlib.sha256(payload).digest()
    flags = 1 if inputs["ack_requested"] else 0
    header = (
        b"QW5D" + struct.pack("!HHHHQQ", 1, 64, flags, 0, sequence, payload_bytes)
        + plan[:16] + flow_digest + struct.pack("!I", 0)
    )
    ack = (
        b"QW5A" + struct.pack("!HHHHQQ", 1, 64, 0, 0, sequence, payload_bytes)
        + trailer + struct.pack("!I", 0)
    )
    return {"handshake": handshake, "payload": payload, "data_header": header, "digest_trailer": trailer, "ack": ack}


def verify_wire_vectors() -> int:
    failures = 0
    vectors = load_json(FIXTURE_DIR / "tb5-wire-v1.vectors.json")
    all_ids = [row.get("vector_id") for row in vectors.get("vectors", []) + vectors.get("invalid_vectors", [])]
    if vectors.get("schema") != "qw5.tb5-wire-vectors/v1" or not ids_unique(all_ids):
        print("FAIL wire vectors: schema ID missing or vector IDs are not unique")
        failures += 1
    materialized: dict[str, dict[str, bytes]] = {}
    for row in vectors["vectors"]:
        parts = wire_parts(row["inputs"])
        materialized[row["vector_id"]] = parts
        for name, raw in parts.items():
            if raw.hex() != row[f"{name}_hex"] or hashlib.sha256(raw).hexdigest() != row[f"{name}_sha256"]:
                print(f"FAIL wire vector {row['vector_id']} {name}: bytes or digest mismatch")
                failures += 1
    for row in vectors.get("invalid_vectors", []):
        try:
            parts = materialized[row["base_vector_id"]]
            raw = bytearray(parts[row["component"]])
            mutation = row["mutation"]
            if mutation["kind"] == "replace_bytes":
                replacement = bytes.fromhex(mutation["replacement_hex"])
                offset = mutation["offset"]
                if not replacement or offset < 0 or offset + len(replacement) > len(raw):
                    raise ValueError("replace_bytes is out of bounds or empty")
                raw[offset:offset + len(replacement)] = replacement
            elif mutation["kind"] == "truncate":
                length = mutation["length"]
                if length < 0 or length >= len(raw):
                    raise ValueError("truncate length must shorten the component")
                del raw[length:]
            elif mutation["kind"] == "append":
                suffix = bytes.fromhex(mutation["suffix_hex"])
                if not suffix:
                    raise ValueError("append suffix is empty")
                raw.extend(suffix)
            else:
                raise ValueError(f"unknown mutation {mutation['kind']!r}")
            if raw.hex() != row["mutated_hex"] or bytes(raw) == parts[row["component"]]:
                raise ValueError("materialized bytes do not match or did not change")
            if not row["expected_error"].startswith("WIRE_"):
                raise ValueError("expected error is not a wire error code")
        except (KeyError, TypeError, ValueError) as exc:
            print(f"FAIL wire negative {row.get('vector_id')}: {exc}")
            failures += 1
    return failures


def safetensors_duplicate_guard(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise JsonInputError("SAFETENSORS_DUPLICATE_MEMBER", f"duplicate header member {key!r}")
        result[key] = value
    return result


def parse_safetensors_v1(raw: bytes) -> dict[str, Any]:
    if len(raw) < 8:
        raise JsonInputError("SAFETENSORS_HEADER_LENGTH", "missing little-endian u64 header length")
    header_length = struct.unpack("<Q", raw[:8])[0]
    if header_length > 16_777_216:
        raise JsonInputError("SAFETENSORS_HEADER_LIMIT", "header exceeds the QW5 v1 limit")
    if header_length == 0 or 8 + header_length > len(raw):
        raise JsonInputError("SAFETENSORS_HEADER_TRUNCATED", "declared header does not fit the artifact")
    header_raw = raw[8:8 + header_length]
    if not header_raw.startswith(b"{"):
        raise JsonInputError("SAFETENSORS_HEADER_OBJECT", "header must start with an object")
    unpadded = header_raw.rstrip(b" ")
    if not unpadded.endswith(b"}"):
        raise JsonInputError("SAFETENSORS_HEADER_PADDING", "only ASCII-space header padding is accepted")
    try:
        header_text = unpadded.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise JsonInputError("SAFETENSORS_UTF8", str(exc)) from exc
    try:
        header = json.loads(
            header_text,
            object_pairs_hook=safetensors_duplicate_guard,
            parse_float=reject_float,
            parse_constant=reject_constant,
        )
    except JsonInputError:
        raise
    except json.JSONDecodeError as exc:
        raise JsonInputError("SAFETENSORS_JSON", str(exc)) from exc
    if not isinstance(header, dict):
        raise JsonInputError("SAFETENSORS_HEADER_OBJECT", "header must be an object")
    metadata = header.get("__metadata__", {})
    if not isinstance(metadata, dict) or any(
        not isinstance(key, str) or not isinstance(value, str)
        for key, value in metadata.items()
    ):
        raise JsonInputError("SAFETENSORS_METADATA", "__metadata__ must be a string-to-string map")
    tensor_items = [(name, row) for name, row in header.items() if name != "__metadata__"]
    if len(tensor_items) > 1_000_000:
        raise JsonInputError("SAFETENSORS_TENSOR_LIMIT", "tensor count exceeds the QW5 v1 limit")
    data = raw[8 + header_length:]
    tensors: list[dict[str, Any]] = []
    ranges: list[tuple[int, int]] = []
    for name, row in tensor_items:
        if not isinstance(name, str) or not isinstance(row, dict) or set(row) != {"dtype", "shape", "data_offsets"}:
            raise JsonInputError("SAFETENSORS_TENSOR_MEMBERS", f"invalid tensor record {name!r}")
        dtype = row["dtype"]
        if dtype not in DTYPES:
            raise JsonInputError("SAFETENSORS_DTYPE", f"unsupported dtype {dtype!r}")
        shape = row["shape"]
        if not isinstance(shape, list) or len(shape) > 16 or any(
            type(dimension) is not int or dimension < 0 or dimension > 9_223_372_036_854_775_807
            for dimension in shape
        ):
            raise JsonInputError("SAFETENSORS_SHAPE", f"invalid shape for {name!r}")
        element_count = 1
        for dimension in shape:
            if dimension and element_count > U64_MAX // dimension:
                raise JsonInputError("SAFETENSORS_SHAPE_OVERFLOW", f"shape product overflows u64 for {name!r}")
            element_count *= dimension
        offsets = row["data_offsets"]
        if not isinstance(offsets, list) or len(offsets) != 2 or any(type(value) is not int or value < 0 for value in offsets):
            raise JsonInputError("SAFETENSORS_OFFSETS", f"invalid offsets for {name!r}")
        start, end = offsets
        if start > end or end > len(data):
            raise JsonInputError("SAFETENSORS_OFFSETS", f"out-of-bounds offsets for {name!r}")
        width = DTYPES[dtype][1]
        if element_count > U64_MAX // width or end - start != element_count * width:
            raise JsonInputError("SAFETENSORS_DTYPE_BYTES", f"dtype/shape byte count differs from offsets for {name!r}")
        ranges.append((start, end))
        tensors.append({
            "name": name, "dtype": dtype, "shape": shape,
            "element_count": element_count, "stored_bytes": end - start,
            "data_offsets": offsets,
        })
    cursor = 0
    for start, end in sorted(ranges):
        if start != cursor:
            raise JsonInputError("SAFETENSORS_RANGE_COVERAGE", "tensor ranges overlap or leave a hole")
        cursor = end
    if cursor != len(data):
        raise JsonInputError("SAFETENSORS_RANGE_COVERAGE", "tensor ranges do not cover the data buffer")
    return {"metadata": metadata, "tensors": tensors}


def verify_safetensors_vectors() -> int:
    failures = 0
    vectors = load_json(FIXTURE_DIR / "safetensors-parser-v1.vectors.json")
    vector_ids = [row.get("vector_id") for row in vectors.get("valid_vectors", []) + vectors.get("invalid_sources", [])]
    if vectors.get("schema") != "qw5.safetensors-parser-vectors/v1" or not ids_unique(vector_ids):
        print("FAIL SafeTensors vectors: schema ID missing or vector IDs are not unique")
        return 1
    for row in vectors["valid_vectors"]:
        raw = bytes.fromhex(row["source_hex"])
        try:
            projection = parse_safetensors_v1(raw)
        except JsonInputError as exc:
            print(f"FAIL SafeTensors vector {row['vector_id']}: {exc.code} {exc}")
            failures += 1
            continue
        if hashlib.sha256(raw).hexdigest() != row["sha256"] or projection != row["projection"]:
            print(f"FAIL SafeTensors vector {row['vector_id']}: digest, metadata, or tensor projection mismatch")
            failures += 1
    for row in vectors["invalid_sources"]:
        try:
            parse_safetensors_v1(bytes.fromhex(row["source_hex"]))
        except JsonInputError as exc:
            if exc.code != row["expected_error"]:
                print(f"FAIL SafeTensors negative {row['vector_id']}: expected {row['expected_error']}, got {exc.code}")
                failures += 1
        else:
            print(f"FAIL SafeTensors negative {row['vector_id']}: source was accepted")
            failures += 1
    return failures


def generated_aborted_measurement(
    cell_id: str,
    schedule_index: int,
    plan: dict[str, Any],
    plan_digest: str,
    local_control_index_digest: str,
) -> dict[str, Any]:
    seed = plan["seed"]
    mode_label, scenario_id, payload_text = cell_id.split(":")
    mode = "round_trip" if mode_label == "round-trip" else "stream"
    payload = int(payload_text)
    flow_ids = SCENARIOS[scenario_id]
    scenario_flows = [
        {"flow_id": flow_id, "source": FLOW[flow_id][0], "destination": FLOW[flow_id][1], "route_alias": FLOW[flow_id][2]}
        for flow_id in flow_ids
    ]
    unavailable_integer = {"status": "unavailable", "method": "generated_fixture"}
    unavailable_string = {"status": "unavailable", "method": "generated_fixture"}
    socket_value = {
        "tcp_nodelay": True, "send_buffer_bytes": 1, "receive_buffer_bytes": 1,
        "address_family": "ipv6", "congestion_control": unavailable_string,
        "maximum_segment_bytes": unavailable_integer,
    }
    socket_settings = [
        {
            "flow_id": flow_id, "endpoint": endpoint,
            "requested": copy.deepcopy(socket_value), "effective": copy.deepcopy(socket_value),
        }
        for flow_id in flow_ids
        for endpoint in FLOW[flow_id][:2]
    ]
    copy_rows = lambda flow_id: [
        {
            "endpoint": endpoint, "stage": stage, "status": "unavailable",
            "evidence_class": None, "observation_method": "generated_fixture",
        }
        for endpoint, stage in sorted(expected_copy_keys(flow_id))
    ]
    flow_samples = [
        {
            "flow_id": flow_id,
            "source_monotonic_start_ns": 1, "source_monotonic_end_ns": 1,
            "receiver_monotonic_start_ns": 1, "receiver_monotonic_end_ns": 1,
            "messages": 0, "logical_payload_bytes": 0, "header_bytes": 0,
            "digest_trailer_bytes": 0, "ack_bytes": 0,
            "source_socket_bytes": copy.deepcopy(unavailable_integer),
            "receiver_socket_bytes": copy.deepcopy(unavailable_integer),
            "checksum_algorithm": "sha256", "checksum_count": 0,
            "checksum_elapsed_ns": 0, "sequence_first": 0, "sequence_last": 0,
            "round_trip_ns": [], "copies": copy_rows(flow_id),
            "errors": [{"code": "GENERATED_ABORT", "message": "Generated bundle fixture."}],
        }
        for flow_id in flow_ids
    ]
    active_nodes = sorted({node for flow_id in flow_ids for node in FLOW[flow_id][:2]})
    thermal = [
        {
            "node": node, "start_monotonic_ns": 1, "end_monotonic_ns": 1,
            "start_state": "nominal", "end_state": "nominal",
            "start_low_power_mode": False, "end_low_power_mode": False,
            "start_power_source": None, "end_power_source": None,
        }
        for node in active_nodes
    ]
    if len(flow_ids) == 1:
        sync = {
            "status": "not_required", "method": "not_required", "calibration_rounds": None,
            "coordinator_receipt_spread_ns": None, "pre_attempt_control_rtt_max_ns": None,
            "worker_start_to_ack_max_ns": None, "timer_resolution_allowance_ns": None,
            "coordinator_observed_start_window_ns": None, "evidence_sha256": None,
        }
    else:
        sync = {
            "status": "unavailable", "method": "unavailable", "calibration_rounds": None,
            "coordinator_receipt_spread_ns": None, "pre_attempt_control_rtt_max_ns": None,
            "worker_start_to_ack_max_ns": None, "timer_resolution_allowance_ns": None,
            "coordinator_observed_start_window_ns": None, "evidence_sha256": None,
        }
    empty_throughput = expected_metric([], "bytes_per_second")
    empty_latency = expected_metric([], "ns")
    error = {"code": "GENERATED_ABORT", "message": "Generated bundle fixture."}
    return {
        "schema": "qw5.tb5-measurement/v1", "artifact_role": "schema_fixture",
        "evidence_class": "SIMULATED", "run_id": "generated-bundle", "cell_id": cell_id,
        "created_at": "2000-01-01T00:00:00Z",
        "producer": {
            "name": "qw5-generated-schema-fixture", "version": "1",
            "executable_sha256": "41" * 32, "qw5_commit": plan["identity"]["qw5_commit"],
            "dirty": False, "parameters": ["--generated-bundle"],
        },
        "identity": {
            "qw5_commit": plan["identity"]["qw5_commit"],
            "dirty": plan["identity"]["dirty"],
            "plan_sha256": plan_digest,
            "harness_sha256": plan["identity"]["harness_sha256"],
            "route_proof_sha256": plan["identity"]["route_proof_sha256"],
            "inventory_sha256": plan["identity"]["inventory_sha256"],
            "local_control_index_sha256": local_control_index_digest,
        },
        "plan_seed": seed, "schedule_index": schedule_index,
        "scenario": {
            "scenario_id": scenario_id, "flows": scenario_flows,
            "maximum_pre_attempt_control_rtt_ns": 1_000_000,
            "maximum_coordinator_observed_start_window_ns": 10_000_000,
        },
        "payload_bytes": payload, "mode": mode,
        "application_buffers": {
            "send_payload_buffers_per_flow": 1,
            "receive_payload_buffers_per_flow": 1,
            "bytes_per_buffer": payload,
            "active_flow_count": len(flow_ids),
            "peak_application_payload_buffer_bytes": 2 * payload * len(flow_ids),
        },
        "framing": {
            "protocol": "qw5-tb5-wire/v1", "handshake_bytes": 96,
            "data_header_bytes": 64, "digest_trailer_bytes": 32,
            "ack_bytes": 64 if mode == "round_trip" else 0, "checksum": "sha256",
        },
        "socket_settings": socket_settings,
        "attempts": [{
            "attempt_id": "warmup-001", "phase": "warmup", "attempt_index": 1,
            "valid": False, "invalid_reasons": ["GENERATED_ABORT"],
            "coordinator_release_at": "2000-01-01T00:00:00Z",
            "synchronization": sync, "thermal": thermal, "flows": flow_samples,
            "errors": [error],
        }],
        "summary": {
            "cell_status": "ABORTED", "warmup_attempts": 1, "measurement_attempts": 0,
            "valid_measurement_attempts": 0, "invalid_measurement_attempts": 0,
            "replacement_attempts": 0,
            "flow_summaries": [
                {
                    "flow_id": flow_id, "valid_attempts": 0, "invalid_attempts": 0,
                    "throughput": empty_throughput, "round_trip_latency": empty_latency,
                }
                for flow_id in flow_ids
            ],
            "aggregate_throughput": empty_throughput, "regime_identities": [],
        },
        "exclusions": [{"attempt_id": "warmup-001", "reason": "GENERATED_ABORT", "included_in_failure_rate": True}],
        "errors": [error],
    }


def generated_local_control_bundle(
    plan_digest: str,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    raw_by_path: dict[str, dict[str, Any]] = {}
    entries = []
    timing_scopes = {
        "buffer_copy": "copy_only", "framing": "frame_and_verify",
        "sha256": "generate_and_sha256",
    }
    for control, node, payload in ordered_local_control_keys():
        raw = {
            "schema": "qw5.tb5-local-control/v1", "artifact_role": "schema_fixture",
            "evidence_class": "SIMULATED", "created_at": "2000-01-01T00:00:00Z",
            "producer": {
                "name": "qw5-generated-schema-fixture", "version": "1",
                "executable_sha256": "47" * 32, "qw5_commit": "47" * 20,
                "dirty": False, "parameters": ["--generated-control-bundle"],
            },
            "plan_sha256": plan_digest, "control_id": control, "node": node,
            "payload_bytes": payload, "status": "COMPLETE",
            "buffer_policy": {
                "preallocated_input_buffers": 1, "preallocated_output_buffers": 1,
                "peak_application_buffer_bytes": 2 * payload,
                "timing_scope": timing_scopes[control],
            },
            "regime": {
                "node": node,
                "observation_start_monotonic_ns": 1,
                "observation_end_monotonic_ns": 2,
                "start_thermal_state": "nominal",
                "end_thermal_state": "nominal",
                "start_low_power_mode": False,
                "end_low_power_mode": False,
                "start_power_source": "ac",
                "end_power_source": "ac",
            },
            "warmup_elapsed_ns": [3, 2, 1],
            "recorded_elapsed_ns": list(range(1, 11)), "errors": [],
        }
        path = f"controls/{node}/{payload}/{control}.json"
        digest = canonical_digest(raw)
        raw_by_path[path] = raw
        entries.append({
            "control_id": control, "node": node, "payload_bytes": payload,
            "relative_path": path, "sha256": digest,
        })
    index = {
        "schema": "qw5.tb5-local-control-index/v1", "artifact_role": "schema_fixture",
        "evidence_class": "SIMULATED", "created_at": "2000-01-01T00:00:00Z",
        "producer": {
            "name": "qw5-generated-schema-fixture", "version": "1",
            "executable_sha256": "48" * 32, "qw5_commit": "48" * 20,
            "dirty": False, "parameters": ["--generated-control-bundle"],
        },
        "plan_sha256": plan_digest, "canonical_profile": "qw5-json-c14n-v1",
        "entries": entries,
    }
    return index, raw_by_path


def verify_generated_local_control_bundle() -> int:
    failures = 0
    plan = load_json(FIXTURE_DIR / "tb5-run-plan.valid.json")
    index, raw_by_path = generated_local_control_bundle(canonical_digest(plan))
    entries = index["entries"]
    issues = validate_instance(index, "qw5.tb5-local-control-index/v1")
    for raw in raw_by_path.values():
        issues.extend(validate_instance(raw, "qw5.tb5-local-control/v1"))
    if issues:
        for item in issues:
            print(f"FAIL generated local controls: {item.code} {item.pointer}: {item.message}")
        return len(issues)
    keys = {(row["control_id"], row["node"], row["payload_bytes"]) for row in entries}
    if keys != expected_local_control_keys() or len(entries) != 108:
        print("FAIL generated local controls: index does not cover all 108 cells")
        failures += 1
    for entry in entries:
        raw = raw_by_path.get(entry["relative_path"])
        if raw is None or canonical_digest(raw) != entry["sha256"]:
            print("FAIL generated local controls: path/digest did not resolve")
            failures += 1
            break
    missing = entries[:-1]
    if len(missing) == 108 or {
        (row["control_id"], row["node"], row["payload_bytes"]) for row in missing
    } == expected_local_control_keys():
        print("FAIL generated local controls negative missing-entry: hostile was not detected")
        failures += 1
    first = entries[0]
    disagreeing = copy.deepcopy(raw_by_path[first["relative_path"]])
    disagreeing["recorded_elapsed_ns"][0] += 1
    if canonical_digest(disagreeing) == first["sha256"]:
        print("FAIL generated local controls negative digest-disagreement: hostile was not detected")
        failures += 1
    return failures


def verify_generated_link_summary() -> int:
    failures = 0
    null_throughput = expected_metric([], "bytes_per_second")
    null_latency = expected_metric([], "ns")
    plan = load_json(FIXTURE_DIR / "tb5-run-plan.valid.json")
    plan_digest = canonical_digest(plan)
    local_control_index, local_controls_by_path = generated_local_control_bundle(plan_digest)
    local_control_index_digest = canonical_digest(local_control_index)
    seed = plan["seed"]
    ordered_cells = scheduled_cell_ids(seed)
    cells = []
    raw_by_path: dict[str, dict[str, Any]] = {}
    index_entries = []
    for index, cell_id in enumerate(ordered_cells):
        mode, scenario_id, payload = cell_id.split(":")
        mode_name = "round_trip" if mode == "round-trip" else "stream"
        raw = generated_aborted_measurement(
            cell_id,
            index,
            plan,
            plan_digest,
            local_control_index_digest,
        )
        relative_path = f"measurements/{index:03d}.json"
        digest = canonical_digest(raw)
        raw_by_path[relative_path] = raw
        index_entries.append({"cell_id": cell_id, "relative_path": relative_path, "sha256": digest})
        cells.append({
            "cell_id": cell_id,
            "schedule_index": index,
            "mode": mode_name,
            "scenario_id": scenario_id,
            "payload_bytes": int(payload),
            "status": "ABORTED",
            "measurement_sha256": digest,
            "flow_summaries": [
                {"flow_id": flow_id, "throughput": null_throughput, "round_trip_latency": null_latency}
                for flow_id in SCENARIOS[scenario_id]
            ],
            "aggregate_throughput": null_throughput,
            "regime_identities": [],
            "exclusions": raw["exclusions"],
            "errors": raw["errors"],
        })
    measurement_index = {
        "schema": "qw5.tb5-measurement-index/v1",
        "artifact_role": "schema_fixture",
        "evidence_class": "SIMULATED",
        "created_at": "2000-01-01T00:00:00Z",
        "producer": {
            "name": "qw5-generated-schema-fixture", "version": "1",
            "executable_sha256": "42" * 32, "qw5_commit": "42" * 20,
            "dirty": False, "parameters": ["--generated-bundle"],
        },
        "plan_sha256": plan_digest,
        "local_control_index_sha256": local_control_index_digest,
        "plan_seed": seed,
        "canonical_profile": "qw5-json-c14n-v1",
        "entries": index_entries,
    }
    data = {
        "schema": "qw5.tb5-link-summary/v1",
        "artifact_role": "schema_fixture",
        "evidence_class": "SIMULATED",
        "created_at": "2000-01-01T00:00:00Z",
        "producer": {
            "name": "qw5-generated-schema-fixture", "version": "1",
            "executable_sha256": "41" * 32, "qw5_commit": "41" * 20, "dirty": False,
        },
        "plan_sha256": plan_digest,
        "plan_seed": seed,
        "measurement_index_sha256": canonical_digest(measurement_index),
        "local_control_index_sha256": local_control_index_digest,
        "coverage": {
            "planned_cells": 246, "complete_cells": 0, "failed_cells": 0,
            "aborted_cells": 246, "undetermined_cells": 0,
        },
        "cells": cells,
        "prohibited_claims": ["Generated schema fixture; not link evidence."],
    }
    issues = validate_instance(plan, "qw5.tb5-run-plan/v1")
    issues.extend(validate_instance(local_control_index, "qw5.tb5-local-control-index/v1"))
    for raw_control in local_controls_by_path.values():
        issues.extend(validate_instance(raw_control, "qw5.tb5-local-control/v1"))
    issues.extend(validate_instance(data, "qw5.tb5-link-summary/v1"))
    issues.extend(validate_instance(measurement_index, "qw5.tb5-measurement-index/v1"))
    for raw in raw_by_path.values():
        issues.extend(validate_instance(raw, "qw5.tb5-measurement/v1"))
    issues.extend(validate_tb5_evidence_bundle(
        data,
        plan,
        local_control_index,
        local_controls_by_path,
        measurement_index,
        raw_by_path,
    ))
    if issues:
        for item in issues:
            print(f"FAIL generated link summary: {item.code} {item.pointer}: {item.message}")
        return len(issues)
    generated_negatives = [
        ("cell-identity", "/cells/0/mode", "round_trip", "TB_SUMMARY_CELL_IDENTITY"),
        ("flow-set", "/cells/0/flow_summaries/0/flow_id", "c-b", "TB_SUMMARY_FLOW_SET"),
        ("metric-shape", "/cells/0/aggregate_throughput/sample_count", 1, "TB_SUMMARY_METRIC_SHAPE"),
    ]
    for case_id, pointer, value, expected in generated_negatives:
        mutated = copy.deepcopy(data)
        parent, key = pointer_parent(mutated, pointer)
        if isinstance(parent, list):
            parent[int(key)] = value
        else:
            parent[key] = value
        codes = {item.code for item in validate_instance(mutated, "qw5.tb5-link-summary/v1")}
        if expected not in codes:
            print(f"FAIL generated link summary negative {case_id}: expected {expected}; got {sorted(codes)}")
            failures += 1
    all_complete = copy.deepcopy(data)
    for cell in all_complete["cells"]:
        cell["status"] = "COMPLETE"
        cell["errors"] = []
    all_complete["coverage"].update({"complete_cells": 246, "aborted_cells": 0})
    codes = {item.code for item in validate_instance(all_complete, "qw5.tb5-link-summary/v1")}
    if "TB_SUMMARY_COMPLETE_EVIDENCE" not in codes:
        print(f"FAIL generated link summary negative all-complete-zero-samples: got {sorted(codes)}")
        failures += 1
    raw_disagreement = copy.deepcopy(raw_by_path)
    first_path = measurement_index["entries"][0]["relative_path"]
    raw_disagreement[first_path]["errors"][0]["message"] += " changed"
    codes = {item.code for item in validate_tb5_evidence_bundle(
        data,
        plan,
        local_control_index,
        local_controls_by_path,
        measurement_index,
        raw_disagreement,
    )}
    if "TB_SUMMARY_RAW_RECONCILIATION" not in codes or "TB_SUMMARY_MEASUREMENT_DIGEST" not in codes:
        print(f"FAIL generated link summary negative raw-disagreement: got {sorted(codes)}")
        failures += 1
    cyclic_plan = copy.deepcopy(plan)
    cyclic_plan["identity"]["local_control_index_sha256"] = local_control_index_digest
    codes = {item.code for item in validate_instance(cyclic_plan, "qw5.tb5-run-plan/v1")}
    if not any(code.startswith("SCHEMA_") for code in codes):
        print(f"FAIL generated link summary negative cyclic-plan-reference: got {sorted(codes)}")
        failures += 1
    wrong_control_index = copy.deepcopy(local_control_index)
    wrong_control_index["plan_sha256"] = "00" * 32
    codes = {item.code for item in validate_tb5_evidence_bundle(
        data,
        plan,
        wrong_control_index,
        local_controls_by_path,
        measurement_index,
        raw_by_path,
    )}
    if "TB_GRAPH_CONTROL_PLAN" not in codes or "TB_GRAPH_CONTROL_INDEX_DIGEST" not in codes:
        print(f"FAIL generated link summary negative control-plan-disagreement: got {sorted(codes)}")
        failures += 1
    if failures:
        return failures
    return 0


def verify_negative_cases() -> int:
    failures = 0
    manifest = load_json(FIXTURE_DIR / "negative-cases.json")
    case_ids = [row.get("case_id") for row in manifest.get("cases", [])]
    if manifest.get("schema") != "qw5.contract-negative-cases/v1" or not ids_unique(case_ids):
        print("FAIL negative-case manifest: schema ID missing or case IDs are not unique")
        return 1
    for row in manifest["cases"]:
        if row.get("schema") not in SCHEMA_FILES or not (FIXTURE_DIR / row.get("base_fixture", "")).is_file():
            print(f"FAIL negative case {row.get('case_id')}: unknown schema or base fixture")
            failures += 1
            continue
        if not row.get("operations") or not isinstance(row.get("expected_error"), str):
            print(f"FAIL negative case {row['case_id']}: operations or expected error missing")
            failures += 1
            continue
        if any(operation.get("op") not in {"add", "copy", "remove", "replace"} or not isinstance(operation.get("path"), str) for operation in row["operations"]):
            print(f"FAIL negative case {row['case_id']}: malformed mutation operation")
            failures += 1
            continue
        data = copy.deepcopy(load_json(FIXTURE_DIR / row["base_fixture"]))
        for operation in row["operations"]:
            apply_operation(data, operation)
        issues = validate_instance(data, row["schema"])
        codes = {item.code for item in issues}
        expected = row["expected_error"]
        matched = any(code == expected or (expected == "SCHEMA" and code.startswith("SCHEMA_")) for code in codes)
        if not matched:
            detail = ", ".join(sorted(codes)) or "accepted"
            print(f"FAIL negative case {row['case_id']}: expected {expected}; got {detail}")
            failures += 1
    return failures


def verify_model_evidence_bundle() -> int:
    failures = 0
    plan = load_json(FIXTURE_DIR / "model-acquisition-plan.valid.json")
    manifest = load_json(FIXTURE_DIR / "model-artifact-manifest.valid.json")
    issues = validate_model_evidence_bundle(plan, manifest)
    if issues:
        print(f"FAIL model evidence bundle: {[(item.code, item.pointer) for item in issues]}")
        failures += len(issues)
    wrong_digest = copy.deepcopy(manifest)
    wrong_digest["selection"]["acquisition_plan_sha256"] = "00" * 32
    codes = {item.code for item in validate_model_evidence_bundle(plan, wrong_digest)}
    if "MODEL_PLAN_DIGEST" not in codes:
        print(f"FAIL model evidence negative plan-digest: got {sorted(codes)}")
        failures += 1
    config_only = copy.deepcopy(manifest)
    config_only["selection"]["components"] = ["configuration"]
    config_only["selection"]["expected_paths"] = ["config.json"]
    config_only["files"] = [row for row in config_only["files"] if row["path"] == "config.json"]
    config_only["completeness"].update({"verified_file_count": 1, "verified_total_bytes": 2})
    codes = {item.code for item in validate_instance(config_only, "qw5.model-artifact-manifest/v1")}
    if "MODEL_ROLE_COMPONENTS" not in codes or "MODEL_ROLE_COVERAGE" not in codes:
        print(f"FAIL model evidence negative config-only-complete: got {sorted(codes)}")
        failures += 1
    return failures


def verify_placement_evidence_contract() -> int:
    failures = 0
    analysis = load_json(FIXTURE_DIR / "placement-analysis.valid.json")
    graph = load_json(FIXTURE_DIR / "placement-evidence-graph.valid.json")
    if analysis["evidence_graph_sha256"] != canonical_digest(graph):
        print("FAIL placement evidence graph: analysis digest does not match graph")
        failures += 1
    hostile = copy.deepcopy(analysis)
    hostile["decision"]["outcome"] = "GO"
    hostile["decision"]["passed_gates"] = list(hostile["decision"]["applicable_gates"])
    hostile["decision"]["unresolved_gates"] = []
    hostile["decision"]["next_permitted_task"] = "m2-fake"
    for evaluation in hostile["decision"]["gate_evaluations"]:
        if evaluation["gate_id"] in {"quality_available", "scratch_bounded", "state_bounded"}:
            evaluation["disposition"] = "passed"
            evaluation["evidence_node_ids"] = ["gate-rule-set"]
    codes = {item.code for item in validate_instance(hostile, "qw5.placement-analysis/v1")}
    expected = {
        "PLACEMENT_MEMORY_CLASS_COVERAGE",
        "PLACEMENT_QUALITY_EVIDENCE",
        "PLACEMENT_GO_REQUIRES_RESOLVED_GRAPH",
    }
    if not expected.issubset(codes):
        print(f"FAIL placement evidence negative producer-asserted-go: expected {sorted(expected)}; got {sorted(codes)}")
        failures += 1
    bundle_codes = {item.code for item in validate_placement_evidence_bundle(hostile, graph, {})}
    bundle_expected = {"PLACEMENT_GO_UNRESOLVED_GRAPH", "PLACEMENT_GO_UNRESOLVED_RULE"}
    if not bundle_expected.issubset(bundle_codes):
        print(f"FAIL placement evidence negative unresolved-go: expected {sorted(bundle_expected)}; got {sorted(bundle_codes)}")
        failures += 1
    wrong_graph = copy.deepcopy(analysis)
    wrong_graph["evidence_graph_sha256"] = "00" * 32
    codes = {item.code for item in validate_placement_evidence_bundle(wrong_graph, graph, {})}
    if "PLACEMENT_GRAPH_DIGEST" not in codes:
        print(f"FAIL placement evidence negative graph-digest: got {sorted(codes)}")
        failures += 1
    return failures


def verify_tb5_evidence_vectors() -> int:
    failures = 0
    vectors = load_json(FIXTURE_DIR / "tb5-evidence-v1.vectors.json")
    artifacts = vectors.get("artifacts", [])
    hostiles = vectors.get("hostile_mutations", [])
    linkage_hostiles = vectors.get("linkage_hostile_mutations", [])
    all_ids = [row.get("vector_id") for row in artifacts + hostiles + linkage_hostiles]
    if vectors.get("schema") != "qw5.tb5-evidence-vectors/v1" or not ids_unique(all_ids):
        print("FAIL TB5 evidence vectors: schema ID missing or vector IDs are not unique")
        return 1
    materialized: dict[str, tuple[dict[str, Any], str]] = {}
    for row in artifacts:
        path = FIXTURE_DIR / row["fixture"]
        if not path.is_file() or row["schema_id"] not in SCHEMA_FILES:
            print(f"FAIL TB5 evidence vector {row['vector_id']}: missing fixture or schema")
            failures += 1
            continue
        data = load_json(path)
        issues = validate_instance(data, row["schema_id"])
        if issues or canonical_digest(data) != row["canonical_sha256"]:
            print(f"FAIL TB5 evidence vector {row['vector_id']}: validation or canonical digest mismatch")
            failures += 1
            continue
        for resolution in row.get("resolved_entries", []):
            entry = next((item for item in data["entries"] if item["relative_path"] == resolution["relative_path"]), None)
            target_path = FIXTURE_DIR / resolution["fixture"]
            if entry is None or not target_path.is_file() or entry["sha256"] != canonical_digest(load_json(target_path)):
                print(f"FAIL TB5 evidence vector {row['vector_id']}: index entry did not resolve to its canonical artifact digest")
                failures += 1
        linked_attempt = row.get("linked_attempt")
        if linked_attempt is not None:
            attempt = {
                "attempt_id": linked_attempt["attempt_id"],
                "valid": linked_attempt["valid"],
                "invalid_reasons": linked_attempt["invalid_reasons"],
                "synchronization": linked_attempt["synchronization"],
            }
            link_issues = validate_sync_reference(
                linked_attempt["cell_id"], linked_attempt["plan_sha256"], attempt, data,
            )
            if link_issues:
                print(f"FAIL TB5 evidence vector {row['vector_id']}: linked attempt did not reconcile: {[item.code for item in link_issues]}")
                failures += 1
        materialized[row["vector_id"]] = (data, row["schema_id"])
    for row in hostiles:
        base = materialized.get(row["base_vector_id"])
        if base is None:
            print(f"FAIL TB5 hostile vector {row['vector_id']}: unknown base vector")
            failures += 1
            continue
        data = copy.deepcopy(base[0])
        for operation in row["operations"]:
            apply_operation(data, operation)
        codes = {item.code for item in validate_instance(data, base[1])}
        expected = row["expected_error"]
        if not any(code == expected or (expected == "SCHEMA" and code.startswith("SCHEMA_")) for code in codes):
            print(f"FAIL TB5 hostile vector {row['vector_id']}: expected {expected}; got {sorted(codes)}")
            failures += 1
    artifact_rows = {row["vector_id"]: row for row in artifacts}
    for row in linkage_hostiles:
        base = materialized.get(row["base_vector_id"])
        base_row = artifact_rows.get(row["base_vector_id"])
        if base is None or base_row is None or "linked_attempt" not in base_row:
            print(f"FAIL TB5 linkage hostile {row['vector_id']}: unknown or unlinked base vector")
            failures += 1
            continue
        linked_attempt = copy.deepcopy(base_row["linked_attempt"])
        for operation in row["operations"]:
            apply_operation(linked_attempt, operation)
        attempt = {
            "attempt_id": linked_attempt["attempt_id"],
            "valid": linked_attempt["valid"],
            "invalid_reasons": linked_attempt["invalid_reasons"],
            "synchronization": linked_attempt["synchronization"],
        }
        codes = {
            item.code for item in validate_sync_reference(
                linked_attempt["cell_id"], linked_attempt["plan_sha256"], attempt, base[0],
            )
        }
        if row["expected_error"] not in codes:
            print(f"FAIL TB5 linkage hostile {row['vector_id']}: expected {row['expected_error']}; got {sorted(codes)}")
            failures += 1
    return failures


def main() -> int:
    failures = 0
    schemas: dict[str, Any] = {}
    for schema_id, filename in SCHEMA_FILES.items():
        schema = load_json(SCHEMA_DIR / filename)
        try:
            Draft202012Validator.check_schema(schema)
        except Exception as exc:  # jsonschema reports the complete schema path.
            print(f"FAIL schema {filename}: {exc}")
            failures += 1
        schemas[schema_id] = schema
    for path in sorted(FIXTURE_DIR.glob("*.valid.json")):
        data = load_json(path)
        schema_id = data.get("schema")
        if schema_id not in schemas:
            print(f"FAIL fixture {path.name}: unknown schema {schema_id!r}")
            failures += 1
            continue
        issues = schema_issues(data, schemas[schema_id])
        if not issues:
            issues = SEMANTIC_VALIDATORS[schema_id](data)
        if issues:
            for item in issues:
                print(f"FAIL fixture {path.name}: {item.code} {item.pointer}: {item.message}")
            failures += len(issues)
    failures += verify_canonical_vectors()
    failures += verify_wire_vectors()
    failures += verify_safetensors_vectors()
    failures += verify_model_evidence_bundle()
    failures += verify_placement_evidence_contract()
    failures += verify_tb5_evidence_vectors()
    failures += verify_generated_local_control_bundle()
    failures += verify_generated_link_summary()
    failures += verify_negative_cases()
    if failures:
        print(f"contract validation failed with {failures} issue(s)")
        return 1
    valid_count = len(list(FIXTURE_DIR.glob("*.valid.json")))
    negative_count = len(load_json(FIXTURE_DIR / "negative-cases.json")["cases"])
    print(
        f"validated {len(schemas)} schemas, {valid_count} committed positive fixtures, "
        "one generated acyclic 108-control/246-cell evidence graph, model and placement "
        f"bundle invariants, {negative_count} negative cases, and exact canonical/wire/"
        "TB5/SafeTensors vectors"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
