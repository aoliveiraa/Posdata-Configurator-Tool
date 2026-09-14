from copy import deepcopy
from pathlib import Path

from lxml import etree

from src.utils.xml_loader import load_xml, save_xml

from src.transformers.performance_kvs_transformer import (
    apply_performance_kvs_configuration
)

LOWERCASE = "abcdefghijklmnopqrstuvwxyz"
UPPERCASE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def get_service_type(service):
    service_type = service.get("type", "")

    return service_type.strip().upper()


def get_service_name(service):
    service_name = service.get("name")

    if service_name is None:
        return None

    return str(service_name).strip()


def is_browser_section(section):
    section_name = section.get("name", "")

    return (
        section_name.upper()
        .startswith("COMPONENT.BROWSER.KVS")
    )


def find_services_container(tree):
    containers = tree.xpath("//Services")

    if not containers:
        raise ValueError(
            "The XML file does not contain "
            "a <Services> element."
        )

    return containers[0]


def find_kvs_service(tree, service_id):
    service_id = str(service_id).strip()

    services = tree.xpath(
        "//Service[translate("
        "@type, "
        f"'{LOWERCASE}', "
        f"'{UPPERCASE}'"
        ")='KVS']"
    )

    for service in services:
        if get_service_name(service) == service_id:
            return service

    return None


def find_npw_service(tree):

    #
    # Pattern 1
    #
    services = tree.xpath(
        "//Service[translate("
        "@type,"
        f"'{LOWERCASE}',"
        f"'{UPPERCASE}'"
        ")='NPW']"
    )

    if services:
        return services[0]

    #
    # Pattern 2
    #
    services = tree.xpath(
        "//Service"
    )

    for service in services:

        browser_sections = service.xpath(
            ".//Section[starts-with("
            "translate("
            "@name,"
            f"'{LOWERCASE}',"
            f"'{UPPERCASE}'"
            "),"
            "'COMPONENT.BROWSER.KVS'"
            ")]"
        )

        if browser_sections:
            return service

    #
    # Pattern 3
    #
    services = tree.xpath(
        "//Service[Configuration]"
    )

    for service in services:

        names = service.xpath(
            ".//Section/@name"
        )

        names_upper = [
            str(name).upper()
            for name in names
        ]

        if any(
            "BROWSER" in name
            for name in names_upper
        ):
            return service

    return None

def find_browser_sections(npw_service):
    if npw_service is None:
        return []

    sections = npw_service.xpath(
        ".//Section[@name]"
    )

    return [
        section
        for section in sections
        if is_browser_section(section)
    ]


def find_npw_configuration(npw_service):
    configurations = npw_service.xpath(
        "./Configuration"
    )

    if not configurations:
        return None

    return configurations[0]


def remove_browser_sections(npw_service):
    browser_sections = find_browser_sections(
        npw_service
    )

    for section in browser_sections:
        parent = section.getparent()

        if parent is not None:
            parent.remove(section)


def browser_section_key(section):
    return (
        section.get("name", "")
        .strip()
        .upper()
    )


def collect_source_data(
    new_posdata_folder,
    mapped_services
):
    new_posdata_folder = Path(
        new_posdata_folder
    )

    collected = []

    for mapped_service in mapped_services:
        service_id = mapped_service["service"]

        source_file_name = (
            mapped_service["source_file"]
        )

        source_file_path = (
            new_posdata_folder
            / source_file_name
        )

        if not source_file_path.exists():
            raise FileNotFoundError(
                "Source file not found: "
                f"{source_file_path}"
            )

        tree = load_xml(source_file_path)

        kvs_service = find_kvs_service(
            tree,
            service_id
        )

        if kvs_service is None:
            raise ValueError(
                f"KVS{service_id} was not found "
                f"inside {source_file_name}."
            )

        npw_service = find_npw_service(tree)

        if npw_service is not None:

            print(
                f"NPW FOUND "
                f"{source_file_name}"
            )

            print(
                f"TYPE="
                f"{npw_service.get('type')}"
            )

            print(
                f"NAME="
                f"{npw_service.get('name')}"
            )

        browser_sections = (
            find_browser_sections(npw_service)
        )

        collected.append({
            "service_id": service_id,
            "source_file": source_file_name,
            "tree": tree,
            "kvs_service": kvs_service,
            "npw_service": npw_service,
            "browser_sections": browser_sections
        })

    return collected


def create_base_tree(first_source_tree):
    source_root = first_source_tree.getroot()

    output_root = etree.Element(
        source_root.tag,
        attrib=dict(source_root.attrib),
        nsmap=source_root.nsmap
    )

    for child in source_root:

        if child.tag == "Services":
            continue

        output_root.append(
            deepcopy(child)
        )

    services_container = etree.SubElement(
        output_root,
        "Services"
    )

    output_tree = etree.ElementTree(
        output_root
    )

    return output_tree, services_container

def collect_reference_browser_sections(
    npw_template,
):
    """
    Collects Browser sections from the reference
    NPW before the template is cleaned.
    """

    reference_browsers = {}

    if npw_template is None:
        return reference_browsers

    for section in find_browser_sections(
        npw_template
    ):

        section_key = browser_section_key(
            section
        )

        if not section_key:
            continue

        reference_browsers[
            section_key
        ] = deepcopy(
            section
        )

    return reference_browsers

def create_shared_npw(
    collected_sources,
    reference_npw_template=None,
):
    warnings = []

    npw_template = None

    #
    # Priority 1:
    # NPW from the corresponding current Itona.
    #
    if reference_npw_template is not None:

        npw_template = deepcopy(
            reference_npw_template
        )

    #
    # Priority 2:
    # NPW contained in one of the new KVS files.
    #
    if npw_template is None:

        for source in collected_sources:

            source_npw = source.get(
                "npw_service"
            )

            if source_npw is None:
                continue

            npw_template = deepcopy(
                source_npw
            )

            break

    if npw_template is None:

        return None, [
            "No NPW template was found in "
            "the reference Itona or selected "
            "KVS source files."
        ]

    #
    # Save current/reference Browser sections
    # before cleaning the NPW template.
    #
    reference_browsers = (
        collect_reference_browser_sections(
            npw_template
        )
    )

    remove_browser_sections(
        npw_template
    )

    configuration = (
        find_npw_configuration(
            npw_template
        )
    )

    if configuration is None:

        return None, [
            "The NPW template does not contain "
            "a Configuration element."
        ]

    selected_browsers = []
    seen_browser_sections = set()

    for source in collected_sources:

        service_id = str(
            source["service_id"]
        ).strip().upper()

        expected_browser_name = (
            "COMPONENT.BROWSER.KVS"
            + service_id
        )

        source_browsers = source.get(
            "browser_sections",
            []
        )

        #
        # Priority 1:
        # Browser from the new KVS source.
        #
        matching_source_browsers = [
            section
            for section in source_browsers
            if browser_section_key(
                section
            )
            == expected_browser_name
        ]

        selected_section = None

        if matching_source_browsers:

            selected_section = deepcopy(
                matching_source_browsers[0]
            )

        #
        # Priority 2:
        # Browser from the current Itona NPW.
        #
        elif (
            expected_browser_name
            in reference_browsers
        ):

            selected_section = deepcopy(
                reference_browsers[
                    expected_browser_name
                ]
            )

            warnings.append(
                "Browser section reused from "
                "the reference Itona for "
                f"KVS{service_id}."
            )

        if selected_section is None:

            warnings.append(
                "Browser section was not found "
                f"for KVS{service_id} in either "
                "the new KVS source or the "
                "reference Itona."
            )

            continue

        section_key = browser_section_key(
            selected_section
        )

        if section_key in seen_browser_sections:
            continue

        selected_browsers.append(
            selected_section
        )

        seen_browser_sections.add(
            section_key
        )

    for browser_section in selected_browsers:

        configuration.append(
            browser_section
        )

    if not collected_sources:

        return None, [
            "No collected KVS sources were "
            "provided for the shared NPW."
        ]

    first_service_id = str(
        collected_sources[0][
            "service_id"
        ]
    ).strip()

    npw_template.set(
        "name",
        first_service_id
    )

    npw_template.set(
        "startonload",
        "true"
    )

    return npw_template, warnings

def validate_generated_itona(
    output_tree,
    expected_services
):
    errors = []

    nested_services = output_tree.xpath(
        "/PosDB/Services/Service//Service"
    )

    if nested_services:
        nested_descriptions = []

        for service in nested_services:
            service_type = service.get(
                "type",
                "UNKNOWN"
            )

            service_name = service.get(
                "name",
                "UNKNOWN"
            )

            nested_descriptions.append(
                f"{service_type}{service_name}"
            )

        errors.append(
            "Nested Service elements found: "
            + ", ".join(
                nested_descriptions
            )
        )

    kvs_services = output_tree.xpath(
        "/PosDB/Services/Service[translate("
        "@type, "
        f"'{LOWERCASE}', "
        f"'{UPPERCASE}'"
        ")='KVS']/@name"
    )

    npw_services = output_tree.xpath(
        "/PosDB/Services/Service[translate("
        "@type, "
        f"'{LOWERCASE}', "
        f"'{UPPERCASE}'"
        ")='NPW']"
    )

    browser_sections = output_tree.xpath(
        "//Service[translate("
        "@type, "
        f"'{LOWERCASE}', "
        f"'{UPPERCASE}'"
        ")='NPW']"
        "//Section[starts-with("
        "translate("
        "@name, "
        f"'{LOWERCASE}', "
        f"'{UPPERCASE}'"
        "), "
        "'COMPONENT.BROWSER.KVS'"
        ")]/@name"
    )

    normalized_expected = sorted(
        str(service).upper()
        for service in expected_services
    )

    normalized_found = sorted(
        str(service).upper()
        for service in kvs_services
    )

    direct_service_count = len(
        output_tree.xpath(
            "/PosDB/Services/Service"
        )
    )

    expected_direct_service_count = (
        len(normalized_expected) + 1
    )

    if (
        direct_service_count
        != expected_direct_service_count
    ):
        errors.append(
            "Expected "
            f"{expected_direct_service_count} direct "
            "Service elements inside <Services>, "
            f"but found {direct_service_count}."
        )

    if normalized_found != normalized_expected:
        errors.append(
            "Generated KVS services do not "
            "match the mapping."
        )

    if len(npw_services) != 1:
        errors.append(
            "The generated Itona must contain "
            "exactly one NPW service."
        )

    expected_browser_names = {
        f"COMPONENT.BROWSER.KVS{service}"
        for service in normalized_expected
    }

    generated_browser_names = {
        browser_name.upper()
        for browser_name in browser_sections
    }

    missing_browsers = (
        expected_browser_names
        - generated_browser_names
    )

    if missing_browsers:
        errors.append(
            "Missing Browser sections: "
            + ", ".join(
                sorted(missing_browsers)
            )
        )

    allowed_types = {
        "KVS",
        "NPW"
    }

    generated_types = {
        get_service_type(service)
        for service in output_tree.xpath(
            "//Services/Service"
        )
    }

    unexpected_types = (
        generated_types
        - allowed_types
    )

    if unexpected_types:
        errors.append(
            "Unexpected service types generated: "
            + ", ".join(
                sorted(unexpected_types)
            )
        )

    return errors


def generate_itona_file(
    mapping,
    new_posdata_folder,
    output_folder,
    reference_posdata_folder,
):
    if mapping["status"] != "READY":
        return {
            "machine": mapping["machine"],
            "generated": False,
            "output_file": None,
            "warnings": mapping["warnings"],
            "errors": [
                "Mapping status is not READY."
            ]
        }

    output_folder = Path(output_folder)

    output_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    unique_mapped_services = []
    seen_service_ids = set()

    for mapped_service in mapping[
        "mapped_services"
    ]:

        service_id = str(
            mapped_service["service"]
        ).strip().upper()

        if service_id in seen_service_ids:
            continue

        seen_service_ids.add(
            service_id
        )

        unique_mapped_services.append(
            mapped_service
        )

    collected_sources = collect_source_data(
        new_posdata_folder,
        unique_mapped_services
    )

    reference_npw_template, (
        reference_npw_warnings
        ) = load_reference_npw_template(
            reference_posdata_folder=
                reference_posdata_folder,
            machine=
                mapping["machine"],
        )

    first_source_tree = (
        collected_sources[0]["tree"]
    )

    output_tree, services_container = (
        create_base_tree(first_source_tree)
    )

    for source in collected_sources:
        services_container.append(
            deepcopy(source["kvs_service"])
        )

    shared_npw, warnings = (
        create_shared_npw(
            collected_sources=
                collected_sources,
            reference_npw_template=
                reference_npw_template,
        )
    )

    warnings = (
        reference_npw_warnings
        + warnings
    )

    if shared_npw is None:
        return {
            "machine": mapping["machine"],
            "generated": False,
            "output_file": None,
            "warnings": warnings,
            "errors": [
                "Unable to create the shared NPW."
            ]
        }

    services_container.append(shared_npw)

    performance_result = (
        apply_performance_kvs_configuration(
            generated_tree=output_tree
        )
    )

    warnings.extend(
        performance_result["warnings"]
    )

    if performance_result["errors"]:

        return {
            "machine": mapping["machine"],
            "generated": False,
            "output_file": None,
            "warnings": warnings,
            "errors": (
                performance_result["errors"]
            ),
            "changes": (
                performance_result["changes"]
            )
        }

    expected_services = [
        service["service"]
        for service in unique_mapped_services
    ]

    validation_errors = (
        validate_generated_itona(
            output_tree,
            expected_services
        )
    )

    if validation_errors:

        return {
            "machine":
                mapping["machine"],
            "generated":
                False,
            "output_file":
                None,
            "warnings":
                warnings,
            "errors":
                validation_errors,
            "changes":
                performance_result[
                    "changes"
                ],
        }
    
    output_path = (
        output_folder
        / mapping["target_file"]
    )

    etree.indent(
        output_tree,
        space="  "
    )

    save_xml(
        output_tree,
        output_path
    )

    validation_tree = load_xml(output_path)

    post_save_errors = validate_generated_itona(
        validation_tree,
        expected_services
    )

    if post_save_errors:
        output_path.unlink(
            missing_ok=True
        )

        return {
            "machine": mapping["machine"],
            "generated": False,
            "output_file": None,
            "warnings": warnings,
            "errors": post_save_errors,
            "changes": []
        }

    return {
        "machine": mapping["machine"],
        "generated": True,
        "output_file": str(output_path),
        "warnings": warnings,
        "errors": [],
        "changes": []
    }

def generate_all_itonas(
    kvs_mapping,
    new_posdata_folder,
    output_folder="output/itonas",
    reference_posdata_folder=(
        "samples/current_posdata"
    ),
):
    results = []

    for mapping in (
        kvs_mapping["mappings"]
    ):

        result = generate_itona_file(
            mapping=mapping,
            new_posdata_folder=
                new_posdata_folder,
            output_folder=
                output_folder,
            reference_posdata_folder=
                reference_posdata_folder,
        )

        results.append(
            result
        )

    return results


def load_reference_npw_template(
    reference_posdata_folder,
    machine,
):
    """
    Loads the NPW template from the corresponding
    current Itona reference file.

    Example:
        machine = Itona1
        file = _Itona1_pos-db.xml
    """

    reference_file = (
        Path(reference_posdata_folder)
        / f"_{machine}_pos-db.xml"
    )

    if not reference_file.is_file():

        return None, [
            "Reference Itona file was not found: "
            f"{reference_file}"
        ]

    try:

        reference_tree = load_xml(
            reference_file
        )

    except Exception as error:

        return None, [
            "Unable to load reference Itona "
            f"{reference_file.name}: {error}"
        ]

    npw_service = find_npw_service(
        reference_tree
    )

    if npw_service is None:

        return None, [
            "NPW service was not found in "
            f"reference Itona {reference_file.name}."
        ]

    return deepcopy(
        npw_service
    ), []



