from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RuntimeContext:
    """
    Shared execution state for the entire PosData Configurator run.

    The objective is to gradually remove large amounts of local
    variables from app.py and concentrate runtime data in a
    single object.
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

    market: Dict[str, Any] = field(
        default_factory=dict
    )

    # ==========================================================
    # STORE ANALYSIS
    # ==========================================================

    store_info: Dict[str, Any] = field(
        default_factory=dict
    )

    screens: List[Dict[str, Any]] = field(
        default_factory=list
    )

    lunch_screen: Optional[
        Dict[str, Any]
    ] = None

    # ==========================================================
    # CURRENT POSDATA
    # ==========================================================

    reference_analysis: Dict[str, Any] = field(
        default_factory=dict
    )

    pos_machine_mapping: List[
        Dict[str, Any]
    ] = field(
        default_factory=list
    )

    current_node_lookup: Dict[
        str,
        Any
    ] = field(
        default_factory=dict
    )

    # ==========================================================
    # DYNAMIC POS DISCOVERY
    # ==========================================================

    dynamic_pos_discovery: Dict[
        str,
        Any
    ] = field(
        default_factory=dict
    )

    # ==========================================================
    # DYNAMIC POS MAPPING
    # ==========================================================

    dynamic_pos_mapping: Dict[
        str,
        Any
    ] = field(
        default_factory=dict
    )

    dynamic_reference_pos_files: List[
        Dict[str, Any]
    ] = field(
        default_factory=list
    )

    # ==========================================================
    # MACHINE RESOLUTION
    # ==========================================================

    machine_resolutions: List[
        Dict[str, Any]
    ] = field(
        default_factory=list
    )

    runtime_pos_machine_lookup: Dict[
        str,
        Any
    ] = field(
        default_factory=dict
    )

    pos_mapping: Dict[
        str,
        Any
    ] = field(
        default_factory=dict
    )

    # ==========================================================
    # WAY
    # ==========================================================

    way_target: Dict[str, Any] = field(
        default_factory=dict
    )

    # ==========================================================
    # FOE
    # ==========================================================

    foe_result: Dict[str, Any] = field(
        default_factory=dict
    )

    # ================

    # ==========================================================
    # GENERATION RESULTS
    # ==========================================================

    generated_pos = field(
        default_factory=list
    )

    generated_way = field(
        default_factory=dict
    )

    generated_production = field(
        default_factory=list
    )

    generated_foe = field(
        default_factory=list
    )

    generated_itonas = field(
        default_factory=list
    )

    generated_cod = field(
        default_factory=dict
    )

    generated_store_cod = field(
        default_factory=dict
    )

    xmlrpccli_result = field(
        default_factory=dict
    )

    # ==========================================================
    # GENERATION
    # ==========================================================

    generated_pos: List[Dict[str, Any]] = field(
        default_factory=list
    )

    xmlrpccli_result: Dict[str, Any] = field(
        default_factory=dict
    )

    generated_way: Dict[str, Any] = field(
        default_factory=dict
    )

    generated_production: List[
        Dict[str, Any]
    ] = field(
        default_factory=list
    )

    generated_foe: List[
        Dict[str, Any]
    ] = field(
        default_factory=list
    )

    generated_itonas: List[
        Dict[str, Any]
    ] = field(
        default_factory=list
    )

    generated_cod: Dict[str, Any] = field(
        default_factory=dict
    )

    generated_store_cod: Dict[str, Any] = field(
        default_factory=dict
    )

    itonas: List[Dict[str, Any]] = field(
        default_factory=list
    )

    kvs_mapping: Dict[str, Any] = field(
        default_factory=dict
    )

    # ==========================================================
    # ANALYSIS
    # ==========================================================

    nodes: Dict[str, Any] = field(
        default_factory=dict
    )

    itonas: List[Dict[str, Any]] = field(
        default_factory=list
    )
    