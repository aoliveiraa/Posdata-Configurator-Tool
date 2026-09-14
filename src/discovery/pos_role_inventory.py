from pathlib import Path

from src.utils.xml_loader import load_xml


def inventory_pos_roles(folder):

    folder = Path(folder)

    results = []

    files = [
        "_JS970WS_pos-db.xml",
        "_NCRXR7PR77_pos-db.xml",
        "_NCRXR7PR7_pos-db.xml",
        "_NCRXR7W10_pos-db.xml"
    ]

    for filename in files:

        file_path = folder / filename

        if not file_path.exists():
            continue

        tree = load_xml(file_path)

        operation_modes = tree.xpath(
            "//Parameter[@name='OperationMode']/@value"
        )

        pod_types = tree.xpath(
            "//Parameter[@name='PODType']/@value"
        )

        pos_types = tree.xpath(
            "//Parameter[@name='PosType']/@value"
        )

        results.append({
            "file": filename,
            "operation_modes": operation_modes,
            "pod_types": pod_types,
            "pos_types": pos_types
        })

    return results