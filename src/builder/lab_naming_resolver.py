"""Naming resolver for PosData Builder outputs.

Uses the selected laboratory JSON configuration as the source of truth for
physical POS filenames. Itona and Production names follow Builder rules.

Production normalization:
    _8000_pos-db.xml -> _PROD_PRI_pos-db.xml
    _8001_pos-db.xml -> _PROD_BACK_pos-db.xml
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping


DEFAULT_CONFIG_FOLDER = Path("config")

LAB_CONFIG_FILES = {
    "BR": "br_lab.json",
    "RIO": "rio_lab.json",
    "RENEIGH": "reneigh_lab.json",
}

PRODUCTION_NAME_MAP = {
    "8000": "_PROD_PRI_pos-db.xml",
    "8001": "_PROD_BACK_pos-db.xml",
    "PROD_PRI": "_PROD_PRI_pos-db.xml",
    "PROD_BACK": "_PROD_BACK_pos-db.xml",
    "PROD_SEC": "_PROD_SEC_pos-db.xml",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _upper(value: Any) -> str:
    return _text(value).upper()


def _normalize_filename(value: str) -> str:
    """Return a filename without changing its configured spelling."""
    return Path(_text(value)).name


def _normalize_pos_node(value: Any) -> str:
    """Normalize POS1, POS01 and POS0001 to POS0001."""
    raw = _upper(value)
    match = re.fullmatch(r"POS0*(\d+)", raw)
    if not match:
        raise ValueError(f"Invalid POS logical machine: {value!r}")
    return f"POS{int(match.group(1)):04d}"


def _normalize_itona_slot(value: Any) -> str:
    """Normalize Itona01 and ITONA1 to Itona1."""
    raw = _upper(value)
    match = re.fullmatch(r"ITONA0*(\d+)", raw)
    if not match:
        raise ValueError(f"Invalid Itona slot: {value!r}")
    number = int(match.group(1))
    if number < 1:
        raise ValueError("Itona number must be greater than zero.")
    return f"Itona{number}"


def _production_key(source_file: Any) -> str:
    filename = _upper(Path(_text(source_file)).name)
    stem = filename
    if stem.endswith(".XML"):
        stem = stem[:-4]
    if stem.endswith("_POS-DB"):
        stem = stem[:-7]
    stem = stem.strip("_")

    if stem.startswith("8000"):
        return "8000"
    if stem.startswith("8001"):
        return "8001"
    if "PROD_PRI" in stem:
        return "PROD_PRI"
    if "PROD_BACK" in stem:
        return "PROD_BACK"
    if "PROD_SEC" in stem:
        return "PROD_SEC"
    return ""


def load_lab_config(config_path: str | Path) -> dict[str, Any]:
    """Load and minimally validate a laboratory JSON file."""
    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(f"Laboratory config was not found: {path}")

    try:
        with path.open("r", encoding="utf-8") as stream:
            config = json.load(stream)
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid laboratory JSON {path}: {error}") from error

    if not isinstance(config, dict):
        raise ValueError(f"Laboratory config must be a JSON object: {path}")
    if not _text(config.get("lab")):
        raise ValueError(f"Laboratory config does not define 'lab': {path}")
    if not isinstance(config.get("reference_pos_files"), list):
        raise ValueError(
            f"Laboratory config does not define 'reference_pos_files': {path}"
        )
    return config


def resolve_lab_config_path(
    lab: str,
    config_folder: str | Path = DEFAULT_CONFIG_FOLDER,
) -> Path:
    """Resolve a supported laboratory code to its JSON file."""
    normalized_lab = _upper(lab)
    filename = LAB_CONFIG_FILES.get(normalized_lab)
    if filename is None:
        supported = ", ".join(sorted(LAB_CONFIG_FILES))
        raise ValueError(
            f"Unsupported laboratory: {lab!r}. Supported laboratories: {supported}."
        )
    return Path(config_folder) / filename


class LabNamingResolver:
    """Resolve output names from a selected laboratory configuration."""

    def __init__(self, config: Mapping[str, Any], config_path: Path | None = None):
        self.config = dict(config)
        self.config_path = config_path
        self.lab = _upper(self.config.get("lab"))
        self._pos_names = self._build_pos_name_index()
        self._configured_itonas = {
            _normalize_itona_slot(value)
            for value in self.config.get("kvs_machines") or []
        }

    @classmethod
    def from_file(cls, config_path: str | Path) -> "LabNamingResolver":
        path = Path(config_path)
        return cls(load_lab_config(path), config_path=path)

    @classmethod
    def from_lab(
        cls,
        lab: str,
        config_folder: str | Path = DEFAULT_CONFIG_FOLDER,
    ) -> "LabNamingResolver":
        return cls.from_file(resolve_lab_config_path(lab, config_folder))

    def _build_pos_name_index(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for item in self.config.get("reference_pos_files") or []:
            if not isinstance(item, Mapping):
                continue
            target_node = _normalize_pos_node(item.get("target_node"))
            source_file = _normalize_filename(_text(item.get("source_file")))
            if not source_file:
                raise ValueError(
                    f"Reference POS entry for {target_node} has no source_file."
                )
            if target_node in result:
                raise ValueError(
                    f"Duplicate POS naming entry for {target_node} in {self.lab}."
                )
            result[target_node] = source_file
        return result

    def resolve_pos_output_name(self, target_node: str) -> str:
        """Return the physical POS filename configured for a logical slot."""
        node = _normalize_pos_node(target_node)
        filename = self._pos_names.get(node)
        if filename is None:
            raise KeyError(
                f"No POS output naming rule for {node} in laboratory {self.lab}."
            )
        return filename

    def resolve_itona_output_name(self, slot: str) -> str:
        """Return the standard Itona filename, including user-created slots."""
        normalized_slot = _normalize_itona_slot(slot)
        return f"_{normalized_slot}_pos-db.xml"

    def resolve_production_output_name(self, source_file: str | Path) -> str:
        """Normalize Production source naming to the Builder target naming."""
        key = _production_key(source_file)
        target = PRODUCTION_NAME_MAP.get(key)
        if target is None:
            raise KeyError(
                f"Unsupported Production filename: {Path(_text(source_file)).name}"
            )
        return target

    def pos_naming_table(self) -> list[dict[str, str]]:
        """Return POS naming rows suitable for reports or UI display."""
        return [
            {
                "lab": self.lab,
                "target_node": node,
                "output_file": filename,
            }
            for node, filename in sorted(self._pos_names.items())
        ]

    def snapshot(self) -> dict[str, Any]:
        """Return the active naming contract for diagnostics and reports."""
        return {
            "lab": self.lab,
            "config_path": str(self.config_path) if self.config_path else None,
            "pos": dict(sorted(self._pos_names.items())),
            "configured_itonas": sorted(
                self._configured_itonas,
                key=lambda value: int(value.removeprefix("Itona")),
            ),
            "production": {
                "_8000_pos-db.xml": "_PROD_PRI_pos-db.xml",
                "_8001_pos-db.xml": "_PROD_BACK_pos-db.xml",
            },
        }


def resolve_pos_output_name(
    target_node: str,
    *,
    config_path: str | Path | None = None,
    lab: str | None = None,
    config_folder: str | Path = DEFAULT_CONFIG_FOLDER,
) -> str:
    resolver = _resolver(config_path, lab, config_folder)
    return resolver.resolve_pos_output_name(target_node)


def resolve_itona_output_name(slot: str) -> str:
    return f"_{_normalize_itona_slot(slot)}_pos-db.xml"


def resolve_production_output_name(source_file: str | Path) -> str:
    key = _production_key(source_file)
    target = PRODUCTION_NAME_MAP.get(key)
    if target is None:
        raise KeyError(
            f"Unsupported Production filename: {Path(_text(source_file)).name}"
        )
    return target


def _resolver(
    config_path: str | Path | None,
    lab: str | None,
    config_folder: str | Path,
) -> LabNamingResolver:
    if config_path is not None:
        return LabNamingResolver.from_file(config_path)
    if lab is not None:
        return LabNamingResolver.from_lab(lab, config_folder)
    raise ValueError("Provide either config_path or lab.")
