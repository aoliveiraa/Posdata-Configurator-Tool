"""Evidence-based Itona type classification for PosData Builder."""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List
from lxml import etree

TYPE_PATTERNS = (
    ("BEST_BURGER", re.compile(r"BEST[\s_.-]*BURGER", re.I)),
    ("PRESENTATION", re.compile(r"PRESENTATION|PRESENTER", re.I)),
    ("RUNNER", re.compile(r"RUNNER", re.I)),
    ("MFY", re.compile(r"(?:^|[^A-Z0-9])MFY(?:[^A-Z0-9]|$)", re.I)),
    ("ORB", re.compile(r"(?:^|[^A-Z0-9])(?:MINI[\s_.-]*)?ORB(?:[^A-Z0-9]|$)", re.I)),
    ("OAT", re.compile(r"(?:^|[^A-Z0-9])OAT(?:[^A-Z0-9]|$)", re.I)),
)


def _unique(values: Iterable[str]) -> List[str]:
    return list(dict.fromkeys(value for value in values if value))


def _norm(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", str(value or "").upper()).strip("_")


def _path(tree: etree._ElementTree, node: etree._Element) -> str:
    try:
        return tree.getpath(node)
    except (ValueError, AttributeError):
        return str(node.tag)


def collect_itona_type_evidence(tree: etree._ElementTree) -> List[Dict[str, str]]:
    """Return traceable evidence only from approved KVS configuration areas."""
    records: List[Dict[str, str]] = []
    nodes = tree.xpath(
        "//*[local-name()='StoreConfiguration' or "
        "local-name()='UsedServices' or local-name()='UsedService' or "
        "local-name()='Configuration' or local-name()='Section' or "
        "local-name()='Parameter' or local-name()='Member']"
    )
    for node in nodes:
        tag = etree.QName(node).localname
        parent = node.getparent()
        container = ""
        if parent is not None:
            container = str(parent.get("name") or parent.get("type") or "")
        for attribute, value in node.attrib.items():
            records.append({
                "source": tag,
                "path": _path(tree, node),
                "container": container,
                "attribute": str(attribute),
                "value": str(value),
                "display": f"{tag}[{attribute}={value}]",
            })
        text = (node.text or "").strip()
        if text:
            records.append({
                "source": tag,
                "path": _path(tree, node),
                "container": container,
                "attribute": "text",
                "value": text,
                "display": f"{tag}[text={text}]",
            })
    return records


def _append(matches, itona_type, evidence, rule, strength):
    item = dict(evidence)
    item["rule"] = rule
    item["strength"] = strength
    bucket = matches.setdefault(itona_type, [])
    key = (item["path"], item["attribute"], item["value"], rule)
    if key not in {
        (x["path"], x["attribute"], x["value"], x["rule"])
        for x in bucket
    }:
        bucket.append(item)


def classify_itona_types(tree: etree._ElementTree) -> Dict[str, Any]:
    evidence = collect_itona_type_evidence(tree)
    matches: Dict[str, List[Dict[str, str]]] = {}

    for item in evidence:
        attr = _norm(item["attribute"])
        value = _norm(item["value"])
        container = _norm(item["container"])
        display = _norm(item["display"])

        # Strong semantic rules from explicit KVS configuration parameters.
        if attr == "VALUE" and container == "WAYOFWORK" and value in {"ORB", "MINI_ORB"}:
            _append(matches, "ORB", item, "WayOfWork monitorType identifies ORB", "STRONG")
        if attr == "VALUE" and value == "TRUE" and "RUNNERENABLED" in display:
            _append(matches, "RUNNER", item, "runnerEnabled=true", "STRONG")
        if attr == "VALUE" and value == "TRUE" and "PRESENTERMONITOR" in display:
            _append(matches, "PRESENTATION", item, "presenterMonitor=true", "STRONG")
        if attr == "VALUE" and "RUNNERSERVE" in value:
            _append(matches, "RUNNER", item, "TouchScreen action runnerServe", "STRONG")

        # Fallback token rules, restricted to meaningful attributes.
        if attr in {"NAME", "ALIAS", "TYPE", "VALUE", "IMPORTS", "TEXT"}:
            for itona_type, pattern in TYPE_PATTERNS:
                if pattern.search(item["value"]):
                    _append(
                        matches,
                        itona_type,
                        item,
                        f"Explicit {itona_type} token in approved configuration",
                        "TOKEN",
                    )

    ordered = [name for name, _ in TYPE_PATTERNS if name in matches]
    checked_sources = _unique(item["source"] for item in evidence)
    if not ordered:
        return {
            "types": ["UNKNOWN"],
            "status": "REVIEW REQUIRED",
            "confidence": "NONE",
            "evidence": {},
            "checked_sources": checked_sources,
            "warnings": ["No supported Itona type evidence was found."],
        }

    strong = any(
        entry["strength"] == "STRONG"
        for entries in matches.values()
        for entry in entries
    )
    ambiguous = len(ordered) > 1
    return {
        "types": ordered,
        "status": "REVIEW REQUIRED" if ambiguous else "READY",
        "confidence": "MEDIUM" if ambiguous else ("HIGH" if strong else "MEDIUM"),
        "evidence": {name: entries[:10] for name, entries in matches.items()},
        "checked_sources": checked_sources,
        "warnings": (
            ["Multiple Itona types were detected; review the evidence before assignment."]
            if ambiguous else []
        ),
    }
