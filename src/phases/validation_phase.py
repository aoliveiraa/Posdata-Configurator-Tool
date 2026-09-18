from pathlib import Path

from src.runtime_context import RuntimeContext
from src.validation.validation_manager import ValidationManager
from src.validation.validation_reporter import ValidationReporter
from src.validation.validation_rules_engine import ValidationRulesEngine


def run_validation_phase(
    runtime: RuntimeContext,
) -> RuntimeContext:
    """Run output validation and generate the aggregated validation report."""

    print()
    print("VALIDATION PHASE")
    print("=" * 50)

    output_folder = Path("output")
    manager = ValidationManager()
    reporter = ValidationReporter()

    results = manager.validate_output(
        str(output_folder)
    )

    summary = ValidationRulesEngine.summarize(
        results
    )

    runtime.validation_results = results
    runtime.validation_summary = summary

    validation_folder = output_folder / "validation"
    validation_report = validation_folder / "validation_report.txt"

    runtime.validation_report = reporter.write_report(
        results=results,
        report_path=validation_report,
    )

    print(f"Checks Executed : {summary['total']}")
    print(f"Passed          : {summary['passed']}")
    print(f"Failed          : {summary['failed']}")
    print(f"Skipped         : {summary['skipped']}")
    print(f"Status          : {summary['status']}")
    print(f"Report          : {runtime.validation_report}")

    return runtime
