from src.validation.validation_rules_engine import (
    Applicability,
    DISABLED,
    ENABLED,
    FAIL,
    PRESENT,
    SKIPPED,
    ValidationRule,
    XmlSelector,
)


LOCAL_WEBVIEW_SELECTOR = XmlSelector(
    names=("LocalWebView",),
)

COD_SELECTOR = XmlSelector(
    types=("COD",),
)

COD_SIGNAL_SELECTORS = (
    XmlSelector(types=("COD",)),
    XmlSelector(imports=("COD",)),
    XmlSelector(names=("CODRouting",)),
)


PERFORMANCE_RULES = (
    ValidationRule(
        rule_id="PERF-POS-CASHDRAWER-DISABLED",
        component="PERFORMANCE",
        target_name="CashDrawer",
        expected_state=DISABLED,
        selector=XmlSelector(
            names=("CashDrawer", "CashDrawerEnabled"),
        ),
        applicability=Applicability(
            folders=("pos",),
        ),
        missing_status=SKIPPED,
        description="CashDrawer must not be enabled on performance POS nodes.",
    ),
    ValidationRule(
        rule_id="PERF-POS-PRINTER-DISABLED",
        component="PERFORMANCE",
        target_name="Printer",
        expected_state=DISABLED,
        selector=XmlSelector(
            names=("Printer", "PrinterEnabled"),
        ),
        applicability=Applicability(
            folders=("pos",),
        ),
        missing_status=SKIPPED,
        description="Printer must not be enabled on performance POS nodes.",
    ),
    ValidationRule(
        rule_id="PERF-POS-BUMPBAR-DISABLED",
        component="PERFORMANCE",
        target_name="BumpBar",
        expected_state=DISABLED,
        selector=XmlSelector(
            names=("BumpBar", "BumpBarEnabled"),
        ),
        applicability=Applicability(
            folders=("pos",),
        ),
        missing_status=SKIPPED,
        description="BumpBar must not be enabled on performance POS nodes.",
    ),
    ValidationRule(
        rule_id="PERF-POS-SCALE-DISABLED",
        component="PERFORMANCE",
        target_name="Scale",
        expected_state=DISABLED,
        selector=XmlSelector(
            names=("Scale", "ScaleEnabled"),
        ),
        applicability=Applicability(
            folders=("pos",),
        ),
        missing_status=SKIPPED,
        description="Scale must not be enabled on performance POS nodes.",
    ),
    ValidationRule(
        rule_id="PERF-POS-WEBVIEW-PRESENT",
        component="PERFORMANCE",
        target_name="LocalWebView",
        expected_state=PRESENT,
        selector=LOCAL_WEBVIEW_SELECTOR,
        applicability=Applicability(
            folders=("pos",),
        ),
        missing_status=FAIL,
        description="Every generated POS node must contain LocalWebView.",
    ),
    ValidationRule(
        rule_id="PERF-KVS-WEBVIEW-PRESENT",
        component="PERFORMANCE",
        target_name="LocalWebView",
        expected_state=PRESENT,
        selector=LOCAL_WEBVIEW_SELECTOR,
        applicability=Applicability(
            folders=("itonas",),
        ),
        missing_status=FAIL,
        description="Every generated Itona/KVS node must contain LocalWebView.",
    ),
    ValidationRule(
        rule_id="PERF-COD-ENABLED-WHEN-APPLICABLE",
        component="PERFORMANCE",
        target_name="COD",
        expected_state=ENABLED,
        selector=COD_SELECTOR,
        applicability=Applicability(
            folders=("pos",),
            file_patterns=("*POS12*_pos-db.xml", "*POS12*-pos-db.xml"),
        ),
        missing_status=FAIL,
        description=(
            "COD is currently required on POS12 nodes. Update the file patterns "
            "when another market uses a different COD host."
        ),
    ),
    ValidationRule(
        rule_id="PERF-WAY-FOE-ENABLED",
        component="PERFORMANCE",
        target_name="FOE",
        expected_state=ENABLED,
        selector=XmlSelector(types=("FOE",)),
        applicability=Applicability(
            folders=("way",),
        ),
        missing_status=FAIL,
        description="The generated WAY node must contain an enabled FOE service.",
    ),
    ValidationRule(
        rule_id="PERF-WAY-RPS-ENABLED",
        component="PERFORMANCE",
        target_name="RPS",
        expected_state=ENABLED,
        selector=XmlSelector(types=("RPS",)),
        applicability=Applicability(
            folders=("way",),
        ),
        missing_status=FAIL,
        description="The generated WAY node must contain an enabled RPS service.",
    ),
)
