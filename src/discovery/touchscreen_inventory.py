from pathlib import Path

from src.utils.xml_loader import load_xml


def inventory_touchscreens(folder):

    folder = Path(folder)

    results = []

    for file in sorted(
        folder.glob("_Itona*_pos-db.xml")
    ):

        tree = load_xml(file)

        touchscreens = tree.xpath(
            "//Section[@name='Touchscreen']"
        )

        results.append({
            "file": file.name,
            "count": len(touchscreens)
        })

    return results