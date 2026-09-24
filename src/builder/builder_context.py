from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class BuilderContext:
    """Shared state for one PosData Builder execution."""

    selected_lab: Optional[str] = None
    config_path: Optional[str] = None

    template_market: Optional[str] = None
    template_folder: Optional[Path] = None
    source_posdata_folder: Optional[Path] = None

    store_db_path: Optional[Path] = None
    screen_xml_path: Optional[Path] = None

    template_validation: Dict[str, Any] = field(default_factory=dict)
    source_validation: Dict[str, Any] = field(default_factory=dict)

    market: Dict[str, Any] = field(default_factory=dict)
    store_info: Dict[str, Any] = field(default_factory=dict)
    screens: List[Dict[str, Any]] = field(default_factory=list)
    lunch_screen: Optional[Dict[str, Any]] = None

    discovered_pos: Dict[str, Any] = field(default_factory=dict)
    discovered_itona_candidates: List[Dict[str, Any]] = field(default_factory=list)

    proposed_pos_mapping: Dict[str, Any] = field(default_factory=dict)
    confirmed_pos_mapping: Dict[str, Any] = field(default_factory=dict)
    proposed_itona_mapping: Dict[str, Any] = field(default_factory=dict)
    confirmed_itona_mapping: Dict[str, Any] = field(default_factory=dict)

    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
