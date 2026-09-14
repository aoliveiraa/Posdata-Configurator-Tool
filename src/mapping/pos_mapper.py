from pathlib import Path

from src.utils.config_loader import (
    load_json_config
)


def node_to_source_filename(node_name):
    """
    Converte:

    POS0001
        -> _POS0001_pos-db.xml
    """

    return f"_{node_name}_pos-db.xml"


def map_new_pos_files(
    new_posdata_folder,
    config_path="config/rio_lab.json"
):
    """
    Mapeia os POS do novo PosData para os
    nomes físicos das máquinas do laboratório.

    Exemplo:

    _POS0001_pos-db.xml
        -> _JS970WS_pos-db.xml
    """

    new_posdata_folder = Path(
        new_posdata_folder
    )

    config = load_json_config(
        config_path
    )

    configured_mappings = config.get(
        "reference_pos_files",
        []
    )

    mappings = []
    warnings = []
    errors = []

    for item in configured_mappings:

        target_file = item.get(
            "source_file"
        )

        node_name = item.get(
            "target_node"
        )

        if not target_file or not node_name:

            errors.append(
                "Invalid reference_pos_files item. "
                "source_file and target_node "
                "are required."
            )

            continue

        source_file = (
            node_to_source_filename(
                node_name
            )
        )

        source_path = (
            new_posdata_folder
            / source_file
        )

        status = "READY"

        if not source_path.exists():

            status = "MISSING"

            warnings.append(
                f"{source_file} was not found "
                "in the new PosData."
            )

        mappings.append({
            "node_name": node_name,
            "source_file": source_file,
            "source_path": str(source_path),
            "target_file": target_file,
            "status": status,
            "warnings": (
                []
                if status == "READY"
                else [
                    f"Source POS not found: "
                    f"{source_file}"
                ]
            )
        })

    expected_count = (
        config["scope"]["pos_count"]
    )

    ready_count = len([
        mapping
        for mapping in mappings
        if mapping["status"] == "READY"
    ])

    if ready_count != expected_count:

        warnings.append(
            f"Expected {expected_count} ready POS "
            f"mappings, but found {ready_count}."
        )

    return {
        "mappings": mappings,
        "warnings": warnings,
        "errors": errors
    }