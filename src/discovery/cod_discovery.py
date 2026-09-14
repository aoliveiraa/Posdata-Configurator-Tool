from src.utils.config_loader import (
    load_json_config
)


def normalize_upper(value):
    if value is None:
        return ""

    return str(value).strip().upper()


def discover_cod_target(
    pos_machine_mapping,
    config_path="config/rio_lab.json"
):
    """
    Resolve o destino COD usando o nome da
    máquina de referência configurada.

    O node POS e o nome do arquivo final não
    ficam hardcoded na configuração COD.
    """

    config = load_json_config(
        config_path
    )

    cod_config = config.get(
        "cod",
        {}
    )

    if not cod_config.get(
        "enabled",
        False
    ):
        return {
            "enabled": False,
            "found": False,
            "reference_machine": None,
            "node_name": None,
            "output_file": None,
            "ip": None,
            "config": cod_config,
            "warnings": [
                "COD is disabled in the "
                "laboratory configuration."
            ],
            "errors": []
        }

    reference_machine = cod_config.get(
        "reference_machine"
    )

    if not reference_machine:
        return {
            "enabled": True,
            "found": False,
            "reference_machine": None,
            "node_name": None,
            "output_file": None,
            "ip": None,
            "config": cod_config,
            "warnings": [],
            "errors": [
                "COD reference_machine was "
                "not configured."
            ]
        }

    expected_machine = normalize_upper(
        reference_machine
    )

    matching_items = []

    for item in pos_machine_mapping:
        machine_file = normalize_upper(
            item.get("machine_file")
        )

        if machine_file == expected_machine:
            matching_items.append(item)

    if not matching_items:
        return {
            "enabled": True,
            "found": False,
            "reference_machine": (
                reference_machine
            ),
            "node_name": None,
            "output_file": None,
            "ip": None,
            "config": cod_config,
            "warnings": [],
            "errors": [
                "COD reference machine was "
                "not found in Current PosData: "
                f"{reference_machine}"
            ]
        }

    if len(matching_items) > 1:
        return {
            "enabled": True,
            "found": False,
            "reference_machine": (
                reference_machine
            ),
            "node_name": None,
            "output_file": None,
            "ip": None,
            "config": cod_config,
            "warnings": [],
            "errors": [
                "More than one machine mapping "
                "was found for COD: "
                f"{reference_machine}"
            ]
        }

    item = matching_items[0]

    status = normalize_upper(
        item.get("status")
    )

    if status != "READY":
        return {
            "enabled": True,
            "found": False,
            "reference_machine": (
                reference_machine
            ),
            "node_name": item.get(
                "detected_node"
            ),
            "output_file": item.get(
                "output_file"
            ),
            "ip": item.get("ip"),
            "config": cod_config,
            "warnings": [],
            "errors": [
                "COD machine discovery is not "
                f"READY. Status: {status}"
            ]
        }

    node_name = item.get(
        "detected_node"
    )

    output_file = item.get(
        "output_file"
    )

    errors = []

    if not node_name:
        errors.append(
            "COD node was not discovered from "
            "the reference machine."
        )

    if not output_file:
        errors.append(
            "COD output filename was not "
            "resolved from the reference machine."
        )

    return {
        "enabled": True,
        "found": not errors,
        "reference_machine": (
            reference_machine
        ),
        "node_name": node_name,
        "output_file": output_file,
        "ip": item.get("ip"),
        "config": cod_config,
        "warnings": [],
        "errors": errors
    }