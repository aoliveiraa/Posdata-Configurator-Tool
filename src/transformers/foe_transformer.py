from collections import Counter
from pathlib import Path

from lxml import etree

from src.utils.xml_loader import load_xml, save_xml

FOE_SERVICE_ATTRIBUTES = {"type": "FOE", "classname": "npfoe.dll"}
RPS_SERVICE_ATTRIBUTES = {"type": "RPS", "classname": "npRPSService.dll"}
REQUIRED_RPS_PARAMETERS = ("clientsList", "FOEOperatorId", "FOEOperatorName")
OPTIONAL_FOE_PARAMETERS = ("ValidateRPSState", "PriceDiffThreshold", "TLOGDstName")
PRODUCT_PRICING_ADAPTOR = "npAdpProductPricing"


def normalize_text(value):
    return "" if value is None else str(value).strip()


def normalize_upper(value):
    return normalize_text(value).upper()


def unique_messages(messages):
    return list(dict.fromkeys(messages))


def get_service_by_type(tree, service_type):
    expected = normalize_upper(service_type)
    matches = [
        service for service in tree.xpath("//Service[@type]")
        if normalize_upper(service.get("type")) == expected
    ]
    return matches[0] if matches else None


def get_foe_service(tree):
    return get_service_by_type(tree, "FOE")


def get_rps_service(tree):
    return get_service_by_type(tree, "RPS")


def get_parameter(scope, parameter_name):
    if scope is None:
        return None
    expected = normalize_upper(parameter_name)
    for parameter in scope.xpath(".//Parameter[@name]"):
        if normalize_upper(parameter.get("name")) == expected:
            return parameter
    return None


def get_parameter_from_scopes(scopes, parameter_name):
    for scope in scopes:
        parameter = get_parameter(scope, parameter_name)
        if parameter is not None:
            return parameter
    return None


def get_adaptor(tree, adaptor_name):
    expected = normalize_upper(adaptor_name)

    for adaptor in tree.xpath("//Adaptor"):

        name = normalize_upper(
            adaptor.get("name")
        )

        adaptor_type = normalize_upper(
            adaptor.get("type")
        )

        if (
            name == expected
            or adaptor_type == expected
        ):
            return adaptor

    return None


def get_service_identifiers(tree):
    identifiers = set()
    for service in tree.xpath("//Service"):
        for attribute in ("name", "id", "serviceName"):
            value = normalize_text(service.get(attribute))
            if value:
                identifiers.add(normalize_upper(value))
    return identifiers


def deduplicate_members(tree):
    """Remove only exact duplicates, using name + alias as the key."""
    changes = []
    for used_service in tree.xpath("//UsedService"):
        seen = set()
        service_type = normalize_text(used_service.get("serviceType"))
        for member in list(used_service.xpath("./Member")):
            key = (
                normalize_text(member.get("name")),
                normalize_text(member.get("alias")),
            )
            if key in seen:
                used_service.remove(member)
                changes.append(
                    "Duplicate Member removed from UsedService "
                    f"{service_type}: name={key[0]}, alias={key[1]}."
                )
            else:
                seen.add(key)
    return changes


def find_duplicate_members(tree):
    errors = []
    for used_service in tree.xpath("//UsedService"):
        service_type = normalize_text(used_service.get("serviceType"))
        keys = [
            (normalize_text(member.get("name")), normalize_text(member.get("alias")))
            for member in used_service.xpath("./Member")
        ]
        for key, count in Counter(keys).items():
            if count > 1:
                errors.append(
                    "Duplicate Member in UsedService "
                    f"{service_type}: name={key[0]}, alias={key[1]}, count={count}."
                )
    return errors


def validate_service(service, expected_attributes, label):
    errors = []
    if service is None:
        return [f"{label} Service was not found."]
    for name, expected in expected_attributes.items():
        actual = service.get(name)
        if actual != expected:
            errors.append(
                f"{label} Service attribute {name} must be {expected}, found {actual}."
            )
    return errors


def validate_required_used_services(tree):
    errors = []
    types = {
        normalize_upper(node.get("serviceType"))
        for node in tree.xpath("//UsedService[@serviceType]")
    }
    for service_type in ("FOE", "RPS"):
        if service_type not in types:
            errors.append(f"UsedService {service_type} was not found.")
    return errors


def validate_required_parameters(scope, names, label):
    errors = []
    values = {}
    if scope is None:
        return errors, values
    for name in names:
        parameter = get_parameter(scope, name)
        value = parameter.get("value") if parameter is not None else None
        values[name] = value
        if parameter is None:
            errors.append(f"{label} Parameter {name} was not found.")
        elif not normalize_text(value):
            errors.append(f"{label} Parameter {name} has no value.")
    return errors, values


def inspect_optional_foe_parameters(tree, foe, rps):
    """Inspect market-specific FOE parameters without blocking generation."""
    warnings = []
    values = {}
    scopes = [scope for scope in (foe, rps, tree) if scope is not None]
    for name in OPTIONAL_FOE_PARAMETERS:
        parameter = get_parameter_from_scopes(scopes, name)
        if parameter is None:
            values[name] = None
            warnings.append(
                f"FOE parameter not found during readiness inspection: {name}."
            )
            continue
        value = normalize_text(parameter.get("value"))
        values[name] = value or None
        if not value:
            warnings.append(f"FOE parameter has no value: {name}.")
    return warnings, values


def validate_tlog_destination(tree, destination):
    warnings = []
    if not destination:
        return warnings
    if normalize_upper(destination) not in get_service_identifiers(tree):
        warnings.append(
            f"REVIEW REQUIRED: TLOG destination {destination} "
            "does not exist in generated topology."
        )
    return warnings


def validate_product_pricing(tree, product_pricing_root=None):
    errors = []
    warnings = []
    details = {
        "adaptor_found": False,
        "enabled": None,
        "target_path": None,
        "target_exists": None,
    }
    adaptor = get_adaptor(tree, PRODUCT_PRICING_ADAPTOR)
    if adaptor is None:
        errors.append(
            f"ProductPricing Adaptor {PRODUCT_PRICING_ADAPTOR} was not found."
        )
        return errors, warnings, details
    details["adaptor_found"] = True
    enable = get_parameter(adaptor, "enable")
    target = get_parameter(adaptor, "targetPath")
    details["enabled"] = enable.get("value") if enable is not None else None
    details["target_path"] = target.get("value") if target is not None else None
    if enable is None or normalize_upper(enable.get("value")) != "TRUE":
        errors.append("ProductPricing parameter enable must be true.")
    if target is None or not normalize_text(target.get("value")):
        errors.append("ProductPricing parameter targetPath is missing or empty.")
    elif product_pricing_root is not None:
        raw_path = normalize_text(target.get("value"))
        relative = raw_path[2:] if raw_path.startswith("./") else raw_path
        resolved = Path(product_pricing_root) / relative
        details["target_exists"] = resolved.exists()
        if not resolved.exists():
            warnings.append(
                "REVIEW REQUIRED: ProductPricing targetPath does not exist: "
                f"{resolved}."
            )
    return errors, warnings, details


def extract_store_integrity(tree):
    result = {}
    for name in ("StoreId", "CompanyId", "StoreLegacyId"):
        parameter = get_parameter(tree, name)
        result[name] = parameter.get("value") if parameter is not None else None
    return result


def compare_store_integrity(before, after):
    errors = []
    for name in ("StoreId", "CompanyId", "StoreLegacyId"):
        old = before.get(name)
        new = after.get(name)
        if old != new:
            errors.append(f"Store Integrity changed for {name}: {old} -> {new}.")
        if new is None or not normalize_text(new):
            errors.append(f"Store Integrity value {name} is missing.")
    return unique_messages(errors)


def validate_foe(tree, product_pricing_root=None, store_integrity_before=None):


    print()
    print("FOE VALIDATION DEBUG")
    print("-" * 50)

    print(
        "FOE FOUND:",
        get_foe_service(tree) is not None
    )

    print(
        "RPS FOUND:",
        get_rps_service(tree) is not None
    )

    print(
        "PRODUCT PRICING FOUND:",
        get_adaptor(
            tree,
            "npAdpProductPricing"
        ) is not None
    )


    errors = []
    warnings = []
    foe = get_foe_service(tree)
    rps = get_rps_service(tree)

    print()
    print("FOE VALIDATION SOURCE")
    print("-" * 50)

    print(
        "Tree object id:",
        id(tree)
    )

    print(
        "Root tag:",
        tree.getroot().tag
    )

    print(
        "FOE services:",
        len(
            tree.xpath(
                "//Service[@type='FOE']"
            )
        )
    )

    print(
        "RPS services:",
        len(
            tree.xpath(
                "//Service[@type='RPS']"
            )
        )
    )

    print(
        "ProductPricing adaptors:",
        len(
            tree.xpath(
                "//Adaptor[contains(@name,'ProductPricing')]"
            )
        )
    )

    foe_service_errors = validate_service(foe, FOE_SERVICE_ATTRIBUTES, "FOE")
    rps_service_errors = validate_service(rps, RPS_SERVICE_ATTRIBUTES, "RPS")
    errors.extend(foe_service_errors)
    errors.extend(rps_service_errors)
    errors.extend(validate_required_used_services(tree))


    print()
    print("RPS PARAMETERS FOUND")
    print("-" * 50)

    for parameter in rps.xpath(".//Parameter"):
        print(parameter.get("name"))

    rps_errors, rps_values = validate_required_parameters(
        rps, REQUIRED_RPS_PARAMETERS, "RPS"
    )
    errors.extend(rps_errors)

    foe_parameter_warnings, foe_values = inspect_optional_foe_parameters(
        tree, foe, rps
    )
    warnings.extend(foe_parameter_warnings)
    warnings.extend(
        validate_tlog_destination(tree, foe_values.get("TLOGDstName"))
    )

    duplicate_errors = find_duplicate_members(tree)
    errors.extend(duplicate_errors)

    pricing_errors, pricing_warnings, pricing_details = validate_product_pricing(
        tree, product_pricing_root
    )
    errors.extend(pricing_errors)
    warnings.extend(pricing_warnings)

    integrity_after = extract_store_integrity(tree)
    integrity_errors = []
    if store_integrity_before is not None:
        integrity_errors = compare_store_integrity(
            store_integrity_before, integrity_after
        )
        errors.extend(integrity_errors)

    review_required = any(
        message.startswith("REVIEW REQUIRED:") for message in warnings
    )

    readiness = {
        "foe_service_ok": foe is not None and not foe_service_errors,
        "rps_service_ok": rps is not None and not rps_service_errors,
        "rps_parameters_ok": not rps_errors,
        "product_pricing_ok": not pricing_errors and not pricing_warnings,
        "tlog_destination_ok": not any(
            "TLOG destination" in warning for warning in warnings
        ),
        "duplicate_members_ok": not duplicate_errors,
        "store_integrity_ok": not integrity_errors,
        "rps_parameters": rps_values,
        "foe_parameters": foe_values,
        "tlog_destination": foe_values.get("TLOGDstName"),
        "product_pricing": pricing_details,
        "store_integrity": integrity_after,
    }

    if errors:
        overall_status = "FAIL"
    elif review_required:
        overall_status = "REVIEW REQUIRED"
    else:
        overall_status = "FOE READY"

    return {
        "valid": not errors,
        "overall_status": overall_status,
        "errors": unique_messages(errors),
        "warnings": unique_messages(warnings),
        "readiness": readiness,
    }


def format_foe_readiness_report(validation):
    readiness = validation.get("readiness", {})

    def status(value):
        return "OK" if value else "REVIEW REQUIRED"

    lines = [
        "FOE READINESS REPORT",
        "=" * 50,
        f"FOE Service       : {status(readiness.get('foe_service_ok'))}",
        f"RPS Service       : {status(readiness.get('rps_service_ok'))}",
        f"RPS Parameters    : {status(readiness.get('rps_parameters_ok'))}",
        f"ProductPricing    : {status(readiness.get('product_pricing_ok'))}",
        f"TLOG Destination  : {status(readiness.get('tlog_destination_ok'))}",
        f"Duplicate Members : {status(readiness.get('duplicate_members_ok'))}",
        f"Store Integrity   : {status(readiness.get('store_integrity_ok'))}",
        "-" * 50,
        f"Overall Status    : {validation.get('overall_status', 'FAIL')}",
    ]
    lines.extend(f"WARNING: {item}" for item in validation.get("warnings", []))
    lines.extend(f"ERROR: {item}" for item in validation.get("errors", []))
    return "\n".join(lines)


def ensure_required_foe_sections(
    tree,
):
    """
    Backward-compatible entry point used by
    the WAY generation pipeline.

    This phase preserves FOE/RPS and must not
    perform final readiness validation.
    """

    return ensure_foe_standard(
        tree
    )

def ensure_foe_standard(
    tree,
    product_pricing_root=None,
):
    """
    Preserves FOE and RPS during WAY generation.

    This function is intentionally non-blocking.

    It does not rebuild FOE/RPS and does not run
    final FOE readiness validation. Final validation
    must run only after the transformed WAY has been
    saved to output/way.
    """

    changes = deduplicate_members(
        tree
    )

    warnings = []

    foe = get_foe_service(
        tree
    )

    rps = get_rps_service(
        tree
    )

    if foe is None:
        warnings.append(
            "FOE Service was not found during "
            "WAY preparation."
        )

    if rps is None:
        warnings.append(
            "RPS Service was not found during "
            "WAY preparation."
        )

    return {
        "success": True,
        "overall_status": "PRESERVED",
        "changes": unique_messages(
            changes
        ),
        "warnings": unique_messages(
            warnings
        ),
        "errors": [],
        "readiness": {
            "foe_service_found": (
                foe is not None
            ),
            "rps_service_found": (
                rps is not None
            ),
        },
        "report": (
            "FOE/RPS preserved during "
            "WAY preparation."
        ),
    }

def generate_foe_file(
    source_file,
    output_folder,
):

    print()
    print("FOE INPUT FILE")
    print("-" * 50)
    print(source_file)

    print()
    print("FOE FILE EXISTS")
    print("-" * 50)
    print(source_file.exists())

    """
    Validates the final transformed WAY and exports
    the validated FOE result.

    This function must receive the generated WAY,
    not the raw WAY from new_posdata.
    """

    source_file = Path(
        source_file
    )

    if not source_file.exists():
        return {
            "generated": False,
            "output_file": None,
            "errors": [
                "FOE source file was not found: "
                f"{source_file}"
            ],
            "warnings": [],
            "changes": [],
            "readiness": {},
            "report": (
                "FOE source file was not found."
            ),
        }

    tree = load_xml(
        source_file
    )

    print()
    print("FOE XML PATH")
    print("-" * 50)
    print(source_file.resolve())


    store_integrity_before = (
        extract_store_integrity(
            tree
        )
    )

    changes = deduplicate_members(
        tree
    )

    validation = validate_foe(
        tree,
        product_pricing_root=(
            source_file.parent
        ),
        store_integrity_before=(
            store_integrity_before
        ),
    )

    if validation["errors"]:
        return {
            "generated": False,
            "output_file": None,
            "errors": validation["errors"],
            "warnings": validation["warnings"],
            "changes": changes,
            "readiness": validation[
                "readiness"
            ],
            "report": (
                format_foe_readiness_report(
                    validation
                )
            ),
        }

    output_folder = Path(
        output_folder
    )

    output_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        output_folder
        / source_file.name
    )

    etree.indent(
        tree,
        space="  ",
    )

    save_xml(
        tree,
        output_path,
    )

    saved_tree = load_xml(
        output_path
    )

    post_validation = validate_foe(
        saved_tree,
        product_pricing_root=(
            source_file.parent
        ),
        store_integrity_before=(
            store_integrity_before
        ),
    )

    if post_validation["errors"]:
        output_path.unlink(
            missing_ok=True
        )

        return {
            "generated": False,
            "output_file": None,
            "errors": (
                post_validation["errors"]
            ),
            "warnings": (
                post_validation["warnings"]
            ),
            "changes": changes,
            "readiness": (
                post_validation[
                    "readiness"
                ]
            ),
            "report": (
                format_foe_readiness_report(
                    post_validation
                )
            ),
        }

    return {
        "generated": True,
        "output_file": str(
            output_path
        ),
        "errors": [],
        "warnings": (
            post_validation["warnings"]
        ),
        "changes": unique_messages(
            changes
            + [
                "FOE/RPS preserved and "
                "validated."
            ]
        ),
        "readiness": (
            post_validation["readiness"]
        ),
        "report": (
            format_foe_readiness_report(
                post_validation
            )
        ),
    }

def generate_all_foe(
    new_posdata_folder,
    output_folder="output/foe",
    generated_way_folder="output/way",
):
    """
    Validates FOE/RPS using the transformed WAY.

    The raw WAY from new_posdata is not accepted as
    a fallback, because it may not contain the final
    FOE/RPS/ProductPricing configuration.
    """

    generated_way_file = (
        Path(generated_way_folder)
        / "_WAYSTATION_pos-db.xml"
    )

    if not generated_way_file.exists():
        return [
            {
                "file": (
                    "_WAYSTATION_pos-db.xml"
                ),
                "generated": False,
                "output_file": None,
                "errors": [
                    "Generated WAY file was not "
                    "found for FOE validation: "
                    f"{generated_way_file}"
                ],
                "warnings": [],
                "changes": [],
                "readiness": {},
                "report": (
                    "FOE validation could not run "
                    "because the generated WAY file "
                    "was not found."
                ),
                "source_file": None,
                "source_type": (
                    "GENERATED WAY NOT FOUND"
                ),
            }
        ]

    print()
    print("FOE SOURCE SELECTION")
    print("-" * 50)
    print("Source type: GENERATED WAY")
    print(
        f"Source file: "
        f"{generated_way_file.resolve()}"
    )

    result = generate_foe_file(
        generated_way_file,
        output_folder,
    )

    result["file"] = (
        generated_way_file.name
    )

    result["source_file"] = str(
        generated_way_file.resolve()
    )

    result["source_type"] = (
        "GENERATED WAY"
    )

    return [result]


