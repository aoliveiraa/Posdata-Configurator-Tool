from pathlib import Path

from src.utils.xml_loader import load_xml


KEYWORDS = [
    "DT",
    "FC",
    "OperationMode",
    "PODType",
    "DriveThru",
    "FrontCounter"
]


def inventory_pos_keywords(folder):

    folder = Path(folder)

    files = [
        "_JS970WS_pos-db.xml",
        "_NCRXR7PR77_pos-db.xml",
        "_NCRXR7PR7_pos-db.xml",
        "_NCRXR7W10_pos-db.xml"
    ]

    results = []

    for filename in files:

        file_path = folder / filename

        if not file_path.exists():
            continue

        content = file_path.read_text(
            encoding="utf-8",
            errors="ignore"
        )

        matches = {}

        for keyword in KEYWORDS:

            matches[keyword] = (
                content.upper().count(
                    keyword.upper()
                )
            )

        results.append({
            "file": filename,
            "matches": matches
        })

    return results