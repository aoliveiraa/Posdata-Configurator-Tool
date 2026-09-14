from pathlib import Path

from src.utils.xml_loader import load_xml


RIO_POS_STANDARD = {
    "_JS970WS_POS-DB.XML": {
        "output_file": "_US80421POS01_pos-db.xml",
        "ip": "10.118.57.1"
    },

    "_NCRXR7W10_POS-DB.XML": {
        "output_file": "_US80421POS02_pos-db.xml",
        "ip": "10.118.57.2"
    },

    "_NCRXR7PR77_POS-DB.XML": {
        "output_file": "_US80421POS11_pos-db.xml",
        "ip": "10.118.57.11"
    },

    "_NCRXR7PR7_POS-DB.XML": {
        "output_file": "_US80421POS12_pos-db.xml",
        "ip": "10.118.57.12"
    }
}


def _extract_pos_node(tree):
    """
    Procura o POS associado ao arquivo.
    """

    search_order = [
        "//Parameter[@name='NodeName']",
        "//Parameter[@name='LogicalName']",
        "//Parameter[@name='Urn']"
    ]

    for xpath in search_order:

        matches = tree.xpath(xpath)

        for match in matches:

            value = (
                match.get("value", "")
                .strip()
            )

            if not value:
                continue

            value_upper = value.upper()

            if value_upper.startswith("POS"):
                return value_upper

            if "POS/" in value_upper:
                return value_upper.split("/")[-1]

    return None


def discover_current_pos_nodes(
    current_posdata_folder
):
    """
    Descobre qual POS roda
    em cada máquina física.
    """

    results = []

    folder = Path(
        current_posdata_folder
    )

    if not folder.exists():

        return []

    for file_path in sorted(
        folder.glob("*_pos-db.xml")
    ):

        filename = (
            file_path.name.upper()
        )

        if (
            filename
            not in RIO_POS_STANDARD
        ):
            continue

        try:

            tree = load_xml(
                file_path
            )

            node = (
                _extract_pos_node(
                    tree
                )
            )

            if not node:

                results.append(
                    {
                        "machine_file":
                            file_path.name,

                        "detected_node":
                            None,

                        "output_file":
                            None,

                        "ip":
                            None,

                        "status":
                            "NODE_NOT_FOUND"
                    }
                )

                continue

            rio_info = (
                RIO_POS_STANDARD[
                    filename
                ]
            )

            results.append(
                {
                    "machine_file":
                        file_path.name,

                    "detected_node":
                        node,

                    "output_file":
                        rio_info[
                            "output_file"
                        ],

                    "ip":
                        rio_info[
                            "ip"
                        ],

                    "status":
                        "READY"
                }
            )

        except Exception as ex:

            results.append(
                {
                    "machine_file":
                        file_path.name,

                    "detected_node":
                        None,

                    "output_file":
                        None,

                    "ip":
                        None,

                    "status":
                        f"ERROR: {ex}"
                }
            )

    return results


def build_node_lookup(
    discovery_results
):
    """
    Retorna lookup:

    POS0001 -> info
    """

    lookup = {}

    for item in discovery_results:

        node = item.get(
            "detected_node"
        )

        if not node:
            continue

        lookup[
            node.upper()
        ] = item

    return lookup