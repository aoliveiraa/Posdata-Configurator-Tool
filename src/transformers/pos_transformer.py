from pathlib import Path

from lxml import etree

from src.utils.xml_loader import (
    load_xml,
    save_xml
)


LOWERCASE = "abcdefghijklmnopqrstuvwxyz"
UPPERCASE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

COORDINATOR_JAVASCRIPT_CODE = (
    "ClickPOSButtonHelper,"
    "MessageHubResponseHelper"
)


def normalize_text(value):
    if value is None:
        return ""

    return str(value).strip()


def normalize_upper(value):
    return normalize_text(value).upper()


def find_direct_services(
    tree,
    service_type
):
    expected_type = normalize_upper(
        service_type
    )

    return tree.xpath(
        "/PosDB/Services/Service[translate("
        "@type, "
        f"'{LOWERCASE}', "
        f"'{UPPERCASE}'"
        f")='{expected_type}']"
    )


def find_parameter(
    parent,
    parameter_name
):
    expected_name = normalize_upper(
        parameter_name
    )

    for parameter in parent.xpath(
        "./Parameter[@name]"
    ):
        current_name = normalize_upper(
            parameter.get("name")
        )

        if current_name == expected_name:
            return parameter

    return None


def set_parameter(
    parent,
    parameter_name,
    parameter_value
):
    parameter = find_parameter(
        parent,
        parameter_name
    )

    created = False
    old_value = None

    if parameter is None:
        parameter = etree.SubElement(
            parent,
            "Parameter"
        )

        parameter.set(
            "name",
            parameter_name
        )

        created = True

    else:
        old_value = parameter.get(
            "value"
        )

    new_value = str(
        parameter_value
    )

    parameter.set(
        "value",
        new_value
    )

    return {
        "created": created,
        "changed": (
            created
            or old_value != new_value
        ),
        "old_value": old_value,
        "new_value": new_value
    }


def get_direct_configuration(service):
    configurations = service.xpath(
        "./Configuration"
    )

    if not configurations:
        return None

    return configurations[0]


def get_section(
    configuration,
    section_name
):
    expected_name = normalize_upper(
        section_name
    )

    for section in configuration.xpath(
        "./Section[@name]"
    ):
        current_name = normalize_upper(
            section.get("name")
        )

        if current_name == expected_name:
            return section

    return None


def ensure_section(
    configuration,
    section_name
):
    section = get_section(
        configuration,
        section_name
    )

    created = False

    if section is None:
        section = etree.SubElement(
            configuration,
            "Section"
        )

        section.set(
            "name",
            section_name
        )

        created = True

    return section, created


def find_pos_browser_sections(tree):
    sections = tree.xpath(
        "/PosDB/Services/Service/"
        "Configuration/Section[@name]"
    )

    return [
        section
        for section in sections
        if normalize_upper(
            section.get("name")
        ).startswith(
            "COMPONENT.BROWSER.POS"
        )
    ]


def select_main_pos_browser(
    tree,
    node_name
):
    expected_section_name = (
        f"COMPONENT.BROWSER.{node_name}"
    ).upper()

    browser_sections = (
        find_pos_browser_sections(tree)
    )

    for section in browser_sections:
        current_name = normalize_upper(
            section.get("name")
        )

        if current_name == expected_section_name:
            return section

    if len(browser_sections) == 1:
        return browser_sections[0]

    return None


def configure_pos_browser(
    browser_section,
    node_name
):
    changes = []

    expected_section_name = (
        f"Component.Browser.{node_name}"
    )

    old_section_name = (
        browser_section.get("name")
    )

    if old_section_name != expected_section_name:
        browser_section.set(
            "name",
            expected_section_name
        )

        changes.append(
            "Browser section renamed: "
            f"{old_section_name} -> "
            f"{expected_section_name}."
        )

    required_parameters = {
        "BrowserServer": "messagehub",
        "NodeName": node_name,
        "LogicalName": node_name,
        "InjectJavascriptCode": (
            COORDINATOR_JAVASCRIPT_CODE
        ),
        "Urn": f"POS/{node_name}"
    }

    for parameter_name, expected_value in (
        required_parameters.items()
    ):
        result = set_parameter(
            browser_section,
            parameter_name,
            expected_value
        )

        if not result["changed"]:
            continue

        action = (
            "created"
            if result["created"]
            else "updated"
        )

        changes.append(
            f"{parameter_name} {action} "
            f"for {node_name}: "
            f"{result['old_value']} -> "
            f"{result['new_value']}."
        )

    return changes


def configure_auto_update(tree):
    changes = []
    configured_count = 0

    npw_services = find_direct_services(
        tree,
        "NPW"
    )

    if not npw_services:
        return {
            "configured": False,
            "changes": changes,
            "error": (
                "No direct NPW service "
                "was found."
            )
        }

    for npw_service in npw_services:
        configuration = (
            get_direct_configuration(
                npw_service
            )
        )

        if configuration is None:
            continue

        auto_update, created_section = (
            ensure_section(
                configuration,
                "AutoUpdate"
            )
        )

        result = set_parameter(
            auto_update,
            "EnableAutoUpdate",
            "true"
        )

        if created_section:
            changes.append(
                "AutoUpdate section created."
            )

        if result["changed"]:
            changes.append(
                "EnableAutoUpdate set to true."
            )

        configured_count += 1

    if configured_count == 0:
        return {
            "configured": False,
            "changes": changes,
            "error": (
                "No NPW Configuration element "
                "was available."
            )
        }

    return {
        "configured": True,
        "changes": changes,
        "error": None
    }


def disable_hardware_services(tree):
    changes = []

    blocked_service_types = {
        "BUMPBAR",
        "SCANNER",
        "PRINTER",
        "CDR",
        "CASHDRAWER"
    }

    services = tree.xpath(
        "/PosDB/Services/Service"
    )

    for service in services:
        service_type = normalize_upper(
            service.get("type")
        )

        classname = normalize_upper(
            service.get("classname")
        )

        should_disable = (
            service_type
            in blocked_service_types
            or "SCANNER" in classname
            or "BUMPBAR" in classname
            or "CASHDRAWER" in classname
            or "CASHDRAW" in classname
        )

        if not should_disable:
            continue

        old_value = service.get(
            "startonload"
        )

        service.set(
            "startonload",
            "false"
        )

        if normalize_text(
            old_value
        ).lower() != "false":
            changes.append(
                f"Service {service_type} "
                "startonload changed: "
                f"{old_value} -> false."
            )

    return changes


def disable_hardware_adaptors(tree):
    changes = []

    blocked_patterns = (
        "SCANNER",
        "BUMPBAR",
        "CASHDRAWER",
        "CASHDRAW"
    )

    adaptors = tree.xpath(
        "/PosDB/Services/Service/"
        "Adaptors/Adaptor"
    )

    for adaptor in adaptors:
        name = normalize_upper(
            adaptor.get("name")
        )

        imports_name = normalize_upper(
            adaptor.get("imports")
        )

        should_disable = any(
            pattern in name
            or pattern in imports_name
            for pattern in blocked_patterns
        )

        if not should_disable:
            continue

        old_value = adaptor.get(
            "startonload"
        )

        adaptor.set(
            "startonload",
            "false"
        )

        if normalize_text(
            old_value
        ).lower() != "false":
            adaptor_name = (
                adaptor.get("name")
                or adaptor.get("imports")
                or "UNKNOWN"
            )

            changes.append(
                f"Adaptor {adaptor_name} "
                "startonload changed: "
                f"{old_value} -> false."
            )

    return changes


def validate_pos_tree(
    tree,
    node_name
):
    errors = []
    warnings = []

    nested_services = tree.xpath(
        "/PosDB/Services/Service//Service"
    )

    if nested_services:
        errors.append(
            "Nested Service elements found."
        )

    browser_sections = (
        find_pos_browser_sections(tree)
    )

    expected_section_name = (
        f"COMPONENT.BROWSER.{node_name}"
    ).upper()

    matching_browsers = [
        section
        for section in browser_sections
        if normalize_upper(
            section.get("name")
        ) == expected_section_name
    ]

    if len(matching_browsers) != 1:
        errors.append(
            "Expected exactly one Browser "
            f"for {node_name}, but found "
            f"{len(matching_browsers)}."
        )

        return {
            "errors": errors,
            "warnings": warnings
        }

    browser = matching_browsers[0]

    expected_parameters = {
        "BrowserServer": "messagehub",
        "NodeName": node_name,
        "LogicalName": node_name,
        "InjectJavascriptCode": (
            COORDINATOR_JAVASCRIPT_CODE
        ),
        "Urn": f"POS/{node_name}"
    }

    for parameter_name, expected_value in (
        expected_parameters.items()
    ):
        parameter = find_parameter(
            browser,
            parameter_name
        )

        if parameter is None:
            errors.append(
                f"{parameter_name} was not "
                f"found for {node_name}."
            )

            continue

        actual_value = parameter.get(
            "value",
            ""
        )

        if actual_value != expected_value:
            errors.append(
                f"{parameter_name} has an "
                f"invalid value for {node_name}. "
                f"Expected '{expected_value}', "
                f"found '{actual_value}'."
            )

    npw_services = find_direct_services(
        tree,
        "NPW"
    )

    if not npw_services:
        errors.append(
            f"No NPW service found for "
            f"{node_name}."
        )

    auto_update_parameters = tree.xpath(
        "/PosDB/Services/Service["
        "translate("
        "@type, "
        f"'{LOWERCASE}', "
        f"'{UPPERCASE}'"
        ")='NPW']"
        "/Configuration/"
        "Section[translate("
        "@name, "
        f"'{LOWERCASE}', "
        f"'{UPPERCASE}'"
        ")='AUTOUPDATE']"
        "/Parameter[translate("
        "@name, "
        f"'{LOWERCASE}', "
        f"'{UPPERCASE}'"
        ")='ENABLEAUTOUPDATE']"
    )

    if not auto_update_parameters:
        errors.append(
            "EnableAutoUpdate was not found."
        )

    elif not any(
        normalize_text(
            parameter.get("value")
        ).lower() == "true"
        for parameter in auto_update_parameters
    ):
        errors.append(
            "EnableAutoUpdate is not true."
        )

    errors = list(
        dict.fromkeys(errors)
    )

    warnings = list(
        dict.fromkeys(warnings)
    )

    return {
        "errors": errors,
        "warnings": warnings
    }


def build_result(
    node_name,
    generated,
    source_file,
    machine_info=None,
    output_filename=None,
    output_path=None,
    changes=None,
    warnings=None,
    errors=None
):
    return {
        "node_name": node_name,
        "generated": generated,
        "source_file": source_file,
        "machine_file": (
            machine_info.get(
                "machine_file"
            )
            if machine_info
            else None
        ),
        "machine_ip": (
            machine_info.get("ip")
            if machine_info
            else None
        ),
        "rio_output_file": (
            output_filename
        ),
        "output_file": (
            str(output_path)
            if output_path
            else None
        ),
        "changes": changes or [],
        "warnings": warnings or [],
        "errors": errors or []
    }


def generate_pos_file(
    mapping,
    pos_machine_lookup,
    new_posdata_folder,
    output_folder
):
    node_name = normalize_upper(
        mapping.get("node_name")
    )

    source_file = mapping.get(
        "source_file"
    )

    machine_info = (
        pos_machine_lookup.get(
            node_name
        )
    )

    if not node_name:
        return build_result(
            node_name="UNKNOWN",
            generated=False,
            source_file=source_file,
            errors=[
                "POS mapping does not contain "
                "a valid node_name."
            ]
        )

    if mapping.get("status") != "READY":
        return build_result(
            node_name=node_name,
            generated=False,
            source_file=source_file,
            machine_info=machine_info,
            warnings=mapping.get(
                "warnings",
                []
            ),
            errors=[
                "POS mapping status "
                "is not READY."
            ]
        )

    if machine_info is None:
        return build_result(
            node_name=node_name,
            generated=False,
            source_file=source_file,
            errors=[
                "Machine discovery was not found "
                f"for {node_name}."
            ]
        )

    output_filename = machine_info.get(
        "output_file"
    )

    if not output_filename:
        return build_result(
            node_name=node_name,
            generated=False,
            source_file=source_file,
            machine_info=machine_info,
            errors=[
                "RIO output file was not defined "
                f"for {node_name}."
            ]
        )

    new_posdata_folder = Path(
        new_posdata_folder
    )

    output_folder = Path(
        output_folder
    )

    output_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    source_path = (
        new_posdata_folder
        / source_file
    )

    output_path = (
        output_folder
        / output_filename
    )

    if not source_path.exists():
        return build_result(
            node_name=node_name,
            generated=False,
            source_file=source_file,
            machine_info=machine_info,
            output_filename=output_filename,
            errors=[
                "Source POS file not found: "
                f"{source_path}"
            ]
        )

    try:
        tree = load_xml(
            source_path
        )

    except Exception as error:
        return build_result(
            node_name=node_name,
            generated=False,
            source_file=source_file,
            machine_info=machine_info,
            output_filename=output_filename,
            errors=[
                "Unable to load source POS file: "
                f"{error}"
            ]
        )

    changes = []
    warnings = []
    errors = []

    browser_section = (
        select_main_pos_browser(
            tree,
            node_name
        )
    )

    if browser_section is None:
        errors.append(
            "Unable to identify a unique "
            f"POS Browser for {node_name}."
        )

    else:
        changes.extend(
            configure_pos_browser(
                browser_section,
                node_name
            )
        )

    auto_update_result = (
        configure_auto_update(tree)
    )

    changes.extend(
        auto_update_result["changes"]
    )

    if auto_update_result["error"]:
        errors.append(
            auto_update_result["error"]
        )

    changes.extend(
        disable_hardware_services(tree)
    )

    changes.extend(
        disable_hardware_adaptors(tree)
    )

    validation = validate_pos_tree(
        tree,
        node_name
    )

    errors.extend(
        validation["errors"]
    )

    warnings.extend(
        validation["warnings"]
    )

    errors = list(
        dict.fromkeys(errors)
    )

    warnings = list(
        dict.fromkeys(warnings)
    )

    changes = list(
        dict.fromkeys(changes)
    )

    if errors:
        return build_result(
            node_name=node_name,
            generated=False,
            source_file=source_file,
            machine_info=machine_info,
            output_filename=output_filename,
            changes=changes,
            warnings=warnings,
            errors=errors
        )

    etree.indent(
        tree,
        space="  "
    )

    try:
        save_xml(
            tree,
            output_path
        )

    except Exception as error:
        return build_result(
            node_name=node_name,
            generated=False,
            source_file=source_file,
            machine_info=machine_info,
            output_filename=output_filename,
            changes=changes,
            warnings=warnings,
            errors=[
                "Unable to save generated POS: "
                f"{error}"
            ]
        )

    try:
        saved_tree = load_xml(
            output_path
        )

        post_save_validation = (
            validate_pos_tree(
                saved_tree,
                node_name
            )
        )

    except Exception as error:
        output_path.unlink(
            missing_ok=True
        )

        return build_result(
            node_name=node_name,
            generated=False,
            source_file=source_file,
            machine_info=machine_info,
            output_filename=output_filename,
            changes=changes,
            warnings=warnings,
            errors=[
                "Unable to validate generated "
                f"POS file: {error}"
            ]
        )

    if post_save_validation["errors"]:
        output_path.unlink(
            missing_ok=True
        )

        return build_result(
            node_name=node_name,
            generated=False,
            source_file=source_file,
            machine_info=machine_info,
            output_filename=output_filename,
            changes=changes,
            warnings=warnings,
            errors=(
                post_save_validation[
                    "errors"
                ]
            )
        )

    return build_result(
        node_name=node_name,
        generated=True,
        source_file=source_file,
        machine_info=machine_info,
        output_filename=output_filename,
        output_path=output_path,
        changes=changes,
        warnings=warnings,
        errors=[]
    )


def generate_all_pos(
    pos_mapping,
    pos_machine_lookup,
    new_posdata_folder,
    output_folder="output/pos"
):
    results = []

    mappings = pos_mapping.get(
        "mappings",
        []
    )

    for mapping in mappings:
        result = generate_pos_file(
            mapping=mapping,
            pos_machine_lookup=(
                pos_machine_lookup
            ),
            new_posdata_folder=(
                new_posdata_folder
            ),
            output_folder=output_folder
        )

        results.append(result)

    return results