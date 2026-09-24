from src.builder.builder_generation_adapter import (
    build_builder_runtime_context,
)

from src.builder.builder_output_manager import (
    clean_previous_output,
)

from src.phases.generation_phase import (
    run_generation_phase,
)

from src.phases.validation_phase import (
    run_validation_phase,
)

from src.builder.builder_generation_report import (
    generate_builder_generation_report,
)


def run_builder_generation_phase(
    builder_context,
):
    """
    Sprint 1.6.4

    Builder Adapter
        ↓
    Output Isolation
        ↓
    Generation
        ↓
    Validation
    """

    print()
    print(
        "BUILDER GENERATION PHASE"
    )

    print(
        "=" * 50
    )

    #
    # Output Builder
    #
    output_paths = (
        clean_previous_output()
    )

    #
    # Build Runtime Context
    #
    runtime = (
        build_builder_runtime_context(
            builder_context=builder_context,
            strict=True,
        )
    )

    #
    # Attach isolated output folder
    #
    runtime.output_paths = (
        output_paths
    )

    runtime.output_root = str(
        output_paths["root"]
    )

    runtime.storedb_output = str(
        output_paths["storedb"]
    )

    runtime.pos_output_folder = str(
        output_paths["pos"]
    )

    runtime.itona_output_folder = str(
        output_paths["itonas"]
    )

    runtime.production_output_folder = str(
        output_paths["production"]
    )

    runtime.validation_output_folder = str(
        output_paths["validation"]
    )

    runtime.reports_output_folder = str(
        output_paths["reports"]
    )

    print()

    print(
        "Generation Adapter"
    )

    print(
        "-" * 50
    )

    print(
        "Status:",
        runtime.builder_adapter_status,
    )

    print()

    print(
        "Output Folder:"
    )

    print(
        runtime.output_root
    )

    #
    # Existing generation pipeline
    #
    runtime = (
        run_generation_phase(
            runtime
        )
    )

    #
    # Existing validation pipeline
    #
    runtime = (
        run_validation_phase(
            runtime
        )
    )

    runtime.builder_generation_report = (
        generate_builder_generation_report(
            runtime=runtime,
            builder_context=builder_context,
            output_root="output",
        )
    )

    report_result = (
        runtime.builder_generation_report
    )

    print()
    print("BUILDER GENERATION REPORT")
    print("-" * 50)

    print(
        "Status:",
        report_result.get(
            "status",
            "UNKNOWN",
        ),
    )

    print(
        "TXT:",
        report_result.get(
            "text_report",
        ),
    )

    print(
        "JSON:",
        report_result.get(
            "json_report",
        ),
    )

    for error in report_result.get(
        "errors",
        [],
    ):
        print(
            "ERROR:",
            error,
        )

    #
    # Real counters
    #
    generated_pos_count = sum(
        1
        for item in (
            runtime.generated_pos
            or []
        )
        if item.get("generated") is True
    )

    not_generated_pos_count = sum(
        1
        for item in (
            runtime.generated_pos
            or []
        )
        if item.get("generated") is not True
    )

    generated_itona_count = sum(
        1
        for item in (
            runtime.generated_itonas
            or []
        )
        if item.get("generated") is True
    )

    not_generated_itona_count = sum(
        1
        for item in (
            runtime.generated_itonas
            or []
        )
        if item.get("generated") is not True
    )

    generated_production_count = sum(
        1
        for item in (
            runtime.generated_production
            or []
        )
        if item.get("generated") is True
    )

    not_generated_production_count = sum(
        1
        for item in (
            runtime.generated_production
            or []
        )
        if item.get("generated") is not True
    )

    print()

    print(
        "Generation Complete"
    )

    print(
        "-" * 50
    )

    print(
        "Generated POS:",
        generated_pos_count,
    )

    print(
        "POS not generated:",
        not_generated_pos_count,
    )

    print(
        "Generated Itonas:",
        generated_itona_count,
    )

    print(
        "Itonas not generated:",
        not_generated_itona_count,
    )

    print(
        "Generated Production:",
        generated_production_count,
    )

    print(
        "Production not generated:",
        not_generated_production_count,
    )

    print(
        "Validation:",
        runtime.validation_summary.get(
            "status",
            "UNKNOWN",
        )
    )

    return runtime