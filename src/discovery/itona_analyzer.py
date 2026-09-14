from pathlib import Path
import re

from src.utils.config_loader import load_json_config
from src.utils.xml_loader import load_xml


def normalize_service_name(service_name):

    if service_name is None:
        return None

    return str(service_name).strip().upper()


def normalize_kvs_node(service_name):

    normalized = normalize_service_name(service_name)

    if not normalized:
        return None

    if normalized.startswith("KVS"):
        return normalized

    return f"KVS{normalized}"


def extract_browser_node(section_name):

    if not section_name:
        return None

    match = re.search(
        r"COMPONENT\.BROWSER\.(KVS\d+)",
        section_name.upper()
    )

    if match:
        return match.group(1)

    return None


def analyze_itona_file(
    itona_name,
    file_path
):

    tree = load_xml(file_path)

    kvs_services = []

    for service in tree.xpath(
        "//Service[translate(@type, "
        "'abcdefghijklmnopqrstuvwxyz', "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ')='KVS']"
    ):

        service_name = normalize_service_name(
            service.get("name")
        )

        if service_name:
            kvs_services.append(service_name)

    npw_services = []

    for service in tree.xpath(
        "//Service[translate(@type, "
        "'abcdefghijklmnopqrstuvwxyz', "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ')='NPW']"
    ):

        service_name = normalize_service_name(
            service.get("name")
        )

        if service_name:
            npw_services.append(service_name)

    browser_nodes = []

    for section in tree.xpath(
        "//Service[translate(@type, "
        "'abcdefghijklmnopqrstuvwxyz', "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ')='NPW']"
        "//Section[@name]"
    ):

        browser_node = extract_browser_node(
            section.get("name")
        )

        if (
            browser_node
            and browser_node not in browser_nodes
        ):
            browser_nodes.append(browser_node)

    expected_browser_nodes = [
        normalize_kvs_node(service_name)
        for service_name in kvs_services
    ]

    missing_browser_nodes = [
        node_name
        for node_name in expected_browser_nodes
        if node_name not in browser_nodes
    ]

    extra_browser_nodes = [
        node_name
        for node_name in browser_nodes
        if node_name not in expected_browser_nodes
    ]

    warnings = []

    if not npw_services:
        warnings.append(
            "No NPW service was found."
        )

    if missing_browser_nodes:
        warnings.append(
            "KVS nodes without Browser section: "
            + ", ".join(missing_browser_nodes)
        )

    if extra_browser_nodes:
        warnings.append(
            "Browser sections without active KVS service: "
            + ", ".join(extra_browser_nodes)
        )

    return {
        "machine": itona_name,
        "file": file_path.name,
        "found": True,
        "kvs_count": len(kvs_services),
        "kvs_services": kvs_services,
        "npw_services": npw_services,
        "browser_nodes": browser_nodes,
        "expected_browser_nodes": expected_browser_nodes,
        "missing_browser_nodes": missing_browser_nodes,
        "extra_browser_nodes": extra_browser_nodes,
        "webview_complete": (
            bool(npw_services)
            and not missing_browser_nodes
        ),
        "warnings": warnings
    }


def analyze_itonas(
    folder,
    config_path="config/rio_lab.json"
):

    folder = Path(folder)

    config = load_json_config(config_path)

    active_itonas = config["scope"]["active_itonas"]

    results = []

    for itona_name in active_itonas:

        expected_file = (
            folder
            / f"_{itona_name}_pos-db.xml"
        )

        if not expected_file.exists():

            results.append({
                "machine": itona_name,
                "file": expected_file.name,
                "found": False,
                "kvs_count": 0,
                "kvs_services": [],
                "npw_services": [],
                "browser_nodes": [],
                "expected_browser_nodes": [],
                "missing_browser_nodes": [],
                "extra_browser_nodes": [],
                "webview_complete": False,
                "warnings": [
                    "Reference Itona file not found."
                ]
            })

            continue

        result = analyze_itona_file(
            itona_name,
            expected_file
        )

        results.append(result)

    return results