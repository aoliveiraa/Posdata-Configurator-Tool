"""Discovery phase for PosData Builder.

This phase analyzes the source market PosData. The internal template remains the
reference/current PosData for later mapping and generation phases, while the
source market provides store-db.xml, screen.xml, POS candidates, Itona
candidates, WAY and production files.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from lxml import etree

from src.builder.builder_context import BuilderContext
from src.discovery.market_detector import detect_market
from src.discovery.node_detector import detect_nodes
from src.discovery.pos_source_discovery import discover_pos_sources
from src.discovery.screen_analyzer import analyze_screens, find_lunch_screen
from src.discovery.storedb_analyzer import analyze_storedb

from src.builder.itona_type_classifier import (
    classify_itona_types,
)

from src.builder.builder_generation_report import (
    generate_builder_generation_report,
)

KVS_TYPE_PATTERNS = (
    ("BEST_BURGER", re.compile(r"BEST[\s_.-]*BURGER", re.IGNORECASE)),
    ("PRESENTATION", re.compile(r"PRESENTATION|PRESENTER", re.IGNORECASE)),
    ("RUNNER", re.compile(r"RUNNER", re.IGNORECASE)),
    ("MFY", re.compile(r"(?:^|[^A-Z0-9])MFY(?:[^A-Z0-9]|$)", re.IGNORECASE)),
    ("ORB", re.compile(r"(?:^|[^A-Z0-9])ORB(?:[^A-Z0-9]|$)", re.IGNORECASE)),
    ("OAT", re.compile(r"(?:^|[^A-Z0-9])OAT(?:[^A-Z0-9]|$)", re.IGNORECASE)),
)


def _load_xml(path: Path) -> etree._ElementTree:
    parser = etree.XMLParser(
        recover=False,
        resolve_entities=False,
        remove_blank_text=False,
    )
    return etree.parse(str(path), parser)


def _unique(values: Iterable[str]) -> List[str]:
    return list(dict.fromkeys(value for value in values if value))


def _normalized_service_name(value: object) -> Optional[str]:
    text = str(value or "").strip().upper()
    return text or None


def _collect_kvs_services(tree: etree._ElementTree) -> List[str]:
    services = tree.xpath(
        "//Service[translate(@type, "
        "'abcdefghijklmnopqrstuvwxyz', "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ')='KVS']/@name"
    )
    return _unique(
        normalized
        for normalized in (
            _normalized_service_name(value) for value in services
        )
        if normalized
    )


def _collect_npw_services(tree: etree._ElementTree) -> List[str]:
    services = tree.xpath(
        "//Service[translate(@type, "
        "'abcdefghijklmnopqrstuvwxyz', "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ')='NPW']/@name"
    )
    return _unique(
        normalized
        for normalized in (
            _normalized_service_name(value) for value in services
        )
        if normalized
    )


def _collect_browser_nodes(tree: etree._ElementTree) -> List[str]:
    nodes: List[str] = []
    for section_name in tree.xpath("//Section[@name]/@name"):
        match = re.search(
            r"COMPONENT\.BROWSER\.(KVS[A-Z0-9_-]+)",
            str(section_name),
            re.IGNORECASE,
        )
        if match:
            nodes.append(match.group(1).upper())
    return _unique(nodes)


def _classification_evidence(tree: etree._ElementTree) -> List[str]:
    """Collect only the XML areas approved for KVS type classification."""
    evidence: List[str] = []

    approved_nodes = tree.xpath(
        "//*["
        "local-name()='StoreConfiguration' or "
        "local-name()='UsedServices' or "
        "local-name()='UsedService' or "
        "local-name()='Configuration' or "
        "local-name()='Section' or "
        "local-name()='Parameter'"
        "]"
    )

    for node in approved_nodes:
        for key, value in node.attrib.items():
            evidence.append(f"{key}={value}")
        if node.text and node.text.strip():
            evidence.append(node.text.strip())

    return evidence


def _classify_kvs_types(tree: etree._ElementTree) -> Dict[str, Any]:
    evidence = _classification_evidence(tree)
    combined = "\n".join(evidence)
    matches: List[str] = []
    matching_evidence: Dict[str, List[str]] = {}

    for kvs_type, pattern in KVS_TYPE_PATTERNS:
        type_evidence = [value for value in evidence if pattern.search(value)]
        if type_evidence:
            matches.append(kvs_type)
            matching_evidence[kvs_type] = type_evidence[:10]

    if not matches:
        return {
            "types": ["UNKNOWN"],
            "status": "REVIEW REQUIRED",
            "confidence": "NONE",
            "evidence": {},
            "warnings": [
                "No supported KVS type evidence was found in "
                "StoreConfiguration, UsedServices or KVS Configuration."
            ],
        }

    return {
        "types": matches,
        "status": "READY",
        "confidence": "HIGH" if len(matches) == 1 else "MEDIUM",
        "evidence": matching_evidence,
        "warnings": (
            []
            if len(matches) == 1
            else ["More than one KVS type was detected in the candidate."]
        ),
    }


def analyze_itona_candidate(file_path: str | Path) -> Dict[str, Any]:
    """Analyze one market KVS file as an Itona assignment candidate."""
    path = Path(file_path)
    result: Dict[str, Any] = {
        "file": path.name,
        "path": str(path),
        "found": False,
        "kvs_services": [],
        "npw_services": [],
        "browser_nodes": [],
        "kvs_types": ["UNKNOWN"],
        "type_status": "REVIEW REQUIRED",
        "type_confidence": "NONE",
        "type_evidence": {},
        "warnings": [],
        "errors": [],
    }

    try:
        tree = _load_xml(path)
    except (OSError, etree.XMLSyntaxError) as error:
        result["errors"].append(f"Unable to load candidate XML: {error}")
        return result

    if tree.getroot().tag != "PosDB":
        result["errors"].append("Root element is not PosDB.")
        return result

    result["kvs_services"] = _collect_kvs_services(tree)
    result["npw_services"] = _collect_npw_services(tree)
    result["browser_nodes"] = _collect_browser_nodes(tree)

    if not result["kvs_services"]:
        result["warnings"].append("No KVS service was found in the candidate.")
        return result

    classification = classify_itona_types(tree)
    result["kvs_types"] = classification["types"]
    result["type_status"] = classification["status"]
    result["type_confidence"] = classification["confidence"]
    result["type_evidence"] = classification["evidence"]
    result["type_checked_sources"] = (
    classification.get("checked_sources",[],))
    result["warnings"].extend(classification["warnings"])
    result["found"] = True
    return result


def discover_itona_candidates(folder: str | Path) -> Dict[str, Any]:
    """Discover source-market KVS XMLs that can be assigned to Itona slots."""
    source_folder = Path(folder)
    result: Dict[str, Any] = {
        "status": "READY",
        "folder": str(source_folder),
        "candidates": [],
        "ignored_files": [],
        "warnings": [],
        "errors": [],
    }

    if not source_folder.is_dir():
        result["status"] = "FAIL"
        result["errors"].append(
            f"Source PosData folder was not found: {source_folder}"
        )
        return result

    files = sorted(source_folder.glob("*_pos-db.xml"))
    for file_path in files:
        upper_name = file_path.name.upper()
        if "KVS" not in upper_name:
            continue

        candidate = analyze_itona_candidate(file_path)
        if candidate["found"]:
            result["candidates"].append(candidate)
        else:
            result["ignored_files"].append(file_path.name)
            result["warnings"].extend(
                f"{file_path.name}: {message}"
                for message in candidate["warnings"]
            )
            result["errors"].extend(
                f"{file_path.name}: {message}"
                for message in candidate["errors"]
            )

    if not result["candidates"]:
        result["status"] = "FAIL"
        result["errors"].append("No valid Itona candidates were discovered.")
    elif result["errors"] or any(
        candidate["type_status"] != "READY"
        for candidate in result["candidates"]
    ):
        result["status"] = "REVIEW REQUIRED"

    return result


def _is_production_candidate(
    filename: str,
) -> bool:

    upper = (
        filename
        .strip()
        .upper()
    )

    #
    # Standard production files
    #
    if (
        upper.startswith(
            "_PROD"
        )
    ):
        return True

    #
    # Spain market
    #
    if re.match(
        r"^_8000.*POS-DB\.XML$",
        upper,
    ):
        return True

    #
    # Generic fallback
    #
    if (
        "PRODUCTION"
        in upper
    ):
        return True

    return False


def _discover_infrastructure(
    folder: Path,
) -> Dict[str, Any]:

    detected = detect_nodes(
        folder
    )

    production_files = list(
        detected.get(
            "production",
            [],
        )
    )

    #
    # Builder fallback
    #
    if not production_files:

        for file_path in sorted(
            folder.glob(
                "*_pos-db.xml"
            )
        ):

            if _is_production_candidate(
                file_path.name
            ):

                production_files.append(
                    file_path.name
                )

    return {
        "way_files": list(
            detected.get(
                "way",
                [],
            )
        ),
        "production_files":
            production_files,
    }


def run_builder_discovery_phase(
    context: BuilderContext,
) -> BuilderContext:
    """Populate BuilderContext using the source market PosData.

    The market StoreDB and screen.xml remain the transformation sources. The
    internal template is not modified by this phase.
    """
    required_values = {
        "source_posdata_folder": context.source_posdata_folder,
        "store_db_path": context.store_db_path,
        "screen_xml_path": context.screen_xml_path,
    }
    missing = [name for name, value in required_values.items() if not value]
    if missing:
        context.errors.append(
            "Builder discovery cannot start. Missing context values: "
            + ", ".join(missing)
        )
        context.source_validation = {
            "status": "FAIL",
            "errors": list(context.errors),
        }
        return context

    source_folder = Path(context.source_posdata_folder)
    store_db_path = Path(context.store_db_path)
    screen_xml_path = Path(context.screen_xml_path)

    try:
        context.market = detect_market(store_db_path)
        context.store_info = analyze_storedb(store_db_path)
        context.screens = analyze_screens(screen_xml_path)
        context.lunch_screen = find_lunch_screen(context.screens)
    except Exception as error:
        context.errors.append(f"Market metadata discovery failed: {error}")

    context.discovered_pos = discover_pos_sources(source_folder)
    itona_discovery = discover_itona_candidates(source_folder)
    context.discovered_itona_candidates = list(
        itona_discovery.get("candidates", [])
    )
    infrastructure = _discover_infrastructure(source_folder)

    phase_errors = list(context.discovered_pos.get("errors", []))
    phase_errors.extend(itona_discovery.get("errors", []))
    phase_errors.extend(context.errors)

    phase_warnings = list(context.discovered_pos.get("warnings", []))
    phase_warnings.extend(itona_discovery.get("warnings", []))

    status = "READY"
    if phase_errors:
        status = "FAIL"
    elif (
        context.discovered_pos.get("status") != "READY"
        or itona_discovery.get("status") != "READY"
    ):
        status = "REVIEW REQUIRED"

    context.source_validation = {
        "status": status,
        "source_folder": str(source_folder),
        "market": context.market,
        "store_info": context.store_info,
        "screen_count": len(context.screens),
        "lunch_screen": context.lunch_screen,
        "pos_count": len(context.discovered_pos.get("pos_files", [])),
        "itona_candidate_count": len(context.discovered_itona_candidates),
        "way_files": infrastructure["way_files"],
        "production_files": infrastructure["production_files"],
        "warnings": phase_warnings,
        "errors": phase_errors,
    }
    context.warnings.extend(phase_warnings)
    context.errors = list(dict.fromkeys(phase_errors))
    context.warnings = list(dict.fromkeys(context.warnings))
    return context
