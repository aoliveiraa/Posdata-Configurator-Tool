from copy import deepcopy

from lxml import etree

from src.utils.xml_loader import (
    load_xml,
    save_xml,
)


STORE_NETWORK_PREFIX_BY_LAB = {
    "RIO": "10.118.57",
    "RENEIGH": "10.118.51",
    "BR": "10.0.12",
}


STOREDB_POS_UI_PARAMETERS = (
    "enableInfoAlertPOSUIDesign",
    "enableListPOSUIDesign",
    "enablePOSUIDesign",
    "enableAlphanumericKeyboardPOSUIDesign",
    "enableSpacebarOnAlphanumericKeyboardPOSUIDesign",
)


STOREDB_MESSAGING_PARAMETERS = (
    ("WSCheckTime", "60"),
    ("fixedResource", None),
    ("multicastIp", "233.2.3.179"),
    ("multicastPackageLength", "5120"),
    ("multicastPort", "4176"),
    ("multicastTTL", "5"),
    ("networkAdaptorBaseIp", None),
    ("networkCheckTime", "5"),
    ("obligate", "true"),
    ("serverPort", None),
    ("MulticastTTL", "5"),
)


def normalize_lab_name(
    lab
):
    if lab is None:
        return ""

    return str(
        lab
    ).strip().upper()


def get_lab_network_prefix(
    lab
):
    normalized_lab = normalize_lab_name(
        lab
    )

    if not normalized_lab:
        raise ValueError(
            "Lab was not provided for StoreDB "
            "Messaging configuration."
        )

    network_prefix = (
        STORE_NETWORK_PREFIX_BY_LAB.get(
            normalized_lab
        )
    )

    if network_prefix is None:
        supported_labs = ", ".join(
            sorted(
                STORE_NETWORK_PREFIX_BY_LAB
            )
        )

        raise ValueError(
            f"Unsupported lab '{lab}'. "
            f"Supported labs: {supported_labs}."
        )

    return network_prefix


def get_direct_parameter(
    section,
    parameter_name
):
    if section is None:
        return None

    for parameter in section.findall(
        "Parameter"
    ):
        if (
            parameter.get("name")
            == parameter_name
        ):
            return parameter

    return None


def remove_duplicate_parameters(
    section,
    parameter_name,
    parameter_to_keep
):
    removed = 0

    for parameter in list(
        section.findall("Parameter")
    ):
        if (
            parameter.get("name")
            == parameter_name
            and parameter is not parameter_to_keep
        ):
            section.remove(
                parameter
            )

            removed += 1

    return removed


def update_main_screen(
    store_db_path,
    output_path,
    new_screen
):
    """
    Updates the first mainScreenNumber parameter
    found in the StoreDB.

    This function does not change Messaging or
    any other StoreDB runtime configuration.
    """

    tree = load_xml(
        store_db_path
    )

    nodes = tree.xpath(
        "//Parameter[@name='mainScreenNumber']"
    )

    if not nodes:
        return False

    nodes[0].set(
        "value",
        str(new_screen)
    )

    etree.indent(
        tree,
        space="  "
    )

    save_xml(
        tree,
        output_path
    )

    return True


def update_business_limits(
    store_db_path,
    output_path,
    business_limits_file
):
    """
    Replaces the first BusinessLimits node in
    the StoreDB using the supplied XML file.
    """

    tree = load_xml(
        store_db_path
    )

    business_tree = etree.parse(
        str(
            business_limits_file
        )
    )

    new_limits = deepcopy(
        business_tree.getroot()
    )

    old_limits = tree.xpath(
        "//BusinessLimits"
    )

    if not old_limits:
        return False

    parent = old_limits[0].getparent()

    parent.replace(
        old_limits[0],
        new_limits
    )

    etree.indent(
        tree,
        space="  "
    )

    save_xml(
        tree,
        output_path
    )

    return True


def update_storedb_messaging(
    tree,
    network_prefix
):
    """
    Normalizes the Messaging section inside:

    Document
      -> Configurations
        -> Configuration type="Store.wide"
          -> Section name="Messaging"

    Existing children of the Messaging section
    are replaced by the approved standard.
    """

    changes = []
    warnings = []
    errors = []

    if tree is None:
        errors.append(
            "StoreDB XML tree was not provided."
        )

        return {
            "updated": False,
            "changes": changes,
            "warnings": warnings,
            "errors": errors,
        }

    if not network_prefix:
        errors.append(
            "StoreDB Messaging network prefix "
            "was not provided."
        )

        return {
            "updated": False,
            "changes": changes,
            "warnings": warnings,
            "errors": errors,
        }

    messaging_nodes = tree.xpath(
        "/Document/Configurations/"
        "Configuration[@type='Store.wide']/"
        "Section[@name='Messaging']"
    )

    if not messaging_nodes:
        errors.append(
            "Store.wide Messaging section "
            "was not found in StoreDB."
        )

        return {
            "updated": False,
            "changes": changes,
            "warnings": warnings,
            "errors": errors,
        }

    if len(messaging_nodes) > 1:
        warnings.append(
            "Multiple Store.wide Messaging "
            "sections were found. All sections "
            "will be normalized."
        )

    for section_index, messaging in enumerate(
        messaging_nodes,
        start=1
    ):
        current_parameters = [
            (
                child.get("name"),
                child.get("value"),
            )
            for child in messaging.findall(
                "Parameter"
            )
        ]

        expected_parameters = []

        for parameter_name, parameter_value in (
            STOREDB_MESSAGING_PARAMETERS
        ):
            if (
                parameter_name
                == "networkAdaptorBaseIp"
            ):
                expected_parameters.append(
                    (
                        parameter_name,
                        str(network_prefix),
                    )
                )
            else:
                expected_parameters.append(
                    (
                        parameter_name,
                        (
                            str(parameter_value)
                            if parameter_value
                            is not None
                            else None
                        ),
                    )
                )

        unexpected_children = [
            child
            for child in messaging
            if child.tag != "Parameter"
        ]

        if (
            current_parameters
            == expected_parameters
            and not unexpected_children
        ):
            changes.append(
                "StoreDB Messaging section "
                f"{section_index} already matches "
                "the expected configuration."
            )

            continue

        for child in list(
            messaging
        ):
            messaging.remove(
                child
            )

        for parameter_name, parameter_value in (
            STOREDB_MESSAGING_PARAMETERS
        ):
            parameter = etree.SubElement(
                messaging,
                "Parameter"
            )

            parameter.set(
                "name",
                parameter_name
            )

            if (
                parameter_name
                == "networkAdaptorBaseIp"
            ):
                parameter.set(
                    "value",
                    str(network_prefix)
                )

            elif parameter_value is not None:
                parameter.set(
                    "value",
                    str(parameter_value)
                )

        changes.append(
            "StoreDB Messaging section "
            f"{section_index} normalized with "
            f"network prefix {network_prefix}."
        )

    return {
        "updated": True,
        "changes": changes,
        "warnings": warnings,
        "errors": errors,
    }


def update_storedb_pos_ui(
    tree
):
    """
    Ensures the required POS UI design parameters
    exist with value=false inside:

    Document
      -> Configurations
        -> Configuration type="POS"
          -> Section name="UserInterface"

    Existing unrelated UserInterface parameters
    are preserved.
    """

    changes = []
    warnings = []
    errors = []

    if tree is None:
        errors.append(
            "StoreDB XML tree was not provided."
        )

        return {
            "updated": False,
            "changes": changes,
            "warnings": warnings,
            "errors": errors,
        }

    configs = tree.xpath(
        "/Document/Configurations/"
        "Configuration[@type='POS']"
    )

    if not configs:
        errors.append(
            "POS Configuration was not found "
            "in StoreDB."
        )

        return {
            "updated": False,
            "changes": changes,
            "warnings": warnings,
            "errors": errors,
        }

    if len(configs) > 1:
        warnings.append(
            "Multiple POS Configurations were "
            "found. All matching configurations "
            "will be updated."
        )

    for config_index, config in enumerate(
        configs,
        start=1
    ):
        ui_sections = config.xpath(
            "./Section[@name='UserInterface']"
        )

        if not ui_sections:
            ui = etree.SubElement(
                config,
                "Section"
            )

            ui.set(
                "name",
                "UserInterface"
            )

            changes.append(
                "StoreDB POS UserInterface "
                f"section created for POS "
                f"Configuration {config_index}."
            )

        else:
            ui = ui_sections[0]

            if len(ui_sections) > 1:
                warnings.append(
                    "Multiple UserInterface "
                    "sections were found inside "
                    "POS Configuration "
                    f"{config_index}. The first "
                    "section was updated."
                )

        for parameter_name in (
            STOREDB_POS_UI_PARAMETERS
        ):
            parameter = get_direct_parameter(
                ui,
                parameter_name
            )

            if parameter is None:
                parameter = etree.SubElement(
                    ui,
                    "Parameter"
                )

                parameter.set(
                    "name",
                    parameter_name
                )

                parameter.set(
                    "value",
                    "false"
                )

                changes.append(
                    "StoreDB POS UserInterface "
                    f"parameter {parameter_name} "
                    "created with value=false."
                )

            else:
                current_value = parameter.get(
                    "value"
                )

                if current_value != "false":
                    parameter.set(
                        "value",
                        "false"
                    )

                    changes.append(
                        "StoreDB POS UserInterface "
                        f"parameter {parameter_name} "
                        f"changed from "
                        f"{current_value!r} to "
                        "'false'."
                    )

            duplicate_count = (
                remove_duplicate_parameters(
                    ui,
                    parameter_name,
                    parameter
                )
            )

            if duplicate_count:
                changes.append(
                    f"Removed {duplicate_count} "
                    "duplicate StoreDB parameter(s) "
                    f"named {parameter_name}."
                )

    if not changes:
        changes.append(
            "StoreDB POS UserInterface already "
            "matches the expected configuration."
        )

    return {
        "updated": True,
        "changes": changes,
        "warnings": warnings,
        "errors": errors,
    }


def update_storedb_runtime_configuration(
    store_db_path,
    output_path,
    lab,
    update_pos_ui=True
):
    """
    Loads a StoreDB, applies runtime configuration,
    validates the saved result and returns a report.

    Applied rules:
        1. Store.wide Messaging normalization.
        2. POS UserInterface flags, when enabled.

    The function can update the same file in place:

        store_db_path="output/store-db.xml"
        output_path="output/store-db.xml"
    """

    result = {
        "updated": False,
        "store_db_path": str(
            store_db_path
        ),
        "output_path": str(
            output_path
        ),
        "lab": normalize_lab_name(
            lab
        ),
        "network_prefix": None,
        "changes": [],
        "warnings": [],
        "errors": [],
    }

    try:
        network_prefix = (
            get_lab_network_prefix(
                lab
            )
        )

    except ValueError as error:
        result["errors"].append(
            str(error)
        )

        return result

    result["network_prefix"] = (
        network_prefix
    )

    try:
        tree = load_xml(
            store_db_path
        )

    except Exception as error:
        result["errors"].append(
            "Unable to load StoreDB XML: "
            f"{error}"
        )

        return result

    messaging_result = (
        update_storedb_messaging(
            tree,
            network_prefix
        )
    )

    result["changes"].extend(
        messaging_result.get(
            "changes",
            []
        )
    )

    result["warnings"].extend(
        messaging_result.get(
            "warnings",
            []
        )
    )

    result["errors"].extend(
        messaging_result.get(
            "errors",
            []
        )
    )

    if update_pos_ui:
        pos_ui_result = (
            update_storedb_pos_ui(
                tree
            )
        )

        result["changes"].extend(
            pos_ui_result.get(
                "changes",
                []
            )
        )

        result["warnings"].extend(
            pos_ui_result.get(
                "warnings",
                []
            )
        )

        result["errors"].extend(
            pos_ui_result.get(
                "errors",
                []
            )
        )

    result["changes"] = list(
        dict.fromkeys(
            result["changes"]
        )
    )

    result["warnings"] = list(
        dict.fromkeys(
            result["warnings"]
        )
    )

    result["errors"] = list(
        dict.fromkeys(
            result["errors"]
        )
    )

    if result["errors"]:
        return result

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
        result["errors"].append(
            "Unable to save configured StoreDB: "
            f"{error}"
        )

        return result

    try:
        saved_tree = load_xml(
            output_path
        )

    except Exception as error:
        result["errors"].append(
            "Unable to reload configured StoreDB: "
            f"{error}"
        )

        return result

    validation = (
        validate_storedb_runtime_configuration(
            saved_tree,
            network_prefix,
            validate_pos_ui=update_pos_ui
        )
    )

    result["warnings"].extend(
        validation.get(
            "warnings",
            []
        )
    )

    result["errors"].extend(
        validation.get(
            "errors",
            []
        )
    )

    result["warnings"] = list(
        dict.fromkeys(
            result["warnings"]
        )
    )

    result["errors"] = list(
        dict.fromkeys(
            result["errors"]
        )
    )

    result["updated"] = (
        not result["errors"]
    )

    return result


def validate_storedb_runtime_configuration(
    tree,
    network_prefix,
    validate_pos_ui=True
):
    """
    Validates Store.wide Messaging and optionally
    validates the five POS UserInterface flags.
    """

    warnings = []
    errors = []

    messaging_nodes = tree.xpath(
        "/Document/Configurations/"
        "Configuration[@type='Store.wide']/"
        "Section[@name='Messaging']"
    )

    if not messaging_nodes:
        errors.append(
            "Store.wide Messaging section "
            "was not found after generation."
        )

    else:
        for section_index, messaging in enumerate(
            messaging_nodes,
            start=1
        ):
            actual_parameters = [
                (
                    parameter.get("name"),
                    parameter.get("value"),
                )
                for parameter in messaging.findall(
                    "Parameter"
                )
            ]

            expected_parameters = []

            for parameter_name, parameter_value in (
                STOREDB_MESSAGING_PARAMETERS
            ):
                if (
                    parameter_name
                    == "networkAdaptorBaseIp"
                ):
                    expected_parameters.append(
                        (
                            parameter_name,
                            str(network_prefix),
                        )
                    )
                else:
                    expected_parameters.append(
                        (
                            parameter_name,
                            (
                                str(parameter_value)
                                if parameter_value
                                is not None
                                else None
                            ),
                        )
                    )

            if (
                actual_parameters
                != expected_parameters
            ):
                errors.append(
                    "StoreDB Messaging section "
                    f"{section_index} does not "
                    "match the expected standard."
                )

    if validate_pos_ui:
        ui_sections = tree.xpath(
            "/Document/Configurations/"
            "Configuration[@type='POS']/"
            "Section[@name='UserInterface']"
        )

        if not ui_sections:
            errors.append(
                "POS UserInterface section was "
                "not found after generation."
            )

        else:
            for section_index, ui in enumerate(
                ui_sections,
                start=1
            ):
                for parameter_name in (
                    STOREDB_POS_UI_PARAMETERS
                ):
                    matching_parameters = [
                        parameter
                        for parameter in ui.findall(
                            "Parameter"
                        )
                        if (
                            parameter.get("name")
                            == parameter_name
                        )
                    ]

                    if not matching_parameters:
                        errors.append(
                            "StoreDB POS "
                            f"UserInterface parameter "
                            f"{parameter_name} was "
                            "not found in section "
                            f"{section_index}."
                        )

                        continue

                    if len(matching_parameters) > 1:
                        errors.append(
                            "StoreDB POS "
                            f"UserInterface parameter "
                            f"{parameter_name} is "
                            "duplicated in section "
                            f"{section_index}."
                        )

                    actual_value = (
                        matching_parameters[0].get(
                            "value"
                        )
                    )

                    if actual_value != "false":
                        errors.append(
                            "StoreDB POS "
                            f"UserInterface parameter "
                            f"{parameter_name} has "
                            "unexpected value "
                            f"{actual_value!r}."
                        )

    return {
        "valid": not errors,
        "warnings": warnings,
        "errors": errors,
    }