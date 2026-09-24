from src.builder.builder_context import BuilderContext
from src.builder.builder_inputs import validate_builder_inputs
from src.builder.builder_discovery_phase import (
    run_builder_discovery_phase,
)
from src.builder.builder_reporting import (
    print_builder_discovery_report,
)
from src.builder.assignment_proposal_engine import (
    build_assignment_proposal,
)


def print_assignment_proposal(proposal):
    print()
    print("ASSIGNMENT PROPOSAL")
    print("=" * 50)
    print(f"Status: {proposal['status']}")

    print()
    print("POS ASSIGNMENTS")
    print("-" * 50)

    for assignment in proposal["pos"].get("assignments", []):
        print(
            f"{assignment['target_node']} "
            f"[{assignment['target_role']}]"
        )
        print(
            "  Source: "
            f"{assignment['source_file'] or 'NONE'}"
        )
        print(f"  Status: {assignment['status']}")
        print()

    extra_pos = proposal["pos"].get("extra_candidates", [])
    if extra_pos:
        print("EXTRA POS CANDIDATES")
        print("-" * 50)
        for candidate in extra_pos:
            print(
                f"{candidate.get('file')} "
                f"[{candidate.get('role')}]"
            )
            print(f"  Decision: {candidate.get('decision')}")
            print()

    print("ITONA ASSIGNMENTS")
    print("-" * 50)

    for assignment in proposal["itonas"].get("assignments", []):
        print(assignment["slot"])
        print(
            "  Source: "
            f"{assignment['source_file'] or 'NONE'}"
        )
        print(
            "  Types: "
            + (
                ", ".join(assignment.get("source_types", []))
                or "NONE"
            )
        )
        print(f"  Status: {assignment['status']}")
        print()

    extra_itonas = proposal["itonas"].get("extra_candidates", [])
    if extra_itonas:
        print("UNASSIGNED ITONA CANDIDATES")
        print("-" * 50)
        for candidate in extra_itonas:
            print(candidate.get("file"))
            print(
                "  Types: "
                + (", ".join(candidate.get("types", [])) or "UNKNOWN")
            )
            print(f"  Status: {candidate.get('status')}")
            print()


def configure_builder(
    selected_lab,
    template_market,
    source_posdata_folder,
    template_root="templates",
):
    inputs = validate_builder_inputs(
        selected_lab=selected_lab,
        template_market=template_market,
        source_posdata_folder=source_posdata_folder,
        template_root=template_root,
    )

    context = BuilderContext(
        selected_lab=inputs["lab"],
        config_path=inputs["config_path"],
        template_market=inputs["template_market"],
        template_folder=inputs["template_folder"],
        source_posdata_folder=inputs["source_folder"],
        store_db_path=inputs["store_db_path"],
        screen_xml_path=inputs["screen_xml_path"],
        template_validation=inputs["template_validation"],
    )

    print("POSDATA BUILDER SETUP")
    print("-" * 50)
    print(f"Selected lab: {context.selected_lab}")
    print(f"Template market: {context.template_market}")
    print(f"Template folder: {context.template_folder}")
    print(f"Source PosData: {context.source_posdata_folder}")

    context = run_builder_discovery_phase(context)
    print(f"Status: {context.source_validation.get('status')}")

    print_builder_discovery_report(context)

    proposal = build_assignment_proposal(context)
    print_assignment_proposal(proposal)

    return context


if __name__ == "__main__":
    configure_builder(
        selected_lab="BR",
        template_market="CA",
        source_posdata_folder="samples/new_posdata",
    )
