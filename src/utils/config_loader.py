import json
from pathlib import Path


def load_json_config(config_path):

    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}"
        )

    with config_path.open(
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)
