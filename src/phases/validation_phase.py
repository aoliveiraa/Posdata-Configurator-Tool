from src.runtime_context import (
    RuntimeContext
)

from src.validators.pos_role_validator import (
    validate_generated_pos_roles
)


def run_validation_phase(
    runtime: RuntimeContext,
) -> RuntimeContext:

    runtime.pos_role_validation = (
        validate_generated_pos_roles(
            output_folder="output/pos",
            pos_machine_lookup=
                runtime.runtime_pos_machine_lookup,
            config_path=
                runtime.config_path
        )
    )

    return runtime