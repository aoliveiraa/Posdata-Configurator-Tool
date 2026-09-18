from src.validation.validators.xml_validator import XmlValidator
from src.validation.validators.webview_validator import (
    WebViewValidator,
)
from src.validation.validators.performance_validator import (
    PerformanceValidator,
)

class ValidationManager:

    def __init__(self):

        self.xml_validator = XmlValidator()
        self.webview_validator = WebViewValidator()
        self.performance_validator = PerformanceValidator()

    def validate_output(
        self,
        output_folder: str,
    ):

        results = []

        results.extend(
            self.xml_validator.validate_folder(
                output_folder
            )
        )

        results.extend(
            self.webview_validator.validate_folder(
                "output/pos"
            )
        )

        results.extend(
            self.webview_validator.validate_folder(
                "output/itonas"
            )
        )

        results.extend(
            self.performance_validator.validate_output(
                output_folder
            )
        )

        return results