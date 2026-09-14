from src.runtime_context import (
    RuntimeContext,
)


def print_discovery_report(
    runtime: RuntimeContext,
) -> None:

    discovery = (
        runtime.dynamic_pos_discovery
    )

    print()
    print("DYNAMIC POS DISCOVERY")
    print("-" * 50)

    print(
        f"Status: "
        f"{discovery.get('status', 'UNKNOWN')}"
    )

    print(
        f"POS candidates: "
        f"{len(discovery.get('pos_files', []))}"
    )

    for pos_source in (
        discovery.get(
            "pos_files",
            []
        )
    ):

        print()

        print(
            f"File: "
            f"{pos_source.get('file')}"
        )

        print(
            f"Role: "
            f"{pos_source.get('role')}"
        )

        print(
            f"Role source: "
            f"{pos_source.get('role_source')}"
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
                    pos_source.get(
                        "node_candidates",
                        []
                    )
                )
                or "None"
            )
        )

    if discovery.get("errors"):

        print()
        print("Errors:")

        for error in (
            discovery.get(
                "errors",
                []
            )
        ):
            print(
                f"  - {error}"
            )

def print_mapping_report(
    runtime: RuntimeContext,
) -> None:

    mapping = (
        runtime.dynamic_pos_mapping
    )

    reference_files = (
        runtime.dynamic_reference_pos_files
    )

    print()
    print("DYNAMIC POS MAPPING")
    print("-" * 50)

    print(
        f"Status: "
        f"{mapping.get('status', 'UNKNOWN')}"
    )

    print()

    for item in (
        mapping.get(
            "mappings",
            []
        )
    ):

        print(
            f"{item.get('target_node')} "
            f"[{item.get('expected_role')}]"
        )

        print(
            f"  Source: "
            f"{item.get('source_file')}"
        )

        print(
            f"  Source node: "
            f"{item.get('source_node')}"
        )

        print(
            f"  Source role: "
            f"{item.get('source_role')}"
        )

        print(
            f"  Selection: "
            f"{item.get('selection_reason')}"
        )

        print(
            f"  Status: "
            f"{item.get('status')}"
        )

        for warning in (
            item.get(
                "warnings",
                []
            )
        ):
            print(
                f"  WARNING: {warning}"
            )

        print()

    print()
    print("REFERENCE POS FILES IN USE")
    print("-" * 50)

    for item in reference_files:

        print(
            f"{item.get('target_node')} "
            f"<- "
            f"{item.get('source_file')}"
        )

    if mapping.get(
        "unused_sources"
    ):

        print()
        print("UNUSED POS SOURCES")
        print("-" * 50)

        for source in (
            mapping.get(
                "unused_sources",
                []
            )
        ):

            print(
                f"{source.get('file')} "
                f"[{source.get('role')}]"
            )

    if mapping.get(
        "errors"
    ):

        print()
        print("MAPPING ERRORS")
        print("-" * 50)

        for error in (
            mapping.get(
                "errors",
                []
            )
        ):

            print(
                f"  - {error}"
            )

def print_analysis_report(
    runtime: RuntimeContext,
) -> None:

    itonas = runtime.itonas

    kvs_mapping = runtime.kvs_mapping

    foe_info = runtime.foe_result

    #
    # ACTIVE ITONA ANALYSIS
    #

    print()
    print("ACTIVE ITONA ANALYSIS")
    print("-" * 50)

    for itona in itonas:

        print()
        print(itona["machine"])

        if not itona["found"]:

            print(
                "  File: NOT FOUND"
            )

            for warning in (
                itona.get(
                    "warnings",
                    []
                )
            ):
                print(
                    f"  WARNING: {warning}"
                )

            continue

        print(
            f"  File: "
            f"{itona['file']}"
        )

        print(
            "  KVS Services: "
            + (
                ", ".join(
                    itona.get(
                        "kvs_services",
                        []
                    )
                )
                or "NONE"
            )
        )

        print(
            "  NPW Service Containers: "
            + (
                ", ".join(
                    itona.get(
                        "npw_services",
                        []
                    )
                )
                or "NONE"
            )
        )

        print(
            "  Browser Nodes: "
            + (
                ", ".join(
                    itona.get(
                        "browser_nodes",
                        []
                    )
                )
                or "NONE"
            )
        )

        print(
            "  WebView Status: "
            + (
                "COMPLETE"
                if itona.get(
                    "webview_complete"
                )
                else "INCOMPLETE"
            )
        )

        for warning in (
            itona.get(
                "warnings",
                []
            )
        ):
            print(
                f"  WARNING: {warning}"
            )

    #
    # KVS MAPPING
    #

    print()
    print("KVS MAPPING PROPOSAL")
    print("-" * 50)

    for mapping in (
        kvs_mapping.get(
            "mappings",
            []
        )
    ):

        print()

        print(
            f"{mapping['machine']} "
            f"-> "
            f"{mapping['target_file']}"
        )

        print(
            f"  Status: "
            f"{mapping['status']}"
        )

        if mapping.get(
            "mapped_services"
        ):

            print(
                "  Selected Services:"
            )

            for service in (
                mapping[
                    "mapped_services"
                ]
            ):

                active_status = (
                    "ACTIVE"
                    if service[
                        "startonload"
                    ]
                    else "INACTIVE"
                )

                print(
                    f"    KVS{service['service']} "
                    f"from "
                    f"{service['source_file']} "
                    f"[{active_status}]"
                )

        if mapping.get(
            "missing_services"
        ):

            missing_text = (
                ", ".join(
                    f"KVS{s}"
                    for s in (
                        mapping[
                            "missing_services"
                        ]
                    )
                )
            )

            print(
                "  Missing Services: "
                + missing_text
            )

        for warning in (
            mapping.get(
                "warnings",
                []
            )
        ):
            print(
                f"  WARNING: {warning}"
            )

    #
    # UNUSED KVS
    #

    print()
    print("UNUSED KVS SERVICES")
    print("-" * 50)

    if kvs_mapping.get(
        "extra_services"
    ):

        for extra in (
            kvs_mapping[
                "extra_services"
            ]
        ):

            active_status = (
                "ACTIVE"
                if extra[
                    "startonload"
                ]
                else "INACTIVE"
            )

            print(
                f"KVS{extra['service']} "
                f"from "
                f"{extra['source_file']} "
                f"[{active_status}]"
            )

    else:

        print("NONE")

    #
    # FOE
    #

    print()
    print("FOE ANALYSIS")
    print("-" * 50)

    if foe_info.get(
        "found"
    ):

        print(
            f"Service Name: "
            f"{foe_info['service_name']}"
        )

        print()
        print("Sections:")

        for section in (
            foe_info.get(
                "sections",
                []
            )
        ):
            print(
                f"  {section}"
            )

        print()
        print("Adaptors:")

        for adaptor in (
            foe_info.get(
                "adaptors",
                []
            )
        ):
            print(
                f"  {adaptor}"
            )

    else:

        print(
            f"ERROR: "
            f"{foe_info.get('error')}"
        )

def print_generation_report(
    runtime: RuntimeContext,
) -> None:

    xmlrpccli_result = (
        runtime.xmlrpccli_result
        or {}
    )

    generated_foe = (
        runtime.generated_foe
        or []
    )

    generated_cod = (
        runtime.generated_cod
        or {}
    )

    generated_store_cod = (
        runtime.generated_store_cod
        or {}
    )

    #
    # GENERATION REPORT
    #

    print()
    print("GENERATION REPORT")
    print("=" * 50)

    #
    # XMLRPCCLI GENERATION
    #

    print()
    print("XMLRPCCLI GENERATION")
    print("-" * 50)

    if not xmlrpccli_result:

        print("No XMLRPCCLI generation result available.")

    else:

        print(
            "Store Controller IP: "
            f"{xmlrpccli_result.get('store_controller_ip', 'NOT FOUND')}"
        )

        print(
            "URL: "
            f"{xmlrpccli_result.get('url', 'NOT FOUND')}"
        )

        print(
            "Status: "
            f"{xmlrpccli_result.get('status', 'UNKNOWN')}"
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
                "  File: "
                f"{store_result.get('file', 'NOT FOUND')}"
            )

            print(
                "  Status: "
                f"{store_result.get('status', 'UNKNOWN')}"
            )

            for change in (
                store_result.get(
                    "changes",
                    []
                )
            ):
                print(
                    f"  - {change}"
                )

        print()
        print("POS Files")

        pos_results = (
            xmlrpccli_result.get(
                "pos",
                []
            )
        )

        if not pos_results:

            print("  NONE")

        for pos_result in pos_results:

            print(
                f"  {pos_result.get('node', 'UNKNOWN')}: "
                f"{pos_result.get('status', 'UNKNOWN')}"
            )

            print(
                "    Current: "
                f"{pos_result.get('current_file', 'NOT FOUND')}"
            )

            print(
                "    Output: "
                f"{pos_result.get('file', 'NOT GENERATED')}"
            )

            for change in (
                pos_result.get(
                    "changes",
                    []
                )
            ):
                print(
                    f"    - {change}"
                )

        warnings = (
            xmlrpccli_result.get(
                "warnings",
                []
            )
        )

        if warnings:

            print()
            print("Warnings")

            for warning in warnings:

                print(
                    f"  - {warning}"
                )

        errors = (
            xmlrpccli_result.get(
                "errors",
                []
            )
        )

        if errors:

            print()
            print("Errors")

            for error in errors:

                print(
                    f"  - {error}"
                )

    #
    # FOE GENERATION
    #

    print()
    print("FOE GENERATION")
    print("-" * 50)

    if not generated_foe:

        print("No FOE files found.")

    for result in generated_foe:

        print()
        print(
            result.get(
                "file",
                "UNKNOWN FILE"
            )
        )

        if result.get(
            "generated",
            False
        ):

            print(
                "  Status: GENERATED"
            )

            print(
                "  Output: "
                f"{result.get('output_file', 'NOT FOUND')}"
            )

        else:

            print(
                "  Status: NOT GENERATED"
            )

        changes = (
            result.get(
                "changes",
                []
            )
        )

        if changes:

            print(
                "  Changes:"
            )

            for change in changes:

                print(
                    f"    - {change}"
                )

        for warning in (
            result.get(
                "warnings",
                []
            )
        ):

            print(
                f"  WARNING: {warning}"
            )

        for error in (
            result.get(
                "errors",
                []
            )
        ):

            print(
                f"  ERROR: {error}"
            )

    #
    # COD GENERATION
    #

    print()
    print("COD GENERATION")
    print("-" * 50)

    if generated_cod.get(
        "generated",
        False
    ):

        print(
            "Node: "
            f"{generated_cod.get('node', 'NOT FOUND')}"
        )

        print(
            "File: "
            f"{generated_cod.get('file', 'NOT FOUND')}"
        )

        print(
            "Status: GENERATED"
        )

    else:

        print(
            "Status: NOT GENERATED"
        )

        if generated_cod.get(
            "node"
        ):

            print(
                "Node: "
                f"{generated_cod['node']}"
            )

        if generated_cod.get(
            "file"
        ):

            print(
                "File: "
                f"{generated_cod['file']}"
            )

    changes = (
        generated_cod.get(
            "changes",
            []
        )
    )

    if changes:

        print("Changes:")

        for change in changes:

            print(
                f"  - {change}"
            )

    for warning in (
        generated_cod.get(
            "warnings",
            []
        )
    ):

        print(
            f"WARNING: {warning}"
        )

    for error in (
        generated_cod.get(
            "errors",
            []
        )
    ):

        print(
            f"ERROR: {error}"
        )

    #
    # STORE COD GENERATION
    #

    print()
    print("STORE COD GENERATION")
    print("-" * 50)

    if generated_store_cod.get(
        "generated",
        False
    ):

        print(
            "File: "
            f"{generated_store_cod.get('file', 'NOT FOUND')}"
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
                "File: "
                f"{generated_store_cod['file']}"
            )

    changes = (
        generated_store_cod.get(
            "changes",
            []
        )
    )

    if changes:

        print("Changes:")

        for change in changes:

            print(
                f"  - {change}"
            )

    for warning in (
        generated_store_cod.get(
            "warnings",
            []
        )
    ):

        print(
            f"WARNING: {warning}"
        )

    for error in (
        generated_store_cod.get(
            "errors",
            []
        )
    ):

        print(
            f"ERROR: {error}"
        )

def print_validation_report(
    runtime: RuntimeContext,
) -> None:

    results = (
        runtime.pos_role_validation
    )

    print()
    print("POS ROLE VALIDATION")
    print("-" * 50)

    if not results:

        print(
            "No validation results found."
        )

        return

    for result in results:

        print()

        print(
            result["file"]
        )

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

        print(
            "  Status: "
            + (
                "VALID"
                if result["valid"]
                else "INVALID"
            )
        )

        for warning in (
            result.get(
                "warnings",
                []
            )
        ):

            print(
                f"  WARNING: {warning}"
            )

        for error in (
            result.get(
                "errors",
                []
            )
        ):

            print(
                f"  ERROR: {error}"
            )

