from pathlib import Path

from src.validation.performance_rules import PERFORMANCE_RULES
from src.validation.validation_result import ValidationResult
from src.validation.validation_rules_engine import ValidationRulesEngine


class PerformanceValidator:
    """Runs the performance profile through the Validation Rules Engine."""

    def __init__(self) -> None:
        self.engine = ValidationRulesEngine(PERFORMANCE_RULES)

    def validate_output(
        self,
        output_folder: str | Path,
    ) -> list[ValidationResult]:
        return self.engine.validate(output_folder)
