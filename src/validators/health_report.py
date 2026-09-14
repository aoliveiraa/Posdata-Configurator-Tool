from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import json


@dataclass
class HealthResult:
    """
    Resultado individual de uma validação.
    """

    name: str
    passed: bool
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def status(self) -> str:
        return "PASS" if self.passed else "FAIL"


def generate_health_report(
    results: list[HealthResult],
) -> dict[str, Any]:
    """
    Consolida todos os resultados de validação.
    """

    total_warnings = sum(
        len(result.warnings)
        for result in results
    )

    total_errors = sum(
        len(result.errors)
        for result in results
    )

    overall_status = (
        "PASS"
        if all(result.passed for result in results)
        else "FAIL"
    )

    return {
        "overall_status": overall_status,
        "warnings": total_warnings,
        "errors": total_errors,
        "validations": [
            {
                "name": result.name,
                "status": result.status,
                "warnings": result.warnings,
                "errors": result.errors,
                "details": result.details,
            }
            for result in results
        ],
    }


def save_health_report_json(
    report: dict[str, Any],
    output_file: str | Path,
) -> None:

    output_path = Path(output_file)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            indent=4,
            ensure_ascii=False,
        )


def save_health_report_txt(
    report: dict[str, Any],
    output_file: str | Path,
) -> None:

    output_path = Path(output_file)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    lines = []

    lines.append(
        "CONFIGURATION HEALTH REPORT"
    )

    lines.append("=" * 50)

    lines.append(
        f"OVERALL STATUS: "
        f"{report['overall_status']}"
    )

    lines.append(
        f"WARNINGS: "
        f"{report['warnings']}"
    )

    lines.append(
        f"ERRORS: "
        f"{report['errors']}"
    )

    lines.append("")

    for validation in report[
        "validations"
    ]:

        lines.append(
            f"{validation['name']}: "
            f"{validation['status']}"
        )

        for warning in validation[
            "warnings"
        ]:
            lines.append(
                f"  WARNING: {warning}"
            )

        for error in validation[
            "errors"
        ]:
            lines.append(
                f"  ERROR: {error}"
            )

        lines.append("")

    output_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )