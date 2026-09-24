"""Adapter between PosData Builder mappings and the existing generation pipeline.

The Builder works with user-confirmed structures:

    context.confirmed_pos_mapping
    context.confirmed_itona_mapping

The existing Configurator generation pipeline expects RuntimeContext fields:

    runtime.pos_mapping
    runtime.runtime_pos_machine_lookup
    runtime.kvs_mapping
    runtime.current_posdata_folder
    runtime.new_posdata_folder

This module converts the Builder contract into that existing contract. It does
not generate XML and does not modify source or template files.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence

from src.runtime_context import RuntimeContext

from src.builder.lab_naming_resolver import (
    LabNamingResolver,
)

READY_STATUSES = {
    "READY",
    "READY WITH OBSERVATION",
    "READY WITH OBSERVATIONS",
}
SKIPPED_STATUSES = {
    "SKIPPED",
    "NONE",
}
MAX_KVS_FILES_PER_ITONA = 2


def _text(value: Any) -> str:
    return str(value or "").strip()


def _upper(value: Any) -> str:
    return _text(value).upper()


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _as_path(value: Any) -> Optional[Path]:
    text = _text(value)
    return Path(text) if text else None


def _normalize_generation_status(value: Any) -> str:
    """Convert Builder statuses to statuses accepted by existing generators."""
    status = _upper(value)
    if status in READY_STATUSES:
        return "READY"
    if status in SKIPPED_STATUSES:
        return "SKIPPED"
    return status or "REVIEW REQUIRED"


def _normalize_service_id(value: Any) -> str:
    service_id = _upper(value)
    if service_id.startswith("KVS"):
        service_id = service_id[3:]
    return service_id


def _natural_key(value: Any) -> tuple[Any, ...]:
    parts = re.split(r"(\d+)", _upper(value))
    return tuple(int(part) if part.isdigit() else part for part in parts)


def _load_json_config(config_path: str | Path | None) -> Dict[str, Any]:
    if not config_path:
        return {}
    path = Path(config_path)
    if not path.is_file():
        return {}
    try:
        with path.open("r", encoding="utf-8") as stream:
            loaded = json.load(stream)
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _walk_dicts(value: Any) -> Iterable[Mapping[str, Any]]:
    """Yield every dictionary contained in a JSON-compatible structure."""
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _walk_dicts(child)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for child in value:
            yield from _walk_dicts(child)


def _dict_node_name(item: Mapping[str, Any]) -> str:
    for key in (
        "node_name",
        "target_node",
        "node",
        "machine",
        "logical_name",
        "name",
    ):
        value = _upper(item.get(key))
        if re.fullmatch(r"POS\d+", value):
            return value
    return ""


def _find_config_machine(
    config: Mapping[str, Any],
    node_name: str,
) -> Dict[str, Any]:
    expected = _upper(node_name)
    for item in _walk_dicts(config):
        if _dict_node_name(item) == expected:
            return dict(item)
    return {}


def _first_value(
    sources: Sequence[Mapping[str, Any]],
    keys: Sequence[str],
) -> Any:
    for source in sources:
        for key in keys:
            value = source.get(key)
            if value is not None and _text(value):
                return value
    return None


def _default_pos_output_file(node_name: str) -> str:
    """Return a deterministic fallback when lab config has no machine filename.

    The fallback is intentionally based on the target node, never on the source
    market filename. Lab configuration remains the preferred source.
    """
    return f"_{node_name}_pos-db.xml"


def build_runtime_pos_mapping(
    confirmed_pos_mapping: Mapping[str, Any],
    config_path: str | Path | None = None,
    naming_resolver: LabNamingResolver | None = None,
) -> Dict[str, Any]:
    """Build pos_mapping and runtime_pos_machine_lookup for POS generation."""
    result: Dict[str, Any] = {
        "status": "READY",
        "pos_mapping": {
            "status": "READY",
            "mappings": [],
            "unused_sources": [],
            "warnings": [],
            "errors": [],
        },
        "machine_lookup": {},
        "warnings": [],
        "errors": [],
    }

    config = _load_json_config(config_path)
    assignments = confirmed_pos_mapping.get("assignments") or []

    if not assignments:
        result["errors"].append("Confirmed POS mapping does not contain assignments.")
        result["status"] = "FAIL"
        result["pos_mapping"]["status"] = "FAIL"
        result["pos_mapping"]["errors"] = list(result["errors"])
        return result

    used_sources: set[str] = set()

    for assignment in assignments:
        node_name = _upper(
            assignment.get("target_node")
            or assignment.get("node_name")
            or assignment.get("slot")
        )
        source_file = _text(assignment.get("source_file")) or None
        source_path = _text(assignment.get("source_path")) or None
        builder_status = _upper(assignment.get("status"))
        generation_status = _normalize_generation_status(builder_status)
        warnings = list(assignment.get("warnings") or [])
        errors = list(assignment.get("errors") or [])

        if not node_name:
            result["errors"].append("A confirmed POS assignment has no target node.")
            continue

        if generation_status == "READY" and not source_file:
            errors.append(f"No source POS file was selected for {node_name}.")
            generation_status = "REVIEW REQUIRED"

        if source_file and source_file in used_sources:
            errors.append(f"POS source cannot be reused: {source_file}")
            generation_status = "REVIEW REQUIRED"
        elif source_file:
            used_sources.add(source_file)

        mapping = {
            "node_name": node_name,
            "target_node": node_name,
            "expected_role": _upper(assignment.get("expected_role")),
            "effective_role": _upper(
                assignment.get("effective_role")
                or assignment.get("source_role")
                or assignment.get("target_role")
            ),
            "source_role": _upper(assignment.get("source_role")),
            "source_file": source_file,
            "source_path": source_path,
            "status": generation_status,
            "builder_status": builder_status,
            "selection_mode": assignment.get("selection_mode", "MANUAL"),
            "selection_reason": assignment.get("selection_reason"),
            "warnings": warnings,
            "errors": errors,
        }
        result["pos_mapping"]["mappings"].append(mapping)

        config_machine = _find_config_machine(
            config,
            node_name,
        )

        sources = (
            assignment,
            config_machine,
        )

        machine_file = _first_value(
            sources,
            (
                "machine_file",
                "target_machine_file",
                "file",
            ),
        )

        #
        # Priority 1:
        # Explicit output configured in the
        # confirmed assignment.
        #
        output_file = _first_value(
            (
                assignment,
            ),
            (
                "output_file",
                "target_output_file",
            ),
        )

        machine_ip = _first_value(
            sources,
            (
                "target_machine_ip",
                "machine_ip",
                "ip",
                "address",
            ),
        )

        #
        # Priority 2:
        # Laboratory naming resolver.
        #
        if (
            not output_file
            and naming_resolver is not None
        ):

            try:

                output_file = (
                    naming_resolver
                    .resolve_pos_output_name(
                        node_name
                    )
                )

            except (
                KeyError,
                ValueError,
            ) as error:

                naming_warning = str(
                    error
                )

                result[
                    "warnings"
                ].append(
                    naming_warning
                )

                mapping[
                    "warnings"
                ].append(
                    naming_warning
                )

        #
        # Priority 3:
        # Legacy values found in the
        # laboratory configuration.
        #
        if not output_file:

            output_file = _first_value(
                (
                    config_machine,
                ),
                (
                    "output_file",
                    "machine_file",
                    "target_machine_file",
                    "file",
                ),
            )

        #
        # Final controlled fallback.
        #
        if not output_file:

            output_file = (
                _default_pos_output_file(
                    node_name
                )
            )

            fallback_warning = (
                "Lab output filename was not "
                f"found for {node_name}; "
                "using deterministic fallback "
                f"{output_file}."
            )

            result[
                "warnings"
            ].append(
                fallback_warning
            )

            mapping[
                "warnings"
            ].append(
                fallback_warning
            )

        machine_file = (
            _text(
                machine_file
            )
            or _text(
                output_file
            )
        )

        #
        # Keep the resolved filename inside
        # the mapping for reporting and
        # generation diagnostics.
        #
        mapping[
            "output_file"
        ] = _text(
            output_file
        )

        mapping[
            "machine_file"
        ] = machine_file

        result["warnings"].append(fallback_warning)
        mapping["warnings"].append(fallback_warning)

        result["machine_lookup"][node_name] = {
            "node_name": node_name,
            "machine_file": _text(machine_file) or _text(output_file),
            "output_file": _text(output_file),
            "ip": _text(machine_ip) or None,
            "expected_role": mapping["expected_role"],
            "effective_role": mapping["effective_role"],
        }

    for extra in confirmed_pos_mapping.get("extra_candidates") or []:
        if _upper(extra.get("status")) in {"IGNORED", "UNASSIGNED"}:
            result["pos_mapping"]["unused_sources"].append(deepcopy(extra))

    if result["errors"] or any(
        mapping["status"] not in {"READY", "SKIPPED"}
        or mapping["errors"]
        for mapping in result["pos_mapping"]["mappings"]
    ):
        result["status"] = "FAIL"
        result["pos_mapping"]["status"] = "FAIL"
    elif any(
        mapping["status"] == "SKIPPED"
        for mapping in result["pos_mapping"]["mappings"]
    ):
        result["status"] = "READY WITH SKIPS"
        result["pos_mapping"]["status"] = "READY WITH SKIPS"

    result["pos_mapping"]["warnings"] = _unique(result["warnings"])
    result["pos_mapping"]["errors"] = _unique(result["errors"])
    return result


def _build_itona_candidate_index(
    discovered_candidates: Iterable[Mapping[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    return {
        _text(candidate.get("file")): dict(candidate)
        for candidate in discovered_candidates
        if candidate.get("file")
    }


def _selected_source_files(assignment: Mapping[str, Any]) -> list[str]:
    files = [
        _text(value)
        for value in assignment.get("source_files") or []
        if _text(value)
    ]
    if not files and assignment.get("source_file"):
        files = [_text(assignment.get("source_file"))]
    return _unique(files)


def build_runtime_kvs_mapping(
    confirmed_itona_mapping: Mapping[str, Any],
    discovered_candidates: Iterable[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Build the kvs_mapping contract consumed by generate_all_itonas()."""
    result: Dict[str, Any] = {
        "status": "READY",
        "kvs_mapping": {
            "status": "READY",
            "mappings": [],
            "extra_services": [],
            "warnings": [],
            "errors": [],
        },
        "warnings": [],
        "errors": [],
    }

    assignments = confirmed_itona_mapping.get("assignments") or []
    candidate_index = _build_itona_candidate_index(discovered_candidates)

    if not assignments:
        result["errors"].append("Confirmed Itona mapping does not contain assignments.")
        result["status"] = "FAIL"
        result["kvs_mapping"]["status"] = "FAIL"
        result["kvs_mapping"]["errors"] = list(result["errors"])
        return result

    used_files: Dict[str, str] = {}
    used_services: set[str] = set()

    for assignment in assignments:
        machine = _text(assignment.get("slot") or assignment.get("machine"))
        source_files = _selected_source_files(assignment)
        builder_status = _upper(assignment.get("status"))
        generation_status = _normalize_generation_status(builder_status)
        warnings = list(assignment.get("warnings") or [])
        errors = list(assignment.get("errors") or [])

        mapping: Dict[str, Any] = {
            "machine": machine,
            "target_file": (
                resolver.resolve_itona_output_name(
                    machine
                )
            ),
            "status": generation_status,
            "builder_status": builder_status,
            "mapped_services": [],
            "missing_services": [],
            "candidate_services": {},
            "source_files": source_files,
            "warnings": warnings,
            "errors": errors,
        }

        if not machine:
            mapping["errors"].append("An Itona assignment has no slot/machine name.")
            mapping["status"] = "REVIEW REQUIRED"
            result["kvs_mapping"]["mappings"].append(mapping)
            continue

        if len(source_files) > MAX_KVS_FILES_PER_ITONA:
            mapping["errors"].append(
                f"{machine} supports a maximum of "
                f"{MAX_KVS_FILES_PER_ITONA} KVS source files."
            )
            mapping["status"] = "REVIEW REQUIRED"

        if generation_status == "SKIPPED" or not source_files:
            mapping["status"] = "SKIPPED"
            result["kvs_mapping"]["mappings"].append(mapping)
            continue

        for file_name in source_files:
            previous_machine = used_files.get(file_name)
            if previous_machine and previous_machine != machine:
                mapping["errors"].append(
                    f"{file_name} is already assigned to {previous_machine} "
                    f"and cannot also be assigned to {machine}."
                )
                mapping["status"] = "REVIEW REQUIRED"
                continue

            candidate = candidate_index.get(file_name)
            if candidate is None:
                mapping["errors"].append(
                    f"Selected KVS source was not discovered: {file_name}"
                )
                mapping["status"] = "REVIEW REQUIRED"
                continue

            used_files[file_name] = machine
            services = _unique(
                _normalize_service_id(value)
                for value in candidate.get("kvs_services") or []
            )
            if not services:
                mapping["errors"].append(
                    f"No KVS service was discovered in {file_name}."
                )
                mapping["status"] = "REVIEW REQUIRED"
                continue

            for service_id in services:
                if service_id in used_services:
                    mapping["errors"].append(
                        f"KVS{service_id} is assigned more than once."
                    )
                    mapping["status"] = "REVIEW REQUIRED"
                    continue
                used_services.add(service_id)
                mapping["mapped_services"].append({
                    "service": service_id,
                    "source_service": service_id,
                    "source_file": file_name,
                    "startonload": True,
                    "selection_mode": "MANUAL",
                })

        mapping["mapped_services"] = sorted(
            mapping["mapped_services"],
            key=lambda item: (_natural_key(item["service"]), item["source_file"]),
        )

        if not mapping["mapped_services"] and mapping["status"] != "SKIPPED":
            mapping["errors"].append(
                f"No valid mapped KVS services were built for {machine}."
            )
            mapping["status"] = "REVIEW REQUIRED"

        result["kvs_mapping"]["mappings"].append(mapping)

    for file_name, candidate in candidate_index.items():
        if file_name in used_files:
            continue
        for service_id in _unique(
            _normalize_service_id(value)
            for value in candidate.get("kvs_services") or []
        ):
            result["kvs_mapping"]["extra_services"].append({
                "service": service_id,
                "source_service": service_id,
                "source_file": file_name,
                "startonload": False,
            })

    invalid = [
        mapping
        for mapping in result["kvs_mapping"]["mappings"]
        if mapping["status"] not in {"READY", "SKIPPED"}
        or mapping["errors"]
    ]
    if result["errors"] or invalid:
        result["status"] = "FAIL"
        result["kvs_mapping"]["status"] = "FAIL"
    elif any(
        mapping["status"] == "SKIPPED"
        for mapping in result["kvs_mapping"]["mappings"]
    ):
        result["status"] = "READY WITH SKIPS"
        result["kvs_mapping"]["status"] = "READY WITH SKIPS"

    result["kvs_mapping"]["warnings"] = _unique(result["warnings"])
    result["kvs_mapping"]["errors"] = _unique(result["errors"])
    return result


def _copy_optional_builder_values(builder_context: Any, runtime: RuntimeContext) -> None:
    """Copy optional values used by later Configurator generation steps."""
    for name, default in (
        ("cod_target", {}),
        ("way_target", {}),
        ("foe_result", {}),
        ("market", {}),
        ("store_info", {}),
        ("screens", []),
        ("lunch_screen", None),
    ):
        value = getattr(builder_context, name, default)
        setattr(runtime, name, deepcopy(value if value is not None else default))


def build_builder_runtime_context(
    builder_context: Any,
    *,
    strict: bool = True,
) -> RuntimeContext:
    """Create RuntimeContext ready for the existing generation phase.

    Raises ValueError in strict mode if an adapter contract is incomplete.
    """
    confirmed_pos = getattr(builder_context, "confirmed_pos_mapping", None) or {}
    confirmed_itonas = (
        getattr(builder_context, "confirmed_itona_mapping", None) or {}
    )
    discovered_itonas = (
        getattr(builder_context, "discovered_itona_candidates", None) or []
    )

    pos_result = build_runtime_pos_mapping(
        confirmed_pos_mapping=confirmed_pos,
        config_path=getattr(builder_context, "config_path", None),
    )
    kvs_result = build_runtime_kvs_mapping(
        confirmed_itona_mapping=confirmed_itonas,
        discovered_candidates=discovered_itonas,
    )

    adapter_errors = _unique(
        list(pos_result.get("errors") or [])
        + list(kvs_result.get("errors") or [])
        + [
            error
            for mapping in pos_result["pos_mapping"].get("mappings", [])
            for error in mapping.get("errors", [])
        ]
        + [
            error
            for mapping in kvs_result["kvs_mapping"].get("mappings", [])
            for error in mapping.get("errors", [])
        ]
    )
    adapter_warnings = _unique(
        list(pos_result.get("warnings") or [])
        + list(kvs_result.get("warnings") or [])
    )

    if strict and adapter_errors:
        raise ValueError(
            "Builder generation adapter is not ready:\n- "
            + "\n- ".join(adapter_errors)
        )

    runtime = RuntimeContext()
    runtime.selected_lab = getattr(builder_context, "selected_lab", None)
    resolver = (
        LabNamingResolver.from_file(
            runtime.config_path
        )
    )

    runtime.lab_naming = (
        resolver.snapshot()
    )
    runtime.config_path = getattr(builder_context, "config_path", None)

    # The internal template replaces Current PosData as generation reference.
    runtime.current_posdata_folder = str(
        getattr(builder_context, "template_folder", "") or ""
    ) or None

    # Source-market PosData replaces New PosData as transformation source.
    runtime.new_posdata_folder = str(
        getattr(builder_context, "source_posdata_folder", "") or ""
    ) or None
    runtime.store_db_path = getattr(builder_context, "store_db_path", None)
    runtime.screen_xml_path = getattr(builder_context, "screen_xml_path", None)

    runtime.pos_mapping = pos_result["pos_mapping"]
    runtime.runtime_pos_machine_lookup = pos_result["machine_lookup"]
    runtime.kvs_mapping = kvs_result["kvs_mapping"]

    # Keep Builder contracts for reporting and traceability.
    runtime.builder_confirmed_pos_mapping = deepcopy(confirmed_pos)
    runtime.builder_confirmed_itona_mapping = deepcopy(confirmed_itonas)
    runtime.builder_adapter_status = (
        "FAIL"
        if adapter_errors
        else (
            "READY WITH SKIPS"
            if (
                pos_result["status"] == "READY WITH SKIPS"
                or kvs_result["status"] == "READY WITH SKIPS"
            )
            else "READY"
        )
    )
    runtime.builder_adapter_warnings = adapter_warnings
    runtime.builder_adapter_errors = adapter_errors

    _copy_optional_builder_values(builder_context, runtime)
    return runtime


# Backward-friendly alias for the Builder generation phase.
adapt_builder_context_to_runtime = build_builder_runtime_context
