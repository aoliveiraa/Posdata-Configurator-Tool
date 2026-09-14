from src.runtime_context import RuntimeContext

from src.discovery.dynamic_pos_mapping import (
    build_dynamic_pos_mapping,
    to_legacy_reference_pos_files,
)

from src.discovery.lab_independent_machine_mapping import (
    resolve_machine_for_target,
)


def run_mapping_phase(
    runtime: RuntimeContext,
) -> RuntimeContext:

    runtime.dynamic_pos_mapping = (
        build_dynamic_pos_mapping(
            discovery_result=
                runtime.dynamic_pos_discovery,
            config_path=
                runtime.config_path,
        )
    )

    runtime.dynamic_reference_pos_files = (
        to_legacy_reference_pos_files(
            runtime.dynamic_pos_mapping
        )
    )

    runtime.runtime_pos_machine_lookup = dict(
        runtime.current_node_lookup
    )

    runtime.pos_mapping = {
        "mappings": [],
        "warnings": list(
            runtime.dynamic_pos_mapping.get(
                "warnings",
                []
            )
        ),
        "errors": list(
            runtime.dynamic_pos_mapping.get(
                "errors",
                []
            )
        ),
    }

    for mapping in runtime.dynamic_pos_mapping.get(
        "mappings",
        []
    ):

        target_node = mapping["target_node"]

        machine_resolution = (
            resolve_machine_for_target(
                target={
                    "node": target_node,
                    "machine_ip": mapping.get(
                        "machine_ip"
                    ),
                    "output_file": mapping.get(
                        "output_file"
                    ),
                },
                current_machines=
                    runtime.pos_machine_mapping,
            )
        )

        runtime.runtime_pos_machine_lookup[
            target_node
        ] = {
            "machine_file":
                machine_resolution[
                    "current_machine_file"
                ],

            "ip":
                machine_resolution[
                    "target_machine_ip"
                ],

            "current_ip":
                machine_resolution[
                    "current_machine_ip"
                ],

            "output_file":
                machine_resolution[
                    "output_file"
                ],

            "detected_node":
                target_node,

            "status":
                "READY",
        }

        runtime.pos_mapping["mappings"].append(
            {
                "source_file":
                    mapping.get(
                        "source_file"
                    ),

                "node_name":
                    target_node,

                "target_file":
                    machine_resolution.get(
                        "output_file"
                    ),

                "status": "READY",

                "warnings":
                    list(
                        mapping.get(
                            "warnings",
                            []
                        )
                    ),

                "errors":
                    list(
                        mapping.get(
                            "errors",
                            []
                        )
                    ),
            }
        )

    return runtime