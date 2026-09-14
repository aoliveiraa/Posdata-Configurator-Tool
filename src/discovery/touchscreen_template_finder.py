from pathlib import Path

from src.utils.xml_loader import load_xml


def find_global_touchscreen_template(folder):

    folder = Path(folder)

    for file in sorted(
        folder.glob("_Itona*_pos-db.xml")
    ):

        tree = load_xml(file)

        sections = tree.xpath(
            "//Section[@name='Touchscreen']"
        )

        if sections:

            return {
                "source_file": file.name,
                "template": sections[0]
            }

    return None