from collections import Counter
from pathlib import Path

from lxml import etree

from src.utils.xml_loader import load_xml, save_xml


FOE_SERVICE_ATTRIBUTES = {
    "type": "FOE",
    "classname": "npfoe.dll",
}

RPS_SERVICE_ATTRIBUTES = {
    "type": "RPS",
    "classname": "npRPSService.dll",
}

REQUIRED_RPS_PARAMETERS = (
    "clientsList",
    "FOEOperatorId",
    "FOEOperatorName",
)

REQUIRED_FOE_PARAMETERS = (
    "ValidateRPSState",
    "PriceDiffThreshold",
    "TLOGDstName",
)

REQUIRED_QUEUE_MEMBERS = {
    ("8007", "PAID_DT"),
    ("8007", "DT"),
    ("8004", "PAID_FC"),
    ("8004", "FC"),
}

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
        service
        for service in tree.xpath("//Service[@type]")
        if normalize_upper(service.get("type")) == expected
    ]
    return matches[0] if matches else None


def get_foe_service(tree):
    return get_service_by_type(tree, "FOE")


def get_rps_service(tree):
    return get_service_by_type(tree, "RPS")


def get_parameter(scope, parameter_name):
    expected = normalize_upper(parameter_name)
    for parameter in scope.xpath(".//Parameter[@name]"):
        if normalize_upper(parameter.get("name")) == expected:
            return parameter
    return None


def get_adaptor(tree, adaptor_name):
    expected = normalize_upper(adaptor_name)
    matches = [
        adaptor
        for adaptor in tree.xpath("//Adaptor[@name]")
        if normalize_upper(adaptor.get("name")) == expected
    ]
    return matches[0] if matches else None


def get_service_identifiers(tree):
    identifiers = set()
    for service in tree.xpath("//Service"):
        for attribute in ("name", "id", "serviceName"):
            value = normalize_text(service.get(attribute))
            if value:
                identifiers.add(normalize_upper(value))
    return identifiers


def deduplicate_members(tree):
    """Remove exact duplicate Member nodes from each UsedService.

    The first Member is preserved. A repeated service number with a different
    alias is not treated as a duplicate because FOE queues legitimately use
    the same number with distinct aliases.
    """
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
            (
                normalize_text(member.get("name")),
                normalize_text(member.get("alias")),
            )
            for member in used_service.xpath("./Member")
        ]
        for key, count in Counter(keys).items():
            if count > 1:
                errors.append(
                    "Duplicate Member in UsedService "
                    f"{service_type}: name={key[0]}, alias={key[1]}, "
                    f"count={count}."
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
                f"{label} Service attribute {name} must be "
                f"{expected}, found {actual}."
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


def validate_queue_mapping(foe):
    errors = []
    actual = set()
    if foe is None:
        return ["FOE Service was not found; queues cannot be validated."], actual
    for used_service in foe.xpath(".//UsedService[@serviceType]"):
        if normalize_upper(used_service.get("serviceType")) != "QUE":
            continue
        for member in used_service.xpath("./Member"):
            actual.add(
                (
                    normalize_text(member.get("name")),
                    normalize_text(member.get("alias")),
                )
            )
    for name, alias in sorted(REQUIRED_QUEUE_MEMBERS - actual):
        errors.append(
            f"FOE queue mapping is missing name={name}, alias={alias}."
        )
    return errors, actual


def validate_tlog_destination(tree, foe):
    errors = []
    warnings = []
    destination = None
    if foe is None:
        return errors, warnings, destination
    parameter = get_parameter(foe, "TLOGDstName")
    if parameter is None:
        errors.append("FOE Parameter TLOGDstName was not found.")
        return errors, warnings, destination
    destination = normalize_text(parameter.get("value"))
    if not destination:
        errors.append("FOE Parameter TLOGDstName has no value.")
        return errors, warnings, destination
    if normalize_upper(destination) not in get_service_identifiers(tree):
        warnings.append(
            f"REVIEW REQUIRED: TLOG destination {destination} "
            "does not exist in generated topology."
        )
    return errors, warnings, destination


def validate_used_service_references(tree):
    """Report broken references for topology-related UsedServices.

    QUE is excluded because 8004/8007 are logical queue identifiers and are
    checked by validate_queue_mapping().
    """
    warnings = []
    service_ids = get_service_identifiers(tree)
    checked_types = {"FOE", "RPS", "WAY", "PST", "POS", "STO", "PSW"}
    for used_service in tree.xpath("//UsedService[@serviceType]"):
        service_type = normalize_upper(used_service.get("serviceType"))
        if service_type not in checked_types:
            continue
        for member in used_service.xpath("./Member"):
            name = normalize_text(member.get("name"))
            if not name:
                warnings.append(
                    f"REVIEW REQUIRED: UsedService {service_type} "
                    "contains a Member without name."
                )
            elif normalize_upper(name) not in service_ids:
                warnings.append(
                    f"REVIEW REQUIRED: UsedService {service_type} "
                    f"references missing Service {name}."
                )
    return unique_messages(warnings)


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
        relative_path = raw_path[2:] if raw_path.startswith("./") else raw_path
        resolved = Path(product_pricing_root) / relative_path
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
    errors = []
    warnings = []
    foe = get_foe_service(tree)
    rps = get_rps_service(tree)

    foe_service_errors = validate_service(foe, FOE_SERVICE_ATTRIBUTES, "FOE")
    rps_service_errors = validate_service(rps, RPS_SERVICE_ATTRIBUTES, "RPS")
    errors.extend(foe_service_errors)
    errors.extend(rps_service_errors)
    errors.extend(validate_required_used_services(tree))

    rps_errors, rps_values = validate_required_parameters(
        rps,
        REQUIRED_RPS_PARAMETERS,
        "RPS",
    )
    errors.extend(rps_errors)

    foe_parameter_errors, foe_values = validate_required_parameters(
        foe,
        REQUIRED_FOE_PARAMETERS,
        "FOE",
    )
    errors.extend(foe_parameter_errors)

    queue_errors, queue_mapping = validate_queue_mapping(foe)
    errors.extend(queue_errors)

    tlog_errors, tlog_warnings, tlog_destination = validate_tlog_destination(
        tree,
        foe,
    )
    errors.extend(tlog_errors)
    warnings.extend(tlog_warnings)

    errors.extend(find_duplicate_members(tree))

    reference_warnings = validate_used_service_references(tree)
    warnings.extend(reference_warnings)

    pricing_errors, pricing_warnings, pricing_details = validate_product_pricing(
        tree,
        product_pricing_root,
    )
    errors.extend(pricing_errors)
    warnings.extend(pricing_warnings)

    integrity_after = extract_store_integrity(tree)
    integrity_errors = []
    if store_integrity_before is not None:
        integrity_errors = compare_store_integrity(
            store_integrity_before,
            integrity_after,
        )
        errors.extend(integrity_errors)

    review_required = any(
        message.startswith("REVIEW REQUIRED:")
        for message in warnings
    )

    readiness = {
        "foe_service_ok": foe is not None and not foe_service_errors,
        "rps_service_ok": rps is not None and not rps_service_errors,
        "product_pricing_ok": not pricing_errors and not pricing_warnings,
        "queue_mapping_ok": not queue_errors,
        "tlog_destination_ok": not tlog_errors and not tlog_warnings,
        "used_service_references_ok": not reference_warnings,
        "store_integrity_ok": not integrity_errors,
        "rps_parameters": rps_values,
        "foe_parameters": foe_values,
        "queue_mapping": sorted(queue_mapping),
        "tlog_destination": tlog_destination,
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
        f"ProductPricing    : {status(readiness.get('product_pricing_ok'))}",
        f"Queue Mapping     : {status(readiness.get('queue_mapping_ok'))}",
        f"TLOG Destination  : {status(readiness.get('tlog_destination_ok'))}",
        f"UsedService Refs  : {status(readiness.get('used_service_references_ok'))}",
        f"Store Integrity   : {status(readiness.get('store_integrity_ok'))}",
        "-" * 50,
        f"Overall Status    : {validation.get('overall_status', 'FAIL')}",
    ]
    lines.extend(f"WARNING: {item}" for item in validation.get("warnings", []))
    lines.extend(f"ERROR: {item}" for item in validation.get("errors", []))
    return "\n".join(lines)


def ensure_required_foe_sections(tree):
    """Backward-compatible entry point used by older pipeline code."""
    return ensure_foe_standard(tree)


def ensure_foe_standard(tree, product_pricing_root=None):
    """Preserve FOE/RPS content and validate it without rebuilding it.

    Only exact duplicate Member nodes are removed. Existing Services,
    UsedServices, Sections, Parameters and Adaptors are otherwise untouched.
    """
    changes = deduplicate_members(tree)
    validation = validate_foe(
        tree,
        product_pricing_root=product_pricing_root,
    )
    return {
        "success": validation["valid"],
        "overall_status": validation["overall_status"],
        "changes": unique_messages(changes),
        "warnings": validation["warnings"],
        "errors": validation["errors"],
        "readiness": validation["readiness"],
        "report": format_foe_readiness_report(validation),
    }


def generate_foe_file(source_file, output_folder):
    source_file = Path(source_file)
    tree = load_xml(source_file)
    store_integrity_before = extract_store_integrity(tree)

    transformation = ensure_foe_standard(
        tree,
        product_pricing_root=source_file.parent,
    )

    if transformation["errors"]:
        return {
            "generated": False,
            "output_file": None,
            "errors": transformation["errors"],
            "warnings": transformation["warnings"],
            "changes": transformation["changes"],
            "readiness": transformation["readiness"],
            "report": transformation["report"],
        }

    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)
    output_path = output_folder / source_file.name

    etree.indent(tree, space="  ")
    save_xml(tree, output_path)

    validation_tree = load_xml(output_path)
    post_validation = validate_foe(
        validation_tree,
        product_pricing_root=source_file.parent,
        store_integrity_before=store_integrity_before,
    )

    if post_validation["errors"]:
        output_path.unlink(missing_ok=True)
        return {
            "generated": False,
            "output_file": None,
            "errors": post_validation["errors"],
            "warnings": post_validation["warnings"],
            "changes": transformation["changes"],
            "readiness": post_validation["readiness"],
            "report": format_foe_readiness_report(post_validation),
        }

    return {
        "generated": True,
        "output_file": str(output_path),
        "errors": [],
        "warnings": post_validation["warnings"],
        "changes": unique_messages(
            transformation["changes"] + ["FOE/RPS preserved and validated."]
        ),
        "readiness": post_validation["readiness"],
        "report": format_foe_readiness_report(post_validation),
    }


def generate_all_foe(new_posdata_folder, output_folder="output/foe"):
    source_file = Path(new_posdata_folder) / "_WAYSTATION_pos-db.xml"
    if not source_file.exists():
        return []

    result = generate_foe_file(source_file, output_folder)
    result["file"] = "_WAYSTATION_pos-db.xml"
    return [result]
