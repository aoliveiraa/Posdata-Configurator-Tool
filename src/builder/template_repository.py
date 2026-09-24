from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional


SUPPORTED_TEMPLATES = ("AU", "CA", "DE", "PT", "UK", "US")
REQUIRED_FILES = ("store-db.xml", "screen.xml")


class TemplateRepository:
    """Discovers and validates internal market templates."""

    def __init__(self, root: str | Path = "templates") -> None:
        self.root = Path(root)

    def available_templates(self) -> List[str]:
        if not self.root.is_dir():
            return []
        return [
            market
            for market in SUPPORTED_TEMPLATES
            if (self.root / market).is_dir()
        ]

    def resolve(self, market: str) -> Optional[Path]:
        normalized = str(market or "").strip().upper()
        if normalized not in SUPPORTED_TEMPLATES:
            return None
        folder = self.root / normalized
        return folder if folder.is_dir() else None

    def validate(self, market: str) -> Dict:
        normalized = str(market or "").strip().upper()
        result = {
            "market": normalized,
            "folder": None,
            "status": "READY",
            "missing_files": [],
            "pos_db_files": [],
            "warnings": [],
            "errors": [],
        }

        folder = self.resolve(normalized)
        if folder is None:
            result["status"] = "FAIL"
            result["errors"].append(
                f"Internal template was not found: {normalized}"
            )
            return result

        result["folder"] = str(folder)
        for filename in REQUIRED_FILES:
            if not (folder / filename).is_file():
                result["missing_files"].append(filename)

        result["pos_db_files"] = sorted(
            path.name for path in folder.glob("*_pos-db.xml")
        )

        if result["missing_files"]:
            result["status"] = "FAIL"
            result["errors"].append(
                "Template is missing required files: "
                + ", ".join(result["missing_files"])
            )

        if not result["pos_db_files"]:
            result["status"] = "FAIL"
            result["errors"].append(
                "Template does not contain pos-db.xml files."
            )

        return result
