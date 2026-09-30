from lxml import etree


def disable_rpr_used_services(tree):
    """
    Remove:

        <UsedService serviceType="RPR">

    from POS DBs.

    This prevents printer retry dialogs such as:

        RPR0001
        RPR0002
        RPR0004
        RPR0005
    """

    changes = []

    used_services = tree.xpath(
        "//UsedService[@serviceType='RPR']"
    )

    for used_service in used_services:

        parent = used_service.getparent()

        if parent is None:
            continue

        member_count = len(
            used_service.xpath("./Member")
        )

        parent.remove(
            used_service
        )

        changes.append(
            "UsedService RPR removed "
            f"({member_count} members)."
        )

    return changes


def disable_rpr_services(tree):
    """
    Remove:

        <Service type='RPR'>

    completely.
    """

    changes = []

    services = tree.xpath(
        "//Service[@type='RPR']"
    )

    for service in services:

        parent = service.getparent()

        if parent is None:
            continue

        service_name = service.get(
            "name",
            "UNKNOWN"
        )

        parent.remove(
            service
        )

        changes.append(
            "RPR Service removed: "
            f"{service_name}."
        )

    return changes


def disable_rpr_driverhosts(tree):
    """
    Remove:

        Component.DriverHost.RPR0001
        Component.DriverHost.RPR0002
        Component.DriverHost.RPR0004
        Component.DriverHost.RPR0005

    from NPW services.
    """

    changes = []

    sections = tree.xpath(
        "//Section[starts-with(@name,'Component.DriverHost.RPR')]"
    )

    for section in sections:

        parent = section.getparent()

        if parent is None:
            continue

        section_name = section.get(
            "name",
            "UNKNOWN"
        )

        parent.remove(
            section
        )

        changes.append(
            "RPR DriverHost removed: "
            f"{section_name}."
        )

    return changes


def apply_rpr_configuration(
    tree,
    disable_rpr_printers=False,
):
    """
    Main transformer entry point.
    """

    result = {
        "modified": False,
        "changes": [],
        "warnings": [],
        "errors": [],
    }

    if not disable_rpr_printers:
        return result

    changes = []

    changes.extend(
        disable_rpr_used_services(
            tree
        )
    )

    changes.extend(
        disable_rpr_services(
            tree
        )
    )

    changes.extend(
        disable_rpr_driverhosts(
            tree
        )
    )

    result["modified"] = bool(
        changes
    )

    result["changes"] = changes

    return result