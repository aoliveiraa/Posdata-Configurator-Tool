from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple, Union

XmlSource = Union[str, Path, ET.ElementTree, ET.Element]

ROLE_VALUE_MAP = {
    "FRONT_COUNTER": "FC",
    "FRONTCOUNTER": "FC",
    "FC": "FC",
    "DRIVE_THRU": "DT",
    "DRIVETHRU": "DT",
    "DRIVE_THROUGH": "DT",
    "DRIVETHROUGH": "DT",
    "DT": "DT",
}


def _local_name(tag: str) -> str:
    """Remove an optional XML namespace from a tag."""
    return tag.rsplit("}", 1)[-1]


def _attr(element: ET.Element, name: str) -> Optional[str]:
    """Read an attribute case-insensitively."""
    wanted = name.casefold()
    for key, value in element.attrib.items():
        if key.casefold() == wanted:
            return value
    return None


def normalize_pos_role(value: Optional[str]) -> Optional[str]:
    """Normalize supported POS role values to FC or DT."""
    if value is None:
        return None

    normalized = re.sub(r"[\s-]+", "_", str(value).strip().upper())
    normalized = re.sub(r"_+", "_", normalized)
    return ROLE_VALUE_MAP.get(normalized)


def _result(
    role: Optional[str],
    source: Optional[str],
    raw_value: Optional[str],
    confidence: str,
    status: str,
    warnings: Optional[list[str]] = None,
) -> Dict[str, Any]:
    return {
        "role": role,
        "source": source,
        "role_source": source,
        "raw_value": raw_value,
        "role_value": raw_value,
        "confidence": confidence,
        "status": status,
        "warnings": warnings or [],
    }


def _load_root(source: XmlSource) -> Tuple[ET.Element, Optional[Path]]:
    if isinstance(source, ET.ElementTree):
        return source.getroot(), None
    if isinstance(source, ET.Element):
        return source, None

    path = Path(source)
    return ET.parse(path).getroot(), path


def _iter_children(element: ET.Element, tag_name: str) -> Iterable[ET.Element]:
    wanted = tag_name.casefold()
    for child in list(element):
        if _local_name(child.tag).casefold() == wanted:
            yield child


def _iter_descendants(element: ET.Element, tag_name: str) -> Iterable[ET.Element]:
    wanted = tag_name.casefold()
    for descendant in element.iter():
        if _local_name(descendant.tag).casefold() == wanted:
            yield descendant


def _find_role_in_configuration(
    configuration: ET.Element,
    parameter_name: str,
) -> Optional[Tuple[str, str]]:
    for section in _iter_descendants(configuration, "Section"):
        if (_attr(section, "name") or "").casefold() != "postype":
            continue

        for parameter in _iter_descendants(section, "Parameter"):
            if (_attr(parameter, "name") or "").casefold() != parameter_name.casefold():
                continue

            raw_value = _attr(parameter, "value")
            role = normalize_pos_role(raw_value)
            if role:
                return role, raw_value or ""

    return None


def _find_in_pos_service(
    root: ET.Element,
    parameter_name: str,
) -> Optional[Tuple[str, str]]:
    """Highest confidence: PosType inside Service type=POS."""
    for service in _iter_descendants(root, "Service"):
        if (_attr(service, "type") or "").casefold() != "pos":
            continue

        for configuration in _iter_descendants(service, "Configuration"):
            found = _find_role_in_configuration(configuration, parameter_name)
            if found:
                return found

    return None


def _find_in_pos_configuration(
    root: ET.Element,
    parameter_name: str,
) -> Optional[Tuple[str, str]]:
    """Fallback for XMLs where Configuration imports=POS is outside Service."""
    for configuration in _iter_descendants(root, "Configuration"):
        if (_attr(configuration, "imports") or "").casefold() != "pos":
            continue

        found = _find_role_in_configuration(configuration, parameter_name)
        if found:
            return found

    return None


def _find_in_filename(filename: str) -> Optional[Tuple[str, str]]:
    """Match only delimited FC/DT tokens, never arbitrary substrings."""
    stem = Path(filename).name.upper()
    matches = re.findall(r"(?:^|[_\-.])(FC|DT)(?=[_\-.]|$)", stem)
    unique = list(dict.fromkeys(matches))

    if len(unique) == 1:
        return unique[0], f"_{unique[0]}"
    return None


def discover_pos_role(
    source: XmlSource,
    filename: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Discover FC/DT using safe, ordered evidence.

    Priority:
      1. Service type=POS > Configuration > PosType/POD
      2. Service type=POS > Configuration > PosType/RemPOD
      3. Configuration imports=POS > PosType/POD
      4. Configuration imports=POS > PosType/RemPOD
      5. Explicit _FC/_DT token in filename
      6. REVIEW REQUIRED
    """
    xml_path: Optional[Path] = None

    try:
        root, xml_path = _load_root(source)
    except (ET.ParseError, OSError, ValueError) as exc:
        return _result(
            role=None,
            source=None,
            raw_value=None,
            confidence="NONE",
            status="REVIEW REQUIRED",
            warnings=[f"POS XML could not be parsed: {exc}"],
        )

    effective_filename = filename or (xml_path.name if xml_path else "")

    checks = (
        (_find_in_pos_service, "POD", "xml_pos_service_pod", "HIGH"),
        (_find_in_pos_service, "RemPOD", "xml_pos_service_rempod", "HIGH"),
        (_find_in_pos_configuration, "POD", "xml_pos_configuration_pod", "HIGH"),
        (_find_in_pos_configuration, "RemPOD", "xml_pos_configuration_rempod", "HIGH"),
    )

    for finder, parameter_name, evidence_source, confidence in checks:
        found = finder(root, parameter_name)
        if found:
            role, raw_value = found
            return _result(
                role=role,
                source=evidence_source,
                raw_value=raw_value,
                confidence=confidence,
                status="READY",
            )

    filename_role = _find_in_filename(effective_filename)
    if filename_role:
        role, raw_value = filename_role
        return _result(
            role=role,
            source="filename",
            raw_value=raw_value,
            confidence="MEDIUM",
            status="READY",
            warnings=["POS role was inferred from the filename."],
        )

    return _result(
        role=None,
        source=None,
        raw_value=None,
        confidence="NONE",
        status="REVIEW REQUIRED",
        warnings=["No reliable POS role evidence was found."],
    )
