"""Manual confirmation rules for PosData Builder assignments.

Sprint 1.5.2 changes:
- POS candidates are no longer limited by the role configured for a lab slot.
- Any discovered POS can be placed in any available POS target.
- The selected source role becomes the effective role of that target.
- The original laboratory role is retained in expected_role for traceability.
- A POS listed as extra is automatically considered assigned when selected in a slot.
- Each Itona accepts at most two KVS files.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, Mapping, Sequence

NONE_VALUE = "NONE"
MAX_KVS_PER_ITONA = 2
VALID_EXTRA_DECISIONS = {"ADD", "IGNORE"}


def _upper(value: Any) -> str:
    return str(value or "").strip().upper()


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def build_pos_candidate_index(
    discovered_pos: Mapping[str, Any],
) -> Dict[str, Dict[str, Any]]:
    return {
        str(item.get("file")): dict(item)
        for item in discovered_pos.get("pos_files") or []
        if item.get("file")
    }


def available_pos_options(
    discovered_pos: Mapping[str, Any],
) -> list[str]:
    """Return every discovered POS, regardless of FC/DT classification."""
    names = [
        str(item.get("file"))
        for item in discovered_pos.get("pos_files") or []
        if item.get("file")
    ]
    return [NONE_VALUE, *sorted(names)]


def compatible_pos_options(
    discovered_pos: Mapping[str, Any],
    target_role: str | None = None,
) -> list[str]:
    """Backward-compatible alias with no role filtering.

    target_role is intentionally ignored. The role shown by the laboratory is
    now a suggestion only, not a validation boundary.
    """
    return available_pos_options(discovered_pos)


def confirm_pos_assignments(
    context: Any,
    slot_selections: Mapping[str, str],
    extra_decisions: Mapping[str, str] | None = None,
) -> Dict[str, Any]:
    """Validate and store manual POS assignments.

    Business rules:
    - any discovered POS can occupy any target POS slot;
    - one source cannot be assigned to two slots;
    - NONE is allowed and becomes SKIPPED;
    - source role becomes target_role/effective_role;
    - original lab role is retained as expected_role;
    - an extra candidate selected in a target is automatically ASSIGNED;
    - an unassigned extra candidate still requires ADD or IGNORE.
    """
    extra_decisions = extra_decisions or {}
    proposal = deepcopy(context.proposed_pos_mapping or {})
    assignments = proposal.get("assignments") or []
    extras = proposal.get("extra_candidates") or []
    candidate_index = build_pos_candidate_index(context.discovered_pos or {})

    result: Dict[str, Any] = {
        "status": "READY",
        "assignments": [],
        "extra_candidates": [],
        "warnings": [],
        "errors": [],
    }
    used_sources: set[str] = set()

    for proposed in assignments:
        target_node = str(proposed.get("target_node") or "")
        expected_role = _upper(
            proposed.get("expected_role") or proposed.get("target_role")
        )
        selected = str(
            slot_selections.get(
                target_node,
                proposed.get("source_file") or NONE_VALUE,
            )
        ).strip() or NONE_VALUE

        confirmed = deepcopy(proposed)
        confirmed["selection_mode"] = "MANUAL"
        confirmed["expected_role"] = expected_role

        if _upper(selected) == NONE_VALUE:
            confirmed.update({
                "source_file": None,
                "source_path": None,
                "source_node": None,
                "source_role": None,
                "source_confidence": "NONE",
                "effective_role": None,
                "selection_reason": "user selected NONE",
                "status": "SKIPPED",
                "requires_user_decision": False,
                "warnings": [f"{target_node} was skipped by the user."],
                "errors": [],
            })
            result["assignments"].append(confirmed)
            result["warnings"].append(f"{target_node} will be skipped.")
            continue

        source = candidate_index.get(selected)
        if source is None:
            result["errors"].append(
                f"Selected POS source was not discovered: {selected}"
            )
            continue

        if selected in used_sources:
            result["errors"].append(
                f"POS source cannot be reused: {selected}"
            )
            continue

        used_sources.add(selected)
        source_role = _upper(source.get("role")) or "UNKNOWN"
        nodes = source.get("node_candidates") or []
        role_changed = (
            expected_role
            and source_role != "UNKNOWN"
            and source_role != expected_role
        )
        warnings = list(source.get("warnings") or [])
        if role_changed:
            warning = (
                f"{target_node} was configured as {source_role} instead of "
                f"the laboratory suggestion {expected_role}."
            )
            warnings.append(warning)
            result["warnings"].append(warning)

        confirmed.update({
            "source_file": selected,
            "source_path": source.get("path"),
            "source_node": nodes[0] if nodes else None,
            "source_role": source_role,
            "source_confidence": source.get("role_confidence") or "NONE",
            "target_role": source_role,
            "effective_role": source_role,
            "role_changed_from_lab_suggestion": role_changed,
            "selection_reason": "user confirmed assignment",
            "status": "READY WITH OBSERVATION" if role_changed else "READY",
            "requires_user_decision": False,
            "warnings": warnings,
            "errors": list(source.get("errors") or []),
        })
        result["assignments"].append(confirmed)

    extra_files = {
        str(item.get("file") or "")
        for item in extras
        if item.get("file")
    }

    # Include every discovered but currently unused POS as an extra candidate,
    # even if it was not part of the original automatic proposal extras.
    all_unassigned = [
        file_name
        for file_name in candidate_index
        if file_name not in used_sources
    ]
    extra_files.update(all_unassigned)

    original_extra_index = {
        str(item.get("file")): item
        for item in extras
        if item.get("file")
    }

    for file_name in sorted(extra_files):
        source = candidate_index.get(file_name, {})
        confirmed_extra = deepcopy(
            original_extra_index.get(file_name)
            or {
                "file": file_name,
                "path": source.get("path"),
                "role": source.get("role"),
                "node": (source.get("node_candidates") or [None])[0],
                "confidence": source.get("role_confidence"),
            }
        )

        if file_name in used_sources:
            confirmed_extra.update({
                "decision": "USED_IN_SLOT",
                "status": "ASSIGNED",
            })
            result["extra_candidates"].append(confirmed_extra)
            continue

        decision = _upper(extra_decisions.get(file_name))
        if decision not in VALID_EXTRA_DECISIONS:
            result["errors"].append(
                f"Unassigned POS requires ADD or IGNORE decision: {file_name}"
            )
            confirmed_extra.update({
                "decision": "PENDING",
                "status": "REVIEW REQUIRED",
            })
        else:
            confirmed_extra["decision"] = decision
            confirmed_extra["status"] = (
                "REVIEW REQUIRED" if decision == "ADD" else "IGNORED"
            )
            if decision == "ADD":
                result["warnings"].append(
                    f"{file_name} was marked ADD and still needs a free lab POS slot."
                )
        result["extra_candidates"].append(confirmed_extra)

    if result["errors"]:
        result["status"] = "FAIL"
    elif any(
        item.get("status") == "REVIEW REQUIRED"
        for item in result["extra_candidates"]
    ):
        result["status"] = "REVIEW REQUIRED"
    elif any(
        item.get("status") == "SKIPPED"
        for item in result["assignments"]
    ):
        result["status"] = "READY WITH SKIPS"
    elif any(
        item.get("status") == "READY WITH OBSERVATION"
        for item in result["assignments"]
    ):
        result["status"] = "READY WITH OBSERVATIONS"

    context.confirmed_pos_mapping = result
    return result


def build_itona_candidate_index(
    candidates: Iterable[Mapping[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for item in candidates:
        file_name = str(item.get("file") or "")
        if not file_name or _upper(file_name).startswith("_SC_"):
            continue
        result[file_name] = dict(item)
    return result


def itona_candidate_display(candidate: Mapping[str, Any]) -> str:
    types = ", ".join(candidate.get("kvs_types") or ["UNKNOWN"])
    services = ", ".join(candidate.get("kvs_services") or ["NONE"])
    return f"{candidate.get('file')} | {types} | Services: {services}"


def initial_itona_selections(
    proposal: Mapping[str, Any],
) -> Dict[str, list[str]]:
    result: Dict[str, list[str]] = {}
    for assignment in proposal.get("assignments") or []:
        slot = str(assignment.get("slot") or "")
        existing = assignment.get("source_files") or []
        if not existing and assignment.get("source_file"):
            existing = [assignment["source_file"]]
        result[slot] = list(existing)[:MAX_KVS_PER_ITONA]
    return result


def confirm_itona_assignments(
    context: Any,
    slot_selections: Mapping[str, Sequence[str]],
) -> Dict[str, Any]:
    proposal = deepcopy(context.proposed_itona_mapping or {})
    candidate_index = build_itona_candidate_index(
        context.discovered_itona_candidates or []
    )
    result = {
        "status": "READY",
        "assignments": [],
        "extra_candidates": [],
        "warnings": [],
        "errors": [],
    }
    used_by: Dict[str, str] = {}

    for proposed in proposal.get("assignments") or []:
        slot = str(proposed.get("slot") or "")
        selected = _unique(
            str(value).strip()
            for value in slot_selections.get(slot, [])
        )
        confirmed = deepcopy(proposed)
        confirmed["selection_mode"] = "MANUAL"

        if len(selected) > MAX_KVS_PER_ITONA:
            result["errors"].append(
                f"{slot} supports a maximum of {MAX_KVS_PER_ITONA} KVS assignments."
            )
            continue

        if not selected:
            confirmed.update({
                "source_file": None,
                "source_path": None,
                "source_files": [],
                "source_paths": [],
                "source_types": [],
                "kvs_services": [],
                "selection_reason": "user selected no KVS",
                "status": "SKIPPED",
                "requires_user_decision": False,
                "warnings": [f"{slot} was configured without KVS sources."],
                "errors": [],
            })
            result["assignments"].append(confirmed)
            result["warnings"].append(f"{slot} will be skipped.")
            continue

        candidates: list[Dict[str, Any]] = []
        slot_errors: list[str] = []
        for file_name in selected:
            candidate = candidate_index.get(file_name)
            if candidate is None:
                slot_errors.append(
                    f"{slot}: selected KVS was not discovered: {file_name}"
                )
                continue
            if file_name in used_by:
                slot_errors.append(
                    f"{file_name} is already assigned to {used_by[file_name]} "
                    f"and cannot also be assigned to {slot}."
                )
                continue
            candidates.append(candidate)

        if slot_errors:
            result["errors"].extend(slot_errors)
            continue

        for file_name in selected:
            used_by[file_name] = slot

        all_types = _unique(
            _upper(value)
            for candidate in candidates
            for value in (candidate.get("kvs_types") or ["UNKNOWN"])
        )
        all_services = _unique(
            str(value)
            for candidate in candidates
            for value in (candidate.get("kvs_services") or [])
        )
        observations: list[str] = []
        for candidate in candidates:
            types = [
                _upper(value)
                for value in candidate.get("kvs_types") or ["UNKNOWN"]
            ]
            if "UNKNOWN" in types:
                observations.append(
                    f"{candidate.get('file')} has UNKNOWN type but was explicitly selected."
                )
            elif len(types) > 1:
                observations.append(
                    f"{candidate.get('file')} has multiple detected types: "
                    f"{', '.join(types)}."
                )

        confirmed.update({
            "source_file": selected[0],
            "source_path": candidates[0].get("path"),
            "source_files": selected,
            "source_paths": [candidate.get("path") for candidate in candidates],
            "source_types": all_types,
            "kvs_services": all_services,
            "selection_reason": "user confirmed one or more KVS sources",
            "status": "READY WITH OBSERVATIONS" if observations else "READY",
            "requires_user_decision": False,
            "warnings": observations,
            "errors": [],
        })
        result["assignments"].append(confirmed)
        result["warnings"].extend(
            f"{slot}: {note}" for note in observations
        )

    assigned_files = set(used_by)
    result["extra_candidates"] = [
        {
            "file": file_name,
            "types": list(candidate.get("kvs_types") or ["UNKNOWN"]),
            "kvs_services": list(candidate.get("kvs_services") or []),
            "status": "UNASSIGNED",
        }
        for file_name, candidate in candidate_index.items()
        if file_name not in assigned_files
    ]

    if result["errors"]:
        result["status"] = "FAIL"
    elif any(
        item.get("status") == "SKIPPED"
        for item in result["assignments"]
    ):
        result["status"] = "READY WITH SKIPS"
    elif any(
        item.get("status") == "READY WITH OBSERVATIONS"
        for item in result["assignments"]
    ):
        result["status"] = "READY WITH OBSERVATIONS"

    context.confirmed_itona_mapping = result
    return result
