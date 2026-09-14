"""
Dynamic POS source discovery.

Discovers POS source files from a new PosData without assuming filenames such
as _POS0001_pos-db.xml. Physical filenames may vary by market.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

from lxml import etree

from src.discovery.pos_role_discovery import (
    discover_pos_role,
)

POS_NODE_PATTERN = re.compile(r"^POS\d+$", re.IGNORECASE)
POS_FILENAME_PATTERN = re.compile(
    r"(?:^|_)POS\d+(?:_|-|$)",
    re.IGNORECASE,
)

EXCLUDED_FILENAME_TOKENS = (
    "KVS",
    "KIOSK",
    "ORB",
    "CSO",
    "COD",
    "PROD",
    "WAY",
    "ITONA",
    "NPSHARP",
)

ROLE_PATTERNS = {
    "DT": (
        re.compile(r"(?:^|[_-])DT(?:[_-]|$)", re.IGNORECASE),
        re.compile(r"DRIVE[_ -]?THRU", re.IGNORECASE),
    ),
    "FC": (
        re.compile(r"(?:^|[_-])FC(?:[_-]|$)", re.IGNORECASE),
        re.compile(r"FRONT[_ -]?COUNTER", re.IGNORECASE),
    ),
}


def load_xml(path: Path | str) -> etree._ElementTree:
    parser = etree.XMLParser(
        recover=False,
        resolve_entities=False,
        remove_blank_text=False,
    )
    return etree.parse(str(path), parser)


def _normalize_pos_node(value: object) -> Optional[str]:
    normalized = str(value or "").strip().upper()
    return normalized if POS_NODE_PATTERN.fullmatch(normalized) else None


def _extract_node_candidates(tree: etree._ElementTree) -> List[str]:
    """Extract logical POS nodes from explicit XML values, never filenames."""
    candidates: List[str] = []

    parameter_values = tree.xpath(
        "//Parameter["
        "translate(@name, "
        "'abcdefghijklmnopqrstuvwxyz', "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ'"
        ")='NODENAME'"
        "]/@value"
    )

    for value in parameter_values:
        node = _normalize_pos_node(value)
        if node:
            candidates.append(node)

    urn_values = tree.xpath(
        "//Parameter["
        "translate(@name, "
        "'abcdefghijklmnopqrstuvwxyz', "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ'"
        ")='URN'"
        "]/@value"
    )

    for value in urn_values:
        match = re.search(r"(?:^|[/])POS(\d+)(?:$|[/])", str(value), re.I)
        if match:
            candidates.append(f"POS{match.group(1)}".upper())

    return list(dict.fromkeys(candidates))


def _detect_role_from_filename(file_name: str) -> Optional[str]:
    for role, patterns in ROLE_PATTERNS.items():
        if any(pattern.search(file_name) for pattern in patterns):
            return role
    return None


def _detect_role_from_xml(tree: etree._ElementTree) -> Optional[str]:
    values = tree.xpath(
        "//Parameter["
        "translate(@name, "
        "'abcdefghijklmnopqrstuvwxyz', "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ'"
        ")='OPERATIONMODE' or "
        "translate(@name, "
        "'abcdefghijklmnopqrstuvwxyz', "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ'"
        ")='PODTYPE' or "
        "translate(@name, "
        "'abcdefghijklmnopqrstuvwxyz', "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ'"
        ")='POSTYPE'"
        "]/@value"
    )

    normalized_values = " ".join(str(value).upper() for value in values)

    if "DRIVE_THRU" in normalized_values or "DRIVE THRU" in normalized_values:
        return "DT"
    if re.search(r"(?:^|[^A-Z])DT(?:[^A-Z]|$)", normalized_values):
        return "DT"
    if "FRONT_COUNTER" in normalized_values or "FRONT COUNTER" in normalized_values:
        return "FC"
    if re.search(r"(?:^|[^A-Z])FC(?:[^A-Z]|$)", normalized_values):
        return "FC"

    return None


def _has_pos_browser(tree: etree._ElementTree) -> bool:
    sections = tree.xpath("//Section[@name]")
    for section in sections:
        name = str(section.get("name", "")).upper()
        if name.startswith("COMPONENT.BROWSER.POS"):
            return True
    return False


def _has_pos_service_evidence(tree: etree._ElementTree) -> bool:
    """Detects evidence that the XML represents a sale POS source."""
    if _extract_node_candidates(tree):
        return True

    values = tree.xpath("//Parameter/@value")
    for value in values:
        text = str(value).strip().upper()
        if POS_NODE_PATTERN.fullmatch(text):
            return True
        if re.search(r"(?:^|/)POS/POS\d+(?:$|/)", text, re.I):
            return True

    return _has_pos_browser(tree)


def _is_excluded_filename(file_name: str) -> bool:
    upper_name = file_name.upper()
    return any(token in upper_name for token in EXCLUDED_FILENAME_TOKENS)


def analyze_pos_source_file(file_path: Path | str) -> Dict:
    """Analyzes one XML and returns a structured POS-source candidate."""
    path = Path(file_path)
    result = {
        "file": path.name,
        "path": str(path),
        "is_pos": False,
        "node_candidates": [],
        "role": None,
        "role_source": None,
        "role_value": None,
        "role_confidence": "NONE",
        "role_status": "REVIEW REQUIRED",
        "has_pos_browser": False,
        "warnings": [],
        "errors": [],
    }
    if _is_excluded_filename(path.name):
        result["warnings"].append("Filename identifies a non-POS device type.")
        return result

    if not POS_FILENAME_PATTERN.search(path.stem):
        result["warnings"].append("Filename does not match a POS candidate pattern.")
        return result

    try:
        tree = load_xml(path)
    except Exception as error:
        result["errors"].append(f"Unable to load XML: {error}")
        return result

    if tree.getroot().tag != "PosDB":
        result["warnings"].append("Root element is not PosDB.")
        return result

    result["node_candidates"] = _extract_node_candidates(tree)
    result["has_pos_browser"] = _has_pos_browser(tree)

    role_result = discover_pos_role(
        source=path,
        filename=path.name,
    )

    result["role"] = (
        role_result["role"]
    )

    result["role_source"] = (
        role_result["role_source"]
    )

    result["role_value"] = (
        role_result["role_value"]
    )

    result["role_confidence"] = (
        role_result["confidence"]
    )

    result["role_status"] = (
        role_result["status"]
    )

    result["warnings"].extend(
        role_result["warnings"]
    )
    result["is_pos"] = _has_pos_service_evidence(tree)

    if not result["is_pos"]:
        result["warnings"].append("No POS evidence was found inside the XML.")

    if len(result["node_candidates"]) > 1:
        result["warnings"].append(
            "Multiple logical POS nodes were found: "
            + ", ".join(result["node_candidates"])
        )

    return result


def discover_pos_sources(
    new_posdata_folder: str | Path = "samples/new_posdata",
) -> Dict:
    """
    Discovers every sale-POS source dynamically.

    The result is not limited by lab POS count. Selection/mapping belongs to a
    later step because a market may contain more POS sources than the lab uses.
    """
    folder = Path(new_posdata_folder)
    result = {
        "folder": str(folder),
        "status": "READY",
        "pos_files": [],
        "ignored_files": [],
        "warnings": [],
        "errors": [],
    }

    if not folder.is_dir():
        result["status"] = "FAIL"
        result["errors"].append(f"New PosData folder was not found: {folder}")
        return result

    files = sorted(folder.glob("*_pos-db.xml"))

    if not files:
        result["status"] = "FAIL"
        result["errors"].append(f"No pos-db.xml files were found in: {folder}")
        return result

    for file_path in files:
        analysis = analyze_pos_source_file(file_path)

        if analysis["errors"]:
            result["errors"].extend(
                f"{file_path.name}: {message}"
                for message in analysis["errors"]
            )

        if analysis["is_pos"]:
            result["pos_files"].append(analysis)
        else:
            result["ignored_files"].append(file_path.name)

    if not result["pos_files"]:
        result["status"] = "FAIL"
        result["errors"].append("No valid POS source files were discovered.")
    elif result["errors"]:
        result["status"] = "REVIEW REQUIRED"

    return result
