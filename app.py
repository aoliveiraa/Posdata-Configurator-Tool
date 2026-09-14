from src.runtime_context import (
    RuntimeContext
)

from src.phases import (
    run_discovery_phase,
    run_mapping_phase,
    run_generation_phase,
    run_validation_phase,
)

from config.lab_loader import load_lab_config

from src.discovery.cod_discovery import (
    discover_cod_target
)

from src.transformers.pos_transformer import (
    generate_all_pos
)

from src.transformers.storedb_transformer import (
    update_main_screen,
    update_business_limits
)

from src.discovery.node_detector import (
    detect_nodes
)

from src.discovery.pos_role_detector import (
    detect_pos_roles
)

from src.discovery.reference_analyzer import (
    analyze_reference
)

from src.discovery.itona_analyzer import (
    analyze_itonas
)

from src.discovery.foe_analyzer import (
    analyze_foe
)

from src.mapping.kvs_mapper import map_kvs_to_itonas

from src.discovery.pos_browser_inventory import (
    inventory_pos_browsers
)

from src.discovery.pos_role_inventory import (
    inventory_pos_roles
)

from src.discovery.pos_keyword_inventory import (
    inventory_pos_keywords
)

from src.validators.pos_role_validator import (
    validate_generated_pos_roles
)

from src.discovery.pos_machine_discovery import (
    discover_current_pos_nodes,
    build_node_lookup
)

from src.discovery.pos_source_discovery import (
    discover_pos_sources,
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

    runtime.config_path = CONFIG_PATH

    #
    # MAPPING
    #

    runtime = run_mapping_phase(
        runtime
    )

    #
    # COMPATIBILIDADE TEMPORÁRIA
    #

    market = runtime.market

    info = runtime.store_info

    screens = runtime.screens

    lunch_screen = runtime.lunch_screen

    pos_machine_mapping = (
        runtime.pos_machine_mapping
    )

    pos_machine_lookup = (
        runtime.current_node_lookup
    )

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

    store_db = runtime.store_db_path

    #
    # ANALYSIS
    #

    nodes = detect_nodes(
        "samples/new_posdata"
    )

    reference = analyze_reference(
        "samples/current_posdata"
    )

    cod_target = discover_cod_target(
        pos_machine_mapping=
            pos_machine_mapping,
        config_path=
            CONFIG_PATH
    )

    runtime.cod_target = cod_target

    #
    # COD Multi-Lab Override
    #

    cod_node = runtime.cod_target.get(
        "node_name"
    )

    if (
        cod_node
        and cod_node in runtime.runtime_pos_machine_lookup
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
            ] = resolved_output_file


    itonas = analyze_itonas(
        "samples/current_posdata"
    )

    runtime.itonas = itonas

    kvs_mapping = map_kvs_to_itonas(
        reference_itonas=
            itonas,
        new_posdata_folder=
            runtime.new_posdata_folder,
    )

    runtime.kvs_mapping = (
        kvs_mapping
    )

    #
    # GENERATION
    #
    # SOMENTE AGORA
    #

    runtime = run_generation_phase(
        runtime
    )

    #
    # RESULTADOS
    #

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


    print()
    print("DYNAMIC POS DISCOVERY")
    print("-" * 50)

    print(
        f"Status: "
        f"{dynamic_pos_discovery['status']}"
    )

    print(
        f"POS candidates: "
        f"{len(dynamic_pos_discovery['pos_files'])}"
    )

    for pos_source in (
        dynamic_pos_discovery["pos_files"]
    ):
        print()

        print(
            f"File: "
            f"{pos_source['file']}"
        )

        print(
            f"Role: "
            f"{pos_source['role']}"
        )

        print(
            f"Role source: "
            f"{pos_source['role_source']}"
        )

        print(
            f"Role value: "
            f"{pos_source.get('role_value')}"
        )

        print(
            f"Role confidence: "
            f"{pos_source.get('role_confidence')}"
        )

        print(
            f"Role status: "
            f"{pos_source.get('role_status')}"
        )


        print(
            "Node candidates: "
            + (
                ", ".join(
                    pos_source[
                        "node_candidates"
                    ]
                )
                or "None"
            )
        )

    if dynamic_pos_discovery["errors"]:

        print()
        print("Errors:")

        for error in (
            dynamic_pos_discovery["errors"]
        ):
            print(
                f"  - {error}"
            )
    print()
    print("DYNAMIC POS MAPPING")
    print("-" * 50)

    print(
        f"Status: "
        f"{dynamic_pos_mapping['status']}"
    )

    print()

    for mapping in (
        dynamic_pos_mapping["mappings"]
    ):

        print(
            f"{mapping['target_node']} "
            f"[{mapping['expected_role']}]"
        )

        print(
            f"  Source: "
            f"{mapping['source_file']}"
        )

        print(
            f"  Source node: "
            f"{mapping['source_node']}"
        )

        print(
            f"  Source role: "
            f"{mapping['source_role']}"
        )

        print(
            f"  Selection: "
            f"{mapping['selection_reason']}"
        )

        print(
            f"  Status: "
            f"{mapping['status']}"
        )

        for warning in mapping["warnings"]:
            print(
                f"  WARNING: {warning}"
            )

        print()


    print()
    print("REFERENCE POS FILES IN USE")
    print("-" * 50)

    for item in dynamic_reference_pos_files:

        print(
            f"{item['target_node']} "
            f"<- "
            f"{item['source_file']}"
        )

    if dynamic_pos_mapping["unused_sources"]:

        print("UNUSED POS SOURCES")
        print("-" * 50)

        for source in (
            dynamic_pos_mapping[
                "unused_sources"
            ]
        ):

            print(
                f"{source['file']} "
                f"[{source['role']}]"
            )

    if dynamic_pos_mapping["errors"]:

        print()
        print("MAPPING ERRORS")
        print("-" * 50)

        for error in (
            dynamic_pos_mapping["errors"]
        ):

            print(
                f"  - {error}"
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


    foe_info = analyze_foe(
        "samples/new_posdata/_WAYSTATION_pos-db.xml"
    )

    pos_browsers = inventory_pos_browsers(
        "samples/current_posdata"
    )

    itonas = analyze_itonas(
        "samples/current_posdata"
    )
    runtime.itonas = itonas

    kvs_mapping = map_kvs_to_itonas(
    reference_itonas=itonas,
    new_posdata_folder="samples/new_posdata"
    )
    runtime.kvs_mapping = kvs_mapping  

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


      

    pos_role_validation = (
        validate_generated_pos_roles(
            output_folder="output/pos",
            pos_machine_lookup=
                runtime_pos_machine_lookup,
            config_path=
                CONFIG_PATH
        )
    )

    print()
    print(
        f"POS ROLE RESULTS: "
        f"{len(pos_role_validation)}"
    )

    roles = detect_pos_roles(
    "samples/new_posdata"
    )

    pos_role_inventory = inventory_pos_roles(
        "samples/current_posdata"
    )

    pos_keywords = inventory_pos_keywords(
    "samples/current_posdata"
    )

    print("\n=== PosData Configurator ===")
    print()

    print(f"Market: {market['country']}")
    print()

    print("Store Information")
    print("---------------------------------")

    print(f"Store ID: {info['store_id']}")
    print(f"City: {info['city']}")
    print(f"Country: {info['country']}")

    print()

    print(
        f"Main Screen: {info['main_screen']}"
    )

    print(
        f"Business Limits Found: {info['business_limits']}"
    )

    print()
    print("Screen Analysis")
    print("---------------------------------")
    print(f"Total Screens Found: {len(screens)}")

    print()
    print("Lunch Detection")
    print("---------------------------------")

    if lunch_screen:

        print(
            f"Lunch Screen Found: {lunch_screen['number']}"
        )

        print(
            f"Title: {lunch_screen['title']}"
        )

        if str(info["main_screen"]) == str(lunch_screen["number"]):

            print()
            print("✅ Main Screen already correct")

        else:

            print()
            print("⚠ Main Screen needs update")

            print(
                f"Current: {info['main_screen']}"
            )

            print(
                f"Expected: {lunch_screen['number']}"
            )

    else:

        print("❌ Lunch Screen not found")

    if lunch_screen:

        update_main_screen(
            runtime.store_db_path,
            "output/store-db.xml",
            lunch_screen["number"]
        )

        print()
        print(
            "✅ output/store-db.xml generated"
        )

    else:

        generated_store_cod = {
            "generated": False,
            "file": None,
            "changes": [],
            "warnings": [],
            "errors": [
                "StoreDB output was not generated "
                "because the lunch screen "
                "was not found."
            ]
        }

        print()
        print(
            "✅ output/store-db.xml generated"
        )
    update_business_limits(
        "output/store-db.xml",
        "output/store-db.xml",
        "config/business_limits.xml"
    )

    print()
    print(
        "✅ BusinessLimits updated"
    )

    generated_pos = generate_all_pos(
        pos_mapping=pos_mapping,
        pos_machine_lookup=runtime_pos_machine_lookup,
        new_posdata_folder=(
            "samples/new_posdata"
        ),
        output_folder="output/pos"
    )

    print()
    print("XMLRPCCLI GENERATION")
    print("-" * 50)

    print(
        "Store Controller IP: "
        f"{xmlrpccli_result['store_controller_ip']}"
    )

    print(
        "URL: "
        f"{xmlrpccli_result['url']}"
    )

    print(
        "Status: "
        f"{xmlrpccli_result['status']}"
    )

    store_result = (
        xmlrpccli_result.get(
            "store"
        )
    )

    if store_result:

        print()
        print("StoreDB")

        print(
            f"  File: "
            f"{store_result['file']}"
        )

        print(
            f"  Status: "
            f"{store_result['status']}"
        )

        for change in (
            store_result["changes"]
        ):
            print(
                f"  - {change}"
            )

    print()
    print("POS Files")

    for pos_result in (
        xmlrpccli_result["pos"]
    ):

        print(
            f"  {pos_result['node']}: "
            f"{pos_result['status']}"
        )

        print(
            f"    Current: "
            f"{pos_result['current_file']}"
        )

        print(
            f"    Output: "
            f"{pos_result['file']}"
        )

        for change in (
            pos_result["changes"]
        ):
            print(
                f"    - {change}"
            )

    if xmlrpccli_result["warnings"]:

        print()
        print("Warnings")

        for warning in (
            xmlrpccli_result["warnings"]
        ):
            print(
                f"  - {warning}"
            )

    if xmlrpccli_result["errors"]:

        print()
        print("Errors")

        for error in (
            xmlrpccli_result["errors"]
        ):
            print(
                f"  - {error}"
            )



    print()
    print("POS Found")
    print("---------------------------------")

    for pos in nodes["pos"]:
        print(pos)

    print()
    print("KVS Found")
    print("---------------------------------")

    for kvs in nodes["kvs"]:
        print(kvs)

    print()
    print("WAY Found")
    print("---------------------------------")

    for way in nodes["way"]:
        print(way)

    print()
    print("Production Found")
    print("---------------------------------")

    for prod in nodes["production"]:
        print(prod)

    print()
    print("POS Roles")
    print("---------------------------------")

    for role in roles:

        print(
            f"{role['file']} -> {role['role']}"
        )

    print()
    print("REFERENCE POSDATA")
    print("---------------------------------")

    print()
    print("Performance POS Machines")

    for pos_file in reference["pos_machines"]:
        print(f"  {pos_file}")

    print()
    print("Performance Itonas")

    for itona_file in reference["itonas"]:
        print(f"  {itona_file}")

    print()
    print("WAY")

    if reference["way_files"]:
        for way_file in reference["way_files"]:
            print(f"  {way_file}")
    else:
        print("  NOT FOUND")

    print()
    print("Production")

    if reference["production_primary"]:
        print(
            "  Primary: "
            + ", ".join(
                reference["production_primary"]
            )
        )
    else:
        print("  Primary: NOT FOUND")

    if reference["production_backup"]:
        print(
            "  Backup: "
            + ", ".join(
                reference["production_backup"]
            )
        )
    else:
        print("  Backup: NOT FOUND")

    print()
    print(
        "Ignored reference files: "
        f"{len(reference['ignored_files'])}"
    )

    if reference["warnings"]:

        print()
        print("Reference Warnings")

        for warning in reference["warnings"]:
            print(f"  WARNING: {warning}")


    print()
    print("ACTIVE ITONA ANALYSIS")
    print("---------------------------------")

    for itona in itonas:

        print()
        print(itona["machine"])

        if not itona["found"]:
            print("  File: NOT FOUND")

            for warning in itona["warnings"]:
                print(f"  WARNING: {warning}")

            continue

        print(f"  File: {itona['file']}")

        print(
            "  KVS Services: "
            + (
                ", ".join(itona["kvs_services"])
                if itona["kvs_services"]
                else "NONE"
            )
        )

        print(
            "  NPW Service Containers: "
            + (
                ", ".join(itona["npw_services"])
                if itona["npw_services"]
                else "NONE"
            )
        )

        print(
            "  Browser Nodes: "
            + (
                ", ".join(itona["browser_nodes"])
                if itona["browser_nodes"]
                else "NONE"
            )
        )

        if itona["webview_complete"]:
            print("  WebView Status: COMPLETE")
        else:
            print("  WebView Status: INCOMPLETE")

        for warning in itona["warnings"]:
            print(f"  WARNING: {warning}")

    print()
    print("KVS MAPPING PROPOSAL")
    print("---------------------------------")

    for mapping in kvs_mapping["mappings"]:

        print()
        print(
            f"{mapping['machine']} "
            f"-> {mapping['target_file']}"
        )

        print(
            f"  Status: {mapping['status']}"
        )

        if mapping["mapped_services"]:

            print("  Selected Services:")

            for service in mapping["mapped_services"]:

                active_status = (
                    "ACTIVE"
                    if service["startonload"]
                    else "INACTIVE"
                )

                print(
                    f"    KVS{service['service']} "
                    f"from {service['source_file']} "
                    f"[{active_status}]"
                )

        else:

            print("  Selected Services: NONE")

        if mapping["missing_services"]:

            missing_text = ", ".join(
                f"KVS{service_id}"
                for service_id
                in mapping["missing_services"]
            )

            print(
                "  Missing Services: "
                + missing_text
            )

        for warning in mapping["warnings"]:
            print(f"  WARNING: {warning}")

    
    print()
    print("UNUSED KVS SERVICES")
    print("---------------------------------")

    if kvs_mapping["extra_services"]:

        for extra in kvs_mapping["extra_services"]:

            active_status = (
                "ACTIVE"
                if extra["startonload"]
                else "INACTIVE"
            )

            print(
                f"KVS{extra['service']} "
                f"from {extra['source_file']} "
                f"[{active_status}]"
            )

    else:

        print("NONE")

    if kvs_mapping["discovery_errors"]:

        print()
        print("KVS DISCOVERY ERRORS")
        print("---------------------------------")

        for error in kvs_mapping["discovery_errors"]:

            print(
                f"{error['source_file']}: "
                f"{error['error']}"
            )
     
    print()
    print("ITONA GENERATION")
    print("---------------------------------")

    for result in generated_itonas:

        print()
        print(result["machine"])

        if result["generated"]:

            print("  Status: GENERATED")

            print(
                "  Output: "
                f"{result['output_file']}"
            )

        else:

            print("  Status: NOT GENERATED")

        for warning in result["warnings"]:

            print(
                f"  WARNING: {warning}"
            )

        for error in result["errors"]:

            print(
                f"  ERROR: {error}"
            )

    print()
    print("POS BROWSER INVENTORY")
    print("---------------------------------")

    for pos in pos_browsers:

        print()
        print(pos["file"])

        print(
            f"Browser Count: "
            f"{pos['browser_count']}"
        )

        for browser in pos["browser_names"]:

            print(f"  {browser}")

    print()
    print("POS ROLE INVENTORY")
    print("---------------------------------")

    for pos in pos_role_inventory:

        print()
        print(pos["file"])

        print(
            f"OperationMode: "
            f"{pos['operation_modes']}"
        )

        print(
            f"PODType: "
            f"{pos['pod_types']}"
        )

        print(
            f"PosType: "
            f"{pos['pos_types']}"
        )

    print()
    print("POS KEYWORD INVENTORY")
    print("---------------------------------")

    for pos in pos_keywords:

        print()
        print(pos["file"])

        for key, value in pos["matches"].items():

            print(
                f"  {key}: {value}"
            )

    print()
    print("POS MAPPING")
    print("---------------------------------")

    for mapping in pos_mapping["mappings"]:

        print()

        print(
            f"{mapping['source_file']}"
        )

        print(
            f"  Node: "
            f"{mapping['node_name']}"
        )

        print(
            f"  Machine file: "
            f"{mapping['target_file']}"
        )

        print(
            f"  Status: "
            f"{mapping['status']}"
        )

        for warning in mapping[
            "warnings"
        ]:

            print(
                f"  WARNING: {warning}"
            )

    for warning in pos_mapping[
        "warnings"
    ]:

        print(
            f"WARNING: {warning}"
        )

    for error in pos_mapping[
        "errors"
    ]:

        print(
            f"ERROR: {error}"
        )

    print()
    print("POS GENERATION")
    print("---------------------------------")

    for result in generated_pos:

        print()
        print(result["node_name"])

        print(
            f"  Source: "
            f"{result['source_file']}"
        )

        if result.get("machine_file"):
            print(
                f"  Machine file: "
                f"{result['machine_file']}"
            )

        if result.get("machine_ip"):
            print(
                f"  Machine IP: "
                f"{result['machine_ip']}"
            )

        if result.get("rio_output_file"):
            print(
                f"  RIO filename: "
                f"{result['rio_output_file']}"
            )

        if result["generated"]:
            print("  Status: GENERATED")

            print(
                f"  Output: "
                f"{result['output_file']}"
            )

        else:
            print("  Status: NOT GENERATED")

        if result["changes"]:
            print("  Changes:")

            for change in result["changes"]:
                print(f"    - {change}")

        for warning in result["warnings"]:
            print(f"  WARNING: {warning}")

        for error in result["errors"]:
            print(f"  ERROR: {error}")

    print()
    print("WAY GENERATION")
    print("---------------------------------")

    print(
        f"Source: "
        f"{generated_way['source_file']}"
    )

    if generated_way["generated"]:
        print("Status: GENERATED")

        print(
            f"Output: "
            f"{generated_way['output_file']}"
        )

    else:
        print("Status: NOT GENERATED")

    if generated_way["changes"]:
        print("Changes:")

        for change in generated_way[
            "changes"
        ]:
            print(f"  - {change}")

    for warning in generated_way[
        "warnings"
    ]:
        print(
            f"WARNING: {warning}"
        )

    for error in generated_way[
        "errors"
    ]:
        print(
            f"ERROR: {error}"
        )

    print()
    print("PRODUCTION GENERATION")
    print("---------------------------------")

    if not generated_production:

        print(
            "No Production files found."
        )

    for result in generated_production:

        print()
        print(result["file"])

        if result["generated"]:

            print(
                "  Status: GENERATED"
            )

            print(
                f"  Output: "
                f"{result['output_file']}"
            )

        else:

            print(
                "  Status: NOT GENERATED"
            )

        if result["changes"]:

            print(
                "  Changes:"
            )

            for change in result[
                "changes"
            ]:

                print(
                    f"    - {change}"
                )

        for error in result[
            "errors"
        ]:

            print(
                f"  ERROR: {error}"
            )

    print()
    print("FOE ANALYSIS")
    print("---------------------------------")

    if foe_info["found"]:

        print(
            f"Service Name: "
            f"{foe_info['service_name']}"
        )

        print()

        print("Sections:")

        for section in foe_info["sections"]:

            print(
                f"  {section}"
            )

        print()

        print("Adaptors:")

        for adaptor in foe_info["adaptors"]:

            print(
                f"  {adaptor}"
            )

    else:

        print(
            f"ERROR: "
            f"{foe_info['error']}"
        )

    print()
    print("FOE GENERATION")
    print("---------------------------------")

    if not generated_foe:

        print(
            "No FOE files found."
        )

    for result in generated_foe:

        print()
        print(result["file"])

        if result["generated"]:

            print(
                "  Status: GENERATED"
            )

            print(
                f"  Output: "
                f"{result['output_file']}"
            )

        else:

            print(
                "  Status: NOT GENERATED"
            )

        if result["changes"]:

            print(
                "  Changes:"
            )

            for change in result[
                "changes"
            ]:

                print(
                    f"    - {change}"
                )

        for error in result[
            "errors"
        ]:

            print(
                f"  ERROR: {error}"
            )

    print()
    print("POS ROLE VALIDATION")
    print("---------------------------------")

    for result in pos_role_validation:

        print()

        print(result["file"])

        print(
            f"  Expected: "
            f"{result['expected_role']}"
        )

        print(
            f"  Detected: "
            f"{result['detected_role']}"
        )

        print(
            f"  POD: "
            f"{result['pod']}"
        )

        print(
            f"  RemPOD: "
            f"{result['rem_pod']}"
        )

        print(
            f"  PODType: "
            f"{result['pod_type']}"
        )

        if result["valid"]:
            print(
                "  Status: VALID"
            )

        else:
            print(
                "  Status: INVALID"
            )

        for warning in result[
            "warnings"
        ]:

            print(
                f"  WARNING: {warning}"
            )

        for error in result[
            "errors"
        ]:

            print(
                f"  ERROR: {error}"
            )

    print()
    print("POS MACHINE DISCOVERY")
    print("---------------------------------")

    for item in pos_machine_mapping:

        print()

        print(
            item["machine_file"]
        )

        print(
            f"  Node: "
            f"{item['detected_node']}"
        )

        print(
            f"  IP: "
            f"{item['ip']}"
        )

        print(
            f"  Output: "
            f"{item['output_file']}"
        )

        print(
            f"  Status: "
            f"{item['status']}"
        )


    print()
    print("POS MACHINE LOOKUP")
    print("---------------------------------")

    for node, info in runtime_pos_machine_lookup.items():

        print(
            f"{node} -> "
            f"{info['output_file']}"
        )
    
    print()
    print("COD TARGET DISCOVERY")
    print("---------------------------------")

    print(
        f"Enabled: "
        f"{cod_target['enabled']}"
    )

    print(
        f"Reference machine: "
        f"{cod_target['reference_machine']}"
    )

    print(
        f"Detected node: "
        f"{cod_target['node_name']}"
    )

    print(
        f"Machine IP: "
        f"{cod_target['ip']}"
    )

    print(
        f"Output file: "
        f"{cod_target['output_file']}"
    )

    if cod_target["found"]:
        print("Status: READY")
    else:
        print("Status: NOT READY")

    for warning in cod_target[
        "warnings"
    ]:
        print(
            f"WARNING: {warning}"
        )

    for error in cod_target[
        "errors"
    ]:
        print(
            f"ERROR: {error}"
        )

    print()
    print("COD GENERATION")
    print("---------------------------------")

    if generated_cod["generated"]:

        print(
            f"Node: "
            f"{generated_cod['node']}"
        )

        print(
            f"File: "
            f"{generated_cod['file']}"
        )

        print("Status: GENERATED")

        print("Changes:")

        for change in generated_cod[
            "changes"
        ]:

            print(
                f"  - {change}"
            )

    else:

        print(
            "Status: NOT GENERATED"
        )

        for error in generated_cod[
            "errors"
        ]:

            print(
                f"ERROR: {error}"
            )

    print()
    print("STORE COD GENERATION")
    print("---------------------------------")

    if generated_store_cod["generated"]:

        print(
            f"File: "
            f"{generated_store_cod['file']}"
        )

        print(
            "Status: GENERATED"
        )

    else:

        print(
            "Status: NOT GENERATED"
        )

        if generated_store_cod.get(
            "file"
        ):

            print(
                f"File: "
                f"{generated_store_cod['file']}"
            )

    if generated_store_cod[
        "changes"
    ]:

        print(
            "Changes:"
        )

        for change in (
            generated_store_cod[
                "changes"
            ]
        ):

            print(
                f"  - {change}"
            )

    for warning in (
        generated_store_cod[
            "warnings"
        ]
    ):

        print(
            f"WARNING: {warning}"
        )

    for error in (
        generated_store_cod[
            "errors"
        ]
    ):

        print(
            f"ERROR: {error}"
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