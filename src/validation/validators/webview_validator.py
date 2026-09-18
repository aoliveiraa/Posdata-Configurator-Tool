from pathlib import Path

from src.validation.validation_result import ValidationResult


class WebViewValidator:

    WEBVIEW_MARKERS = [
        "LocalWebView",
        "WebView",
    ]

    def validate_folder(
        self,
        folder_path: str,
    ) -> list[ValidationResult]:

        results = []

        folder = Path(folder_path)

        if not folder.exists():

            results.append(
                ValidationResult(
                    component="WEBVIEW",
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
                    component="WEBVIEW",
                    status="FAIL",
                    message="No XML files found",
                )
            )

            return results

        for xml_file in xml_files:

            try:

                content = xml_file.read_text(
                    encoding="utf-8",
                    errors="ignore"
                )

                webview_found = any(
                    marker in content
                    for marker in self.WEBVIEW_MARKERS
                )

                if webview_found:

                    results.append(
                        ValidationResult(
                            component="WEBVIEW",
                            status="PASS",
                            message=(
                                f"{xml_file.name} "
                                f"contains WebView"
                            ),
                        )
                    )

                else:

                    results.append(
                        ValidationResult(
                            component="WEBVIEW",
                            status="FAIL",
                            message=(
                                f"{xml_file.name} "
                                f"missing WebView"
                            ),
                        )
                    )

            except Exception as exc:

                results.append(
                    ValidationResult(
                        component="WEBVIEW",
                        status="FAIL",
                        message=(
                            f"{xml_file.name} "
                            f"could not be validated"
                        ),
                        details=[
                            str(exc)
                        ],
                    )
                )

        return results