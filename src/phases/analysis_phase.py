from src.runtime_context import (
    RuntimeContext,
)

from src.discovery.node_detector import (
    detect_nodes,
)

from src.discovery.reference_analyzer import (
    analyze_reference,
)

from src.discovery.itona_analyzer import (
    analyze_itonas,
)

from src.discovery.foe_analyzer import (
    analyze_foe,
)

from src.discovery.cod_discovery import (
    discover_cod_target,
)

from src.mapping.kvs_mapper import (
    map_kvs_to_itonas,
)


def run_analysis_phase(
    runtime: RuntimeContext,
) -> RuntimeContext:

    #
    # Nodes
    #

    runtime.nodes = detect_nodes(
        runtime.new_posdata_folder
    )

    #
    # Reference Analysis
    #

    runtime.reference_analysis = (
        analyze_reference(
            runtime.current_posdata_folder
        )
    )

    #
    # ITONA Analysis
    #

    runtime.itonas = (
        analyze_itonas(
            runtime.current_posdata_folder
        )
    )

    #
    # KVS Mapping
    #

    runtime.kvs_mapping = (
        map_kvs_to_itonas(
            reference_itonas=
                runtime.itonas,
            new_posdata_folder=
                runtime.new_posdata_folder,
        )
    )

    #
    # FOE Analysis
    #

    runtime.foe_result = (
        analyze_foe(
            f"{runtime.new_posdata_folder}/_WAYSTATION_pos-db.xml"
        )
    )

    #
    # COD Discovery
    #

    runtime.cod_target = (
        discover_cod_target(
            pos_machine_mapping=
                runtime.pos_machine_mapping,
            config_path=
                runtime.config_path,
        )
    )

    #
    # Multi-Lab COD Override
    #

    cod_node = runtime.cod_target.get(
        "node_name"
    )

    if (
        cod_node
        and cod_node in
        runtime.runtime_pos_machine_lookup
    ):

        resolved_output_file = (
            runtime.runtime_pos_machine_lookup[
                cod_node
            ].get(
                "output_file"
            )
        )

        if resolved_output_file:

            runtime.cod_target[
                "output_file"
            ] = (
                resolved_output_file
            )

    return runtime