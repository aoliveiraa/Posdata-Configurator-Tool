from src.runtime_context import (
    RuntimeContext,
)

from src.resolution import (
    resolve_missing_kvs,
)

from src.phases import (
    run_discovery_phase,
    run_mapping_phase,
    run_analysis_phase,
    run_generation_phase,
    run_validation_phase,
    print_discovery_report,
    print_mapping_report,
    print_analysis_report,
    print_generation_report,
    print_validation_report,
)

from config.lab_loader import (
    load_lab_config,
)

from src.discovery.pos_browser_inventory import (
    inventory_pos_browsers,
)


from src.validators.pos_role_validator import (
    validate_generated_pos_roles
)


def main():

    runtime = RuntimeContext()

    LAB = "RENEIGH"

    lab_config = load_lab_config(
        LAB
    )

    CONFIG_PATH = (
        f"config/{LAB.lower()}_lab.json"
    )

    #
    # IMPORTANTE
    #
    runtime.config_path = CONFIG_PATH

    runtime.store_db_path = (
        "samples/new_posdata/store-db.xml"
    )

    runtime.screen_xml_path = (
        "samples/new_posdata/screen.xml"
    )

    runtime.current_posdata_folder = (
        "samples/current_posdata"
    )

    runtime.new_posdata_folder = (
        "samples/new_posdata"
    )

    #
    # DISCOVERY
    #

    runtime = run_discovery_phase(
        runtime
    )

    #
    # MAPPING
    #

    runtime = run_mapping_phase(
        runtime
    )

    #
    # ANALYSIS
    #

    runtime = run_analysis_phase(
        runtime
    )

    runtime.kvs_mapping = (
        resolve_missing_kvs(
            runtime.kvs_mapping
        )
    )
    
    #
    # GENERATION
    #

    runtime = run_generation_phase(
        runtime
    )

    runtime = run_validation_phase(
        runtime
    )

    #
    # SHORTCUTS
    #

    market = runtime.market
    info = runtime.store_info
    screens = runtime.screens
    lunch_screen = runtime.lunch_screen

    nodes = runtime.nodes
    reference = runtime.reference_analysis

    itonas = runtime.itonas
    kvs_mapping = runtime.kvs_mapping

    cod_target = runtime.cod_target
    foe_info = runtime.foe_result

    dynamic_pos_discovery = (
        runtime.dynamic_pos_discovery
    )

    dynamic_pos_mapping = (
        runtime.dynamic_pos_mapping
    )

    dynamic_reference_pos_files = (
        runtime.dynamic_reference_pos_files
    )

    runtime_pos_machine_lookup = (
        runtime.runtime_pos_machine_lookup
    )

    pos_mapping = (
        runtime.pos_mapping
    )

    pos_machine_mapping = (
        runtime.pos_machine_mapping
    )

    generated_pos = (
        runtime.generated_pos
    )

    xmlrpccli_result = (
        runtime.xmlrpccli_result
    )

    generated_way = (
        runtime.generated_way
    )

    generated_production = (
        runtime.generated_production
    )

    generated_foe = (
        runtime.generated_foe
    )

    generated_itonas = (
        runtime.generated_itonas
    )

    generated_cod = (
        runtime.generated_cod
    )

    generated_store_cod = (
        runtime.generated_store_cod
    )

    store_db = runtime.store_db_path

    print_discovery_report(
        runtime
    )

    print_mapping_report(
        runtime
    )

    print_analysis_report(
        runtime
    )

    print_generation_report(
        runtime
    )

    print_validation_report(
        runtime
    )


    # Integrates Ticket 10.1/10.2 with the existing POS transformer.
    # The selected source files come from dynamic discovery, while the
    # physical output machine is resolved by the lab IP. This avoids
    # assuming that logical POS numbers are identical across markets.
    machine_by_ip = {
        str(item.get("ip", "")).strip(): item
        for item in pos_machine_mapping
        if str(item.get("ip", "")).strip()
    }


    ready_count = sum(
        item["status"] == "READY"
        for item in pos_mapping["mappings"]
    )

    
    expected_count = len(dynamic_pos_mapping.get("mappings", []))

    if ready_count != expected_count:
        pos_mapping["warnings"].append(
            f"Expected {expected_count} ready POS mappings, "
            f"but found {ready_count}."
        )

    pos_browsers = inventory_pos_browsers(
        "samples/current_posdata"
    )



    runtime = run_generation_phase(
        runtime
    )

    generated_pos = runtime.generated_pos

    xmlrpccli_result = runtime.xmlrpccli_result

    generated_way = runtime.generated_way

    generated_production = (
        runtime.generated_production
    )

    generated_foe = (
        runtime.generated_foe
    )

    generated_itonas = (
        runtime.generated_itonas
    )

    generated_cod = (
        runtime.generated_cod
    )

    generated_store_cod = (
        runtime.generated_store_cod
    )


    runtime = run_validation_phase(
        runtime
    )

    print_generation_report(
        runtime
    )

    print_execution_summary(
        generated_pos=generated_pos,
        generated_way=generated_way,
        generated_foe=generated_foe,
        generated_itonas=generated_itonas,
        generated_cod=generated_cod,
        generated_store_cod=generated_store_cod,
    )


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

    #
    # POS
    #
    total_pos = len(generated_pos)

    generated_pos_count = sum(
        result.get("generated", False)
        for result in generated_pos
    )

    if generated_pos_count == total_pos:
        print(
            f"POS       : ✅ GENERATED "
            f"({generated_pos_count}/{total_pos})"
        )
    else:
        print(
            f"POS       : ⚠ GENERATED "
            f"({generated_pos_count}/{total_pos})"
        )

    #
    # WAY
    #
    if generated_way.get("generated"):
        print("WAY       : ✅ GENERATED")
    else:
        print("WAY       : ❌ FAILED")
        summary_errors.append(
            "WAY generation failed"
        )

    #
    # FOE
    #
    foe_generated = all(
        item.get("generated", False)
        for item in generated_foe
    )

    if foe_generated:
        print("FOE       : ✅ GENERATED")
    else:
        print("FOE       : ❌ FAILED")
        summary_errors.append(
            "FOE generation failed"
        )

    #
    # COD
    #
    if generated_cod.get("generated"):
        print("COD       : ✅ GENERATED")
    else:
        print("COD       : ❌ FAILED")
        summary_errors.append(
            "COD generation failed"
        )

    #
    # STORE COD
    #
    if generated_store_cod.get("generated"):
        print("STORE COD : ✅ GENERATED")
    else:
        print("STORE COD : ❌ FAILED")
        summary_errors.append(
            "Store COD generation failed"
        )

    #
    # ITONAS
    #
    generated_itona_count = sum(
        result.get("generated", False)
        for result in generated_itonas
    )

    total_itonas = len(generated_itonas)

    print(
        f"ITONAS    : "
        f"{generated_itona_count}/{total_itonas}"
    )

    for result in generated_itonas:

        if result.get("generated"):
            print(
                f"  ✅ {result['machine']}"
            )
        else:
            print(
                f"  ⚠ {result['machine']}"
            )

            summary_warnings.extend(
                result.get("warnings", [])
            )

            summary_errors.extend(
                result.get("errors", [])
            )

    #
    # ISSUES
    #
    if summary_warnings or summary_errors:

        print()
        print("-" * 50)
        print("ISSUES")
        print("-" * 50)

        for warning in summary_warnings:
            print(
                f"⚠ {warning}"
            )

        for error in summary_errors:
            print(
                f"❌ {error}"
            )

    #
    # OVERALL STATUS
    #
    print()
    print("-" * 50)
    print("OVERALL STATUS")
    print("-" * 50)

    if summary_errors:

        print("❌ FAILED")

    elif summary_warnings:

        print(
            "✅ SUCCESS WITH WARNINGS"
        )

    else:

        print(
            "✅ SUCCESS"
        )

    print("=" * 50)



if __name__ == "__main__":
    main()