"""Automatic assignment proposal engine for PosData Builder.

Builds editable POS and Itona assignment proposals from:
- laboratory POS targets;
- source-market POS discovery;
- template Itona slots;
- source-market Itona candidates.

This module does not generate files and does not modify XML.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from src.discovery.dynamic_pos_mapping import (
    load_lab_pos_targets,
)

from src.builder.lab_naming_resolver import (
    load_lab_config,
)

SUPPORTED_POS_ROLES = ("FC", "DT")
CONFIDENCE_RANK = {
    "HIGH": 0,
    "MEDIUM": 1,
    "LOW": 2,
    "NONE": 3,
}
STATUS_RANK = {
    "READY": 0,
    "REVIEW REQUIRED": 1,
    "MISSING": 2,
    "FAIL": 3,
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _upper(value: Any) -> str:
    return _text(value).upper()


def _natural_key(value: Any) -> Tuple[Any, ...]:
    parts = re.split(r"(\d+)", _upper(value))
    return tuple(int(part) if part.isdigit() else part for part in parts)


def _first_node(source: Mapping[str, Any]) -> Optional[str]:
    candidates = source.get("node_candidates") or []
    if candidates:
        return _upper(candidates[0]) or None
    return None


def _normalize_pos_sources(
    discovery_result: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []

    for source in discovery_result.get("pos_files") or []:
        role = _upper(source.get("role"))
        if role not in SUPPORTED_POS_ROLES:
            continue

        normalized.append(
            {
                "file": source.get("file"),
                "path": source.get("path"),
                "role": role,
                "node": _first_node(source),
                "node_candidates": list(
                    source.get("node_candidates") or []
                ),
                "confidence": _upper(
                    source.get("role_confidence")
                ) or "NONE",
                "discovery_status": _upper(
                    source.get("role_status")
                ) or "REVIEW REQUIRED",
                "warnings": list(source.get("warnings") or []),
                "errors": list(source.get("errors") or []),
            }
        )

    return sorted(
        normalized,
        key=lambda item: (
            SUPPORTED_POS_ROLES.index(item["role"]),
            _natural_key(item.get("node")),
            _natural_key(item.get("file")),
        ),
    )


def _select_pos_source(
    target: Mapping[str, Any],
    available: Sequence[Dict[str, Any]],
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    target_node = _upper(target.get("target_node"))
    expected_role = _upper(target.get("expected_role"))

    same_role = [
        source
        for source in available
        if source.get("role") == expected_role
    ]

    for source in same_role:
        nodes = {
            _upper(node)
            for node in source.get("node_candidates") or []
        }
        if target_node and target_node in nodes:
            return source, "exact node and role match"

    if same_role:
        return same_role[0], "first available source with required role"

    return None, None


def build_pos_assignment_proposal(
    discovered_pos: Mapping[str, Any],
    config_path: str | Path,
) -> Dict[str, Any]:
    """Build editable POS assignments using laboratory targets."""
    result: Dict[str, Any] = {
        "status": "READY",
        "config_path": str(config_path),
        "assignments": [],
        "extra_candidates": [],
        "warnings": [],
        "errors": [],
    }

    target_result = load_lab_pos_targets(config_path)
    result["warnings"].extend(target_result.get("warnings") or [])
    result["errors"].extend(target_result.get("errors") or [])

    if result["errors"]:
        result["status"] = "FAIL"
        return result

    sources = _normalize_pos_sources(discovered_pos)
    available = list(sources)

    for index, target in enumerate(
        target_result.get("targets") or [],
        start=1,
    ):
        selected, reason = _select_pos_source(target, available)
        target_node = target.get("target_node")
        expected_role = target.get("expected_role")

        if selected is None:
            assignment = {
                "slot_index": index,
                "slot": target_node,
                "target_node": target_node,
                "target_role": expected_role,
                "target_machine_ip": target.get("machine_ip"),
                "source_file": None,
                "source_path": None,
                "source_node": None,
                "source_role": None,
                "source_confidence": "NONE",
                "selection_reason": "no compatible source available",
                "selection_mode": "AUTOMATIC",
                "status": "SKIPPED",
                "requires_user_decision": True,
                "warnings": [
                    f"No unused {expected_role} POS source is available."
                ],
                "errors": [],
            }
            result["assignments"].append(assignment)
            result["warnings"].append(
                f"{target_node} has no proposed source and was set to NONE."
            )
            continue

        assignment_status = (
            "READY"
            if selected["discovery_status"] == "READY"
            else "REVIEW REQUIRED"
        )
        result["assignments"].append(
            {
                "slot_index": index,
                "slot": target_node,
                "target_node": target_node,
                "target_role": expected_role,
                "target_machine_ip": target.get("machine_ip"),
                "source_file": selected.get("file"),
                "source_path": selected.get("path"),
                "source_node": selected.get("node"),
                "source_role": selected.get("role"),
                "source_confidence": selected.get("confidence"),
                "selection_reason": reason,
                "selection_mode": "AUTOMATIC",
                "status": assignment_status,
                "requires_user_decision": (
                    assignment_status != "READY"
                ),
                "warnings": list(selected.get("warnings") or []),
                "errors": list(selected.get("errors") or []),
            }
        )

    result["extra_candidates"] = [
        {
            "file": source.get("file"),
            "path": source.get("path"),
            "role": source.get("role"),
            "node": source.get("node"),
            "confidence": source.get("confidence"),
            "decision": "PENDING",
            "status": "REVIEW REQUIRED",
        }
        for source in available
    ]

    if result["extra_candidates"]:
        result["warnings"].append(
            f"{len(result['extra_candidates'])} extra POS candidate(s) "
            "require Add or Ignore decision."
        )

    if any(
        assignment["status"] != "READY"
        for assignment in result["assignments"]
    ) or result["extra_candidates"]:
        result["status"] = "REVIEW REQUIRED"

    return result

def _normalize_itona_slot(
    value: Any,
) -> Optional[Dict[str, Any]]:
    """
    Normalize a configured Itona machine.

    Accepted examples:
        Itona1
        ITONA01
        itona_2
        Itona-3

    Returns:
        {
            "slot_index": 1,
            "slot": "Itona1",
        }

    Returns None when the value does not represent
    a supported Itona slot.
    """

    raw_value = _text(value)

    if not raw_value:
        return None

    match = re.fullmatch(
        r"ITONA[\s_.-]*0*(\d+)",
        raw_value,
        re.IGNORECASE,
    )

    if match is None:
        return None

    number = int(
        match.group(1)
    )

    if number < 1:
        return None

    return {
        "slot_index": number,
        "slot": f"Itona{number}",
    }


def _load_lab_itona_slots(
    config_path: str | Path,
) -> Dict[str, Any]:
    """
    Sprint 2.0.1

    Load Itona slots from the selected laboratory
    configuration.

    The laboratory field `kvs_machines` is now the
    source of truth for Builder Itona slots.

    No template folder or template XML is used.
    """

    result: Dict[str, Any] = {
        "status": "READY",
        "config_path": str(
            config_path
        ),
        "source": "LAB_CONFIG",
        "slots": [],
        "warnings": [],
        "errors": [],
    }

    try:
        config = load_lab_config(
            config_path
        )

    except (
        FileNotFoundError,
        ValueError,
        OSError,
    ) as error:

        result["status"] = "FAIL"

        result["errors"].append(
            "Unable to load laboratory configuration: "
            f"{error}"
        )

        return result

    configured_machines = (
        config.get(
            "kvs_machines"
        )
        or []
    )

    if not isinstance(
        configured_machines,
        list,
    ):
        result["status"] = "FAIL"

        result["errors"].append(
            "Laboratory configuration field "
            "'kvs_machines' must be a list."
        )

        return result

    normalized_slots: Dict[
        int,
        Dict[str, Any],
    ] = {}

    for configured_value in configured_machines:

        normalized = _normalize_itona_slot(
            configured_value
        )

        if normalized is None:
            result["warnings"].append(
                "Ignoring invalid Itona machine "
                "configured in laboratory JSON: "
                f"{configured_value!r}"
            )

            continue

        slot_index = normalized[
            "slot_index"
        ]

        if slot_index in normalized_slots:
            result["warnings"].append(
                "Duplicate Itona slot configured "
                "in laboratory JSON: "
                f"{normalized['slot']}"
            )

            continue

        normalized_slots[
            slot_index
        ] = {
            **normalized,
            "configured_value": str(
                configured_value
            ),
            "origin": "LAB_CONFIG",
        }

    result["slots"] = [
        normalized_slots[number]
        for number in sorted(
            normalized_slots
        )
    ]

    if not result["slots"]:
        result["status"] = "FAIL"

        result["errors"].append(
            "No valid Itona slots were found in "
            "the laboratory configuration field "
            "'kvs_machines'."
        )

    elif result["warnings"]:
        result["status"] = (
            "REVIEW REQUIRED"
        )

    return result

def _candidate_sort_key(
    candidate: Mapping[str, Any],
) -> Tuple[Any, ...]:
    """Rank normalized Itona candidates from safest to least suitable.

    Important: this function receives the normalized contract created by
    _normalize_itona_candidates, therefore it must read types, confidence and
    discovery_status instead of the original discovery field names.
    """
    status = _upper(
        candidate.get("discovery_status")
    ) or "REVIEW REQUIRED"
    confidence = _upper(
        candidate.get("confidence")
    ) or "NONE"
    types = [
        _upper(value)
        for value in candidate.get("types") or ["UNKNOWN"]
    ]

    has_unknown = not types or "UNKNOWN" in types
    is_ambiguous = len(types) > 1

    if has_unknown:
        quality_rank = 2
    elif is_ambiguous:
        quality_rank = 1
    else:
        quality_rank = 0

    services = candidate.get("kvs_services") or [""]

    return (
        quality_rank,
        STATUS_RANK.get(status, 99),
        CONFIDENCE_RANK.get(confidence, 99),
        _natural_key(services[0]),
        _natural_key(candidate.get("file")),
    )


def _normalize_itona_candidates(
    candidates: Iterable[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []

    for candidate in candidates:
        file_name = _upper(candidate.get("file"))
        if file_name.startswith("_SC_"):
            continue

        types = [
            _upper(value)
            for value in candidate.get("kvs_types") or ["UNKNOWN"]
        ]
        normalized.append(
            {
                "file": candidate.get("file"),
                "path": candidate.get("path"),
                "types": types,
                "confidence": _upper(
                    candidate.get("type_confidence")
                ) or "NONE",
                "discovery_status": _upper(
                    candidate.get("type_status")
                ) or "REVIEW REQUIRED",
                "kvs_services": list(
                    candidate.get("kvs_services") or []
                ),
                "npw_services": list(
                    candidate.get("npw_services") or []
                ),
                "browser_nodes": list(
                    candidate.get("browser_nodes") or []
                ),
                "warnings": list(candidate.get("warnings") or []),
                "errors": list(candidate.get("errors") or []),
            }
        )

    return sorted(normalized, key=_candidate_sort_key)



def build_itona_assignment_proposal(
    config_path,
    discovered_candidates,
):
    """
    Sprint 2.0.1

    Itona slots come from:
        config/<lab>_lab.json
        -> kvs_machines

    No template dependency.
    """

    result = {
        "status": "READY",
        "config_path": str(config_path),
        "slot_source": "LAB_CONFIG",
        "generation_mode": "FROM_SCRATCH",
        "assignments": [],
        "extra_candidates": [],
        "warnings": [],
        "errors": [],
    }

    slot_result = _load_lab_itona_slots(
        config_path
    )

    result["warnings"].extend(
        slot_result.get("warnings", [])
    )

    result["errors"].extend(
        slot_result.get("errors", [])
    )

    if result["errors"]:
        result["status"] = "FAIL"
        return result

    slots = slot_result.get(
        "slots",
        []
    )

    candidates = (
        _normalize_itona_candidates(
            discovered_candidates
        )
    )

    slot_count = len(slots)

    selected = candidates[:slot_count]
    extras = candidates[slot_count:]

    for index, slot in enumerate(slots):

        candidate = (
            selected[index]
            if index < len(selected)
            else None
        )

        slot_name = slot["slot"]

        if candidate is None:

            result["assignments"].append(
                {
                    "slot_index": slot["slot_index"],
                    "slot": slot_name,
                    "output_file": f"_{slot_name}_pos-db.xml",
                    "source_file": None,
                    "source_files": [],
                    "source_path": None,
                    "source_paths": [],
                    "source_types": [],
                    "source_confidence": "NONE",
                    "kvs_services": [],
                    "selection_reason": "no candidate available",
                    "selection_mode": "AUTOMATIC",
                    "status": "SKIPPED",
                    "requires_user_decision": True,
                    "origin": "LAB_CONFIG",
                    "warnings": [
                        f"No KVS candidate available for {slot_name}"
                    ],
                    "errors": [],
                }
            )

            continue

        candidate_is_safe = (
            candidate["discovery_status"] == "READY"
            and candidate["confidence"] in ["HIGH", "MEDIUM"]
            and len(candidate["types"]) == 1
            and candidate["types"][0] != "UNKNOWN"
        )

        assignment_status = (
            "READY"
            if candidate_is_safe
            else "REVIEW REQUIRED"
        )

        source_file = candidate.get(
            "file"
        )

        source_path = candidate.get(
            "path"
        )

        result["assignments"].append(
            {
                "slot_index": slot["slot_index"],
                "slot": slot_name,
                "output_file": f"_{slot_name}_pos-db.xml",
                "source_file": source_file,
                "source_files": (
                    [source_file]
                    if source_file
                    else []
                ),
                "source_path": source_path,
                "source_paths": (
                    [source_path]
                    if source_path
                    else []
                ),
                "source_types": list(
                    candidate.get(
                        "types",
                        [],
                    )
                ),
                "source_confidence": candidate.get(
                    "confidence"
                ),
                "kvs_services": list(
                    candidate.get(
                        "kvs_services",
                        [],
                    )
                ),
                "selection_reason": (
                    "highest ranked available Itona candidate"
                ),
                "selection_mode": "AUTOMATIC",
                "status": assignment_status,
                "requires_user_decision": not candidate_is_safe,
                "origin": "LAB_CONFIG",
                "warnings": list(
                    candidate.get(
                        "warnings",
                        [],
                    )
                ),
                "errors": list(
                    candidate.get(
                        "errors",
                        [],
                    )
                ),
            }
        )

    result["extra_candidates"] = []

    for candidate in extras:

        result["extra_candidates"].append(
            {
                "file": candidate.get(
                    "file"
                ),
                "path": candidate.get(
                    "path"
                ),
                "types": list(
                    candidate.get(
                        "types",
                        [],
                    )
                ),
                "confidence": candidate.get(
                    "confidence"
                ),
                "kvs_services": list(
                    candidate.get(
                        "kvs_services",
                        [],
                    )
                ),
                "decision": "UNASSIGNED_BY_LAB_LIMIT",
                "status": "UNASSIGNED",
            }
        )

    if extras:
        result["warnings"].append(
            f"{len(extras)} extra Itona candidate(s) found."
        )

    if any(
        assignment["status"] != "READY"
        for assignment in result["assignments"]
    ):
        result["status"] = "REVIEW REQUIRED"

    return result

def build_assignment_proposal(
    context,
):
    """
    Sprint 2.0.1

    Assignment proposal without
    template dependency.
    """

    missing = []

    if not context.config_path:
        missing.append(
            "config_path"
        )

    if missing:

        proposal = {
            "status": "FAIL",
            "generation_mode": "FROM_SCRATCH",
            "pos": {},
            "itonas": {},
            "warnings": [],
            "errors": [
                "Assignment proposal cannot start. Missing: "
                + ", ".join(missing)
            ],
        }

        context.proposed_pos_mapping = {}
        context.proposed_itona_mapping = {}

        context.errors.extend(
            proposal["errors"]
        )

        return proposal

    pos_proposal = (
        build_pos_assignment_proposal(
            discovered_pos=(
                context.discovered_pos
                or {}
            ),
            config_path=context.config_path,
        )
    )

    itona_proposal = (
        build_itona_assignment_proposal(
            config_path=context.config_path,
            discovered_candidates=(
                context.discovered_itona_candidates
                or []
            ),
        )
    )

    context.proposed_pos_mapping = (
        pos_proposal
    )

    context.proposed_itona_mapping = (
        itona_proposal
    )

    warnings = list(
        pos_proposal.get(
            "warnings",
            [],
        )
    )

    warnings.extend(
        itona_proposal.get(
            "warnings",
            [],
        )
    )

    errors = list(
        pos_proposal.get(
            "errors",
            [],
        )
    )

    errors.extend(
        itona_proposal.get(
            "errors",
            [],
        )
    )

    if errors:
        status = "FAIL"

    elif (
        pos_proposal.get("status")
        != "READY"
        or
        itona_proposal.get("status")
        != "READY"
    ):
        status = "REVIEW REQUIRED"

    else:
        status = "READY"

    context.warnings.extend(
        warnings
    )

    context.errors.extend(
        errors
    )

    context.warnings = list(
        dict.fromkeys(
            context.warnings
        )
    )

    context.errors = list(
        dict.fromkeys(
            context.errors
        )
    )

    return {
        "status": status,
        "generation_mode": "FROM_SCRATCH",
        "slot_source": "LAB_CONFIG",
        "pos": pos_proposal,
        "itonas": itona_proposal,
        "warnings": list(
            dict.fromkeys(
                warnings
            )
        ),
        "errors": list(
            dict.fromkeys(
                errors
            )
        ),
    }