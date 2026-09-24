from src.builder.builder_context import (
    BuilderContext,
)

from src.builder.builder_inputs import (
    validate_builder_inputs,
)

from src.builder.builder_discovery_phase import (
    run_builder_discovery_phase,
)

from src.builder.assignment_proposal_engine import (
    build_assignment_proposal,
)

from src.builder.builder_generation_phase import (
    run_builder_generation_phase,
)

#
# Same Setup used by the UI
#
inputs = validate_builder_inputs(
    selected_lab="BR",
    template_market="CA",
    source_posdata_folder="samples/new_posdata",
    template_root="templates",
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

#
# Discovery
#
context = run_builder_discovery_phase(
    context
)

#
# Automatic proposal
#
proposal = build_assignment_proposal(
    context
)

#
# Temporary shortcut:
# use the proposal as if it had been confirmed.
#
context.confirmed_pos_mapping = (
    proposal["pos"]
)

context.confirmed_itona_mapping = (
    proposal["itonas"]
)

#
# Generation
#
runtime = run_builder_generation_phase(
    context
)


print()
print("POS RESULTS")
print("=" * 50)

for item in runtime.generated_pos:

    print(
        item.get("node_name"),
        item.get("generated")
    )

print()
print("ITONA RESULTS")
print("=" * 50)

for item in runtime.generated_itonas:

    print(
        item.get("machine"),
        item.get("generated")
    )

print()
print("ITONA DETAILS")
print("=" * 50)

for item in runtime.generated_itonas:

    print()

    print(
        "Machine:",
        item.get("machine")
    )

    print(
        "Generated:",
        item.get("generated")
    )

    print(
        "Output:",
        item.get(
            "output_file"
        )
    )

    print(
        "Warnings:",
        item.get(
            "warnings",
            []
        )
    )

    print(
        "Errors:",
        item.get(
            "errors",
            []
        )
    )

print()
print("KVS MAPPING")
print("=" * 50)

for mapping in runtime.kvs_mapping["mappings"]:

    print(mapping["machine"])

    for service in mapping["mapped_services"]:

        print(
            service
        )

print()
print("VALIDATION SUMMARY")
print(runtime.validation_summary)
