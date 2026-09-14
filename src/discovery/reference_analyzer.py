from pathlib import Path

from src.utils.config_loader import load_json_config


def analyze_reference(
    folder,
    config_path="config/rio_lab.json"
):

    folder = Path(folder)

    config = load_json_config(config_path)

    configured_pos_files = {
        item["source_file"].upper()
        for item in config.get(
            "reference_pos_files",
            []
        )
    }

    active_itonas = {
        itona.upper()
        for itona in config["scope"]["active_itonas"]
    }

    excluded_patterns = [
        pattern.upper()
        for pattern in config["scope"].get(
            "exclude_name_patterns",
            []
        )
    ]

    result = {
        "pos_machines": [],
        "itonas": [],
        "way_files": [],
        "production_primary": [],
        "production_backup": [],
        "ignored_files": [],
        "warnings": []
    }

    for file in sorted(
        folder.glob("*_pos-db.xml")
    ):

        name = file.name
        upper_name = name.upper()

        if any(
            pattern in upper_name
            for pattern in excluded_patterns
        ):
            result["ignored_files"].append(name)
            continue

        if upper_name in configured_pos_files:
            result["pos_machines"].append(name)
            continue

        matching_itona = next(
            (
                itona
                for itona in active_itonas
                if f"_{itona.upper()}_POS-DB.XML"
                == upper_name
            ),
            None
        )

        if matching_itona:
            result["itonas"].append(name)
            continue

        if "_WAYSTATION_POS-DB.XML" in upper_name:
            result["way_files"].append(name)
            continue

        if "_PROD_PRI_POS-DB.XML" in upper_name:
            result["production_primary"].append(name)
            continue

        if (
            "_PROD_BACK_POS-DB.XML" in upper_name
            or "_PROD_SEC_POS-DB.XML" in upper_name
        ):
            result["production_backup"].append(name)
            continue

        result["ignored_files"].append(name)

    expected_pos_count = config["scope"]["pos_count"]

    if len(result["pos_machines"]) != expected_pos_count:
        result["warnings"].append(
            "Expected "
            f"{expected_pos_count} reference POS files, "
            f"but found {len(result['pos_machines'])}."
        )

    if len(result["itonas"]) != len(active_itonas):
        result["warnings"].append(
            "Expected "
            f"{len(active_itonas)} active Itonas, "
            f"but found {len(result['itonas'])}."
        )

    if len(result["way_files"]) != 1:
        result["warnings"].append(
            "Expected exactly one WAYSTATION file, "
            f"but found {len(result['way_files'])}."
        )

    if not result["production_primary"]:
        result["warnings"].append(
            "Production Primary was not found."
        )

    if not result["production_backup"]:
        result["warnings"].append(
            "Production Backup or Secondary "
            "was not found."
        )

    return result