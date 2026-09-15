from pathlib import Path

from config.lab_loader import load_lab_config
from src.phases import (
    print_analysis_report,
    print_discovery_report,
    print_generation_report,
    print_mapping_report,
    print_validation_report,
    run_analysis_phase,
    run_discovery_phase,
    run_generation_phase,
    run_mapping_phase,
    run_validation_phase,
)
from src.phases.market_readiness_phase import run_market_readiness_phase
from src.phases.reporting_phase import print_market_readiness_report
from src.resolution import resolve_missing_kvs
from src.resolution.pos_resolver import resolve_missing_positions
from src.runtime_context import RuntimeContext


SUPPORTED_LABS = {
    "RIO",
    "RENEIGH",
    "BR",
}


def normalize_inputs(
    selected_lab=None,
    current_posdata_folder=None,
    new_posdata_folder=None,
):
    normalized_lab = (
        str(selected_lab).strip().upper()
        if selected_lab
        else "RENEIGH"
    )

    if normalized_lab not in SUPPORTED_LABS:
        raise ValueError(
            "Unsupported laboratory: "
            f"{selected_lab}. "
            "Supported laboratories: RIO, RENEIGH and BR."
        )

    current_folder = Path(
        current_posdata_folder
        or "samples/current_posdata"
    )

    new_folder = Path(
        new_posdata_folder
        or "samples/new_posdata"
    )

    if not current_folder.is_dir():
        raise FileNotFoundError(
            "Current PosData folder was not found: "
            f"{current_folder}"
        )

    if not new_folder.is_dir():
        raise FileNotFoundError(
            "New PosData folder was not found: "
            f"{new_folder}"
        )

    store_db_path = new_folder / "store-db.xml"
    screen_xml_path = new_folder / "screen.xml"

    if not store_db_path.is_file():
        raise FileNotFoundError(
            "New StoreDB file was not found: "
            f"{store_db_path}"
        )

    if not screen_xml_path.is_file():
        raise FileNotFoundError(
            "New screen.xml file was not found: "
            f"{screen_xml_path}"
        )

    return {
        "lab": normalized_lab,
        "config_path": (
            f"config/{normalized_lab.lower()}_lab.json"
        ),
        "current_folder": current_folder,
        "new_folder": new_folder,
        "store_db_path": store_db_path,
        "screen_xml_path": screen_xml_path,
    }


def configure_runtime(runtime, inputs):
    runtime.selected_lab = inputs["lab"]
    runtime.config_path = inputs["config_path"]
    runtime.current_posdata_folder = inputs["current_folder"]
    runtime.new_posdata_folder = inputs["new_folder"]
    runtime.store_db_path = inputs["store_db_path"]
    runtime.screen_xml_path = inputs["screen_xml_path"]
    return runtime


def print_ui_configuration(inputs):
    print()
    print("UI CONFIGURATION")
    print("-" * 50)
    print(f"Selected Lab: {inputs['lab']}")
    print(f"Configuration: {inputs['config_path']}")
    print(f"Current PosData: {inputs['current_folder']}")
    print(f"New PosData: {inputs['new_folder']}")
    print(f"StoreDB: {inputs['store_db_path']}")
    print(f"Screen XML: {inputs['screen_xml_path']}")


def main(
    selected_lab=None,
    current_posdata_folder=None,
    new_posdata_folder=None,
):
    inputs = normalize_inputs(
        selected_lab=selected_lab,
        current_posdata_folder=current_posdata_folder,
        new_posdata_folder=new_posdata_folder,
    )

    # Validate that the selected laboratory configuration exists.
    load_lab_config(inputs["lab"])

    runtime = configure_runtime(
        RuntimeContext(),
        inputs,
    )

    print_ui_configuration(inputs)

    # ==================================================
    # DISCOVERY
    # ==================================================
    runtime = run_discovery_phase(runtime)

    # Some phase implementations may return a new context.
    # Preserve the UI-selected values explicitly.
    runtime = configure_runtime(runtime, inputs)

    # ==================================================
    # MAPPING AND RESOLUTIONS
    # ==================================================
    runtime = run_mapping_phase(runtime)

    runtime.pos_mapping = resolve_missing_positions(
        runtime.pos_mapping
    )

    # ==================================================
    # ANALYSIS
    # ==================================================
    runtime = run_analysis_phase(runtime)

    runtime.kvs_mapping = resolve_missing_kvs(
        runtime.kvs_mapping
    )

    # ==================================================
    # MARKET READINESS
    # ==================================================
    runtime = run_market_readiness_phase(runtime)
    print_market_readiness_report(runtime)

    # ==================================================
    # GENERATION
    # ==================================================
    runtime = run_generation_phase(runtime)

    # ==================================================
    # VALIDATION
    # ==================================================
    runtime = run_validation_phase(runtime)

    # ==================================================
    # REPORTING
    # Each report is printed exactly once.
    # ==================================================
    print_discovery_report(runtime)
    print_mapping_report(runtime)
    print_analysis_report(runtime)
    print_generation_report(runtime)
    print_validation_report(runtime)

    print_execution_summary(
        generated_pos=runtime.generated_pos or [],
        generated_way=runtime.generated_way or {},
        generated_foe=runtime.generated_foe or [],
        generated_itonas=runtime.generated_itonas or [],
        generated_cod=runtime.generated_cod or {},
        generated_store_cod=(
            runtime.generated_store_cod or {}
        ),
    )

    return runtime


def print_execution_summary(
    generated_pos,
    generated_way,
    generated_foe,
    generated_itonas,
    generated_cod,
    generated_store_cod,
):
    print()
    print("=" * 50)
    print("EXECUTION SUMMARY")
    print("=" * 50)

    summary_warnings = []
    summary_errors = []

    # POS
    total_pos = len(generated_pos)
    generated_pos_count = sum(
        bool(result.get("generated", False))
        for result in generated_pos
    )

    if total_pos > 0 and generated_pos_count == total_pos:
        print(
            "POS       : GENERATED "
            f"({generated_pos_count}/{total_pos})"
        )
    else:
        print(
            "POS       : WARNING "
            f"({generated_pos_count}/{total_pos})"
        )
        summary_warnings.append(
            "One or more POS files were not generated."
        )

    # WAY
    if generated_way.get("generated"):
        print("WAY       : GENERATED")
    else:
        print("WAY       : FAILED")
        summary_errors.append("WAY generation failed")

    # FOE is validated inside the generated WAYSTATION file.
    foe_generated = bool(generated_foe) and all(
        item.get("generated", False)
        for item in generated_foe
    )

    if foe_generated:
        print("FOE       : GENERATED")
    else:
        print("FOE       : FAILED")
        summary_errors.append("FOE generation failed")

    # COD
    if generated_cod.get("generated"):
        print("COD       : GENERATED")
    else:
        print("COD       : FAILED")
        summary_errors.append("COD generation failed")

    # STORE COD
    if generated_store_cod.get("generated"):
        print("STORE COD : GENERATED")
    else:
        print("STORE COD : FAILED")
        summary_errors.append("Store COD generation failed")

    # ITONAS
    generated_itona_count = sum(
        bool(result.get("generated", False))
        for result in generated_itonas
    )
    total_itonas = len(generated_itonas)

    print(
        "ITONAS    : "
        f"{generated_itona_count}/{total_itonas}"
    )

    for result in generated_itonas:
        machine = result.get("machine", "UNKNOWN")

        if result.get("generated"):
            print(f"  OK {machine}")
        else:
            print(f"  WARNING {machine}")
            summary_warnings.extend(
                result.get("warnings", [])
            )
            summary_errors.extend(
                result.get("errors", [])
            )

    if generated_itona_count != total_itonas:
        summary_warnings.append(
            "One or more Itona files were not generated."
        )

    # Avoid repeated messages in the summary.
    summary_warnings = list(
        dict.fromkeys(summary_warnings)
    )
    summary_errors = list(
        dict.fromkeys(summary_errors)
    )

    if summary_warnings or summary_errors:
        print()
        print("-" * 50)
        print("ISSUES")
        print("-" * 50)

        for warning in summary_warnings:
            print(f"WARNING: {warning}")

        for error in summary_errors:
            print(f"ERROR: {error}")

    print()
    print("-" * 50)
    print("OVERALL STATUS")
    print("-" * 50)

    if summary_errors:
        print("FAILED")
    elif summary_warnings:
        print("SUCCESS WITH WARNINGS")
    else:
        print("SUCCESS")

    print("=" * 50)


if __name__ == "__main__":
    main()
