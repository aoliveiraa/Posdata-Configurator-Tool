from pathlib import Path
from xml.etree import ElementTree as ET

from src.validation.validation_result import ValidationResult


class XmlValidator:

    def validate_folder(
        self,
        folder_path: str,
    ) -> list[ValidationResult]:

        results = []

        folder = Path(folder_path)

        if not folder.exists():
            results.append(
                ValidationResult(
                    component="XML",
                    status="FAIL",
                    message=f"Folder not found: {folder}",
                )
            )
            return results

        xml_files = sorted(
            folder.rglob("*.xml")
        )

        if not xml_files:
            results.append(
                ValidationResult(
                    component="XML",
                    status="FAIL",
                    message="No XML files found",
                )
            )
            return results

        for xml_file in xml_files:

            try:

                ET.parse(xml_file)

                results.append(
                    ValidationResult(
                        component="XML",
                        status="PASS",
                        message=f"{xml_file.name} valid",
                    )
                )

            except Exception as exc:

                results.append(
                    ValidationResult(
                        component="XML",
                        status="FAIL",
                        message=f"{xml_file.name} invalid",
                        details=[str(exc)],
                    )
                )

        return results