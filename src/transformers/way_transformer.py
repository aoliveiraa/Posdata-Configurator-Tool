from pathlib import Path
from urllib.parse import urlparse, urlunparse

from lxml import etree

from src.utils.config_loader import load_json_config
from src.utils.xml_loader import load_xml, save_xml


from pathlib import Path
from urllib.parse import urlparse, urlunparse

from lxml import etree

from src.transformers.foe_transformer import (
    ensure_foe_standard,
    validate_foe,
)
from src.utils.config_loader import load_json_config
from src.utils.xml_loader import load_xml, save_xml

LOWERCASE = "abcdefghijklmnopqrstuvwxyz"
UPPERCASE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def normalize_text(value):
    if value is None:
        return ""

    return str(value).strip()


def normalize_upper(value):
    return normalize_text(value).upper()


def find_direct_services(tree, service_type):
    expected_type = normalize_upper(service_type)

    return tree.xpath(
        "/PosDB/Services/Service[translate("
        "@type, "
        f"'{LOWERCASE}', "
        f"'{UPPERCASE}'"
        f")='{expected_type}']"
    )


def find_direct_section(parent, section_name):
    expected_name = normalize_upper(section_name)

    for section in parent.xpath(
        "./Section[@name]"
    ):
        current_name = normalize_upper(
            section.get("name")
        )

        if current_name == expected_name:
            return section

    return None


def find_direct_parameter(parent, parameter_name):
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


def set_direct_parameter(
    parent,
    parameter_name,
    parameter_value
):
    parameter = find_direct_parameter(
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
        old_value = parameter.get("value")

    new_value = str(parameter_value)

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


def ensure_root_configuration(tree):
    configurations = tree.xpath(
        "/PosDB/Configuration"
    )

    if configurations:
        return configurations[0], False

    root = tree.getroot()

    configuration = etree.Element(
        "Configuration"
    )

    configuration.set(
        "imports",
        "Store.wide"
    )

    services = root.find("Services")

    if services is not None:
        services_position = root.index(
            services
        )

        root.insert(
            services_position,
            configuration
        )

    else:
        root.append(configuration)

    return configuration, True


def ensure_messaging_network_base(
    tree,
    network_base
):
    changes = []

    configuration, configuration_created = (
        ensure_root_configuration(tree)
    )

    if configuration_created:
        changes.append(
            "Root Configuration created."
        )

    messaging = find_direct_section(
        configuration,
        "Messaging"
    )

    if messaging is None:
        messaging = etree.SubElement(
            configuration,
            "Section"
        )

        messaging.set(
            "name",
            "Messaging"
        )

        changes.append(
            "Active Messaging section created."
        )

    parameter_result = set_direct_parameter(
        messaging,
        "networkAdaptorBaseIp",
        network_base
    )

    if parameter_result["changed"]:
        action = (
            "created"
            if parameter_result["created"]
            else "updated"
        )

        changes.append(
            "networkAdaptorBaseIp "
            f"{action}: "
            f"{parameter_result['old_value']} "
            f"-> {parameter_result['new_value']}."
        )

    return changes


def replace_url_host(url_value, new_host):
    if not url_value:
        return url_value

    parsed = urlparse(url_value)

    if not parsed.scheme or not parsed.netloc:
        return url_value

    port = parsed.port

    new_netloc = new_host

    if port:
        new_netloc = f"{new_host}:{port}"

    return urlunparse(
        (
            parsed.scheme,
            new_netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        )
    )


def update_xmlrpccli_urls(tree, way_ip):
    changes = []

    adaptors = tree.xpath(
        "/PosDB/Services/Service/"
        "Adaptors/Adaptor[@name or @imports]"
    )

    for adaptor in adaptors:
        adaptor_name = normalize_upper(
            adaptor.get("name")
        )

        adaptor_imports = normalize_upper(
            adaptor.get("imports")
        )

        if (
            adaptor_name != "XMLRPCCLI"
            and adaptor_imports != "XMLRPCCLI"
        ):
            continue

        main_section = find_direct_section(
            adaptor,
            "main"
        )

        if main_section is None:
            continue

        url_parameter = find_direct_parameter(
            main_section,
            "url"
        )

        if url_parameter is None:
            continue

        old_url = url_parameter.get(
            "value",
            ""
        )

        new_url = replace_url_host(
            old_url,
            way_ip
        )

        if new_url == old_url:
            continue

        url_parameter.set(
            "value",
            new_url
        )

        service = adaptor.getparent()

        while (
            service is not None
            and service.tag != "Service"
        ):
            service = service.getparent()

        service_description = "UNKNOWN"

        if service is not None:
            service_description = (
                f"{service.get('type', 'UNKNOWN')}"
                f"{service.get('name', '')}"
            )

        changes.append(
            f"xmlrpccli URL updated in "
            f"{service_description}: "
            f"{old_url} -> {new_url}."
        )

    return changes


def find_used_service(
    service,
    service_type
):
    expected_type = normalize_upper(
        service_type
    )

    for used_service in service.xpath(
        "./UsedServices/UsedService"
    ):
        current_type = normalize_upper(
            used_service.get(
                "serviceType"
            )
        )

        if current_type == expected_type:
            return used_service

    return None


def ensure_used_services_container(service):
    containers = service.xpath(
        "./UsedServices"
    )

    if containers:
        return containers[0]

    return etree.SubElement(
        service,
        "UsedServices"
    )


def ensure_used_service(
    service,
    service_type
):
    used_service = find_used_service(
        service,
        service_type
    )

    if used_service is not None:
        return used_service, False

    container = ensure_used_services_container(
        service
    )

    used_service = etree.SubElement(
        container,
        "UsedService"
    )

    used_service.set(
        "serviceType",
        service_type
    )

    return used_service, True


def member_exists(
    used_service,
    member_name,
    member_alias=None
):
    expected_name = normalize_text(
        member_name
    )

    expected_alias = (
        None
        if member_alias is None
        else normalize_text(member_alias)
    )

    for member in used_service.xpath(
        "./Member"
    ):
        current_name = normalize_text(
            member.get("name")
        )

        current_alias = normalize_text(
            member.get("alias")
        )

        if current_name != expected_name:
            continue

        if (
            expected_alias is None
            or current_alias == expected_alias
        ):
            return True

    return False


def add_member_if_missing(
    used_service,
    member_name,
    member_alias=""
):
    if member_exists(
        used_service,
        member_name,
        member_alias
    ):
        return False

    member = etree.SubElement(
        used_service,
        "Member"
    )

    member.set(
        "name",
        str(member_name)
    )

    member.set(
        "alias",
        str(member_alias)
    )

    return True


def ensure_psw_pos_members(
    tree,
    pos_service_ids
):
    changes = []
    warnings = []

    psw_services = find_direct_services(
        tree,
        "PSW"
    )

    if not psw_services:
        warnings.append(
            "PSW service was not found."
        )

        return changes, warnings

    for psw_service in psw_services:
        used_service, created = (
            ensure_used_service(
                psw_service,
                "POS"
            )
        )

        if created:
            changes.append(
                "UsedService POS created "
                "inside PSW."
            )

        for service_id in pos_service_ids:
            if add_member_if_missing(
                used_service,
                service_id,
                ""
            ):
                changes.append(
                    "POS member added to PSW: "
                    f"{service_id}."
                )

    return changes, warnings


def ensure_way_pos_members(
    tree,
    pos_service_ids
):
    changes = []
    warnings = []

    way_services = find_direct_services(
        tree,
        "WAY"
    )

    if not way_services:
        warnings.append(
            "WAY service was not found."
        )

        return changes, warnings

    for way_service in way_services:
        used_service, created = (
            ensure_used_service(
                way_service,
                "POS"
            )
        )

        if created:
            changes.append(
                "UsedService POS created "
                "inside WAY."
            )

        for service_id in pos_service_ids:
            if add_member_if_missing(
                used_service,
                service_id,
                ""
            ):
                changes.append(
                    "POS member added to WAY: "
                    f"{service_id}."
                )

    return changes, warnings


def ensure_way_sto_members(
    tree,
    pos_service_ids
):
    changes = []
    warnings = []

    way_services = find_direct_services(
        tree,
        "WAY"
    )

    if not way_services:
        warnings.append(
            "WAY service was not found "
            "for STO validation."
        )

        return changes, warnings

    for way_service in way_services:
        used_service, created = (
            ensure_used_service(
                way_service,
                "STO"
            )
        )

        if created:
            changes.append(
                "UsedService STO created "
                "inside WAY."
            )

        for service_id in pos_service_ids:
            alias = f"POS{service_id}"

            if add_member_if_missing(
                used_service,
                service_id,
                alias
            ):
                changes.append(
                    "STO member added to WAY: "
                    f"{service_id} / {alias}."
                )

    return changes, warnings


def force_way_npw_disabled(tree):
    changes = []

    npw_services = find_direct_services(
        tree,
        "NPW"
    )

    for npw_service in npw_services:
        old_value = npw_service.get(
            "startonload"
        )

        npw_service.set(
            "startonload",
            "false"
        )

        if old_value != "false":
            changes.append(
                "WAY NPW startonload changed: "
                f"{old_value} -> false."
            )

    return changes


def validate_way_tree(
    tree,
    network_base,
    way_ip,
    pos_service_ids
):
    errors = []
    warnings = []

    way_services = find_direct_services(
        tree,
        "WAY"
    )

    if len(way_services) != 1:
        errors.append(
            "Expected exactly one direct WAY "
            f"service, but found "
            f"{len(way_services)}."
        )

    messaging_parameters = tree.xpath(
        "/PosDB/Configuration/"
        "Section[translate("
        "@name, "
        f"'{LOWERCASE}', "
        f"'{UPPERCASE}'"
        ")='MESSAGING']/"
        "Parameter[translate("
        "@name, "
        f"'{LOWERCASE}', "
        f"'{UPPERCASE}'"
        ")='NETWORKADAPTORBASEIP']"
    )

    if not messaging_parameters:
        errors.append(
            "Active networkAdaptorBaseIp "
            "was not found."
        )

    elif messaging_parameters[0].get(
        "value"
    ) != network_base:
        errors.append(
            "networkAdaptorBaseIp does not "
            f"equal {network_base}."
        )

    xmlrpc_urls = tree.xpath(
        "/PosDB/Services/Service/"
        "Adaptors/Adaptor["
        "translate("
        "@name, "
        f"'{LOWERCASE}', "
        f"'{UPPERCASE}'"
        ")='XMLRPCCLI' "
        "or translate("
        "@imports, "
        f"'{LOWERCASE}', "
        f"'{UPPERCASE}'"
        ")='XMLRPCCLI'"
        "]/Section/"
        "Parameter[translate("
        "@name, "
        f"'{LOWERCASE}', "
        f"'{UPPERCASE}'"
        ")='URL']/@value"
    )

    for url_value in xmlrpc_urls:
        parsed = urlparse(url_value)

        if parsed.hostname != way_ip:
            errors.append(
                "xmlrpccli URL still points "
                f"to {parsed.hostname}: "
                f"{url_value}"
            )

    for psw_service in find_direct_services(
        tree,
        "PSW"
    ):
        used_pos = find_used_service(
            psw_service,
            "POS"
        )

        if used_pos is None:
            errors.append(
                "PSW does not contain "
                "UsedService POS."
            )
            continue

        for service_id in pos_service_ids:
            if not member_exists(
                used_pos,
                service_id
            ):
                errors.append(
                    "PSW is missing POS member "
                    f"{service_id}."
                )

    for way_service in way_services:
        used_pos = find_used_service(
            way_service,
            "POS"
        )

        used_sto = find_used_service(
            way_service,
            "STO"
        )

        if used_pos is None:
            errors.append(
                "WAY does not contain "
                "UsedService POS."
            )

        else:
            for service_id in pos_service_ids:
                if not member_exists(
                    used_pos,
                    service_id
                ):
                    errors.append(
                        "WAY POS references are "
                        f"missing {service_id}."
                    )

        if used_sto is None:
            errors.append(
                "WAY does not contain "
                "UsedService STO."
            )

        else:
            for service_id in pos_service_ids:
                alias = f"POS{service_id}"

                if not member_exists(
                    used_sto,
                    service_id,
                    alias
                ):
                    errors.append(
                        "WAY STO references are "
                        "missing "
                        f"{service_id}/{alias}."
                    )

    for npw_service in find_direct_services(
        tree,
        "NPW"
    ):
        if normalize_text(
            npw_service.get(
                "startonload"
            )
        ).lower() != "false":
            errors.append(
                "WAY NPW must have "
                "startonload=false."
            )

    nested_services = tree.xpath(
        "/PosDB/Services/Service//Service"
    )

    if nested_services:
        errors.append(
            "Nested Service elements found."
        )

    errors = list(dict.fromkeys(errors))
    warnings = list(
        dict.fromkeys(warnings)
    )

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "xmlrpc_urls_found": len(
            xmlrpc_urls
        )
    }


def generate_way_file(
    new_posdata_folder,
    output_folder="output/way",
    config_path="config/rio_lab.json"
):
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

    config = load_json_config(
        config_path
    )

    source_path = (
        new_posdata_folder
        / "_WAYSTATION_pos-db.xml"
    )

    output_path = (
        output_folder
        / "_WAYSTATION_pos-db.xml"
    )

    if not source_path.exists():
        return {
            "generated": False,
            "source_file": str(
                source_path
            ),
            "output_file": None,
            "changes": [],
            "warnings": [],
            "errors": [
                "WAY source file not found: "
                f"{source_path}"
            ]
        }

    tree = load_xml(source_path)

    network_base = config[
        "network_base"
    ]

    way_ip = config[
        "way_ip"
    ]

    pos_service_ids = [
        "0001",
        "0002",
        "0003",
        "0004"
    ]

    changes = []
    warnings = []
    errors = []

    changes.extend(
        ensure_messaging_network_base(
            tree,
            network_base
        )
    )

    changes.extend(
        update_xmlrpccli_urls(
            tree,
            way_ip
        )
    )

    psw_changes, psw_warnings = (
        ensure_psw_pos_members(
            tree,
            pos_service_ids
        )
    )

    changes.extend(psw_changes)
    warnings.extend(psw_warnings)

    way_pos_changes, way_pos_warnings = (
        ensure_way_pos_members(
            tree,
            pos_service_ids
        )
    )

    changes.extend(way_pos_changes)
    warnings.extend(way_pos_warnings)

    sto_changes, sto_warnings = (
        ensure_way_sto_members(
            tree,
            pos_service_ids
        )
    )

    changes.extend(sto_changes)
    warnings.extend(sto_warnings)

    changes.extend(
        force_way_npw_disabled(tree)
    )

    foe_transformation = ensure_foe_standard(
        tree
    )

    changes.extend(
        foe_transformation["changes"]
    )

    warnings.extend(
        foe_transformation.get(
            "warnings",
            []
        )
    )

    errors.extend(
        foe_transformation["errors"]
    )

    validation = validate_way_tree(
        tree,
        network_base,
        way_ip,
        pos_service_ids
    )
    errors.extend(
        validation["errors"]
    )

    warnings.extend(
        validation["warnings"]
    )

    errors = list(dict.fromkeys(errors))
    warnings = list(
        dict.fromkeys(warnings)
    )

    changes = list(
        dict.fromkeys(changes)
    )

    if errors:
        return {
            "generated": False,
            "source_file": str(
                source_path
            ),
            "output_file": None,
            "changes": changes,
            "warnings": warnings,
            "errors": errors
        }

    etree.indent(
        tree,
        space="  "
    )

    save_xml(
        tree,
        output_path
    )

    validation_tree = load_xml(
        output_path
    )

    post_save_validation = (
        validate_way_tree(
            validation_tree,
            network_base,
            way_ip,
            pos_service_ids
        )
    )

    post_save_foe_validation = (
        validate_foe(
            validation_tree
        )
    )

    post_save_errors = (
        post_save_validation["errors"]
        + post_save_foe_validation["errors"]
    )

    post_save_warnings = (
        post_save_validation["warnings"]
        + post_save_foe_validation.get(
            "warnings",
            []
        )
    )

    post_save_errors = list(
        dict.fromkeys(
            post_save_errors
        )
    )

    post_save_warnings = list(
        dict.fromkeys(
            post_save_warnings
        )
    )

    warnings.extend(
        post_save_warnings
    )

    warnings = list(
        dict.fromkeys(
            warnings
        )
    )

    if post_save_errors:
        output_path.unlink(
            missing_ok=True
        )

        return {
            "generated": False,
            "source_file": str(
                source_path
            ),
            "output_file": None,
            "changes": changes,
            "warnings": warnings,
            "errors": post_save_errors
        }
    return {
        "generated": True,
        "source_file": str(
            source_path
        ),
        "output_file": str(
            output_path
        ),
        "changes": changes,
        "warnings": warnings,
        "errors": []
    }