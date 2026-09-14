from pathlib import Path

from src.utils.xml_loader import load_xml


def detect_pos_roles(folder):

    folder = Path(folder)

    results = []

    pos_files = folder.glob("_POS*_pos-db.xml")

    for file in pos_files:

        try:

            tree = load_xml(file)

            content = ""

            for text in tree.xpath("//text()"):

                content += str(text).upper()

            role = "UNKNOWN"

            if "FC" in content:

                role = "FC"

            if "DT" in content:

                role = "DT"

            results.append({
                "file": file.name,
                "role": role
            })

        except Exception as e:

            results.append({
                "file": file.name,
                "role": f"ERROR: {e}"
            })

    return results