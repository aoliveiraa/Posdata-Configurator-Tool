from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET


@dataclass
class CashDrawerTransformResult:
    modified: bool
    adaptors_found: int = 0
    adaptors_modified: list[str] = field(
        default_factory=list
    )
    startonload_updated: list[str] = field(
        default_factory=list
    )
    parameters_created: list[str] = field(
        default_factory=list
    )
    parameters_updated: list[str] = field(
        default_factory=list
    )
    warnings: list[str] = field(
        default_factory=list
    )


class CashDrawerTransformer:
    """
    Disables Cash Drawer adaptors in store-db.xml.

    For each supported Cash Drawer adaptor:

    1. Sets startonload="false".
    2. Sets drawertype="-1" under Section name="main".
    3. Creates Section/main or drawertype when missing.
    4. Removes duplicate drawertype parameters.

    This transformation is idempotent.
    """

    DISABLED_DRAWER_TYPE = "-1"

    CASH_DRAWER_ADAPTOR_TYPES = {
        "DSLDevDrv.cash",
        "native.cash.drawer",
        "opos.cashdrawer",
        "panasonic.cash.drawer",
        "par.cash.drawer",
        "virtual.cashdrawer",
    }

    def transform_file(
        self,
        source_file: str | Path,
        output_file: str | Path | None = None,
    ) -> CashDrawerTransformResult:
        source_path = Path(source_file)

        if not source_path.is_file():
            raise FileNotFoundError(
                f"store-db.xml not found: {source_path}"
            )

        try:
            tree = ET.parse(source_path)
        except ET.ParseError as error:
            raise ValueError(
                f"Invalid store-db XML: "
                f"{source_path}: {error}"
            ) from error

        result = self.apply(tree.getroot())

        destination = (
            Path(output_file)
            if output_file is not None
            else source_path
        )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

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
    ) -> CashDrawerTransformResult:
        result = CashDrawerTransformResult(
            modified=False
        )

        cash_drawer_adaptors = (
            self._find_cash_drawer_adaptors(root)
        )

        result.adaptors_found = len(
            cash_drawer_adaptors
        )

        if not cash_drawer_adaptors:
            result.warnings.append(
                "No supported Cash Drawer adaptor "
                "was found in store-db.xml."
            )
            return result

        for adaptor in cash_drawer_adaptors:
            adaptor_type = (
                adaptor.get("type")
                or "<unknown>"
            )

            adaptor_modified = False

            if adaptor.get("startonload") != "false":
                adaptor.set(
                    "startonload",
                    "false",
                )

                result.startonload_updated.append(
                    adaptor_type
                )

                adaptor_modified = True

            main_section = self._find_direct_section(
                adaptor,
                "main",
            )

            if main_section is None:
                main_section = ET.Element(
                    "Section",
                    {"name": "main"},
                )

                self._insert_section(
                    adaptor,
                    main_section,
                )

                result.parameters_created.append(
                    f"{adaptor_type}:Section/main"
                )

                adaptor_modified = True

            drawertype_matches = (
                self._find_direct_parameters(
                    main_section,
                    "drawertype",
                )
            )

            if not drawertype_matches:
                ET.SubElement(
                    main_section,
                    "Parameter",
                    {
                        "name": "drawertype",
                        "value": (
                            self.DISABLED_DRAWER_TYPE
                        ),
                    },
                )

                result.parameters_created.append(
                    f"{adaptor_type}:drawertype"
                )

                adaptor_modified = True

            else:
                primary_parameter = (
                    drawertype_matches[0]
                )

                if (
                    primary_parameter.get("value")
                    != self.DISABLED_DRAWER_TYPE
                ):
                    primary_parameter.set(
                        "value",
                        self.DISABLED_DRAWER_TYPE,
                    )

                    result.parameters_updated.append(
                        f"{adaptor_type}:drawertype"
                    )

                    adaptor_modified = True

                for duplicate in drawertype_matches[1:]:
                    main_section.remove(duplicate)

                    result.warnings.append(
                        "Duplicate drawertype removed "
                        f"from adaptor {adaptor_type}."
                    )

                    adaptor_modified = True

            if adaptor_modified:
                result.adaptors_modified.append(
                    adaptor_type
                )
                result.modified = True

        return result

    @classmethod
    def _find_cash_drawer_adaptors(
        cls,
        root: ET.Element,
    ) -> list[ET.Element]:
        adaptors = []

        for element in root.iter():
            if cls._local_name(element.tag) != "Adaptor":
                continue

            adaptor_type = element.get("type")

            if (
                adaptor_type
                in cls.CASH_DRAWER_ADAPTOR_TYPES
            ):
                adaptors.append(element)

        return adaptors

    @classmethod
    def _find_direct_section(
        cls,
        adaptor: ET.Element,
        section_name: str,
    ) -> ET.Element | None:
        for child in list(adaptor):
            if cls._local_name(child.tag) != "Section":
                continue

            if child.get("name") == section_name:
                return child

        return None

    @classmethod
    def _find_direct_parameters(
        cls,
        section: ET.Element,
        parameter_name: str,
    ) -> list[ET.Element]:
        return [
            child
            for child in list(section)
            if (
                cls._local_name(child.tag)
                == "Parameter"
                and child.get("name")
                == parameter_name
            )
        ]

    @staticmethod
    def _insert_section(
        adaptor: ET.Element,
        section: ET.Element,
    ) -> None:
        children = list(adaptor)
        insert_index = len(children)

        for index, child in enumerate(children):
            if (
                CashDrawerTransformer._local_name(
                    child.tag
                )
                != "Section"
            ):
                insert_index = index
                break

        adaptor.insert(
            insert_index,
            section,
        )

    @staticmethod
    def _local_name(
        tag: str,
    ) -> str:
        return tag.rsplit("}", 1)[-1]

    @staticmethod
    def _indent(
        tree: ET.ElementTree,
    ) -> None:
        if hasattr(ET, "indent"):
            ET.indent(
                tree,
                space="    ",
            )