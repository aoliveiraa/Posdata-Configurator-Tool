from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET


@dataclass
class OperationModeTransformResult:
    modified: bool
    configuration_found: bool
    section_created: bool = False
    parameters_created: list[str] = field(default_factory=list)
    parameters_updated: list[str] = field(default_factory=list)
    duplicates_removed: list[str] = field(default_factory=list)


class StoreDbOperationModeTransformer:
    """Enforces Performance AutoLogin settings in store-db.xml.

    Target structure:

    <Configuration type="POS">
        <Section name="OperationMode">
            <Parameter name="AnonymousOperatorName" value="AutoLogin" />
            <Parameter name="AnonymousOperatorID" value="99999" />
            <Parameter name="AutomaticOperatorLogin" value="true" />
        </Section>
    </Configuration>
    """

    REQUIRED_PARAMETERS = (
        ("AnonymousOperatorName", "AutoLogin"),
        ("AnonymousOperatorID", "99999"),
        ("AutomaticOperatorLogin", "true"),
    )

    def transform_file(
        self,
        source_file: str | Path,
        output_file: str | Path | None = None,
    ) -> OperationModeTransformResult:
        source_path = Path(source_file)

        if not source_path.is_file():
            raise FileNotFoundError(
                f"store-db.xml not found: {source_path}"
            )

        try:
            tree = ET.parse(source_path)
        except ET.ParseError as error:
            raise ValueError(
                f"Invalid store-db XML: {source_path}: {error}"
            ) from error

        result = self.apply(tree.getroot())

        destination = (
            Path(output_file)
            if output_file is not None
            else source_path
        )
        destination.parent.mkdir(parents=True, exist_ok=True)

        if result.modified or destination != source_path:
            self._indent(tree)
            tree.write(
                destination,
                encoding="utf-8",
                xml_declaration=True,
                short_empty_elements=True,
            )

        return result

    def apply(
        self,
        root: ET.Element,
    ) -> OperationModeTransformResult:
        pos_configuration = self._find_pos_configuration(root)

        if pos_configuration is None:
            raise ValueError(
                'Configuration type="POS" was not found in store-db.xml'
            )

        result = OperationModeTransformResult(
            modified=False,
            configuration_found=True,
        )

        operation_mode = self._find_direct_section(
            pos_configuration,
            "OperationMode",
        )

        if operation_mode is None:
            operation_mode = ET.Element(
                "Section",
                {"name": "OperationMode"},
            )
            self._insert_section(
                pos_configuration,
                operation_mode,
            )
            result.modified = True
            result.section_created = True

        self._enforce_parameters(
            operation_mode,
            result,
        )

        return result

    def _enforce_parameters(
        self,
        operation_mode: ET.Element,
        result: OperationModeTransformResult,
    ) -> None:
        for parameter_name, expected_value in self.REQUIRED_PARAMETERS:
            matches = [
                child
                for child in list(operation_mode)
                if self._local_name(child.tag) == "Parameter"
                and child.get("name") == parameter_name
            ]

            if not matches:
                ET.SubElement(
                    operation_mode,
                    "Parameter",
                    {
                        "name": parameter_name,
                        "value": expected_value,
                    },
                )
                result.parameters_created.append(parameter_name)
                result.modified = True
                continue

            primary = matches[0]

            if primary.get("value") != expected_value:
                primary.set("value", expected_value)
                result.parameters_updated.append(parameter_name)
                result.modified = True

            for duplicate in matches[1:]:
                operation_mode.remove(duplicate)
                result.duplicates_removed.append(parameter_name)
                result.modified = True

        self._order_required_parameters(operation_mode)

    def _order_required_parameters(
        self,
        operation_mode: ET.Element,
    ) -> None:
        children = list(operation_mode)
        required_names = {
            name
            for name, _ in self.REQUIRED_PARAMETERS
        }

        required_by_name = {
            child.get("name"): child
            for child in children
            if self._local_name(child.tag) == "Parameter"
            and child.get("name") in required_names
        }

        other_children = [
            child
            for child in children
            if not (
                self._local_name(child.tag) == "Parameter"
                and child.get("name") in required_names
            )
        ]

        ordered_required = [
            required_by_name[name]
            for name, _ in self.REQUIRED_PARAMETERS
            if name in required_by_name
        ]

        desired_order = ordered_required + other_children

        if children == desired_order:
            return

        for child in children:
            operation_mode.remove(child)

        for child in desired_order:
            operation_mode.append(child)

    @classmethod
    def _find_pos_configuration(
        cls,
        root: ET.Element,
    ) -> ET.Element | None:
        for element in root.iter():
            if cls._local_name(element.tag) != "Configuration":
                continue

            if element.get("type") == "POS":
                return element

        return None

    @classmethod
    def _find_direct_section(
        cls,
        configuration: ET.Element,
        section_name: str,
    ) -> ET.Element | None:
        for child in list(configuration):
            if cls._local_name(child.tag) != "Section":
                continue

            if child.get("name") == section_name:
                return child

        return None

    @staticmethod
    def _insert_section(
        configuration: ET.Element,
        section: ET.Element,
    ) -> None:
        children = list(configuration)
        insert_index = len(children)

        for index, child in enumerate(children):
            if StoreDbOperationModeTransformer._local_name(
                child.tag
            ) != "Section":
                insert_index = index
                break

        configuration.insert(insert_index, section)

    @staticmethod
    def _local_name(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]

    @staticmethod
    def _indent(tree: ET.ElementTree) -> None:
        if hasattr(ET, "indent"):
            ET.indent(tree, space="    ")
