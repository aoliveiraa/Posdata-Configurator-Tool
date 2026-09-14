from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RuntimeContext:
    """
    Shared execution state for the entire PosData Configurator run.

    The objective is to gradually remove large amounts of local
    variables from app.py and concentrate runtime data in a
    single object.

    This class intentionally uses generic Dict types for now
    to avoid forcing refactors across existing modules.
    """

    # ==========================================================
    # EXECUTION
    # ==========================================================

    selected_lab: Optional[str] = None
    config_path: Optional[str] = None

    # ==========================================================
    # INPUT FILES
    # ==========================================================

    current_posdata_folder: Optional[str] = None
    new_posdata_folder: Optional[str] = None

    store_db_path: Optional[str] = None
    screen_xml_path: Optional[str] = None

    # ==========================================================
    # MARKET DISCOVERY
    # ==========================================================

    market: Dict[str, Any] = field(default_factory=dict)

    # ==========================================================
    # STORE ANALYSIS
    # ==========================================================

    store_info: Dict[str, Any] = field(default_factory=dict)

    screens: List[Dict[str, Any]] = field(default_factory=list)

    lunch_screen: Optional[Dict[str, Any]] = None

    # ==========================================================
    # CURRENT POSDATA
    # ==========================================================

    reference_analysis: Dict[str, Any] = field(default_factory=dict)

    pos_machine_mapping: List[Dict[str, Any]] = (
        field(default_factory=list)
    )

    current_node_lookup: Dict[str, Any] = (
        field(default_factory=dict)
    )

    # ==========================================================
    # DYNAMIC POS DISCOVERY
    # ==========================================================

    dynamic_pos_discovery: Dict[str, Any] = (
        field(default_factory=dict)
    )

    dynamic_pos_mapping: Dict[str, Any] = (
        field(default_factory=dict)
    )

    # ==========================================================
    # MACHINE RESOLUTION
    # ==========================================================

    machine_resolutions: List[Dict[str, Any]] = (
        field(default_factory=list)
    )

    runtime_pos_machine_lookup: Dict[str, Any] = (
        field(default_factory=dict)
    )

    # ==========================================================
    # WAY
    # ==========================================================

    way_target: Dict[str, Any] = (
        field(default_factory=dict)
    )

    # ==========================================================
    # FOE
    # ==========================================================

    foe_result: Dict[str, Any] = (
        field(default_factory=dict)
    )

    # ==========================================================
    # ITONA / NPW
    # ==========================================================

    itona_analysis: List[Dict[str, Any]] = (
        field(default_factory=list)
    )

    kvs_mapping: Dict[str, Any] = (
        field(default_factory=dict)
    )

    # ==========================================================
    # COD
    # ==========================================================

    cod_target: Dict[str, Any] = (
        field(default_factory=dict)
    )

    cod_result: Dict[str, Any] = (
        field(default_factory=dict)
    )

    # ==========================================================
    # GENERATION RESULTS
    # ===========================================