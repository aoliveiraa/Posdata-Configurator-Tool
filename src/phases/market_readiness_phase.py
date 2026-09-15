from src.runtime_context import RuntimeContext


def _build_component_status(
    name,
    status,
    details=None,
):
    return {
        "name": name,
        "status": status,
        "details": details or [],
    }


def run_market_readiness_phase(
    runtime: RuntimeContext,
) -> RuntimeContext:
    """
    Sprint 14.1

    Consolida o estado do mercado analisado
    antes da geração.

    Não altera nenhuma lógica existente.
    Apenas produz o objeto:

        runtime.market_readiness
    """

    components = []

    #
    # POS
    #
    pos_status = "READY"

    if hasattr(
        runtime,
        "dynamic_pos_mapping"
    ):
        pos_status = (
            runtime.dynamic_pos_mapping.get(
                "status",
                "READY"
            )
        )

    components.append(
        _build_component_status(
            name="POS",
            status=pos_status,
            details=[
                f"Mappings: "
                f"{len(runtime.dynamic_pos_mapping.get('mappings', []))}"
            ]
            if hasattr(
                runtime,
                "dynamic_pos_mapping"
            )
            else [],
        )
    )
    #
    # KVS
    #
    kvs_status = "READY"

    kvs_mapping = getattr(
        runtime,
        "kvs_mapping",
        {}
    )

    if kvs_mapping:

        kvs_status = (
            kvs_mapping.get(
                "resolution_status",
                kvs_mapping.get(
                    "status",
                    "READY"
                )
            )
        )

    components.append(
        _build_component_status(
            name="KVS",
            status=kvs_status,
        )
    )

    #
    # ITONAS
    #
    itonas = getattr(
        runtime,
        "itonas",
        []
    )

    itona_count = len(
        itonas
    )

    all_itonas_found = all(
        itona.get(
            "found",
            False
        )
        for itona in itonas
    )

    if (
        itona_count > 0
        and all_itonas_found
    ):
        itona_status = "READY"
    else:
        itona_status = (
            "REVIEW REQUIRED"
        )

    components.append(
        _build_component_status(
            name="ITONAS",
            status=itona_status,
            details=[
                f"Itonas Found: {itona_count}"
            ],
        )
    )
    #
    # FOE
    #
    foe_result = getattr(
        runtime,
        "foe_result",
        {}
    )

    foe_status = (
        "READY"
        if foe_result.get(
            "found",
            False
        )
        else "REVIEW REQUIRED"
    )

    components.append(
        _build_component_status(
            name="FOE",
            status=foe_status,
        )
    )
    #
    # COD
    #
    cod_target = getattr(
        runtime,
        "cod_target",
        {}
    )

    cod_status = (
        "READY"
        if (
            cod_target.get(
                "enabled",
                False
            )
            and
            cod_target.get(
                "found",
                False
            )
        )
        else "REVIEW REQUIRED"
    )

    components.append(
        _build_component_status(
            name="COD",
            status=cod_status,
        )
    )

    #
    # StoreDB
    #
    storedb_status = (
        "READY"
        if getattr(
            runtime,
            "store_db_path",
            None
        )
        else "REVIEW REQUIRED"
    )

    components.append(
        _build_component_status(
            name="STOREDB",
            status=storedb_status,
        )
    )

    #
    # WAY
    #

    reference_analysis = getattr(
        runtime,
        "reference_analysis",
        {}
    )

    way_files = (
        reference_analysis.get(
            "way_files",
            []
        )
    )

    way_status = (
        "READY"
        if way_files
        else "REVIEW REQUIRED"
    )

    components.append(
        _build_component_status(
            name="WAY",
            status=way_status,
            details=[
                f"WAY files: {len(way_files)}"
            ],
        )
    )
    #
    # OVERALL STATUS
    #
    overall_status = (
        "READY FOR GENERATION"
    )

    for component in components:

        status = component[
            "status"
        ]

        normalized = str(
            status
        ).upper()

        if normalized in (
            "FAIL",
            "FAILED",
            "ERROR",
            "NOT READY"
        ):

            overall_status = (
                "NOT READY FOR GENERATION"
            )

            break

        if (
            status
            == "REVIEW REQUIRED"
        ):
            overall_status = (
                "REVIEW REQUIRED"
            )

    manual_kvs_resolutions = len(
        kvs_mapping.get(
            "manual_resolutions",
            []
        )
    )

    pos_resolution_summary = (
        getattr(
            runtime,
            "pos_mapping",
            {}
        ).get(
            "resolution_summary",
            {}
        )
    )

    runtime.market_readiness = {
        "overall_status":
            overall_status,

        "components":
            components,

        "manual_kvs_resolutions":
            manual_kvs_resolutions,

        "manual_pos_resolutions":
            pos_resolution_summary.get(
                "resolved",
                0
            ),

        "skipped_pos":
            pos_resolution_summary.get(
                "skipped",
                0
            ),

        "unresolved_pos":
            pos_resolution_summary.get(
                "unresolved",
                0
            ),
    }

    print()
    print("DEBUG GENERATED WAY")
    print(runtime.generated_way)

    return runtime