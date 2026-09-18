from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import Callable, Iterable
from xml.etree import ElementTree as ET

from src.validation.validation_result import ValidationResult


PASS = "PASS"
FAIL = "FAIL"
SKIPPED = "SKIPPED"
UNKNOWN = "UNKNOWN"
ENABLED = "ENABLED"
DISABLED = "DISABLED"
PRESENT = "PRESENT"
MISSING = "MISSING"


@dataclass(frozen=True)
class XmlSelector:
    """Selects XML elements using normalized exact matches."""

    tags: tuple[str, ...] = ()
    names: tuple[str, ...] = ()
    types: tuple[str, ...] = ()
    imports: tuple[str, ...] = ()
    ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class Applicability:
    """Defines where a rule applies."""

    folders: tuple[str, ...]
    file_patterns: tuple[str, ...] = ("*.xml",)
    require_any_selector: tuple[XmlSelector, ...] = ()


@dataclass(frozen=True)
class ValidationRule:
    rule_id: str
    component: str
    target_name: str
    expected_state: str
    selector: XmlSelector
    applicability: Applicability
    missing_status: str = FAIL
    description: str = ""


@dataclass
class RuleContext:
    output_folder: Path
    relative_path: Path
    xml_file: Path
    root: ET.Element


@dataclass
class RuleEvaluation:
    rule: ValidationRule
    context: RuleContext
    status: str
    actual_state: str
    message: str
    details: list[str] = field(default_factory=list)

    def to_validation_result(self) -> ValidationResult:
        return ValidationResult(
            component=self.rule.component,
            status=self.status,
            message=self.message,
            details=self.details,
        )


class ValidationRulesEngine:
    """Executes declarative validation rules against generated XML files."""

    ENABLED_VALUES = {
        "1", "active", "enabled", "on", "true", "yes",
    }
    DISABLED_VALUES = {
        "0", "disabled", "false", "inactive", "no", "off",
    }
    STATE_ATTRIBUTES = (
        "value", "enabled", "available", "active",
        "startOnLoad", "startonload",
    )

    def __init__(self, rules: Iterable[ValidationRule]):
        self.rules = tuple(rules)

    def validate(
        self,
        output_folder: str | Path,
    ) -> list[ValidationResult]:
        output_path = Path(output_folder)

        if not output_path.is_dir():
            return [
                ValidationResult(
                    component="VALIDATION_RULES",
                    status=FAIL,
                    message=f"Output folder not found: {output_path}",
                )
            ]

        results: list[ValidationResult] = []
        parse_cache: dict[Path, ET.Element | Exception] = {}

        for rule in self.rules:
            candidates = self._collect_candidate_files(
                output_path,
                rule.applicability,
            )

            if not candidates:
                results.append(
                    ValidationResult(
                        component=rule.component,
                        status=SKIPPED,
                        message=(
                            f"{rule.target_name}: no applicable XML files "
                            f"were found in {', '.join(rule.applicability.folders)}"
                        ),
                        details=[f"Rule: {rule.rule_id}"],
                    )
                )
                continue

            applicable_count = 0

            for xml_file in candidates:
                parsed = self._parse_cached(xml_file, parse_cache)

                if isinstance(parsed, Exception):
                    results.append(
                        ValidationResult(
                            component=rule.component,
                            status=FAIL,
                            message=f"{xml_file.name}: invalid XML",
                            details=[
                                f"Rule: {rule.rule_id}",
                                f"{type(parsed).__name__}: {parsed}",
                            ],
                        )
                    )
                    continue

                context = RuleContext(
                    output_folder=output_path,
                    relative_path=xml_file.relative_to(output_path),
                    xml_file=xml_file,
                    root=parsed,
                )

                if not self._is_applicable(context, rule.applicability):
                    continue

                applicable_count += 1
                evaluation = self._evaluate_rule(context, rule)
                results.append(evaluation.to_validation_result())

            if applicable_count == 0:
                results.append(
                    ValidationResult(
                        component=rule.component,
                        status=SKIPPED,
                        message=(
                            f"{rule.target_name}: rule not applicable to "
                            "the generated files"
                        ),
                        details=[f"Rule: {rule.rule_id}"],
                    )
                )

        return results

    @staticmethod
    def _parse_cached(
        xml_file: Path,
        parse_cache: dict[Path, ET.Element | Exception],
    ) -> ET.Element | Exception:
        """
        Faz o parse do XML uma única vez.

        Armazena no cache a raiz XML ou a exceção encontrada,
        evitando processar repetidamente o mesmo arquivo.
        """

        if xml_file in parse_cache:
            return parse_cache[xml_file]

        try:
            parsed_result = ET.parse(
                xml_file
            ).getroot()

        except (ET.ParseError, OSError) as error:
            parsed_result = error

        parse_cache[xml_file] = parsed_result

        return parsed_result


    def _evaluate_rule(
        self,
        context: RuleContext,
        rule: ValidationRule,
    ) -> RuleEvaluation:
        matches = list(self._find_matches(context.root, rule.selector))

        if not matches:
            status = rule.missing_status
            message = self._missing_message(context, rule, status)
            return RuleEvaluation(
                rule=rule,
                context=context,
                status=status,
                actual_state=MISSING,
                message=message,
                details=[f"Rule: {rule.rule_id}"],
            )

        states = [self._element_state(element) for element in matches]
        actual_state = self._aggregate_state(states)
        status = self._compare_state(rule.expected_state, actual_state)

        details = [
            f"Rule: {rule.rule_id}",
            f"Expected: {rule.expected_state}",
            f"Actual: {actual_state}",
        ]
        details.extend(
            self._describe_element(element, state)
            for element, state in zip(matches, states)
        )

        return RuleEvaluation(
            rule=rule,
            context=context,
            status=status,
            actual_state=actual_state,
            message=(
                f"{context.relative_path.as_posix()}: {rule.target_name} "
                f"expected {rule.expected_state}, actual {actual_state}"
            ),
            details=details,
        )

    def _is_applicable(
        self,
        context: RuleContext,
        applicability: Applicability,
    ) -> bool:
        if not applicability.require_any_selector:
            return True

        return any(
            next(self._find_matches(context.root, selector), None) is not None
            for selector in applicability.require_any_selector
        )

    def _collect_candidate_files(
        self,
        output_path: Path,
        applicability: Applicability,
    ) -> list[Path]:
        found: dict[str, Path] = {}

        for folder_name in applicability.folders:
            folder = output_path / folder_name
            if not folder.is_dir():
                continue

            for xml_file in folder.rglob("*.xml"):
                if not any(
                    fnmatch(xml_file.name.casefold(), pattern.casefold())
                    for pattern in applicability.file_patterns
                ):
                    continue
                found[str(xml_file.resolve()).casefold()] = xml_file

        return sorted(found.values(), key=lambda path: str(path).casefold())

    def _find_matches(
        self,
        root: ET.Element,
        selector: XmlSelector,
    ) -> Iterable[ET.Element]:
        expected = {
            "tag": self._normalized_set(selector.tags),
            "name": self._normalized_set(selector.names),
            "type": self._normalized_set(selector.types),
            "imports": self._normalized_set(selector.imports),
            "id": self._normalized_set(selector.ids),
        }

        for element in root.iter():
            values = {
                "tag": self._normalize(self._local_name(element.tag)),
                "name": self._normalize(element.attrib.get("name", "")),
                "type": self._normalize(element.attrib.get("type", "")),
                "imports": self._normalize(element.attrib.get("imports", "")),
                "id": self._normalize(element.attrib.get("id", "")),
            }

            if self._selector_matches(expected, values):
                yield element

    @staticmethod
    def _selector_matches(
        expected: dict[str, set[str]],
        actual: dict[str, str],
    ) -> bool:
        constrained = False

        for field_name, expected_values in expected.items():
            if not expected_values:
                continue
            constrained = True
            if actual[field_name] not in expected_values:
                return False

        return constrained

    def _element_state(self, element: ET.Element) -> str:
        for attribute in self.STATE_ATTRIBUTES:
            state = self._value_state(element.attrib.get(attribute))
            if state != UNKNOWN:
                return state

        text_state = self._value_state(element.text)
        if text_state != UNKNOWN:
            return text_state

        return PRESENT

    def _value_state(self, value: object) -> str:
        normalized = str(value).strip().casefold() if value is not None else ""
        if normalized in self.ENABLED_VALUES:
            return ENABLED
        if normalized in self.DISABLED_VALUES:
            return DISABLED
        return UNKNOWN

    @staticmethod
    def _aggregate_state(states: list[str]) -> str:
        if ENABLED in states:
            return ENABLED
        if DISABLED in states:
            return DISABLED
        if PRESENT in states:
            return PRESENT
        return UNKNOWN

    @staticmethod
    def _compare_state(expected: str, actual: str) -> str:
        expected = expected.upper()
        actual = actual.upper()

        if expected == PRESENT:
            return PASS if actual in {PRESENT, ENABLED, DISABLED} else FAIL
        if expected == ENABLED:
            return PASS if actual in {ENABLED, PRESENT} else FAIL
        if expected == DISABLED:
            return PASS if actual == DISABLED else FAIL
        if expected == MISSING:
            return PASS if actual == MISSING else FAIL
        return FAIL

    @staticmethod
    def _missing_message(
        context: RuleContext,
        rule: ValidationRule,
        status: str,
    ) -> str:
        return (
            f"{context.relative_path.as_posix()}: {rule.target_name} is missing; "
            f"expected {rule.expected_state} ({status})"
        )

    @staticmethod
    def _describe_element(element: ET.Element, state: str) -> str:
        attributes = ", ".join(
            f"{key}={value!r}"
            for key, value in sorted(element.attrib.items())
        )
        text = (element.text or "").strip()
        parts = [f"tag={ValidationRulesEngine._local_name(element.tag)!r}"]
        if attributes:
            parts.append(attributes)
        if text:
            parts.append(f"text={text!r}")
        parts.append(f"detected_state={state}")
        return ", ".join(parts)

    @classmethod
    def summarize(
        cls,
        results: Iterable[ValidationResult],
    ) -> dict[str, int | str]:
        results = list(results)
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
    def _normalized_set(values: Iterable[str]) -> set[str]:
        return {
            ValidationRulesEngine._normalize(value)
            for value in values
            if value
        }

    @staticmethod
    def _normalize(value: object) -> str:
        return "".join(
            character
            for character in str(value).casefold()
            if character.isalnum()
        )

    @staticmethod
    def _local_name(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]
