from __future__ import annotations

from pathlib import Path
from typing import Dict

from config.lab_loader import load_lab_config
from src.builder.template_repository import TemplateRepository

SUPPORTED_LABS = {"BR", "RIO", "RENEIGH"}


def validate_builder_inputs(
    selected_lab: str,
    template_market: str,
    source_posdata_folder: str | Path,
    template_root: str | Path = "templates",
) -> Dict:
    lab = str(selected_lab or "").strip().upper()
    if lab not in SUPPORTED_LABS:
        raise ValueError(
            f"Unsupported laboratory: {selected_lab}. "
            "Supported laboratories: BR, RIO and RENEIGH."
        )

    load_lab_config(lab)

    source = Path(source_posdata_folder)
    if not source.is_dir():
        raise FileNotFoundError(
            f"Source PosData folder was not found: {source}"
        )

    store_db = source / "store-db.xml"
    screen_xml = source / "screen.xml"
    if not store_db.is_file():
        raise FileNotFoundError(
            f"Source store-db.xml was not found: {store_db}"
        )
    if not screen_xml.is_file():
        raise FileNotFoundError(
            f"Source screen.xml was not found: {screen_xml}"
        )

    repository = TemplateRepository(template_root)
    template_validation = repository.validate(template_market)
    if template_validation["status"] != "READY":
        raise ValueError("; ".join(template_validation["errors"]))

    return {
        "lab": lab,
        "config_path": f"config/{lab.lower()}_lab.json",
        "template_market": template_validation["market"],
        "template_folder": Path(template_validation["folder"]),
        "source_folder": source,
        "store_db_path": store_db,
        "screen_xml_path": screen_xml,
        "template_validation": template_validation,
    }
