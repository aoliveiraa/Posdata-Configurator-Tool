import json


def load_lab_config(lab):

    file_map = {
        "RIO": "config/rio_lab.json",
        "RENEIGH": "config/reneigh_lab.json",
        "BR": "config/br_lab.json",
    }

    path = file_map[lab.upper()]

    with open(
        path,
        encoding="utf-8"
    ) as file:

        return json.load(file)