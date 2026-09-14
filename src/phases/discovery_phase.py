from pathlib import Path

from src.runtime_context import RuntimeContext

from src.discovery.market_detector import (
    detect_market,
)

from src.discovery.storedb_analyzer import (
    analyze_storedb,
)

from src.discovery.screen_analyzer import (
    analyze_screens,
    find_lunch_screen,
)

from src.discovery.pos_machine_discovery import (
    discover_current_pos_nodes,
    build_node_lookup,
)

from src.discovery.pos_source_discovery import (
    discover_pos_sources,
)

def run_discovery_phase(
    runtime: RuntimeContext,
) -> RuntimeContext:

    #
    # Market / Store
    #

    if runtime.store_db_path:

        runtime.market = detect_market(
            runtime.store_db_path
        )

        runtime.store_info = analyze_storedb(
            runtime.store_db_path
        )

    #
    # Screens
    #

    if runtime.screen_xml_path:

        runtime.screens = analyze_screens(
            runtime.screen_xml_path
        )

        runtime.lunch_screen = (
            find_lunch_screen(
                runtime.screens
            )
        )

    #
    # Current PosData
    #

    runtime = discover_current_posdata(
        runtime
    )

    #
    # Dynamic Discovery
    #

    runtime = discover_dynamic_pos_sources(
        runtime
    )

    return runtime

def discover_current_posdata(
    runtime: RuntimeContext,
) -> RuntimeContext:

    if not runtime.current_posdata_folder:
        return runtime

    runtime.pos_machine_mapping = (
        discover_current_pos_nodes(
            runtime.current_posdata_folder
        )
    )

    runtime.current_node_lookup = (
        build_node_lookup(
            runtime.pos_machine_mapping
        )
    )

    return runtime

def discover_dynamic_pos_sources(
    runtime: RuntimeContext,
) -> RuntimeContext:

    if not runtime.new_posdata_folder:
        return runtime

    runtime.dynamic_pos_discovery = (
        discover_pos_sources(
            new_posdata_folder=
                runtime.new_posdata_folder
        )
    )

    return runtime