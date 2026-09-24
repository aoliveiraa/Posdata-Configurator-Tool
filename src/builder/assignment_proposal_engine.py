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


def _extract_itona_number(value: Any) -> Optional[int]:
    match = re.search(r"ITONA[\s_.-]*(\d+)", _upper(value))
    return int(match.group(1)) if match else None


def _discover_template_itona_slots(
    template_folder: str | Path,
) -> Dict[str, Any]:
    folder = Path(template_folder)
    result: Dict[str, Any] = {
        "status": "READY",
        "slots": [],
        "warnings": [],
        "errors": [],
    }

    if not folder.is_dir():
        result["status"] = "FAIL"
        result["errors"].append(
            f"Template folder was not found: {folder}"
        )
        return result

    by_number: Dict[int, Path] = {}
    duplicates: Dict[int, List[str]] = {}

    for path in sorted(folder.glob("*_pos-db.xml")):
        number = _extract_itona_number(path.name)
        if number is None:
            continue
        if number in by_number:
            duplicates.setdefault(number, [by_number[number].name]).append(
                path.name
            )
            continue
        by_number[number] = path

    for number, path in sorted(by_number.items()):
        result["slots"].append(
            {
                "slot_index": number,
                "slot": f"Itona{number}",
                "template_file": path.name,
                "template_path": str(path),
            }
        )

    for number, files in duplicates.items():
        result["warnings"].append(
            f"Duplicate template files for Itona{number}: "
            + ", ".join(files)
        )

    if not result["slots"]:
        result["status"] = "FAIL"
        result["errors"].append(
            "No Itona slots were found in the selected template."
        )
    elif result["warnings"]:
        result["status"] = "REVIEW REQUIRED"

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
    template_folder: str | Path,
    discovered_candidates: Iterable[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Assign ranked market KVS candidates to template Itona slots."""
    result: Dict[str, Any] = {
        "status": "READY",
        "template_folder": str(template_folder),
        "assignments": [],
        "extra_candidates": [],
        "warnings": [],
        "errors": [],
    }

    slot_result = _discover_template_itona_slots(template_folder)
    result["warnings"].extend(slot_result.get("warnings") or [])
    result["errors"].extend(slot_result.get("errors") or [])

    if result["errors"]:
        result["status"] = "FAIL"
        return result

    candidates = _normalize_itona_candidates(discovered_candidates)
    slot_count = len(slot_result["slots"])
    selected = candidates[:slot_count]
    extras = candidates[slot_count:]

    for position, slot in enumerate(slot_result["slots"]):
        candidate = selected[position] if position < len(selected) else None

        if candidate is None:
            result["assignments"].append(
                {
                    **slot,
                    "source_file": None,
                    "source_path": None,
                    "source_types": [],
                    "source_confidence": "NONE",
                    "kvs_services": [],
                    "selection_reason": "no candidate available",
                    "selection_mode": "AUTOMATIC",
                    "status": "SKIPPED",
                    "requires_user_decision": True,
                    "warnings": [
                        f"No Itona candidate is available for {slot['slot']}."
                    ],
                    "errors": [],
                }
            )
            continue

        candidate_is_safe = (
            candidate["discovery_status"] == "READY"
            and candidate["confidence"] in {"HIGH", "MEDIUM"}
            and len(candidate["types"]) == 1
            and candidate["types"][0] != "UNKNOWN"
        )

        result["assignments"].append(
            {
                **slot,
                "source_file": candidate.get("file"),
                "source_path": candidate.get("path"),
                "source_types": list(candidate.get("types") or []),
                "source_confidence": candidate.get("confidence"),
                "kvs_services": list(
                    candidate.get("kvs_services") or []
                ),
                "selection_reason": (
                    "highest ranked available Itona candidate"
                ),
                "selection_mode": "AUTOMATIC",
                "status": (
                    "READY" if candidate_is_safe else "REVIEW REQUIRED"
                ),
                "requires_user_decision": not candidate_is_safe,
                "warnings": list(candidate.get("warnings") or []),
                "errors": list(candidate.get("errors") or []),
            }
        )

    result["extra_candidates"] = [
        {
            "file": candidate.get("file"),
            "path": candidate.get("path"),
            "types": list(candidate.get("types") or []),
            "confidence": candidate.get("confidence"),
            "kvs_services": list(
                candidate.get("kvs_services") or []
            ),
            "decision": "IGNORED_BY_TEMPLATE_LIMIT",
            "status": "IGNORED",
        }
        for candidate in extras
    ]

    if extras:
        result["warnings"].append(
            f"{len(extras)} Itona candidate(s) were ignored because "
            "the template slot limit was reached."
        )

    if any(
        assignment["status"] != "READY"
        for assignment in result["assignments"]
    ):
        result["status"] = "REVIEW REQUIRED"
    elif slot_result["status"] != "READY":
        result["status"] = "REVIEW REQUIRED"

    return result


def build_assignment_proposal(
    context: Any,
) -> Dict[str, Any]:
    """Build and store POS and Itona proposals in BuilderContext."""
    missing: List[str] = []
    if not context.config_path:
        missing.append("config_path")
    if not context.template_folder:
        missing.append("template_folder")

    if missing:
        proposal = {
            "status": "FAIL",
            "pos": {},
            "itonas": {},
            "warnings": [],
            "errors": [
                "Assignment proposal cannot start. Missing context values: "
                + ", ".join(missing)
            ],
        }
        context.proposed_pos_mapping = {}
        context.proposed_itona_mapping = {}
        context.errors.extend(proposal["errors"])
        return proposal

    pos_proposal = build_pos_assignment_proposal(
        discovered_pos=context.discovered_pos or {},
        config_path=context.config_path,
    )
    itona_proposal = build_itona_assignment_proposal(
        template_folder=context.template_folder,
        discovered_candidates=(
            context.discovered_itona_candidates or []
        ),
    )

    context.proposed_pos_mapping = pos_proposal
    context.proposed_itona_mapping = itona_proposal

    warnings = list(pos_proposal.get("warnings") or [])
    warnings.extend(itona_proposal.get("warnings") or [])
    errors = list(pos_proposal.get("errors") or [])
    errors.extend(itona_proposal.get("errors") or [])

    if errors:
        status = "FAIL"
    elif (
        pos_proposal.get("status") != "READY"
        or itona_proposal.get("status") != "READY"
    ):
        status = "REVIEW REQUIRED"
    else:
        status = "READY"

    context.warnings.extend(warnings)
    context.errors.extend(errors)
    context.warnings = list(dict.fromkeys(context.warnings))
    context.errors = list(dict.fromkeys(context.errors))

    return {
        "status": status,
        "pos": pos_proposal,
        "itonas": itona_proposal,
        "warnings": list(dict.fromkeys(warnings)),
        "errors": list(dict.fromkeys(errors)),
    }
