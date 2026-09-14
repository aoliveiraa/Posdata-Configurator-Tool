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