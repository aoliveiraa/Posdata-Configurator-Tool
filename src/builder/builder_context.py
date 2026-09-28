from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class BuilderContext:

    generation_mode: str = "FROM_SCRATCH"

    selected_lab: Optional[str] = None
    config_path: Optional[str] = None

    rules_path: Optional[Path] = None
    rules_available: bool = False

    source_posdata_folder: Optional[Path] = None

    store_db_path: Optional[Path] = None
    screen_xml_path: Optional[Path] = None

    build_plan: Dict[str, Any] = field(default_factory=dict)
    build_plan_validation: Dict[str, Any] = field(default_factory=dict)
    generated_manifest: Dict[str, Any] = field(default_factory=dict)

    # legacy compatibility
    template_market: Optional[str] = None
    template_folder: Optional[Path] = None
    template_validation: Dict[str, Any] = field(default_factory=dict)