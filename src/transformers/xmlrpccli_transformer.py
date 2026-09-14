"""
XMLRPCCLI transformer.

Rules implemented:
- Reads Store Controller IP from the selected lab config_path.
- Uses current StoreDB/POS files as the structural source of truth.
- Matches current POS and generated POS by POS node name, never by filename.
- Updates or adds xmlrpccli only when the corresponding current file contains it.
- Updates only Parameter name="url".
- Does not process KVS, Itona, WAY or FOE folders.
- Does not confuse foe.xmlrpc with xmlrpccli.
- Is idempotent.
"""

from __future__ import annotations

import copy
import ipaddress
import json
from pathlib import Path
from typing import Dict, List, Optional

from lxml import etree

LOWERCASE = "abcdefghijklmnopqrstuvwxyz"
UPPERCASE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def load_xml(path: Path | str) -> etree._ElementTree:
    parser = etree.XMLParser(
        remove_blank_text=False,
        recover=False,
        resolve_entities=False,
    )
    return etree.parse(str(path), parser)


def save_xml(tree: etree._ElementTree, path: Path | str) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(
        str(output_path),
        encoding="utf-8",
        xml_declaration=True,
        pretty_print=True,
    )


def load_store_controller_ip(config_path: Path | str) -> str:
    """
    Reads the Store Controller IP from the selected lab JSON.

    Supported preferred structure:
        store_db -> cod_adaptor -> store_controller_ip

    A root-level store_controller_ip is accepted as fallback.
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise ValueError(
            f"Lab configuration file was not found: {config_file}"
        )

    try:
        with config_file.open("r", encoding="utf-8") as file:
            config = json.load(file)

    except json.JSONDecodeError as error:
        raise ValueError(
            f"Lab configuration JSON is invalid: {error}"
        ) from error
    except OSError as error:
        raise ValueError(
            f"Unable to read lab configuration: {error}"
        ) from error

    cod_adaptor = (
        config.get("cod", {})
        .get("store_db", {})
        .get("cod_adaptor", {})
    )

    if not cod_adaptor:

        cod_adaptor = (
            config.get("store_db", {})
            .get("cod_adaptor", {})
        )

    store_controller_ip = (
        cod_adaptor.get(
            "store_controller_ip"
        )
    )

    if not store_controller_ip:
        store_controller_ip = config.get("store_controller_ip")

    if not store_controller_ip:
        raise ValueError(
            "store_controller_ip was not found in the lab configuration. "
            "Expected path: cod.store_db.cod_adaptor.store_controller_ip"
        )
    return str(store_controller_ip).strip()


def build_xmlrpccli_url(
    store_controller_ip: str
) -> str:

    value = (
        str(store_controller_ip or "")
        .strip()
        .strip("\"'")
    )

    try:
        normalized_ip = str(
            ipaddress.ip_address(
                value
            )
        )

    except ValueError as error:

        raise ValueError(
            "Store Controller IP is invalid. "
            "Configure only the IP address."
        ) from error

    if ":" in normalized_ip:
        normalized_ip = (
            f"[{normalized_ip}]"
        )

    return (
        f"http://{normalized_ip}"
        ":8888/goform/RPC2"
    )


def _normalized_attribute_xpath(attribute: str) -> str:
    return (
        "translate("
        f"@{attribute}, "
        f"'{LOWERCASE}', "
        f"'{UPPERCASE}'"
        ")='XMLRPCCLI'"
    )


def find_store_xmlrpccli_adaptors(
    tree: etree._ElementTree,
) -> List[etree._Element]:

    matches = tree.xpath(
        '//Adaptor[@type="xmlrpccli"]'
    )

    return matches


def find_pos_xmlrpccli_adaptors(
    tree: etree._ElementTree,
) -> List[etree._Element]:
    """
    Finds valid xmlrpccli adaptors in a PosDB.

    Supported patterns:

        <Adaptor name="xmlrpccli">
        <Adaptor type="xmlrpccli">
        <Adaptor imports="xmlrpccli">

    Only adaptors containing Section main and
    Parameter url are returned.
    """

    candidates = tree.xpath(
        "//Adaptor["
        "translate("
        "@name, "
        "'abcdefghijklmnopqrstuvwxyz', "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ'"
        ")='XMLRPCCLI'"
        " or "
        "translate("
        "@type, "
        "'abcdefghijklmnopqrstuvwxyz', "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ'"
        ")='XMLRPCCLI'"
        " or "
        "translate("
        "@imports, "
        "'abcdefghijklmnopqrstuvwxyz', "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ'"
        ")='XMLRPCCLI'"
        "]"
    )

    valid_adaptors = []

    for adaptor in candidates:

        main_sections = adaptor.xpath(
            "./Section["
            "translate("
            "@name, "
            "'abcdefghijklmnopqrstuvwxyz', "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ'"
            ")='MAIN'"
            "]"
        )

        if not main_sections:
            continue

        url_parameters = main_sections[0].xpath(
            "./Parameter["
            "translate("
            "@name, "
            "'abcdefghijklmnopqrstuvwxyz', "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ'"
            ")='URL'"
            "]"
        )

        if not url_parameters:
            continue

        valid_adaptors.append(
            adaptor
        )

    return valid_adaptors

def find_any_pos_xmlrpccli_adaptors(
    tree: etree._ElementTree,
) -> List[etree._Element]:
    """
    Finds every xmlrpccli adaptor in the output,
    including incomplete adaptors.

    This allows the transformer to repair an
    existing adaptor before considering insertion.
    """

    return tree.xpath(
        "//Adaptor["
        "translate("
        "@name, "
        "'abcdefghijklmnopqrstuvwxyz', "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ'"
        ")='XMLRPCCLI'"
        " or "
        "translate("
        "@type, "
        "'abcdefghijklmnopqrstuvwxyz', "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ'"
        ")='XMLRPCCLI'"
        " or "
        "translate("
        "@imports, "
        "'abcdefghijklmnopqrstuvwxyz', "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ'"
        ")='XMLRPCCLI'"
        "]"
    )

def _direct_section(
    adaptor: etree._Element,
    section_name: str,
) -> Optional[etree._Element]:
    matches = adaptor.xpath(
        "./Section[translate(@name, $lower, $upper)=$name]",
        lower=LOWERCASE,
        upper=UPPERCASE,
        name=section_name.upper(),
    )
    return matches[0] if matches else None


def _direct_parameter(
    section: etree._Element,
    parameter_name: str,
) -> Optional[etree._Element]:
    matches = section.xpath(
        "./Parameter[translate(@name, $lower, $upper)=$name]",
        lower=LOWERCASE,
        upper=UPPERCASE,
        name=parameter_name.upper(),
    )
    return matches[0] if matches else None


def _get_parent_xpath(element: etree._Element) -> str:
    parent = element.getparent()

    if parent is None:
        raise ValueError("xmlrpccli adaptor does not have a parent node.")

    return element.getroottree().getpath(parent)


def _find_parent_service(
    adaptor: etree._Element,
) -> Optional[etree._Element]:
    """
    Returns the Service that owns an adaptor.
    """

    services = adaptor.xpath(
        "ancestor::Service[1]"
    )

    if services:
        return services[0]

    return None


def _find_matching_output_service(
    output_tree: etree._ElementTree,
    current_service: etree._Element,
) -> Optional[etree._Element]:
    """
    Finds the equivalent output Service using
    semantic attributes rather than XML position.
    """

    current_name = (
        current_service.get(
            "name",
            ""
        )
        .strip()
    )

    current_type = (
        current_service.get(
            "type",
            ""
        )
        .strip()
    )

    current_classname = (
        current_service.get(
            "classname",
            ""
        )
        .strip()
    )

    output_services = output_tree.xpath(
        "/PosDB/Services/Service"
    )

    if current_name and current_type:

        for service in output_services:

            if (
                service.get(
                    "name",
                    ""
                ).strip()
                == current_name
                and
                service.get(
                    "type",
                    ""
                ).strip()
                == current_type
            ):
                return service

    if current_type:

        matching_type = [
            service
            for service in output_services
            if (
                service.get(
                    "type",
                    ""
                )
                .strip()
                .upper()
                == current_type.upper()
            )
        ]

        if len(matching_type) == 1:
            return matching_type[0]

    if current_classname:

        matching_class = [
            service
            for service in output_services
            if (
                service.get(
                    "classname",
                    ""
                )
                .strip()
                .lower()
                == current_classname.lower()
            )
        ]

        if len(matching_class) == 1:
            return matching_class[0]

    return None


def _get_or_create_adaptors_container(
    service: etree._Element,
) -> etree._Element:
    """
    Gets or creates the Adaptors container
    directly under a Service.
    """

    containers = service.xpath(
        "./Adaptors"
    )

    if containers:
        return containers[0]

    adaptors = etree.Element(
        "Adaptors"
    )

    configuration = service.find(
        "Configuration"
    )

    if configuration is not None:

        configuration_index = service.index(
            configuration
        )

        service.insert(
            configuration_index,
            adaptors
        )

    else:

        service.append(
            adaptors
        )

    return adaptors


def _insert_like_current(
    output_tree: etree._ElementTree,
    current_adaptor: etree._Element,
) -> etree._Element:
    """
    Copies xmlrpccli from the current file into
    the semantically equivalent output Service.

    It never uses positional paths such as
    Service[5].
    """

    current_service = (
        _find_parent_service(
            current_adaptor
        )
    )

    if current_service is None:
        raise ValueError(
            "The current xmlrpccli adaptor is not "
            "inside a Service."
        )

    output_service = (
        _find_matching_output_service(
            output_tree,
            current_service
        )
    )

    if output_service is None:
        raise ValueError(
            "Unable to find a matching output "
            "Service for the current xmlrpccli. "
            f"Current Service name="
            f"'{current_service.get('name')}', "
            f"type="
            f"'{current_service.get('type')}'."
        )

    output_adaptors = (
        _get_or_create_adaptors_container(
            output_service
        )
    )

    copied_adaptor = copy.deepcopy(
        current_adaptor
    )

    output_adaptors.append(
        copied_adaptor
    )

    return copied_adaptor

def _ensure_url_parameter_from_current(
    output_adaptor: etree._Element,
    current_adaptor: etree._Element,
) -> etree._Element:
    """Ensures main/url using the current adaptor as structural pattern."""
    current_main = _direct_section(current_adaptor, "main")

    if current_main is None:
        raise ValueError(
            "The current xmlrpccli adaptor does not contain Section main."
        )

    current_url = _direct_parameter(current_main, "url")

    if current_url is None:
        raise ValueError(
            "The current xmlrpccli adaptor does not contain Parameter url."
        )

    output_main = _direct_section(output_adaptor, "main")

    if output_main is None:
        output_main = copy.deepcopy(current_main)
        output_adaptor.append(output_main)

    output_url = _direct_parameter(output_main, "url")

    if output_url is None:
        output_url = copy.deepcopy(current_url)
        current_url_index = current_main.index(current_url)

        if current_url_index < len(output_main):
            output_main.insert(current_url_index, output_url)
        else:
            output_main.append(output_url)

    return output_url


import re


def _extract_pos_node_names(tree: etree._ElementTree) -> List[str]:
    """
    Extracts logical POS node names from a PosDB XML.

    Examples:

        POS0001
        POS0002
        POS0003
        POS0004

    Rules:
    - Never use the filename.
    - Prefer NodeName/nodeName parameters.
    - Fallback to URN references.
    - Return unique values only.
    """

    discovered_nodes = []

    #
    # Priority 1
    # Parameter name="NodeName"
    # Parameter name="nodeName"
    #
    node_parameters = tree.xpath(
        "//Parameter[@name='NodeName' or @name='nodeName']"
    )

    for parameter in node_parameters:

        value = (
            parameter.get(
                "value",
                ""
            )
            .strip()
            .upper()
        )

        if re.match(
            r"^POS\d+$",
            value
        ):
            discovered_nodes.append(
                value
            )

    #
    # Priority 2
    # Parameter name="Urn"
    # Example:
    #   pos/POS0001
    #
    urn_parameters = tree.xpath(
        "//Parameter[@name='Urn']"
    )

    for parameter in urn_parameters:

        value = (
            parameter.get(
                "value",
                ""
            )
            .strip()
            .upper()
        )

        match = re.search(
            r"POS\d+",
            value
        )

        if match:
            discovered_nodes.append(
                match.group(0)
            )

    #
    # Remove duplicates
    #
    discovered_nodes = list(
        dict.fromkeys(
            discovered_nodes
        )
    )

    return discovered_nodes

def _build_pos_node_lookup(
    folder: Path,
    source_label: str,
) -> Dict:
    """
    Builds a logical POS node to XML file lookup.

    Rules:
    - Never derives the node from the filename.
    - Ignores XML files without a logical POS node.
    - Ignores KVS, Itona, WAY, FOE and other
      unrelated XML files silently.
    - Treats duplicated nodes as warnings.
    - Keeps the first machine file found for
      each logical node.
    """

    result = {
        "lookup": {},
        "warnings": [],
        "errors": [],
    }

    if not folder.exists():
        result["errors"].append(
            f"{source_label} POS folder "
            f"was not found: {folder}"
        )

        return result

    xml_files = sorted(
        folder.glob(
            "*_pos-db.xml"
        )
    )

    if not xml_files:
        result["warnings"].append(
            f"No POS XML files were found "
            f"in {source_label} folder: "
            f"{folder}"
        )

        return result

    excluded_tokens = (
        "ITONA",
        "KVS",
        "KIOSK",
        "ORB",
        "WAY",
        "PROD",
        "FOE",
    )

    for xml_file in xml_files:
        upper_file_name = xml_file.name.upper()

        if any(token in upper_file_name for token in excluded_tokens):
            continue

        try:
            tree = load_xml(
                xml_file
            )

        except Exception as error:

            result["errors"].append(
                f"{xml_file.name}: "
                f"unable to load XML: "
                f"{error}"
            )

            continue

        root = tree.getroot()

        if root.tag != "PosDB":
            continue

        node_names = (
            _extract_pos_node_names(
                tree
            )
        )

        if not node_names:
            continue

        for node_name in node_names:

            existing_file = (
                result["lookup"].get(
                    node_name
                )
            )

            if (
                existing_file
                and existing_file != xml_file
            ):
                result["warnings"].append(
                    f"Duplicate logical node "
                    f"{node_name} in "
                    f"{source_label}. "
                    f"Using "
                    f"{existing_file.name}; "
                    f"ignoring "
                    f"{xml_file.name}."
                )

                continue

            result["lookup"][
                node_name
            ] = xml_file

    return result

def _transform_one_file(
    current_path: Path,
    output_path: Path,
    expected_url: str,
    kind: str,
    node_name: Optional[str] = None,
) -> Dict:

    result = {
        "file": str(output_path),
        "current_file": str(current_path),
        "node": node_name,
        "status": "SKIPPED",
        "changes": [],
        "warnings": [],
        "errors": [],
    }

    current_exists = current_path.exists()
    output_exists = output_path.exists()
    #
    # Current validation
    #
    if not current_exists:

        result["warnings"].append(
            f"Current reference file was not found: "
            f"{current_path}"
        )

        result["status"] = "SKIPPED"

        return result

    #
    # Output validation
    #
    if not output_exists:

        #
        # StoreDB should be a hard failure.
        #
        if kind == "store":

            result["errors"].append(
                f"Store output file was not found: "
                f"{output_path}"
            )

            result["status"] = "FAIL"

            return result

        #
        # POS can be skipped.
        #
        result["warnings"].append(
            f"Output file was not found: "
            f"{output_path}"
        )

        result["status"] = "SKIPPED"

        return result

    #
    # Load XML
    #
    try:

        current_tree = load_xml(
            current_path
        )

        output_tree = load_xml(
            output_path
        )

    except Exception as error:

        result["errors"].append(
            f"Unable to load XML: {error}"
        )

        result["status"] = "FAIL"

        return result

    #
    # XMLRPCCLI finder
    #
    finder = (
        find_store_xmlrpccli_adaptors
        if kind == "store"
        else find_pos_xmlrpccli_adaptors
    )

    current_adaptors = finder(
        current_tree
    )

    #
    # Current file doesn't contain xmlrpccli
    #
    if not current_adaptors:

        result["warnings"].append(
            "xmlrpccli does not exist in the current "
            "reference; skipped."
        )

        result["status"] = "SKIPPED"

        return result

    if kind == "store":

        output_adaptors = (
            find_store_xmlrpccli_adaptors(
                output_tree
            )
        )

    else:

        output_adaptors = (
            find_any_pos_xmlrpccli_adaptors(
                output_tree
            )
        )
    changed = False

    try:

        for index, current_adaptor in enumerate(
            current_adaptors
        ):

            if index < len(output_adaptors):

                output_adaptor = (
                    output_adaptors[index]
                )

            else:

                output_adaptor = (
                    _insert_like_current(
                        output_tree,
                        current_adaptor
                    )
                )

                output_adaptors.append(
                    output_adaptor
                )

                changed = True

                result["changes"].append(
                    "xmlrpccli adaptor added using "
                    "the current Service pattern."
                )

            url_parameter = (
                _ensure_url_parameter_from_current(
                    output_adaptor,
                    current_adaptor,
                )
            )

            raw_url = url_parameter.get(
                "value",
                ""
            )

            old_url = normalize_xmlrpc_url(
                raw_url
            )

            if raw_url != expected_url:

                url_parameter.set(
                    "value",
                    expected_url
                )

                changed = True

                result["changes"].append(
                    "xmlrpccli url updated: "
                    f"{old_url} -> "
                    f"{expected_url}"
                )

    except Exception as error:

        result["errors"].append(
            str(error)
        )

        result["status"] = "FAIL"

        return result

    #
    # Nothing changed
    #
    if not changed:

        result["status"] = "NO CHANGES"

        return result

    #
    # Save
    #
    try:

        etree.indent(
            output_tree,
            space="  "
        )

        save_xml(
            output_tree,
            output_path,
        )

        saved_tree = load_xml(
            output_path
        )

        if kind == "store":

            saved_adaptors = (
                find_store_xmlrpccli_adaptors(
                    saved_tree
                )
            )

        else:

            saved_adaptors = (
                find_pos_xmlrpccli_adaptors(
                    saved_tree
                )
            )

        saved_urls = []

        for adaptor in saved_adaptors:

            main = _direct_section(
                adaptor,
                "main",
            )

            parameter = (
                _direct_parameter(
                    main,
                    "url",
                )
                if main is not None
                else None
            )

            if parameter is not None:

                saved_urls.append(
                    parameter.get(
                        "value",
                        ""
                    )
                )

        if (
            len(saved_urls)
            < len(current_adaptors)
        ):
            raise ValueError(
                "Saved XML does not contain all "
                "expected xmlrpccli URLs."
            )

        if any(
            url != expected_url
            for url in saved_urls[
                : len(current_adaptors)
            ]
        ):
            raise ValueError(
                "Saved xmlrpccli URL does not "
                "match the expected value."
            )

    except Exception as error:

        result["errors"].append(
            f"Unable to save or validate XML: "
            f"{error}"
        )

        result["status"] = "FAIL"

        return result

    result["status"] = "UPDATED"

    return result

def generate_xmlrpccli_configuration(
    config_path: str = "config/rio_lab.json",
    current_pos_folder: str = "samples/current_posdata",
    output_pos_folder: str = "output/pos",
    current_store_file: str = "samples/current_posdata/store-db.xml",
    output_store_file: str = "output/store-db.xml",
    allowed_pos_nodes: Optional[List[str]] = None,
    pos_file_pairs: Optional[List[Dict]] = None,
) -> Dict:
    """
    Applies xmlrpccli to StoreDB and generated POS files.

    Preferred POS mode:
        pos_file_pairs explicitly associates each generated output with its
        real current machine file. This is market agnostic and avoids matching
        unrelated current XMLs by node references found inside their content.

    Compatibility mode:
        when pos_file_pairs is not provided, current/output lookups are built
        by logical POS node and may be limited with allowed_pos_nodes.
    """
    result = {
        "status": "SUCCESS",
        "config_path": str(config_path),
        "store_controller_ip": None,
        "url": None,
        "store": None,
        "pos": [],
        "node_matches": {},
        "changes": [],
        "warnings": [],
        "errors": [],
    }

    try:
        store_controller_ip = load_store_controller_ip(config_path)
        expected_url = build_xmlrpccli_url(store_controller_ip)
    except ValueError as error:
        result["status"] = "FAIL"
        result["errors"].append(str(error))
        return result

    result["store_controller_ip"] = store_controller_ip
    result["url"] = expected_url

    store_result = _transform_one_file(
        current_path=Path(current_store_file),
        output_path=Path(output_store_file),
        expected_url=expected_url,
        kind="store",
    )
    result["store"] = store_result
    result["changes"].extend(store_result["changes"])
    result["warnings"].extend(store_result["warnings"])
    result["errors"].extend(store_result["errors"])

    normalized_allowed_nodes = None
    if allowed_pos_nodes is not None:
        normalized_allowed_nodes = {
            str(node).strip().upper()
            for node in allowed_pos_nodes
            if str(node).strip()
        }

    pairs_to_process = []

    if pos_file_pairs is not None:
        seen_outputs = set()

        for pair in pos_file_pairs:
            node_name = str(pair.get("node_name") or "").strip().upper()
            current_path = Path(str(pair.get("current_path") or ""))
            output_path = Path(str(pair.get("output_path") or ""))

            if normalized_allowed_nodes is not None and node_name not in normalized_allowed_nodes:
                continue

            output_key = str(output_path.resolve()) if str(output_path) else ""
            if output_key in seen_outputs:
                result["warnings"].append(
                    f"Duplicate explicit XMLRPCCLI output pair ignored: {output_path}"
                )
                continue

            seen_outputs.add(output_key)
            pairs_to_process.append((node_name, current_path, output_path))
    else:
        current_lookup_result = _build_pos_node_lookup(
            Path(current_pos_folder),
            "current",
        )
        output_lookup_result = _build_pos_node_lookup(
            Path(output_pos_folder),
            "output",
        )

        result["warnings"].extend(current_lookup_result["warnings"])
        result["warnings"].extend(output_lookup_result["warnings"])
        result["errors"].extend(current_lookup_result["errors"])
        result["errors"].extend(output_lookup_result["errors"])

        current_lookup = current_lookup_result["lookup"]
        output_lookup = output_lookup_result["lookup"]

        if normalized_allowed_nodes is not None:
            current_lookup = {
                node: path
                for node, path in current_lookup.items()
                if node in normalized_allowed_nodes
            }
            output_lookup = {
                node: path
                for node, path in output_lookup.items()
                if node in normalized_allowed_nodes
            }

        for node_name, output_path in sorted(output_lookup.items()):
            current_path = current_lookup.get(node_name)
            pairs_to_process.append((node_name, current_path, output_path))

    for node_name, current_pos_file, output_pos_file in pairs_to_process:
        if current_pos_file is None or not str(current_pos_file):
            file_result = {
                "file": str(output_pos_file),
                "current_file": None,
                "node": node_name,
                "status": "SKIPPED",
                "changes": [],
                "warnings": [
                    f"No current POS reference was resolved for node {node_name}; skipped."
                ],
                "errors": [],
            }
        else:
            result["node_matches"][node_name] = {
                "current": str(current_pos_file),
                "output": str(output_pos_file),
            }
            file_result = _transform_one_file(
                current_path=Path(current_pos_file),
                output_path=Path(output_pos_file),
                expected_url=expected_url,
                kind="pos",
                node_name=node_name,
            )

        result["pos"].append(file_result)
        result["changes"].extend(file_result["changes"])
        result["warnings"].extend(file_result["warnings"])
        result["errors"].extend(file_result["errors"])

    result["changes"] = list(dict.fromkeys(result["changes"]))
    result["warnings"] = list(dict.fromkeys(result["warnings"]))
    result["errors"] = list(dict.fromkeys(result["errors"]))

    if result["errors"]:
        result["status"] = "FAIL"
    elif not result["changes"]:
        result["status"] = "NO CHANGES"

    return result


def normalize_xmlrpc_url(
    value: str
) -> str:

    value = str(value or "").strip()

    match = re.search(
        r"http://[^\"< >]+",
        value
    )

    if match:
        return match.group(0)

    return value