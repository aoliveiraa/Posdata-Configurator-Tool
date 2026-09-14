from pathlib import Path
from lxml import etree

from src.utils.xml_loader import (
    load_xml,
    save_xml
)


def get_foe_service(tree):

    services = tree.xpath(
        "//Service[@type='FOE']"
    )

    if not services:
        return None

    return services[0]


def ensure_required_foe_sections(tree):

    changes = []
    errors = []

    foe = get_foe_service(tree)

    if foe is None:

        errors.append(
            "FOE service not found."
        )

        return {
            "success": False,
            "changes": changes,
            "errors": errors,
        }

    configuration = foe.find(
        "Configuration"
    )

    if configuration is None:

        configuration = etree.Element(
            "Configuration"
        )

        foe.insert(
            0,
            configuration
        )

        changes.append(
            "FOE Configuration created"
        )

    existing_sections = {
        section.get("name")
        for section in configuration.xpath(
            "./Section"
        )
    }

    required_sections = [
        "podNameMapping",
        "routing",
    ]

    for section_name in required_sections:

        if section_name in existing_sections:
            continue

        section = etree.Element(
            "Section"
        )

        section.set(
            "name",
            section_name
        )

        configuration.append(
            section
        )

        changes.append(
            f"{section_name} created"
        )

    return {
        "success": True,
        "changes": changes,
        "errors": [],
    }


def validate_foe(tree):

    errors = []

    foe = get_foe_service(tree)

    if foe is None:

        errors.append(
            "FOE service not found."
        )

        return {
            "valid": False,
            "errors": errors,
        }

    configuration = foe.find(
        "Configuration"
    )

    if configuration is None:

        errors.append(
            "FOE Configuration not found."
        )

        return {
            "valid": False,
            "errors": errors,
        }

    sections = {
        section.get("name")
        for section in configuration.xpath(
            "./Section"
        )
    }

    required_sections = {
        "podNameMapping",
        "routing"
    }

    missing_sections = (
        required_sections
        - sections
    )

    for section in sorted(
        missing_sections
    ):

        errors.append(
            f"Missing section: {section}"
        )

    adaptors = {
        adaptor.get("name")
        for adaptor in foe.xpath(
            "./Adaptors/Adaptor"
        )
    }

    required_adaptors = {
        "foe.xmlrpc",
        "standard.account",
        "xmlrpccli"
    }

    missing_adaptors = (
        required_adaptors
        - adaptors
    )

    for adaptor in sorted(
        missing_adaptors
    ):

        errors.append(
            f"Missing adaptor: {adaptor}"
        )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }


def generate_foe_file(
    source_file,
    output_folder
):

    tree = load_xml(
        source_file
    )

    repair = (
        ensure_required_foe_sections(
            tree
        )
    )

    if repair["errors"]:

        return {
            "generated": False,
            "output_file": None,
            "errors": repair["errors"],
            "changes": repair["changes"],
        }

    validation = validate_foe(
        tree
    )

    if validation["errors"]:

        return {
            "generated": False,
            "output_file": None,
            "errors": validation["errors"],
            "changes": repair["changes"],
        }

    output_folder = Path(
        output_folder
    )

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
        "output_file": str(
            output_path
        ),
        "errors": [],
        "changes": (
            repair["changes"]
            +
            [
                "FOE validated",
                "FOE exported"
            ]
        ),
    }


def generate_all_foe(
    new_posdata_folder,
    output_folder="output/foe"
):

    source_file = (
        Path(
            new_posdata_folder
        )
        / "_WAYSTATION_pos-db.xml"
    )

    if not source_file.exists():
        return []

    result = generate_foe_file(
        source_file,
        output_folder
    )

    result["file"] = (
        "_WAYSTATION_pos-db.xml"
    )

    return [result]