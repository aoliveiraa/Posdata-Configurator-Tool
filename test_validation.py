from src.validation.validation_manager import ValidationManager


manager = ValidationManager()

results = manager.validate_output(
    "output"
)

for result in results:

    print(
        f"[{result.status}] "
        f"{result.component} - "
        f"{result.message}"
    )

    if result.details:

        for detail in result.details:

            print(
                f"    {detail}"
            )