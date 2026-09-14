from pathlib import Path

from src.utils.xml_loader import load_xml


def inventory_pos_browsers(folder):

    folder = Path(folder)

    results = []

    for file in sorted(
        folder.glob("*_pos-db.xml")
    ):

        if "ITONA" in file.name.upper():
            continue

        tree = load_xml(file)

        browser_sections = tree.xpath(
            "//Section[starts-with(@name,'Component.Browser')]"
        )

        results.append({
            "file": file.name,
            "browser_count": len(browser_sections),
            "browser_names": [
                section.get("name")
                for section in browser_sections
            ]
        })

    return results