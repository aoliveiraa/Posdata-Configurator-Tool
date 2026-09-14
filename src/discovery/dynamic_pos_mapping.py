"""
Dynamic POS mapping.

Selects discovered POS source files for the logical POS nodes configured in a
laboratory JSON. Selection is role-aware, deterministic and market agnostic.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional


SUPPORTED_ROLES = ("FC", "DT")


def load_lab_pos_targets(config_path: str | Path) -> Dict:
    """Reads logical POS targets and roles from the selected lab JSON."""
    path = Path(config_path)

    result = {
        "targets": [],
        "warnings": [],
        "errors": [],
    }

    if not path.is_file():
        result["errors"].append(
            f"Lab configuration file was not found: {path}"
        )
        return result

    try:
        with path.open("r", encoding="utf-8") as file:
            config = json.load(file)
    except json.JSONDecodeError as error:
        result["errors"].append(
            f"Lab configuration JSON is invalid: {error}"
        )
        return result
    except OSError as error:
        result["errors"].append(
            f"Unable to read lab configuration: {error}"
        )
        return result

    pos_roles = config.get("pos_roles", {})

    reference_files = {}

    for item in config.get(
        "reference_pos_files",
        []
    ):
        node = str(
            item.get(
                "target_node",
                ""
            )
        ).strip().upper()

        filename = item.get(
            "source_file"
        )

        if node and filename:
            reference_files[node] = filename

    if not isinstance(pos_roles, dict):
        result["errors"].append(
            "pos_roles must be an object in the lab configuration."
        )
        return result

    seen_nodes = set()

    for role in SUPPORTED_ROLES:
        role_targets = pos_roles.get(role, [])

        if not isinstance(role_targets, list):
            result["errors"].append(
                f"pos_roles.{role} must be a list."
            )
            continue

        for target in role_targets:
            if not isinstance(target, dict):
                result["warnings"].append(
                    f"Invalid {role} target entry was ignored: {target}"
                )
                continue

            node = str(target.get("logical_machine", "")).strip().upper()
            machine_ip = str(target.get("ip", "")).strip()

            if not node:
                result["warnings"].append(
                    f"A {role} target without logical_machine was ignored."
                )
                continue

            if node in seen_nodes:
                result["errors"].append(
                    f"Logical target node is duplicated in lab config: {node}"
                )
                continue

            seen_nodes.add(node)

            result["targets"].append(
                {
                    "target_node": node,
                    "expected_role": role,
                    "machine_ip": machine_ip or None,
                    "output_file": (
                        reference_files.get(node)
                    ),
                }
            )

    if not result["targets"]:
        result["errors"].append(
            "No valid POS targets were found in pos_roles."
        )

    return result
    


def _source_node_number(source: Dict) -> int:
    """Returns the first source node number for deterministic ordering."""
    candidates = source.get("node_candidates", [])

    if candidates:
        node = str(candidates[0]).upper()
        suffix = node[3:]
        if suffix.isdigit():
            return int(suffix)

    return 10**9


def _source_sort_key(source: Dict) -> tuple:
    return (
        _source_node_number(source),
        str(source.get("file", "")).upper(),
    )


def _group_sources_by_role(discovered_pos_files: List[Dict]) -> Dict[str, List[Dict]]:
    grouped = {role: [] for role in SUPPORTED_ROLES}

    for source in discovered_pos_files:
        role = str(source.get("role") or "").strip().upper()
        if role in grouped:
            grouped[role].append(source)

    for role in grouped:
        grouped[role] = sorted(grouped[role], key=_source_sort_key)

    return grouped


def _select_exact_node_match(
    available_sources: List[Dict],
    target_node: str,
) -> Optional[Dict]:
    """Prefers a source carrying the same logical node as the lab target."""
    normalized_target = target_node.upper()

    for source in available_sources:
        candidates = [
            str(node).upper()
            for node in source.get("node_candidates", [])
        ]
        if normalized_target in candidates:
            return source

    return None


def build_dynamic_pos_mapping(
    discovery_result: Dict,
    config_path: str | Path = "config/rio_lab.json",
    prefer_exact_node: bool = True,
) -> Dict:
    """
    Maps discovered market POS sources to laboratory logical POS targets.

    Selection rules:
    1. Respect the role required by the lab target.
    2. Prefer a source with the same logical node when roles also match.
    3. Otherwise select the lowest available source node number.
    4. Never reuse a source file.
    5. Return REVIEW REQUIRED when the market does not provide enough sources.
    """
    result = {
        "status": "READY",
        "config_path": str(config_path),
        "mappings": [],
        "unused_sources": [],
        "warnings": [],
        "errors": [],
    }

    if discovery_result.get("status") == "FAIL":
        result["status"] = "FAIL"
        result["errors"].extend(discovery_result.get("errors", []))
        return result

    discovered_sources = list(discovery_result.get("pos_files", []))

    if not discovered_sources:
        result["status"] = "FAIL"
        result["errors"].append(
            "Dynamic POS discovery did not return any POS source files."
        )
        return result

    target_result = load_lab_pos_targets(config_path)
    result["warnings"].extend(target_result["warnings"])
    result["errors"].extend(target_result["errors"])

    if target_result["errors"]:
        result["status"] = "FAIL"
        return result

    grouped_sources = _group_sources_by_role(discovered_sources)
    used_paths = set()

    for target in target_result["targets"]:
        target_node = target["target_node"]
        expected_role = target["expected_role"]

        available_sources = [
            source
            for source in grouped_sources.get(expected_role, [])
            if source.get("path") not in used_paths
        ]

        selected_source = None
        selection_reason = None

        if prefer_exact_node:
            selected_source = _select_exact_node_match(
                available_sources,
                target_node,
            )
            if selected_source is not None:
                selection_reason = "exact node and role match"

        if selected_source is None and available_sources:
            selected_source = available_sources[0]
            selection_reason = "first available source with required role"

        if selected_source is None:
            result["mappings"].append(
                {
                    "target_node": target_node,
                    "expected_role": expected_role,
                    "machine_ip": target.get("machine_ip"),
                    "source_file": None,
                    "source_path": None,
                    "source_node": None,
                    "source_role": None,
                    "selection_reason": None,
                    "status": "MISSING",
                    "warnings": [
                        f"No unused {expected_role} POS source is available."
                    ],
                    "errors": [],
                            "output_file": target.get(
                    "output_file"
                ),
                }
            )
            source_nodes = selected_source.get(
                "node_candidates",
                []
            )

            source_node = (
                source_nodes[0]
                if source_nodes
                else None
            )

            source_path = selected_source.get(
                "path"
            )

            used_paths.add(source_path)

            result["warnings"].append(
                f"No unused {expected_role} POS source is available "
                f"for target {target_node}."
            )
            continue

        source_nodes = selected_source.get("node_candidates", [])
        source_node = source_nodes[0] if source_nodes else None
        source_path = selected_source.get("path")

        used_paths.add(source_path)

        result["mappings"].append(
            {
                "target_node": target_node,

                "expected_role": expected_role,

                "machine_ip": target.get(
                    "machine_ip"
                ),

                "output_file": target.get(
                    "output_file"
                ),

                "source_file": selected_source.get(
                    "file"
                ),

                "source_path": source_path,

                "source_node": source_node,

                "source_role": selected_source.get(
                    "role"
                ),

                "selection_reason":
                    selection_reason,

                "status": "READY",

                "warnings": list(
                    selected_source.get(
                        "warnings",
                        []
                    )
                ),

                "errors": list(
                    selected_source.get(
                        "errors",
                        []
                    )
                ),
            }
        )

    result["unused_sources"] = [
        {
            "file": source.get("file"),
            "path": source.get("path"),
            "role": source.get("role"),
            "node_candidates": list(source.get("node_candidates", [])),
        }
        for source in discovered_sources
        if source.get("path") not in used_paths
    ]

    missing_mappings = [
        mapping
        for mapping in result["mappings"]
        if mapping["status"] != "READY"
    ]

    if result["errors"]:
        result["status"] = "FAIL"
    elif missing_mappings:
        result["status"] = "REVIEW REQUIRED"

    return result


def to_legacy_reference_pos_files(mapping_result: Dict) -> List[Dict]:
    """
    Converts READY mappings to the existing reference_pos_files contract.

    Existing code can consume:
        source_file
        target_node
    """
    return [
        {
            "source_file": mapping["source_file"],
            "target_node": mapping["target_node"],
        }
        for mapping in mapping_result.get("mappings", [])
        if mapping.get("status") == "READY"
    ]
