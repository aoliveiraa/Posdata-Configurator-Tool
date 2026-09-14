from pathlib import Path

from src.utils.xml_loader import load_xml
from src.utils.config_loader import (
    load_json_config
)


def get_parameter_value(
    tree,
    parameter_name
):
    parameter = tree.xpath(
        f"//Parameter[@name='{parameter_name}']"
    )

    if not parameter:
        return None

    return parameter[0].get("value")


def detect_pos_role(
    pod,
    pod_type
):
    if pod == "FRONT_COUNTER":
        return "FC"

    if (
        pod == "DRIVE_THRU"
        or pod_type == "DT"
    ):
        return "DT"

    return "UNKNOWN"


def validate_pos_file(
    file_path,
    expected_role
):
    tree = load_xml(file_path)

    pod = get_parameter_value(
        tree,
        "POD"
    )

    rem_pod = get_parameter_value(
        tree,
        "RemPOD"
    )

    pod_type = get_parameter_value(
        tree,
        "PODType"
    )

    detected_role = detect_pos_role(
        pod,
        pod_type
    )

    smart_routing = bool(
        tree.xpath(
            "//Section[@name='SmartRouting']"
        )
    )

    errors = []
    warnings = []

    if detected_role != expected_role:

        errors.append(
            f"Expected {expected_role} "
            f"but detected "
            f"{detected_role}"
        )

    if not smart_routing:

        warnings.append(
            "SmartRouting not found"
        )

    return {
        "file": Path(file_path).name,
        "expected_role": expected_role,
        "detected_role": detected_role,
        "pod": pod,
        "rem_pod": rem_pod,
        "pod_type": pod_type,
        "valid": len(errors) == 0,
        "warnings": warnings,
        "errors": errors
    }


def validate_generated_pos_roles(
    output_folder="output/pos",
    pos_machine_lookup=None,
    config_path="config/rio_lab.json"
):

    config = load_json_config(
    config_path
    )

    results = []

    reverse_output_lookup = {}

    if pos_machine_lookup:

        for node_name, info in (
            pos_machine_lookup.items()
        ):

            output_file = (
                info.get("output_file")
            )

            if output_file:

                reverse_output_lookup[
                    output_file.upper()
                ] = node_name.upper()

    role_mapping = {}

    for role_name, members in (
        config["pos_roles"].items()
    ):

        for member in members:

            logical_machine = (
                member["logical_machine"]
                .upper()
            )

            role_mapping[
                logical_machine
            ] = role_name

    output_folder = Path(
        output_folder
    )

    for file_path in output_folder.glob(
        "*_pos-db.xml"
    ):

        output_filename = (
            file_path.name.upper()
        )

        print()

        print(
            f"FILE: {output_filename}"
        )


        node_name = (
            reverse_output_lookup.get(
                output_filename
            )
        )

        print(
            f"NODE: {node_name}"
        )
        
        if not node_name:
            continue

        expected_role = (
            role_mapping.get(
                node_name
            )
        )
        print(
            f"EXPECTED ROLE: {expected_role}"
        )

        if not expected_role:
            continue

        results.append(
            validate_pos_file(
                file_path=file_path,
                expected_role=expected_role
            )
        )
    return results