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
    "qw5.model-artifact-manifest/v1": "model-artifact-manifest.schema.json",
    "qw5.placement-analysis/v1": "placement-analysis.schema.json",
    "qw5.tb5-link-summary/v1": "tb5-link-summary.schema.json",
    "qw5.tb5-measurement/v1": "tb5-measurement.schema.json",
    "qw5.tb5-route-proof/v1": "tb5-route-proof.schema.json",
    "qw5.tb5-run-plan/v1": "tb5-run-plan.schema.json",
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


def semantic_model(data: dict[str, Any]) -> list[Issue]:
    out: list[Issue] = []
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
    role_set = {row["role"] for row in files if row["status"] == "verified"}
    role_requirements = {
        "configuration": {"configuration"}, "language": {"weight_shard"},
        "license": {"license"}, "tokenizer": {"tokenizer", "tokenizer_configuration"},
    }
    for component in data["selection"]["components"]:
        required = role_requirements.get(component)
        if required and not (required & role_set):
            out.append(issue("MODEL_ROLE_COVERAGE", "/files", f"component {component} has no verified file role"))
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


def semantic_placement(data: dict[str, Any]) -> list[Issue]:
    out: list[Issue] = []
    inputs = data["inputs"]
    expected_input_schemas = {
        "model_manifest": "qw5.model-artifact-manifest/v1",
        "tensor_inventory": "qw5.tensor-inventory/v1",
        "link_summary": "qw5.tb5-link-summary/v1",
        "quantization_layout": "qw5.quantization-layout/v1",
        "formula_set": "qw5.formula-set/v1",
        "text_subset_dependency": "qw5.text-subset-dependency/v1",
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
    passed = set(decision["passed_gates"])
    failed = set(decision["failed_gates"])
    unresolved = set(decision["unresolved_gates"])
    if required != ALL_GATES:
        out.append(issue("PLACEMENT_GATE_REQUIRED_SET", "/decision/required_gates", "required gate set is not exhaustive"))
    if (passed & failed) or (passed & unresolved) or (failed & unresolved):
        out.append(issue("PLACEMENT_GATE_DISJOINT", "/decision", "passed, failed, and unresolved gates must be disjoint"))
    if passed | failed | unresolved != required:
        out.append(issue("PLACEMENT_GATE_COVERAGE", "/decision", "gate outcomes must cover every required gate"))
    nonnegative = bool(headrooms) and min(headrooms) >= 0
    if nonnegative and "memory_nonnegative" not in passed:
        out.append(issue("PLACEMENT_MEMORY_GATE", "/decision", "nonnegative headroom must pass the memory gate"))
    if not nonnegative and "memory_nonnegative" in passed:
        out.append(issue("PLACEMENT_MEMORY_GATE", "/decision/passed_gates", "negative headroom cannot pass the memory gate"))
    if decision["outcome"] == "GO" and (not nonnegative or passed != required):
        out.append(issue("PLACEMENT_GO_GATES", "/decision/outcome", "GO requires every gate passed and nonnegative headroom"))
    if decision["outcome"] == "CONDITIONAL_GO" and "memory_nonnegative" not in passed:
        out.append(issue("PLACEMENT_CONDITIONAL_MEMORY", "/decision/outcome", "CONDITIONAL_GO still requires nonnegative memory"))
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
    scenario_id = data["scenario"]["scenario_id"]
    flow_ids = SCENARIOS[scenario_id]
    simultaneous = len(flow_ids) > 1
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
    valid_thermal_regimes: set[str] = set()
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
                expected_uncertainty = (
                    sync["maximum_control_rtt_ns"]
                    + 2 * sync["maximum_worker_start_ack_ns"]
                    + sync["timer_resolution_allowance_ns"]
                )
                if sync["uncertainty_ns"] != expected_uncertainty:
                    out.append(issue("TB_SYNC_RECONCILIATION", base + "/synchronization/uncertainty_ns", f"expected {expected_uncertainty}"))
                expected_upper_bound = sync["coordinator_receipt_skew_ns"] + sync["uncertainty_ns"]
                if sync["start_skew_upper_bound_ns"] != expected_upper_bound:
                    out.append(issue("TB_SYNC_RECONCILIATION", base + "/synchronization/start_skew_upper_bound_ns", f"expected {expected_upper_bound}"))
                uncertainty_exceeded = sync["uncertainty_ns"] > data["scenario"]["maximum_sync_uncertainty_ns"]
                skew_exceeded = sync["start_skew_upper_bound_ns"] > data["scenario"]["start_skew_limit_ns"]
                if uncertainty_exceeded and (attempt["valid"] or "SYNC_UNCERTAINTY_EXCEEDED" not in attempt["invalid_reasons"]):
                    out.append(issue("TB_SYNC_UNCERTAINTY", base + "/synchronization/uncertainty_ns", "uncertainty above 1 ms must invalidate the retained attempt"))
                if skew_exceeded and (attempt["valid"] or "START_SKEW_EXCEEDED" not in attempt["invalid_reasons"]):
                    out.append(issue("TB_SYNC_SKEW", base + "/synchronization/start_skew_upper_bound_ns", "skew upper bound above 10 ms must invalidate the retained attempt"))
        elif sync["status"] != "not_required":
            out.append(issue("TB_SOLO_SYNC", base + "/synchronization", "solo attempt must mark cross-flow synchronization not required"))
        active_nodes = sorted({node for flow_id in flow_ids for node in FLOW[flow_id][:2]})
        thermal_nodes = [row["node"] for row in attempt["thermal"]]
        if thermal_nodes != active_nodes:
            out.append(issue("TB_THERMAL_COVERAGE", base + "/thermal", f"expected nodes {active_nodes}"))
        for thermal_index, thermal in enumerate(attempt["thermal"]):
            if thermal["end_monotonic_ns"] < thermal["start_monotonic_ns"]:
                out.append(issue("TB_THERMAL_TIME", base + f"/thermal/{thermal_index}", "thermal timestamps regress"))
            if attempt["phase"] == "measurement" and attempt["valid"]:
                valid_thermal_regimes.update((thermal["start_state"], thermal["end_state"]))
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
                if receiver_elapsed < minimum:
                    out.append(issue("TB_STREAM_DURATION", sample_base, f"receiver interval must be at least {minimum} ns"))
                if sample["round_trip_ns"]:
                    out.append(issue("TB_STREAM_LATENCY", sample_base + "/round_trip_ns", "stream mode cannot report round-trip exchanges"))
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
        if row["thermal_regimes"] != sorted(valid_thermal_regimes):
            out.append(issue("TB_THERMAL_SUMMARY", f"/summary/flow_summaries/{index}/thermal_regimes", f"expected {sorted(valid_thermal_regimes)}"))
    expected_aggregate = expected_metric(aggregate_rates, "bytes_per_second")
    if summary["aggregate_throughput"] != expected_aggregate:
        out.append(issue("TB_AGGREGATE_SUMMARY", "/summary/aggregate_throughput", f"expected {expected_aggregate}"))
    if summary["thermal_regimes"] != sorted(valid_thermal_regimes):
        out.append(issue("TB_THERMAL_SUMMARY", "/summary/thermal_regimes", f"expected {sorted(valid_thermal_regimes)}"))
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
    sync_unavailable = [row for row in measurements if row["synchronization"]["status"] in {"unavailable", "error"}]
    if simultaneous and measurements and len(sync_unavailable) == len(measurements) and status != "UNDETERMINED":
        out.append(issue("TB_SYNC_CELL_OUTCOME", "/summary/cell_status", "a simultaneous cell without synchronization evidence must be UNDETERMINED"))
    if status == "UNDETERMINED" and not sync_unavailable:
        out.append(issue("TB_UNDETERMINED_STATUS", "/summary/cell_status", "undetermined cell requires unavailable synchronization evidence"))
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
        if row["thermal_regimes"] != sorted(row["thermal_regimes"]):
            out.append(issue("TB_SUMMARY_THERMAL_ORDER", base + "/thermal_regimes", "thermal regimes must be sorted"))
    counts = Counter(row["status"].lower() + "_cells" for row in cells)
    coverage = data["coverage"]
    for key in ("complete_cells", "failed_cells", "aborted_cells", "undetermined_cells"):
        if coverage[key] != counts[key]:
            out.append(issue("TB_SUMMARY_STATUS_RECONCILIATION", f"/coverage/{key}", f"expected {counts[key]}"))
    return out


SEMANTIC_VALIDATORS: dict[str, Callable[[dict[str, Any]], list[Issue]]] = {
    "qw5.hardware-inventory/v1": semantic_hardware,
    "qw5.memory-baseline/v1": semantic_memory,
    "qw5.model-artifact-manifest/v1": semantic_model,
    "qw5.placement-analysis/v1": semantic_placement,
    "qw5.tb5-link-summary/v1": semantic_link_summary,
    "qw5.tb5-measurement/v1": semantic_tb_measurement,
    "qw5.tb5-route-proof/v1": semantic_route,
    "qw5.tb5-run-plan/v1": semantic_tb_plan,
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


def verify_generated_link_summary() -> int:
    failures = 0
    null_throughput = expected_metric([], "bytes_per_second")
    null_latency = expected_metric([], "ns")
    seed = 42
    ordered_cells = scheduled_cell_ids(seed)
    cells = []
    for index, cell_id in enumerate(ordered_cells):
        mode, scenario_id, payload = cell_id.split(":")
        cells.append({
            "cell_id": cell_id,
            "schedule_index": index,
            "mode": "round_trip" if mode == "round-trip" else "stream",
            "scenario_id": scenario_id,
            "payload_bytes": int(payload),
            "status": "UNDETERMINED",
            "measurement_sha256": hashlib.sha256(cell_id.encode("utf-8")).hexdigest(),
            "flow_summaries": [
                {"flow_id": flow_id, "throughput": null_throughput, "round_trip_latency": null_latency}
                for flow_id in SCENARIOS[scenario_id]
            ],
            "aggregate_throughput": null_throughput,
            "thermal_regimes": [],
        })
    data = {
        "schema": "qw5.tb5-link-summary/v1",
        "artifact_role": "schema_fixture",
        "evidence_class": "SIMULATED",
        "created_at": "2000-01-01T00:00:00Z",
        "producer": {
            "name": "qw5-generated-schema-fixture", "version": "1",
            "executable_sha256": "41" * 32, "qw5_commit": "41" * 20, "dirty": False,
        },
        "plan_sha256": "43" * 32,
        "plan_seed": seed,
        "measurement_index_sha256": "44" * 32,
        "local_controls_sha256": "45" * 32,
        "coverage": {
            "planned_cells": 246, "complete_cells": 0, "failed_cells": 0,
            "aborted_cells": 0, "undetermined_cells": 246,
        },
        "cells": cells,
        "prohibited_claims": ["Generated schema fixture; not link evidence."],
    }
    issues = validate_instance(data, "qw5.tb5-link-summary/v1")
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
    failures += verify_generated_link_summary()
    failures += verify_negative_cases()
    if failures:
        print(f"contract validation failed with {failures} issue(s)")
        return 1
    valid_count = len(list(FIXTURE_DIR.glob("*.valid.json")))
    negative_count = len(load_json(FIXTURE_DIR / "negative-cases.json")["cases"])
    print(f"validated {len(schemas)} schemas, {valid_count} committed positive fixtures, one generated 246-cell fixture, {negative_count} negative cases, and exact canonical/wire vectors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
