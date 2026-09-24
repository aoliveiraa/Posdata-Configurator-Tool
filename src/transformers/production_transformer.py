from pathlib import Path
from lxml import etree

from src.utils.config_loader import load_json_config
from src.utils.xml_loader import load_xml, save_xml


def find_or_create_messaging(config):
    section = None

    for child in config.xpath("./Section"):
        if child.get("name", "").upper() == "MESSAGING":
            section = child
            break

    if section is None:
        section = etree.SubElement(
            config,
            "Section"
        )
        section.set("name", "Messaging")

    return section


def set_parameter(
    parent,
    name,
    value
):
    parameter = None

    for item in parent.xpath(
        "./Parameter"
    ):
        if item.get(
            "name",
            ""
        ).upper() == name.upper():

            parameter = item
            break

    created = False

    if parameter is None:
        parameter = etree.SubElement(
            parent,
            "Parameter"
        )
        parameter.set("name", name)
        created = True

    old_value = parameter.get("value")

    parameter.set(
        "value",
        str(value)
    )

    return {
        "created": created,
        "old_value": old_value,
        "new_value": value
    }


def apply_production_configuration(
    tree,
    network_base
):
    changes = []

    configurations = tree.xpath(
        "/PosDB/Configuration"
    )

    if not configurations:
        raise ValueError(
            "Root Configuration not found."
        )

    configuration = configurations[0]

    messaging = find_or_create_messaging(
        configuration
    )

    result = set_parameter(
        messaging,
        "networkAdaptorBaseIp",
        network_base
    )

    changes.append(
        "networkAdaptorBaseIp = "
        f"{network_base}"
    )

    return changes


def validate_production(tree):
    errors = []

    pst_services = tree.xpath(
        "/PosDB/Services/Service[@type='PST']"
    )

    if not pst_services:
        errors.append(
            "PST service not found."
        )

    que_services = tree.xpath(
        "/PosDB/Services/Service[@type='QUE']"
    )

    if not que_services:
        errors.append(
            "QUE services not found."
        )

    messaging = tree.xpath(
        "/PosDB/Configuration/"
        "Section[@name='Messaging']/"
        "Parameter[@name='networkAdaptorBaseIp']"
    )

    if not messaging:
        errors.append(
            "networkAdaptorBaseIp missing."
        )

    return errors


def generate_production_file(
    source_file,
    output_folder,
    network_base
):
    tree = load_xml(source_file)

    changes = apply_production_configuration(
        tree,
        network_base
    )

    errors = validate_production(tree)

    if errors:
        return {
            "generated": False,
            "errors": errors,
            "changes": changes
        }

    output_folder = Path(output_folder)

    output_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = (
        output_folder
        / Path(source_file).name
    )

    etree.indent(
        tree,
        space="  "
    )

    save_xml(
        tree,
        output_path
    )

    return {
        "generated": True,
        "output_file": str(output_path),
        "changes": changes,
        "errors": []
    }


def generate_all_production(
    new_posdata_folder,
    output_folder="output/production",
    config_path="config/rio_lab.json"
):
    """
    Production Discovery + Generation

    Supported patterns:

        _PROD_PRI_pos-db.xml
        _PROD_BACK_pos-db.xml
        _PROD_SEC_pos-db.xml

        _8000_pos-db.xml
        _8000*.xml

        any filename containing
        PRODUCTION
    """

    config = load_json_config(
        config_path
    )

    network_base = config[
        "network_base"
    ]

    results = []

    new_posdata_folder = Path(
        new_posdata_folder
    )

    discovered_candidates = []

    #
    # Standard production files
    #
    standard_candidates = [
        "_PROD_PRI_pos-db.xml",
        "_PROD_BACK_pos-db.xml",
        "_PROD_SEC_pos-db.xml",
    ]

    for filename in standard_candidates:

        source = (
            new_posdata_folder
            / filename
        )

        if source.exists():

            discovered_candidates.append(
                source
            )

    #
    # Spain pattern
    #
    for source in sorted(
        new_posdata_folder.glob(
            "*_pos-db.xml"
        )
    ):

        upper_name = (
            source.name
            .strip()
            .upper()
        )

        if (
            upper_name.startswith(
                "_8000"
            )
        ):

            discovered_candidates.append(
                source
            )

            continue

        if (
            "PRODUCTION"
            in upper_name
        ):

            discovered_candidates.append(
                source
            )

    #
    # Remove duplicates
    #
    unique_candidates = []

    seen = set()

    for candidate in discovered_candidates:

        candidate_key = (
            candidate.name
            .upper()
        )

        if (
            candidate_key
            in seen
        ):
            continue

        seen.add(
            candidate_key
        )

        unique_candidates.append(
            candidate
        )

    #
    # Generation
    #
    for source in unique_candidates:

        result = (
            generate_production_file(
                source_file=source,
                output_folder=output_folder,
                network_base=network_base,
            )
        )

        result["file"] = (
            source.name
        )

        results.append(
            result
        )

    return results