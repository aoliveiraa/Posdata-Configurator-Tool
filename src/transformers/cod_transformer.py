from pathlib import Path

from lxml import etree

from src.utils.xml_loader import (
    load_xml,
    save_xml
)


LOWERCASE = "abcdefghijklmnopqrstuvwxyz"
UPPERCASE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def normalize_text(value):
    if value is None:
        return ""

    return str(value).strip()


def normalize_upper(value):
    return normalize_text(value).upper()


def normalize_service_id(value):
    """
    Normaliza IDs de POS.

    Exemplos:
        POS0004 -> 0004
        0004 -> 0004
        4 -> 0004
    """

    normalized = normalize_upper(value)

    if normalized.startswith("POS"):
        normalized = normalized[3:]

    if normalized.isdigit():
        return normalized.zfill(4)

    return normalized


def get_root_store_wide_configuration(
    tree
):
    """
    Localiza ou cria a Configuration
    imports="Store.wide" diretamente
    abaixo do PosDB.
    """

    configurations = tree.xpath(
        "/PosDB/Configuration["
        "translate("
        "@imports, "
        f"'{LOWERCASE}', "
        f"'{UPPERCASE}'"
        ")='STORE.WIDE'"
        "]"
    )

    if configurations:
        return configurations[0], False

    root = tree.getroot()

    configuration = etree.Element(
        "Configuration"
    )

    configuration.set(
        "imports",
        "Store.wide"
    )

    services_nodes = root.xpath(
        "./Services"
    )

    if services_nodes:
        services_node = services_nodes[0]

        services_position = root.index(
            services_node
        )

        root.insert(
            services_position,
            configuration
        )
    else:
        root.append(
            configuration
        )

    return configuration, True

def get_direct_section(
    parent,
    section_name
):
    """
    Localiza uma Section filha direta,
    ignorando maiúsculas e minúsculas.
    """

    expected_name = normalize_upper(
        section_name
    )

    for section in parent.xpath(
        "./Section[@name]"
    ):
        current_name = normalize_upper(
            section.get("name")
        )

        if current_name == expected_name:
            return section

    return None


def ensure_direct_section(
    parent,
    section_name
):
    """
    Localiza ou cria uma Section filha direta.
    """

    section = get_direct_section(
        parent,
        section_name
    )

    created = False

    if section is None:
        section = etree.SubElement(
            parent,
            "Section"
        )

        section.set(
            "name",
            section_name
        )

        created = True

    return section, created


def get_direct_parameter(
    parent,
    parameter_name
):
    """
    Localiza um Parameter filho direto,
    ignorando maiúsculas e minúsculas.
    """

    expected_name = normalize_upper(
        parameter_name
    )

    for parameter in parent.xpath(
        "./Parameter[@name]"
    ):
        current_name = normalize_upper(
            parameter.get("name")
        )

        if current_name == expected_name:
            return parameter

    return None


def set_direct_parameter(
    parent,
    parameter_name,
    parameter_value
):
    """
    Cria ou atualiza um Parameter filho direto.
    """

    parameter = get_direct_parameter(
        parent,
        parameter_name
    )

    created = False
    old_value = None

    if parameter is None:
        parameter = etree.SubElement(
            parent,
            "Parameter"
        )

        parameter.set(
            "name",
            parameter_name
        )

        created = True

    else:
        old_value = parameter.get(
            "value"
        )

    new_value = str(
        parameter_value
    )

    parameter.set(
        "value",
        new_value
    )

    return {
        "created": created,
        "changed": (
            created
            or old_value != new_value
        ),
        "old_value": old_value,
        "new_value": new_value
    }


def build_routing_value(
    routes
):
    """
    Converte o dicionário de rotas em:

    POS0004=DCOD0002|POS0013=DCOD0002
    """

    if isinstance(routes, str):
        return routes

    if not isinstance(routes, dict):
        raise ValueError(
            "COD routing routes must be "
            "a dictionary or string."
        )

    routing_items = []

    for node_name, route_name in (
        routes.items()
    ):
        routing_items.append(
            f"{node_name}={route_name}"
        )

    return "|".join(
        routing_items
    )


def ensure_cod_routing(
    tree,
    mapping_value,
    routing_value
):
    """
    Cria ou atualiza:

    <Configuration imports="Store.wide">
        <Section name="CODRouting">
            <Parameter name="Mapping" ... />
            <Parameter name="Routing" ... />
        </Section>
    </Configuration>
    """

    changes = []

    configuration, configuration_created = (
        get_root_store_wide_configuration(
            tree
        )
    )

    if configuration_created:
        changes.append(
            "Root Store.wide Configuration created"
        )

    cod_routing, section_created = (
        ensure_direct_section(
            configuration,
            "CODRouting"
        )
    )

    if section_created:
        changes.append(
            "CODRouting created"
        )

    mapping_result = set_direct_parameter(
        cod_routing,
        "Mapping",
        mapping_value
    )

    if mapping_result["changed"]:
        action = (
            "created"
            if mapping_result["created"]
            else "updated"
        )

        changes.append(
            "COD Mapping "
            f"{action}: "
            f"{mapping_result['old_value']} -> "
            f"{mapping_result['new_value']}"
        )

    routing_result = set_direct_parameter(
        cod_routing,
        "Routing",
        routing_value
    )

    if routing_result["changed"]:
        action = (
            "created"
            if routing_result["created"]
            else "updated"
        )

        changes.append(
            "COD Routing "
            f"{action}: "
            f"{routing_result['old_value']} -> "
            f"{routing_result['new_value']}"
        )

    if not mapping_result["changed"]:
        changes.append(
            "COD Mapping already correct"
        )

    if not routing_result["changed"]:
        changes.append(
            "COD Routing already correct"
        )

    return changes


def find_target_pos_service(
    tree,
    node_name
):
    """
    Localiza o serviço POS correspondente
    ao node descoberto.

    Exemplo:
        POS0004 -> Service type="POS" name="0004"

    Se houver somente um serviço POS direto,
    usa esse serviço como fallback.
    """

    expected_service_id = (
        normalize_service_id(
            node_name
        )
    )

    pos_services = tree.xpath(
        "/PosDB/Services/Service["
        "translate("
        "@type, "
        f"'{LOWERCASE}', "
        f"'{UPPERCASE}'"
        ")='POS'"
        "]"
    )

    for service in pos_services:
        service_id = normalize_service_id(
            service.get("name")
        )

        if service_id == expected_service_id:
            return service

    if len(pos_services) == 1:
        return pos_services[0]

    return None


def ensure_used_services_container(
    service
):
    used_services_nodes = service.xpath(
        "./UsedServices"
    )

    if used_services_nodes:
        return used_services_nodes[0], False

    used_services = etree.Element(
        "UsedServices"
    )

    configuration_nodes = service.xpath(
        "./Configuration"
    )

    adaptors_nodes = service.xpath(
        "./Adaptors"
    )

    if configuration_nodes:

        configuration = (
            configuration_nodes[0]
        )

        position = service.index(
            configuration
        )

        service.insert(
            position,
            used_services
        )

    elif adaptors_nodes:

        adaptors = adaptors_nodes[0]

        position = service.index(
            adaptors
        )

        service.insert(
            position,
            used_services
        )

    else:

        service.append(
            used_services
        )

    return used_services, True

def get_used_service(
    used_services,
    service_type
):
    """
    Localiza UsedService dentro de UsedServices.
    """

    expected_type = normalize_upper(
        service_type
    )

    for used_service in used_services.xpath(
        "./UsedService[@serviceType]"
    ):
        current_type = normalize_upper(
            used_service.get(
                "serviceType"
            )
        )

        if current_type == expected_type:
            return used_service

    return None


def ensure_used_service(
    used_services,
    service_type
):
    """
    Localiza ou cria UsedService.
    """

    used_service = get_used_service(
        used_services,
        service_type
    )

    created = False

    if used_service is None:
        used_service = etree.SubElement(
            used_services,
            "UsedService"
        )

        used_service.set(
            "serviceType",
            service_type
        )

        created = True

    return used_service, created


def get_member(
    used_service,
    member_name
):
    """
    Localiza Member pelo atributo name.
    """

    expected_name = normalize_text(
        member_name
    )

    for member in used_service.xpath(
        "./Member[@name]"
    ):
        current_name = normalize_text(
            member.get("name")
        )

        if current_name == expected_name:
            return member

    return None


def ensure_member(
    used_service,
    member_name,
    member_alias=""
):
    """
    Cria ou atualiza um Member.
    """

    member = get_member(
        used_service,
        member_name
    )

    created = False
    old_alias = None

    if member is None:
        member = etree.SubElement(
            used_service,
            "Member"
        )

        member.set(
            "name",
            str(member_name)
        )

        created = True

    else:
        old_alias = member.get(
            "alias"
        )

    new_alias = str(
        member_alias
    )

    member.set(
        "alias",
        new_alias
    )

    return {
        "created": created,
        "changed": (
            created
            or old_alias != new_alias
        ),
        "old_alias": old_alias,
        "new_alias": new_alias
    }


def ensure_cod_used_service(
    tree,
    node_name,
    cod_config
):
    """
    Garante a estrutura:

    <Service type="POS" name="xxxx">
        <UsedServices>
            <UsedService serviceType="COD">
                <Member name="01" alias="" />
                <Member name="02" alias="" />
            </UsedService>
        </UsedServices>
    </Service>

    Todos os blocos ausentes são criados.
    """

    changes = []
    errors = []

    pos_service = find_target_pos_service(
        tree,
        node_name
    )

    if pos_service is None:
        return {
            "changes": changes,
            "errors": [
                "Unable to identify the target "
                f"POS service for {node_name}."
            ]
        }

    service_name = normalize_text(
        pos_service.get("name")
    )

    used_services, container_created = (
        ensure_used_services_container(
            pos_service
        )
    )

    if container_created:
        changes.append(
            "UsedServices created inside "
            f"POS service {service_name}"
        )

    cod_used_service, cod_created = (
        ensure_used_service(
            used_services,
            "COD"
        )
    )

    if cod_created:
        changes.append(
            "UsedService COD created"
        )

    members_config = cod_config.get(
        "used_services",
        []
    )

    if not members_config:
        errors.append(
            "No COD UsedService members "
            "were configured."
        )

        return {
            "changes": changes,
            "errors": errors
        }

    for member_config in members_config:
        member_name = member_config.get(
            "name"
        )

        member_alias = member_config.get(
            "alias",
            ""
        )

        if member_name is None:
            errors.append(
                "A COD UsedService member "
                "does not contain a name."
            )

            continue

        result = ensure_member(
            cod_used_service,
            member_name,
            member_alias
        )

        if result["created"]:
            changes.append(
                f"COD Member {member_name} added"
            )

        elif result["changed"]:
            changes.append(
                f"COD Member {member_name} "
                "alias updated: "
                f"{result['old_alias']} -> "
                f"{result['new_alias']}"
            )

        else:
            changes.append(
                f"COD Member {member_name} "
                "already correct"
            )

    return {
        "changes": changes,
        "errors": errors
    }


def validate_cod_routing(
    tree,
    mapping_value,
    routing_value
):
    errors = []

    configurations = tree.xpath(
        "/PosDB/Configuration["
        "translate("
        "@imports, "
        f"'{LOWERCASE}', "
        f"'{UPPERCASE}'"
        ")='STORE.WIDE'"
        "]"
    )

    if not configurations:
        return [
            "Root Store.wide Configuration "
            "was not found."
        ]

    cod_routing = get_direct_section(
        configurations[0],
        "CODRouting"
    )

    if cod_routing is None:
        return [
            "CODRouting section was not found."
        ]

    mapping_parameter = get_direct_parameter(
        cod_routing,
        "Mapping"
    )

    routing_parameter = get_direct_parameter(
        cod_routing,
        "Routing"
    )

    if mapping_parameter is None:
        errors.append(
            "COD Mapping parameter "
            "was not found."
        )

    elif mapping_parameter.get(
        "value"
    ) != mapping_value:
        errors.append(
            "COD Mapping has an "
            "unexpected value."
        )

    if routing_parameter is None:
        errors.append(
            "COD Routing parameter "
            "was not found."
        )

    elif routing_parameter.get(
        "value"
    ) != routing_value:
        errors.append(
            "COD Routing has an "
            "unexpected value."
        )

    return errors


def validate_cod_used_service(
    tree,
    node_name,
    cod_config
):
    errors = []

    pos_service = find_target_pos_service(
        tree,
        node_name
    )

    if pos_service is None:
        return [
            "Target POS service was not found "
            f"for {node_name}."
        ]

    used_services_nodes = pos_service.xpath(
        "./UsedServices"
    )

    if not used_services_nodes:
        return [
            "UsedServices was not found inside "
            f"the POS service for {node_name}."
        ]

    cod_used_service = get_used_service(
        used_services_nodes[0],
        "COD"
    )

    if cod_used_service is None:
        return [
            "UsedService COD was not found "
            f"for {node_name}."
        ]

    for member_config in cod_config.get(
        "used_services",
        []
    ):
        member_name = member_config.get(
            "name"
        )

        expected_alias = str(
            member_config.get(
                "alias",
                ""
            )
        )

        member = get_member(
            cod_used_service,
            member_name
        )

        if member is None:
            errors.append(
                "COD UsedService is missing "
                f"Member {member_name}."
            )

            continue

        actual_alias = member.get(
            "alias",
            ""
        )

        if actual_alias != expected_alias:
            errors.append(
                f"COD Member {member_name} "
                "has an unexpected alias. "
                f"Expected '{expected_alias}', "
                f"found '{actual_alias}'."
            )

    return errors


def build_cod_result(
    generated,
    cod_target,
    target_file=None,
    changes=None,
    warnings=None,
    errors=None
):
    return {
        "generated": generated,
        "node": cod_target.get(
            "node_name"
        ),
        "reference_machine": (
            cod_target.get(
                "reference_machine"
            )
        ),
        "file": cod_target.get(
            "output_file"
        ),
        "output_file": (
            str(target_file)
            if target_file
            else None
        ),
        "changes": changes or [],
        "warnings": warnings or [],
        "errors": errors or []
    }


def generate_cod_file(
    cod_target,
    config_path="config/rio_lab.json",
    output_folder="output/pos"
):
    """
    Aplica no POS alvo:

    1. CODRouting
    2. UsedServices, se ausente
    3. UsedService COD, se ausente
    4. Members COD, se ausentes

    O arquivo alvo é resolvido pelo COD Discovery.
    """

    changes = []
    warnings = []
    errors = []

    if not cod_target.get(
        "enabled",
        False
    ):
        return build_cod_result(
            generated=False,
            cod_target=cod_target,
            errors=[
                "COD is disabled."
            ]
        )

    if not cod_target.get(
        "found",
        False
    ):
        return build_cod_result(
            generated=False,
            cod_target=cod_target,
            warnings=cod_target.get(
                "warnings",
                []
            ),
            errors=cod_target.get(
                "errors",
                [
                    "COD target was not resolved."
                ]
            )
        )

    cod_config = cod_target.get(
        "config",
        {}
    )

    routing_config = cod_config.get(
        "routing",
        {}
    )

    mapping_value = routing_config.get(
        "mapping"
    )

    routes = routing_config.get(
        "routes"
    )

    if not mapping_value:
        errors.append(
            "COD routing mapping was "
            "not configured."
        )

    if not routes:
        errors.append(
            "COD routes were not configured."
        )

    output_filename = cod_target.get(
        "output_file"
    )

    node_name = cod_target.get(
        "node_name"
    )

    if not output_filename:
        errors.append(
            "COD output filename was not "
            "resolved."
        )

    if not node_name:
        errors.append(
            "COD POS node was not resolved."
        )

    if errors:
        return build_cod_result(
            generated=False,
            cod_target=cod_target,
            errors=errors
        )

    target_file = (
        Path(output_folder)
        / output_filename
    )

    if not target_file.exists():
        return build_cod_result(
            generated=False,
            cod_target=cod_target,
            errors=[
                "COD target POS file was "
                f"not found: {target_file}"
            ]
        )

    try:
        tree = load_xml(
            target_file
        )

    except Exception as error:
        return build_cod_result(
            generated=False,
            cod_target=cod_target,
            target_file=target_file,
            errors=[
                "Unable to load COD target "
                f"POS file: {error}"
            ]
        )

    try:
        routing_value = build_routing_value(
            routes
        )

    except ValueError as error:
        return build_cod_result(
            generated=False,
            cod_target=cod_target,
            target_file=target_file,
            errors=[
                str(error)
            ]
        )

    changes.extend(
        ensure_cod_routing(
            tree,
            mapping_value,
            routing_value
        )
    )

    used_service_result = (
        ensure_cod_used_service(
            tree,
            node_name,
            cod_config
        )
    )

    cod_service_result = (
    ensure_cod_service(
        tree,
        cod_config
    )
    )

    changes.extend(
        cod_service_result[
            "changes"
        ]
    )

    errors.extend(
        cod_service_result[
            "errors"
        ]
    )

    changes.extend(
        used_service_result[
            "changes"
        ]
    )

    errors.extend(
        used_service_result[
            "errors"
        ]
    )

    errors.extend(
        validate_cod_routing(
            tree,
            mapping_value,
            routing_value
        )
    )

    errors.extend(
        validate_cod_used_service(
            tree,
            node_name,
            cod_config
        )
    )

    changes = list(
        dict.fromkeys(changes)
    )

    warnings = list(
        dict.fromkeys(warnings)
    )

    errors = list(
        dict.fromkeys(errors)
    )

    if errors:
        return build_cod_result(
            generated=False,
            cod_target=cod_target,
            target_file=target_file,
            changes=changes,
            warnings=warnings,
            errors=errors
        )

    etree.indent(
        tree,
        space="  "
    )

    try:
        save_xml(
            tree,
            target_file
        )

    except Exception as error:
        return build_cod_result(
            generated=False,
            cod_target=cod_target,
            target_file=target_file,
            changes=changes,
            warnings=warnings,
            errors=[
                "Unable to save COD target "
                f"POS file: {error}"
            ]
        )

    try:
        saved_tree = load_xml(
            target_file
        )

        post_save_errors = []

        post_save_errors.extend(
            validate_cod_routing(
                saved_tree,
                mapping_value,
                routing_value
            )
        )

        post_save_errors.extend(
            validate_cod_used_service(
                saved_tree,
                node_name,
                cod_config
            )
        )

    except Exception as error:
        return build_cod_result(
            generated=False,
            cod_target=cod_target,
            target_file=target_file,
            changes=changes,
            warnings=warnings,
            errors=[
                "Unable to validate saved COD "
                f"configuration: {error}"
            ]
        )

    post_save_errors = list(
        dict.fromkeys(
            post_save_errors
        )
    )

    if post_save_errors:
        return build_cod_result(
            generated=False,
            cod_target=cod_target,
            target_file=target_file,
            changes=changes,
            warnings=warnings,
            errors=post_save_errors
        )

    return build_cod_result(
        generated=True,
        cod_target=cod_target,
        target_file=target_file,
        changes=changes,
        warnings=warnings,
        errors=[]
    )

def ensure_cod_service(
    tree,
    cod_config
):
    """
    Cria ou atualiza:

    <Service
        name="0002"
        type="COD"
        classname="npCODNew.dll"
        startonload="true"
        quitOnFail="true">

        <Configuration imports="COD">
            <Section name="OperationMode">
                <Parameter
                    name="isHtmlUi"
                    value="true"/>
            </Section>
        </Configuration>

    </Service>
    """

    changes = []

    services_nodes = tree.xpath(
        "/PosDB/Services"
    )

    if not services_nodes:

        return {
            "changes": changes,
            "errors": [
                "Services node not found."
            ]
        }

    services = services_nodes[0]

    cod_services = tree.xpath(
        "/PosDB/Services/Service["
        "translate("
        "@type, "
        f"'{LOWERCASE}', "
        f"'{UPPERCASE}'"
        ")='COD'"
        "]"
    )

    service_created = False

    if cod_services:

        cod_service = cod_services[0]

    else:

        cod_service = etree.SubElement(
            services,
            "Service"
        )

        cod_service.set(
            "name",
            cod_config["service"]["name"]
        )

        cod_service.set(
            "type",
            cod_config["service"]["type"]
        )

        cod_service.set(
            "classname",
            cod_config["service"]["classname"]
        )

        cod_service.set(
            "startonload",
            str(
                cod_config["service"][
                    "startonload"
                ]
            ).lower()
        )

        cod_service.set(
            "quitOnFail",
            str(
                cod_config["service"][
                    "quitOnFail"
                ]
            ).lower()
        )

        service_created = True

        changes.append(
            "COD Service created"
        )

    configuration_nodes = (
        cod_service.xpath(
            "./Configuration"
        )
    )

    if configuration_nodes:

        configuration = (
            configuration_nodes[0]
        )

    else:

        configuration = etree.SubElement(
            cod_service,
            "Configuration"
        )

        configuration.set(
            "imports",
            "COD"
        )

        changes.append(
            "COD Configuration created"
        )

    operation_mode, created = (
        ensure_direct_section(
            configuration,
            "OperationMode"
        )
    )

    if created:

        changes.append(
            "COD OperationMode created"
        )

    result = set_direct_parameter(
        operation_mode,
        "isHtmlUi",
        "true"
    )

    if result["changed"]:

        action = (
            "created"
            if result["created"]
            else "updated"
        )

        changes.append(
            f"COD HTML UI {action}"
        )

    adaptor_result = (
        ensure_cod_adaptors(
            cod_service,
            cod_config
        )
    )

    changes.extend(
        adaptor_result[
            "changes"
        ]
    )

    ui_adaptor_result = (
        ensure_cod_ui_adaptor(
            cod_service,
            cod_config
        )
    )

    changes.extend(
        ui_adaptor_result[
            "changes"
        ]
    )

    errors = []

    errors.extend(
        adaptor_result.get(
            "errors",
            []
        )
    )

    errors.extend(
        ui_adaptor_result.get(
            "errors",
            []
        )
    )

    npw_result = ensure_cod_npw_service(
        tree=tree,
        cod_config=cod_config
    )

    changes.extend(
        npw_result.get(
            "changes",
            []
        )
    )

    errors.extend(
        npw_result.get(
            "errors",
            []
        )
    )

    changes = list(
        dict.fromkeys(changes)
    )

    errors = list(
        dict.fromkeys(errors)
    )

    return {
        "changes": changes,
        "errors": errors
    }


def ensure_cod_adaptors(
    cod_service,
    cod_config
):
    """
    Cria:

    npAdpCOD
    npAdpCodUpdt
    npAdpCodComm

    dentro do Service COD.
    """

    changes = []

    adaptors_nodes = (
        cod_service.xpath(
            "./Adaptors"
        )
    )

    if adaptors_nodes:

        adaptors = (
            adaptors_nodes[0]
        )

    else:

        adaptors = etree.SubElement(
            cod_service,
            "Adaptors"
        )

        changes.append(
            "COD Adaptors container created"
        )

    existing_adaptors = {}

    for adaptor in adaptors.xpath(
        "./Adaptor[@name]"
    ):

        existing_adaptors[
            adaptor.get("name")
        ] = adaptor

    adaptor_configs = [
        cod_config[
            "cod_adaptor"
        ],
        cod_config[
            "cod_update_adaptor"
        ],
        cod_config[
            "cod_comm_adaptor"
        ]
    ]

    for adaptor_config in adaptor_configs:

        adaptor_name = (
            adaptor_config["name"]
        )

        if adaptor_name in existing_adaptors:

            adaptor = (
                existing_adaptors[
                    adaptor_name
                ]
            )

        else:

            adaptor = etree.SubElement(
                adaptors,
                "Adaptor"
            )

            adaptor.set(
                "name",
                adaptor_name
            )

            changes.append(
                f"{adaptor_name} created"
            )

        adaptor.set(
            "imports",
            adaptor_config[
                "imports"
            ]
        )

        adaptor.set(
            "startonload",
            str(
                adaptor_config[
                    "startonload"
                ]
            ).lower()
        )

        if adaptor_name == "npAdpCOD":

            main_section, created = (
                ensure_direct_section(
                    adaptor,
                    "main"
                )
            )

            if created:

                changes.append(
                    "npAdpCOD main section created"
                )

            serial_result = (
                set_direct_parameter(
                    main_section,
                    "SerialPort",
                    adaptor_config[
                        "serial_port"
                    ]
                )
            )

            cod_type_result = (
                set_direct_parameter(
                    main_section,
                    "CODType",
                    adaptor_config[
                        "cod_type"
                    ]
                )
            )

            if serial_result["changed"]:

                changes.append(
                    "npAdpCOD "
                    "SerialPort configured"
                )

            if cod_type_result["changed"]:

                changes.append(
                    "npAdpCOD "
                    "CODType configured"
                )

    return {
        "changes": changes,
        "errors": []
    }

def ensure_cod_ui_adaptor(
    cod_service,
    cod_config
):
    """
    Cria ou atualiza o adaptor npAdpCodUI
    dentro do Service COD.

    Estrutura configurada:

    Adaptors
      Adaptor npAdpCodUI
        NGCODUnitSetting
        codHost
        main
        Generic
    """

    changes = []
    errors = []

    ui_config = cod_config.get(
        "cod_ui_adaptor",
        {}
    )

    if not ui_config:
        return {
            "changes": changes,
            "errors": [
                "cod_ui_adaptor configuration "
                "was not found."
            ]
        }

    adaptor_name = ui_config.get(
        "name",
        "npAdpCodUI"
    )

    adaptor_imports = ui_config.get(
        "imports",
        "npAdpCodUI"
    )

    adaptor_startonload = str(
        ui_config.get(
            "startonload",
            True
        )
    ).lower()

    adaptors_nodes = cod_service.xpath(
        "./Adaptors"
    )

    if adaptors_nodes:
        adaptors = adaptors_nodes[0]

    else:
        adaptors = etree.SubElement(
            cod_service,
            "Adaptors"
        )

        changes.append(
            "COD Adaptors container created"
        )

    cod_ui_adaptor = None

    for adaptor in adaptors.xpath(
        "./Adaptor"
    ):
        current_name = normalize_upper(
            adaptor.get("name")
        )

        current_imports = normalize_upper(
            adaptor.get("imports")
        )

        if (
            current_name
            == normalize_upper(adaptor_name)
            or current_imports
            == normalize_upper(adaptor_imports)
        ):
            cod_ui_adaptor = adaptor
            break

    if cod_ui_adaptor is None:
        cod_ui_adaptor = etree.SubElement(
            adaptors,
            "Adaptor"
        )

        changes.append(
            "npAdpCodUI created"
        )

    attribute_values = {
        "name": adaptor_name,
        "imports": adaptor_imports,
        "startonload": adaptor_startonload
    }

    for attribute_name, expected_value in (
        attribute_values.items()
    ):
        old_value = cod_ui_adaptor.get(
            attribute_name
        )

        if old_value == expected_value:
            continue

        cod_ui_adaptor.set(
            attribute_name,
            expected_value
        )

        changes.append(
            f"npAdpCodUI {attribute_name} "
            f"configured: "
            f"{old_value} -> {expected_value}"
        )

    ng_cod_setting, ng_created = (
        ensure_direct_section(
            cod_ui_adaptor,
            "NGCODUnitSetting"
        )
    )

    if ng_created:
        changes.append(
            "npAdpCodUI NGCODUnitSetting "
            "section created"
        )

    ng_parameters = {
        "OperationMode": ui_config.get(
            "operation_mode",
            "DT"
        ),
        "TCPSETTING": ui_config.get(
            "tcp_setting",
            "127.0.0.1:225"
        ),
        "PODType": ui_config.get(
            "pod_type",
            "DT"
        )
    }

    for parameter_name, expected_value in (
        ng_parameters.items()
    ):
        result = set_direct_parameter(
            ng_cod_setting,
            parameter_name,
            expected_value
        )

        if not result["changed"]:
            continue

        action = (
            "created"
            if result["created"]
            else "updated"
        )

        changes.append(
            f"npAdpCodUI {parameter_name} "
            f"{action}: "
            f"{result['old_value']} -> "
            f"{result['new_value']}"
        )

    cod_host, host_created = (
        ensure_direct_section(
            cod_ui_adaptor,
            "codHost"
        )
    )

    if host_created:
        changes.append(
            "npAdpCodUI codHost "
            "section created"
        )

    cod_host_config = cod_config.get(
        "cod_host",
        {}
    )

    host_parameters = {
        "address": cod_host_config.get(
            "address",
            "127.0.0.1"
        ),
        "aliveInterval": cod_host_config.get(
            "alive_interval",
            "20"
        ),
        "port": cod_host_config.get(
            "port",
            "225"
        ),
        "timeout": cod_host_config.get(
            "timeout",
            "15000"
        ),
        "version": cod_host_config.get(
            "version",
            "3"
        )
    }

    for parameter_name, expected_value in (
        host_parameters.items()
    ):
        result = set_direct_parameter(
            cod_host,
            parameter_name,
            expected_value
        )

        if not result["changed"]:
            continue

        action = (
            "created"
            if result["created"]
            else "updated"
        )

        changes.append(
            f"npAdpCodUI codHost "
            f"{parameter_name} {action}: "
            f"{result['old_value']} -> "
            f"{result['new_value']}"
        )

    main_section, main_created = (
        ensure_direct_section(
            cod_ui_adaptor,
            "main"
        )
    )

    if main_created:
        changes.append(
            "npAdpCodUI main section created"
        )

    main_parameters = {
        "adaptorname": "npAdpCodUI",
        "logicalname": "COD UI Adaptor",
        "orderformatterscript": (
            "CODViewFormatterJS@CODUI.nps"
        ),
        "service": "npAdpCodUI.dll"
    }

    for parameter_name, expected_value in (
        main_parameters.items()
    ):
        result = set_direct_parameter(
            main_section,
            parameter_name,
            expected_value
        )

        if not result["changed"]:
            continue

        action = (
            "created"
            if result["created"]
            else "updated"
        )

        changes.append(
            f"npAdpCodUI main "
            f"{parameter_name} {action}: "
            f"{result['old_value']} -> "
            f"{result['new_value']}"
        )

    generic_section, generic_created = (
        ensure_direct_section(
            cod_ui_adaptor,
            "Generic"
        )
    )

    if generic_created:
        changes.append(
            "npAdpCodUI Generic "
            "section created"
        )

    dump_result = set_direct_parameter(
        generic_section,
        "CODDumpEnabled",
        "true"
    )

    if dump_result["changed"]:
        action = (
            "created"
            if dump_result["created"]
            else "updated"
        )

        changes.append(
            "npAdpCodUI CODDumpEnabled "
            f"{action}: "
            f"{dump_result['old_value']} -> "
            f"{dump_result['new_value']}"
        )

    return {
        "changes": changes,
        "errors": errors
    }


def ensure_cod_npw_service(
    tree,
    cod_config
):
    """
    Cria ou atualiza o serviço NPW
    utilizado pelo COD HTML.
    """

    changes = []
    errors = []

    npw_config = cod_config.get(
        "npw",
        {}
    )

    services_nodes = tree.xpath(
        "/PosDB/Services"
    )

    if not services_nodes:

        return {
            "changes": [],
            "errors": [
                "Services node not found."
            ]
        }

    services = services_nodes[0]

    npw_service = None

    service_name = str(
        npw_config.get(
            "service_name",
            "102"
        )
    )

    for service in services.xpath(
        "./Service"
    ):

        if (
            service.get("type")
            == "NPW"
            and service.get("name")
            == service_name
        ):
            npw_service = service
            break

    if npw_service is None:

        npw_service = etree.SubElement(
            services,
            "Service"
        )

        changes.append(
            "COD NPW Service created"
        )

    npw_service.set(
        "name",
        service_name
    )

    npw_service.set(
        "type",
        "NPW"
    )

    npw_service.set(
        "classname",
        ""
    )

    npw_service.set(
        "startonload",
        "true"
    )

    npw_service.set(
        "quitOnFail",
        "true"
    )

    configuration_nodes = (
        npw_service.xpath(
            "./Configuration"
        )
    )

    if configuration_nodes:

        configuration = (
            configuration_nodes[0]
        )

    else:

        configuration = etree.SubElement(
            npw_service,
            "Configuration"
        )

        changes.append(
            "COD NPW Configuration created"
        )

    if (
        configuration.get("imports")
        != "LocalWebView"
    ):
        configuration.set(
            "imports",
            "LocalWebView"
        )

        changes.append(
            "COD NPW Configuration imports updated"
        )

    #
    # BaseHosts
    #

    base_hosts, created = (
        ensure_direct_section(
            configuration,
            "BaseHosts"
        )
    )

    if created:
        changes.append(
            "COD NPW BaseHosts created"
        )

    set_direct_parameter(
        base_hosts,
        "Urls",
        "http://127.0.0.1:8123/npsharp"
    )

    #
    # LocalWebView
    #

    local_webview, created = (
        ensure_direct_section(
            configuration,
            "LocalWebView"
        )
    )

    if created:
        changes.append(
            "COD NPW LocalWebView created"
        )

    set_direct_parameter(
        local_webview,
        "Location",
        "../npwebview"
    )

    #
    # Log
    #

    log_section, created = (
        ensure_direct_section(
            configuration,
            "Log"
        )
    )

    if created:
        changes.append(
            "COD NPW Log section created"
        )

    set_direct_parameter(
        log_section,
        "EnableDebug",
        "true"
    )

    set_direct_parameter(
        log_section,
        "LogFileFolder",
        "out/"
    )

    #
    # AutoUpdate
    #

    auto_update, created = (
        ensure_direct_section(
            configuration,
            "AutoUpdate"
        )
    )

    if created:
        changes.append(
            "COD NPW AutoUpdate created"
        )

    set_direct_parameter(
        auto_update,
        "EnableAutoUpdate",
        "false"
    )

    #
    # Monitoring
    #

    monitoring, created = (
        ensure_direct_section(
            configuration,
            "Monitoring"
        )
    )

    if created:
        changes.append(
            "COD NPW Monitoring created"
        )

    set_direct_parameter(
        monitoring,
        "MonitorInterval",
        "60000"
    )

    #
    # Monitoring.Memory
    #

    monitoring_memory, created = (
        ensure_direct_section(
            configuration,
            "Monitoring.Memory"
        )
    )

    if created:
        changes.append(
            "COD NPW Monitoring.Memory created"
        )

    set_direct_parameter(
        monitoring_memory,
        "MaxMemoryPercentage",
        "80"
    )

    set_direct_parameter(
        monitoring_memory,
        "LauncherLimit",
        "200"
    )

    set_direct_parameter(
        monitoring_memory,
        "BrowserLimit",
        "1500"
    )

    set_direct_parameter(
        monitoring_memory,
        "DriverHostLimit",
        "1500"
    )

    #
    # Browser POS
    #

    browser_pos, created = (
        ensure_direct_section(
            configuration,
            "Component.Browser.POS"
        )
    )

    if created:
        changes.append(
            "COD NPW Browser created"
        )

    browser_parameters = {
        "Position": "800,0",
        "Urn": "COD/COD0002",
        "ShowCursor": "true",
        "ShowFrame": "true",
        "showCloseButton": "true",
        "showMinimizeButton": "true",
        "showMaximizeButton": "true",
        "allowResize": "true",
        "windowMaximized": "false",
        "canMoveWindow": "true",
        "AutoFocus": "false",
        "Size": "800x600"
    }

    for parameter_name, parameter_value in (
        browser_parameters.items()
    ):

        result = set_direct_parameter(
            browser_pos,
            parameter_name,
            parameter_value
        )

        if result["changed"]:

            action = (
                "created"
                if result["created"]
                else "updated"
            )

            changes.append(
                f"COD NPW Browser "
                f"{parameter_name} "
                f"{action}: "
                f"{result['old_value']} -> "
                f"{result['new_value']}"
            )

    return {
        "changes": changes,
        "errors": errors
    }

def ensure_store_cod_routing(
    tree,
    cod_config
):
    """
    Cria ou atualiza:

    <Configuration>
        <Section name="CODRouting">
            <Parameter
                name="Mapping"
                value="COD0001=1|COD0002=2"/>

            <Parameter
                name="Routing"
                value="POS0004=DCOD0002|..."/>
        </Section>
    </Configuration>

    dentro do store-db.xml.
    """

    changes = []
    errors = []

    routing_config = cod_config.get(
        "routing",
        {}
    )

    mapping_value = routing_config.get(
        "mapping"
    )

    routes = routing_config.get(
        "routes",
        {}
    )

    if not mapping_value:

        return {
            "changes": changes,
            "errors": [
                "Store COD Mapping "
                "was not configured."
            ]
        }

    if not routes:

        return {
            "changes": changes,
            "errors": [
                "Store COD Routing "
                "was not configured."
            ]
        }

    try:

        routing_value = (
            build_routing_value(
                routes
            )
        )

    except ValueError as error:

        return {
            "changes": changes,
            "errors": [
                str(error)
            ]
        }

    #
    # Localiza StoreDB
    #

    store_nodes = tree.xpath(
        "/Document/StoreDB"
    )

    if not store_nodes:

        return {
            "changes": [],
            "errors": [
                "StoreDB node was not found."
            ]
        }

    store_db = store_nodes[0]

    #
    # Localiza Configuration
    #

    configuration_nodes = (
        store_db.xpath(
            "./Configuration"
        )
    )

    if configuration_nodes:

        configuration = (
            configuration_nodes[0]
        )

    else:

        configuration = etree.SubElement(
            store_db,
            "Configuration"
        )

        changes.append(
            "Store Configuration created"
        )

    #
    # CODRouting
    #

    cod_routing, created = (
        ensure_direct_section(
            configuration,
            "CODRouting"
        )
    )

    if created:

        changes.append(
            "Store CODRouting created"
        )

    #
    # Mapping
    #

    mapping_result = (
        set_direct_parameter(
            cod_routing,
            "Mapping",
            mapping_value
        )
    )

    if mapping_result["changed"]:

        action = (
            "created"
            if mapping_result["created"]
            else "updated"
        )

        changes.append(
            "Store COD Mapping "
            f"{action}: "
            f"{mapping_result['old_value']} -> "
            f"{mapping_result['new_value']}"
        )

    else:

        changes.append(
            "Store COD Mapping "
            "already correct"
        )

    #
    # Routing
    #

    routing_result = (
        set_direct_parameter(
            cod_routing,
            "Routing",
            routing_value
        )
    )

    if routing_result["changed"]:

        action = (
            "created"
            if routing_result["created"]
            else "updated"
        )

        changes.append(
            "Store COD Routing "
            f"{action}: "
            f"{routing_result['old_value']} -> "
            f"{routing_result['new_value']}"
        )

    else:

        changes.append(
            "Store COD Routing "
            "already correct"
        )

    return {
        "changes": changes,
        "errors": errors
    }

def build_store_cod_result(
    generated,
    target_file=None,
    changes=None,
    warnings=None,
    errors=None
):
    return {
        "generated": generated,
        "file": (
            str(target_file)
            if target_file is not None
            else None
        ),
        "changes": changes or [],
        "warnings": warnings or [],
        "errors": errors or []
    }

def generate_store_cod_file(
    cod_target,
    store_file="output/store-db.xml"
):
    """
    Aplica e valida a configuração CODRouting
    no arquivo output/store-db.xml.

    Fluxo:
        1. Valida se o COD está habilitado.
        2. Valida se o alvo COD foi descoberto.
        3. Carrega o store-db.xml.
        4. Cria ou atualiza CODRouting.
        5. Valida antes de salvar.
        6. Salva o arquivo.
        7. Recarrega e valida novamente.
    """

    changes = []
    warnings = []
    errors = []

    if not cod_target.get(
        "enabled",
        False
    ):
        return build_store_cod_result(
            generated=False,
            errors=[
                "COD is disabled."
            ]
        )

    if not cod_target.get(
        "found",
        False
    ):
        return build_store_cod_result(
            generated=False,
            warnings=cod_target.get(
                "warnings",
                []
            ),
            errors=cod_target.get(
                "errors",
                [
                    "COD target was not resolved."
                ]
            )
        )

    cod_config = cod_target.get(
        "config",
        {}
    )

    if not cod_config:
        return build_store_cod_result(
            generated=False,
            errors=[
                "COD configuration was not found."
            ]
        )

    target_file = Path(
        store_file
    )

    if not target_file.exists():
        return build_store_cod_result(
            generated=False,
            target_file=target_file,
            errors=[
                "StoreDB file was not found: "
                f"{target_file}"
            ]
        )

    try:
        tree = load_xml(
            target_file
        )

    except Exception as error:
        return build_store_cod_result(
            generated=False,
            target_file=target_file,
            errors=[
                "Unable to load StoreDB file: "
                f"{error}"
            ]
        )

    store_result = (
        ensure_store_cod_routing(
            tree,
            cod_config
        )
    )

    changes.extend(
        store_result.get(
            "changes",
            []
        )
    )

    errors.extend(
        store_result.get(
            "errors",
            []
        )
    )

    pre_save_errors = (
        validate_store_cod_routing(
            tree,
            cod_config
        )
    )

    errors.extend(
        pre_save_errors
    )

    changes = list(
        dict.fromkeys(changes)
    )

    warnings = list(
        dict.fromkeys(warnings)
    )

    errors = list(
        dict.fromkeys(errors)
    )

    if errors:
        return build_store_cod_result(
            generated=False,
            target_file=target_file,
            changes=changes,
            warnings=warnings,
            errors=errors
        )

    etree.indent(
        tree,
        space="  "
    )

    try:
        save_xml(
            tree,
            target_file
        )

    except Exception as error:
        return build_store_cod_result(
            generated=False,
            target_file=target_file,
            changes=changes,
            warnings=warnings,
            errors=[
                "Unable to save StoreDB file: "
                f"{error}"
            ]
        )

    try:
        saved_tree = load_xml(
            target_file
        )

    except Exception as error:
        return build_store_cod_result(
            generated=False,
            target_file=target_file,
            changes=changes,
            warnings=warnings,
            errors=[
                "Unable to reload saved "
                f"StoreDB file: {error}"
            ]
        )

    post_save_errors = (
        validate_store_cod_routing(
            saved_tree,
            cod_config
        )
    )

    post_save_errors = list(
        dict.fromkeys(
            post_save_errors
        )
    )

    if post_save_errors:
        return build_store_cod_result(
            generated=False,
            target_file=target_file,
            changes=changes,
            warnings=warnings,
            errors=post_save_errors
        )

    return build_store_cod_result(
        generated=True,
        target_file=target_file,
        changes=changes,
        warnings=warnings,
        errors=[]
    )

def validate_store_cod_routing(
    tree,
    cod_config
):
    """
    Valida a configuração CODRouting
    dentro do store-db.xml.
    """

    errors = []

    routing_config = cod_config.get(
        "routing",
        {}
    )

    mapping_value = routing_config.get(
        "mapping"
    )

    routes = routing_config.get(
        "routes",
        {}
    )

    if not mapping_value:
        return [
            "Store COD Mapping "
            "was not configured."
        ]

    if not routes:
        return [
            "Store COD Routing "
            "was not configured."
        ]

    try:

        routing_value = (
            build_routing_value(
                routes
            )
        )

    except ValueError as error:

        return [
            str(error)
        ]

    #
    # StoreDB
    #

    store_nodes = tree.xpath(
        "/Document/StoreDB"
    )

    if not store_nodes:

        return [
            "StoreDB node was not found."
        ]

    store_db = store_nodes[0]

    #
    # Configuration
    #

    configuration_nodes = (
        store_db.xpath(
            "./Configuration"
        )
    )

    if not configuration_nodes:

        return [
            "Store Configuration "
            "was not found."
        ]

    configuration = (
        configuration_nodes[0]
    )

    #
    # CODRouting
    #

    cod_routing = (
        get_direct_section(
            configuration,
            "CODRouting"
        )
    )

    if cod_routing is None:

        return [
            "Store CODRouting "
            "section was not found."
        ]

    #
    # Mapping
    #

    mapping_parameter = (
        get_direct_parameter(
            cod_routing,
            "Mapping"
        )
    )

    if mapping_parameter is None:

        errors.append(
            "Store COD Mapping "
            "parameter was not found."
        )

    else:

        actual_mapping = (
            mapping_parameter.get(
                "value"
            )
        )

        if actual_mapping != mapping_value:

            errors.append(
                "Store COD Mapping "
                "has an unexpected value. "
                f"Expected '{mapping_value}', "
                f"found '{actual_mapping}'."
            )

    #
    # Routing
    #

    routing_parameter = (
        get_direct_parameter(
            cod_routing,
            "Routing"
        )
    )

    if routing_parameter is None:

        errors.append(
            "Store COD Routing "
            "parameter was not found."
        )

    else:

        actual_routing = (
            routing_parameter.get(
                "value"
            )
        )

        if actual_routing != routing_value:

            errors.append(
                "Store COD Routing "
                "has an unexpected value. "
                f"Expected '{routing_value}', "
                f"found '{actual_routing}'."
            )

    return errors

def validate_cod_complete(
    output_folder="output/pos",
    store_file="output/store-db.xml"
):
    """
    Executa todas as validações de COD disponíveis.
    """

    results = {
        "status": "PASS",
        "changes": [],
        "issues": []
    }

    validations = [
        validate_cod_service(
            output_folder=output_folder
        ),
        validate_cod_adaptors(
            output_folder=output_folder
        ),
        validate_cod_npw_service(
            output_folder=output_folder
        ),
        validate_store_cod_routing(
            store_file=store_file
        )
    ]

    for validation in validations:

        if not validation:
            continue

        results["changes"].extend(
            validation.get("changes", [])
        )

        results["issues"].extend(
            validation.get("issues", [])
        )

    if results["issues"]:
        results["status"] = "FAIL"

    return results

# ============================================================================
# COD HEALTH CHECK
# ============================================================================

    print()
    print("COD HEALTH CHECK")
    print("-" * 50)

    validate_cod_complete(
        output_folder="output",
        config_path="config/rio_lab.json",
        pos_machine_lookup=pos_machine_lookup
    )





