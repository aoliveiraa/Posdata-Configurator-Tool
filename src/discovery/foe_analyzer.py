from pathlib import Path

from src.utils.xml_loader import load_xml


def analyze_foe(file_path):

    file_path = Path(file_path)

    if not file_path.exists():

        return {
            "found": False,
            "error": "File not found."
        }

    tree = load_xml(file_path)

    foe_services = tree.xpath(
        "//Service[@type='FOE']"
    )

    if not foe_services:

        return {
            "found": False,
            "error": "FOE service not found."
        }

    foe = foe_services[0]

    sections = []

    for section in foe.xpath(
        "./Configuration/Section"
    ):
        sections.append(
            section.get("name")
        )

    adaptors = []

    for adaptor in foe.xpath(
        "./Adaptors/Adaptor"
    ):
        adaptors.append(
            adaptor.get("name")
        )

    return {
        "found": True,
        "service_name": foe.get("name"),
        "sections": sections,
        "adaptors": adaptors
    }