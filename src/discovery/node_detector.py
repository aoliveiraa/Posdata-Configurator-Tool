from pathlib import Path


def scan_posdata_folder(folder):

    folder = Path(folder)

    return list(
        folder.glob("*_pos-db.xml")
    )


def detect_nodes(folder):

    files = scan_posdata_folder(folder)

    result = {
        "pos": [],
        "kvs": [],
        "way": [],
        "production": []
    }

    for file in files:

        name = file.name.upper()

        if "_KVS" in name:

            result["kvs"].append(file.name)

        elif "_WAYSTATION" in name:

            result["way"].append(file.name)

        elif "_PROD" in name:

            result["production"].append(file.name)

        elif "_POS" in name:

            result["pos"].append(file.name)

    return result