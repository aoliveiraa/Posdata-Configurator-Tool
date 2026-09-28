from __future__ import annotations

from pathlib import Path
from typing import Dict

from config.lab_loader import load_lab_config

SUPPORTED_LABS = {
    "BR",
    "RIO",
    "RENEIGH",
}


def validate_builder_inputs(
    selected_lab: str,
    source_posdata_folder: str | Path,
    rules_root: str | Path = "config/builder_rules",
) -> Dict:
    """
    Sprint 2.0.1

    Builder no longer requires a template market.

    The source PosData is used only for discovery.
    All generation rules will come from the Builder
    Rules Repository.

    Required:
        - Laboratory
        - Source PosData folder

    Optional:
        - Rules folder
    """

    lab = str(
        selected_lab or ""
    ).strip().upper()

    if lab not in SUPPORTED_LABS:
        raise ValueError(
            f"Unsupported laboratory: {selected_lab}. "
            "Supported laboratories: BR, RIO and RENEIGH."
        )

    #
    # Validate laboratory configuration
    #
    load_lab_config(
        lab
    )

    source = Path(
        source_posdata_folder
    )

    if not source.is_dir():
        raise FileNotFoundError(
            f"Source PosData folder was not found: {source}"
        )

    store_db = (
        source /
        "store-db.xml"
    )

    screen_xml = (
        source /
        "screen.xml"
    )

    if not store_db.is_file():
        raise FileNotFoundError(
            f"Source store-db.xml was not found: {store_db}"
        )

    if not screen_xml.is_file():
        raise FileNotFoundError(
            f"Source screen.xml was not found: {screen_xml}"
        )

    rules_path = Path(
        rules_root
    )

    #
    # Rules repository is optional during Sprint 2.0.1
    #
    rules_available = (
        rules_path.is_dir()
    )

    return {
        #
        # Sprint 2.0.1
        #
        "generation_mode": "FROM_SCRATCH",

        #
        # Lab
        #
        "lab": lab,
        "config_path": (
            f"config/{lab.lower()}_lab.json"
        ),

        #
        # Source PosData
        #
        "source_folder": source,
        "store_db_path": store_db,
        "screen_xml_path": screen_xml,

        #
        # Future Rules Repository
        #
        "rules_path": rules_path,
        "rules_available": rules_available,

        #
        # Template removed
        #
        "template_market": None,
        "template_folder": None,
        "template_validation": {
            "status": "NOT_USED",
            "reason": (
                "Builder is running "
                "in FROM_SCRATCH mode."
            ),
        },
    }