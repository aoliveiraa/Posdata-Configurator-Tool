from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Mapping, Optional
import warnings


@dataclass(frozen=True)
class MachineResolution:
    node: str
    current_machine_file: Optional[str]
    current_machine_ip: Optional[str]
    target_machine_ip: Optional[str]
    output_file: Optional[str]
    source: str
    status: str
    warnings: List[str]
    errors: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def normalize_pos_node(value: Any) -> Optional[str]:
    """Normalize POS node aliases such as POS1, POS01 and POS0001."""
    if value is None:
        return None

    text = str(value).strip().upper()
    if not text.startswith("POS"):
        return None

    suffix = text[3:]
    if not suffix.isdigit():
        return None

    return f"POS{int(suffix):04d}"


def build_current_machine_by_node(
    current_machines: Iterable[Mapping[str, Any]],
) -> Dict[str, Mapping[str, Any]]:
    """
    Build a node-based current-machine lookup.

    No laboratory IP is used as a lookup key. Duplicate nodes are rejected
    because silently choosing one physical machine can generate a wrong POS.
    """
    grouped: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)

    for machine in current_machines:
        node = normalize_pos_node(
            machine.get("node")
            or machine.get("logical_node")
            or machine.get("pos_node")
            or machine.get("detected_node")        )
        if node:
            grouped[node].append(machine)

    lookup: Dict[str, Mapping[str, Any]] = {}
    for node, matches in grouped.items():
        if len(matches) == 1:
            lookup[node] = matches[0]

    return lookup


def _duplicates_by_node(
    current_machines: Iterable[Mapping[str, Any]],
) -> Dict[str, List[Mapping[str, Any]]]:
    grouped: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for machine in current_machines:
        node = normalize_pos_node(
            machine.get("node")
            or machine.get("logical_node")
            or machine.get("pos_node")
            or machine.get("detected_node")        )
        if node:
            grouped[node].append(machine)
    return {node: values for node, values in grouped.items() if len(values) > 1}

def resolve_machine_for_target(
    target: Mapping[str, Any],
    current_machines: Iterable[Mapping[str, Any]],
) -> Dict[str, Any]:

    machines = list(current_machines)

    node = normalize_pos_node(
        target.get("node")
        or target.get("logical_node")
        or target.get("pos_node")
    )

    target_ip = (
        target.get("target_machine_ip")
        or target.get("machine_ip")
        or target.get("ip")
    )

    output_file = (
        target.get("output_file")
        or target.get("target_file")
    )

    if not node:
        return MachineResolution(
            node=str(target.get("node") or ""),
            current_machine_file=None,
            current_machine_ip=None,
            target_machine_ip=target_ip,
            output_file=output_file,
            source="logical_node",
            status="MISSING",
            warnings=[],
            errors=[
                "Target POS logical node is missing or invalid."
            ],
        ).to_dict()

    duplicates = _duplicates_by_node(machines)

    if node in duplicates:

        names = [
            str(
                item.get("file")
                or item.get("machine_file")
                or "<unknown>"
            )
            for item in duplicates[node]
        ]

        return MachineResolution(
            node=node,
            current_machine_file=None,
            current_machine_ip=None,
            target_machine_ip=target_ip,
            output_file=output_file,
            source="logical_node",
            status="REVIEW REQUIRED",
            warnings=[
                f"Duplicate current machines for {node}: "
                f"{', '.join(names)}"
            ],
            errors=[],
        ).to_dict()

    current_by_node = build_current_machine_by_node(
        machines
    )

    current = current_by_node.get(node)

    if current is None:

        return MachineResolution(
            node=node,
            current_machine_file=None,
            current_machine_ip=None,
            target_machine_ip=target_ip,
            output_file=output_file,
            source="logical_node",
            status="MISSING",
            warnings=[
                f"No current machine was found "
                f"for logical node {node}."
            ],
            errors=[],
        ).to_dict()

    current_file = (
        current.get("file")
        or current.get("machine_file")
        or current.get("path")
    )

    current_ip = (
        current.get("ip")
        or current.get("machine_ip")
    )

    warnings: List[str] = []
    errors: List[str] = []

    #
    # CRITICAL
    #

    if not current_file:
        errors.append(
            f"Current machine file is missing for {node}."
        )

    if not target_ip:
        errors.append(
            f"Target lab IP is missing for {node}."
        )

    #
    # NON-CRITICAL
    #

    if not output_file:
        warnings.append(
            f"Target output filename is missing for {node}."
        )

    return MachineResolution(
        node=node,
        current_machine_file=(
            str(current_file)
            if current_file
            else None
        ),
        current_machine_ip=(
            str(current_ip)
            if current_ip
            else None
        ),
        target_machine_ip=(
            str(target_ip)
            if target_ip
            else None
        ),
        output_file=(
            str(output_file)
            if output_file
            else None
        ),
        source="logical_node",
        status=(
            "READY"
            if not errors
            else "MISSING"
        ),
        warnings=warnings,
        errors=errors,
    ).to_dict()

def resolve_all_target_machines(
    targets: Iterable[Mapping[str, Any]],
    current_machines: Iterable[Mapping[str, Any]],
) -> Dict[str, Any]:
    machines = list(current_machines)
    results = [resolve_machine_for_target(target, machines) for target in targets]
    ready = sum(item["status"] == "READY" for item in results)

    return {
        "status": "READY" if ready == len(results) and results else "REVIEW REQUIRED",
        "ready": ready,
        "total": len(results),
        "machines": results,
    }
