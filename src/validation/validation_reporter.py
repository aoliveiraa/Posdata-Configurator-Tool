from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from src.validation.validation_result import ValidationResult


PASS = "PASS"
FAIL = "FAIL"
SKIPPED = "SKIPPED"


@dataclass
class ValidationGroup:
    component: str
    rule_id: str
    target_name: str
    results: list[ValidationResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(result.status == PASS for result in self.results)

    @property
    def failed(self) -> int:
        return sum(result.status == FAIL for result in self.results)

    @property
    def skipped(self) -> int:
        return sum(result.status == SKIPPED for result in self.results)

    @property
    def status(self) -> str:
        if self.failed:
            return FAIL
        if self.passed:
            return PASS
        return SKIPPED


class ValidationReporter:
    """Builds a concise report grouped by component and validation rule."""

    def build_report(
        self,
        results: Iterable[ValidationResult],
    ) -> str:
        result_list = list(results)
        summary = self._build_summary(result_list)
        groups = self._group_results(result_list)

        lines = [
            "VALIDATION REPORT",
            "=" * 80,
            "",
            "EXECUTIVE SUMMARY",
            "-" * 80,
            f"Checks Executed : {summary['total']}",
            f"Passed          : {summary['passed']}",
            f"Failed          : {summary['failed']}",
            f"Skipped         : {summary['skipped']}",
            f"Overall Status  : {summary['status']}",
            "",
            "VALIDATION BY RULE",
            "=" * 80,
        ]

        for group in groups:
            lines.extend(self._render_group(group))

        failures = [result for result in result_list if result.status == FAIL]

        if failures:
            lines.extend([
                "",
                "FAILURE DETAILS",
                "=" * 80,
            ])
            for failure in failures:
                lines.append(f"[FAIL] {failure.message}")
                for detail in failure.details:
                    lines.append(f"    {detail}")
                lines.append("")

        lines.extend([
            "",
            "END OF REPORT",
            "=" * 80,
        ])

        return "\n".join(lines).rstrip() + "\n"

    def write_report(
        self,
        results: Iterable[ValidationResult],
        report_path: str | Path,
    ) -> Path:
        path = Path(report_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.build_report(results), encoding="utf-8")
        return path

    def _group_results(
        self,
        results: list[ValidationResult],
    ) -> list[ValidationGroup]:
        grouped: dict[tuple[str, str, str], ValidationGroup] = {}

        for result in results:
            rule_id = self._extract_detail(result.details, "Rule:")
            target_name = self._extract_target_name(result, rule_id)
            component = str(result.component or "UNKNOWN").upper()

            if not rule_id:
                rule_id = self._legacy_rule_id(component, target_name)

            key = (component, rule_id, target_name)

            if key not in grouped:
                grouped[key] = ValidationGroup(
                    component=component,
                    rule_id=rule_id,
                    target_name=target_name,
                )

            grouped[key].results.append(result)

        return sorted(
            grouped.values(),
            key=lambda group: (
                self._component_order(group.component),
                group.target_name.casefold(),
                group.rule_id.casefold(),
            ),
        )

    def _render_group(self, group: ValidationGroup) -> list[str]:
        files = self._extract_files(group.results)
        lines = [
            "",
            f"{group.component} | {group.target_name}",
            "-" * 80,
            f"Status        : {group.status}",
            f"Checks        : {len(group.results)}",
            f"Passed        : {group.passed}",
            f"Failed        : {group.failed}",
            f"Skipped       : {group.skipped}",
        ]

        if group.rule_id:
            lines.append(f"Rule          : {group.rule_id}")

        if files:
            lines.append(f"Files         : {len(files)}")

        if group.failed:
            failed_files = self._extract_files(
                result for result in group.results if result.status == FAIL
            )
            if failed_files:
                lines.append("Failed Files  :")
                lines.extend(f"  - {file_name}" for file_name in failed_files)

        elif group.status == SKIPPED:
            lines.append(
                "Result        : Setting not configured in applicable files; "
                "no failure generated."
            )

        else:
            lines.append("Result        : All applicable checks are compliant.")

        return lines

    @staticmethod
    def _build_summary(results: list[ValidationResult]) -> dict[str, int | str]:
        passed = sum(result.status == PASS for result in results)
        failed = sum(result.status == FAIL for result in results)
        skipped = sum(result.status == SKIPPED for result in results)
        return {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "status": FAIL if failed else PASS,
        }

    @staticmethod
    def _extract_detail(details: Iterable[str], prefix: str) -> str:
        for detail in details or []:
            if str(detail).startswith(prefix):
                return str(detail)[len(prefix):].strip()
        return ""

    def _extract_target_name(
        self,
        result: ValidationResult,
        rule_id: str,
    ) -> str:
        if rule_id:
            known_targets = (
                "CashDrawer",
                "Printer",
                "BumpBar",
                "Scale",
                "LocalWebView",
                "COD",
                "FOE",
                "RPS",
            )
            normalized_rule = rule_id.casefold()
            for target in known_targets:
                if target.casefold() in normalized_rule:
                    return target

        message = str(result.message)

        if " contains WebView" in message:
            return "WebView Presence"
        if message.endswith(" valid") or "invalid XML" in message:
            return "XML Well-Formedness"

        if ":" in message:
            after_file = message.split(":", 1)[1].strip()
            return after_file.split(" ", 1)[0].strip() or "General"

        return "General"

    @staticmethod
    def _legacy_rule_id(component: str, target_name: str) -> str:
        normalized_target = "-".join(target_name.upper().split())
        return f"{component}-{normalized_target}"

    def _extract_files(
        self,
        results: Iterable[ValidationResult],
    ) -> list[str]:
        files: set[str] = set()

        for result in results:
            message = str(result.message).strip()
            candidate = message.split(":", 1)[0].strip()

            if candidate.endswith(".xml"):
                files.add(candidate.replace("\\", "/"))
                continue

            first_token = message.split(" ", 1)[0].strip()
            if first_token.endswith(".xml"):
                files.add(first_token.replace("\\", "/"))

        return sorted(files, key=str.casefold)

    @staticmethod
    def _component_order(component: str) -> int:
        order = {
            "XML": 0,
            "WEBVIEW": 1,
            "PERFORMANCE": 2,
        }
        return order.get(component, 99)
