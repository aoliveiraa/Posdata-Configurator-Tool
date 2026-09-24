from lxml import etree


LOWERCASE = "abcdefghijklmnopqrstuvwxyz"
UPPERCASE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def normalize_service_id(value):
    """
    Normaliza o ID de um serviço KVS.

    Exemplos:
        0201 -> 0201
        KVS0201 -> 0201
        kvs0201 -> 0201
    """

    if value is None:
        return None

    normalized = str(value).strip().upper()

    if normalized.startswith("KVS"):
        normalized = normalized[3:]

    return normalized


def find_direct_services(tree, service_type):
    """
    Encontra apenas Services que sejam filhos diretos
    de /PosDB/Services.
    """

    expected_type = service_type.upper()

    return tree.xpath(
        "/PosDB/Services/Service[translate("
        "@type, "
        f"'{LOWERCASE}', "
        f"'{UPPERCASE}'"
        f")='{expected_type}']"
    )


def find_parameter(parent, parameter_name):
    """
    Procura um Parameter pelo atributo name,
    ignorando diferenças de maiúsculas e minúsculas.
    """

    expected_name = parameter_name.strip().lower()

    for parameter in parent.xpath(
        "./Parameter[@name]"
    ):
        current_name = (
            parameter.get("name", "")
            .strip()
            .lower()
        )

        if current_name == expected_name:
            return parameter

    return None


def set_parameter(
    parent,
    parameter_name,
    parameter_value
):
    """
    Cria ou atualiza um Parameter diretamente
    dentro do elemento informado.
    """

    parameter = find_parameter(
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
        old_value = parameter.get("value")

    parameter.set(
        "value",
        str(parameter_value)
    )

    return {
        "created": created,
        "old_value": old_value,
        "new_value": str(parameter_value)
    }


def get_section(parent, section_name):
    """
    Procura uma Section dentro do elemento informado,
    ignorando diferenças de maiúsculas e minúsculas.
    """

    expected_name = section_name.strip().upper()

    for section in parent.xpath(
        "./Section[@name]"
    ):
        current_name = (
            section.get("name", "")
            .strip()
            .upper()
        )

        if current_name == expected_name:
            return section

    return None


def get_direct_configuration(service):
    """
    Retorna a Configuration diretamente dentro
    de um Service.
    """

    configurations = service.xpath(
        "./Configuration"
    )

    if not configurations:
        return None

    return configurations[0]


def ensure_touchscreen_enabled(kvs_service):
    """
    Garante que o serviço KVS possua:

    <Section name="Touchscreen">
        <Parameter name="enable" value="true"/>
        <Parameter name="available" value="true"/>
    </Section>

    A função não depende de nenhum template externo.
    """

    configuration = get_direct_configuration(
        kvs_service
    )

    if configuration is None:
        return {
            "updated": False,
            "created_section": False,
            "error": (
                "KVS service does not contain "
                "a Configuration element."
            )
        }

    touchscreen = get_section(
        configuration,
        "Touchscreen"
    )

    created_section = False

    if touchscreen is None:
        touchscreen = etree.SubElement(
            configuration,
            "Section"
        )

        touchscreen.set(
            "name",
            "Touchscreen"
        )

        created_section = True

    enable_result = set_parameter(
        touchscreen,
        "enable",
        "true"
    )

    available_result = set_parameter(
        touchscreen,
        "available",
        "true"
    )

    return {
        "updated": True,
        "created_section": created_section,
        "enable": enable_result,
        "available": available_result,
        "error": None
    }


def disable_bumpbar_adaptors(kvs_service):
    """
    Configura startonload=false em qualquer adaptor
    relacionado a Bumpbar dentro do serviço KVS.
    """

    changes = []

    adaptors = kvs_service.xpath(
        "./Adaptors/Adaptor"
    )

    for adaptor in adaptors:
        adaptor_name = (
            adaptor.get("name", "")
            .strip()
            .upper()
        )

        imports_name = (
            adaptor.get("imports", "")
            .strip()
            .upper()
        )

        if (
            "BUMPBAR" not in adaptor_name
            and "BUMPBAR" not in imports_name
        ):
            continue

        old_value = adaptor.get(
            "startonload"
        )

        adaptor.set(
            "startonload",
            "false"
        )

        changes.append({
            "adaptor": (
                adaptor.get("name")
                or adaptor.get("imports")
                or "UNKNOWN"
            ),
            "old_value": old_value,
            "new_value": "false"
        })

    return changes


def get_npw_service(tree):
    """
    Retorna a primeira NPW que seja filha direta
    de /PosDB/Services.
    """

    npw_services = find_direct_services(
        tree,
        "NPW"
    )

    if not npw_services:
        return None

    return npw_services[0]


def ensure_section(
    configuration,
    section_name
):
    """
    Localiza ou cria uma Section diretamente
    dentro de Configuration.
    """

    section = get_section(
        configuration,
        section_name
    )

    created = False

    if section is None:
        section = etree.SubElement(
            configuration,
            "Section"
        )

        section.set(
            "name",
            section_name
        )

        created = True

    return section, created


def configure_auto_update(npw_service):
    """
    Garante EnableAutoUpdate=true na NPW.
    """

    configuration = get_direct_configuration(
        npw_service
    )

    if configuration is None:
        raise ValueError(
            "NPW service does not contain "
            "a Configuration element."
        )

    auto_update, created_section = (
        ensure_section(
            configuration,
            "AutoUpdate"
        )
    )

    result = set_parameter(
        auto_update,
        "EnableAutoUpdate",
        "true"
    )

    result["created_section"] = (
        created_section
    )

    return result


def ensure_local_webview(
    npw_service,
):
    """
    Guarantees LocalWebView configuration
    required by KVS Performance validation.
    """

    configuration = get_direct_configuration(
        npw_service
    )

    if configuration is None:

        return {
            "updated": False,
            "created_section": False,
            "created_parameter": False,
            "error": (
                "NPW service does not contain "
                "a Configuration element."
            ),
        }

    current_imports = (
        configuration.get(
            "imports",
            ""
        )
        .strip()
    )

    if not current_imports:

        configuration.set(
            "imports",
            "LocalWebView",
        )

    elif (
        "LOCALWEBVIEW"
        not in current_imports.upper()
    ):

        imports = [
            value.strip()
            for value in (
                current_imports
                .replace(";", ",")
                .split(",")
            )
            if value.strip()
        ]

        imports.append(
            "LocalWebView"
        )

        configuration.set(
            "imports",
            ",".join(
                dict.fromkeys(
                    imports
                )
            )
        )

    local_webview, created_section = (
        ensure_section(
            configuration,
            "LocalWebView",
        )
    )

    location_result = set_parameter(
        local_webview,
        "Location",
        "../NpWebView",
    )

    return {
        "updated": True,
        "created_section": (
            created_section
        ),
        "created_parameter": (
            location_result[
                "created"
            ]
        ),
        "old_value": (
            location_result[
                "old_value"
            ]
        ),
        "new_value": (
            location_result[
                "new_value"
            ]
        ),
        "error": None,
    }


def browser_section_for_service(
    npw_service,
    service_id
):
    """
    Localiza:
    Component.Browser.KVSxxxx
    para o serviço informado.
    """

    expected_name = (
        f"COMPONENT.BROWSER.KVS{service_id}"
    ).upper()

    configuration = get_direct_configuration(
        npw_service
    )

    if configuration is None:
        return None

    for section in configuration.xpath(
        "./Section[@name]"
    ):
        section_name = (
            section.get("name", "")
            .strip()
            .upper()
        )

        if section_name == expected_name:
            return section

    return None


def configure_browser_section(
    browser_section,
    service_id
):
    """
    Aplica as configurações obrigatórias
    do Performance Coordinator.
    """

    node_name = f"KVS{service_id}"

    changes = {}

    changes["BrowserServer"] = set_parameter(
        browser_section,
        "BrowserServer",
        "messagehub"
    )

    changes["NodeName"] = set_parameter(
        browser_section,
        "NodeName",
        node_name
    )

    changes["LogicalName"] = set_parameter(
        browser_section,
        "LogicalName",
        node_name
    )

    changes["InjectJavascriptCode"] = (
        set_parameter(
            browser_section,
            "InjectJavascriptCode",
            (
                "ClickPOSButtonHelper,"
                "MessageHubResponseHelper"
            )
        )
    )

    changes["Urn"] = set_parameter(
        browser_section,
        "Urn",
        f"KVS/{node_name}"
    )

    return changes


def remove_physical_driver_sections(
    npw_service
):
    """
    Remove configurações físicas da NPW.

    Regras atuais:
        Component.DriverHost.BUMPBAR*
        Component.DriverHost.Printer*
    """

    removed_sections = []

    configuration = get_direct_configuration(
        npw_service
    )

    if configuration is None:
        return removed_sections

    sections = list(
        configuration.xpath(
            "./Section[@name]"
        )
    )

    blocked_patterns = (
        "COMPONENT.DRIVERHOST.BUMPBAR",
        "COMPONENT.DRIVERHOST.PRINTER"
    )

    for section in sections:
        section_name = (
            section.get("name", "")
            .strip()
            .upper()
        )

        if not any(
            section_name.startswith(pattern)
            for pattern in blocked_patterns
        ):
            continue

        removed_sections.append(
            section.get("name")
        )

        configuration.remove(section)

    return removed_sections


def validate_performance_itona(tree):
    """
    Valida a configuração final da Itona.
    """

    errors = []
    warnings = []

    kvs_services = find_direct_services(
        tree,
        "KVS"
    )

    npw_services = find_direct_services(
        tree,
        "NPW"
    )

    if not kvs_services:
        errors.append(
            "No direct KVS service was found."
        )

    if not npw_services:
        errors.append(
            "No direct NPW service was found."
        )

        return {
            "errors": errors,
            "warnings": warnings
        }

    if len(npw_services) > 1:
        errors.append(
            "More than one direct NPW service "
            "was found."
        )

    npw_service = npw_services[0]

    auto_update_configuration = (
        get_direct_configuration(
            npw_service
        )
    )

    if auto_update_configuration is None:
        errors.append(
            "NPW does not contain Configuration."
        )

        return {
            "errors": errors,
            "warnings": warnings
        }

    auto_update_section = get_section(
        auto_update_configuration,
        "AutoUpdate"
    )

    if auto_update_section is None:
        errors.append(
            "AutoUpdate section was not found."
        )

    else:
        auto_update_parameter = find_parameter(
            auto_update_section,
            "EnableAutoUpdate"
        )

        if auto_update_parameter is None:
            errors.append(
                "EnableAutoUpdate was not found."
            )

        elif (
            auto_update_parameter.get(
                "value",
                ""
            ).strip().lower()
            != "true"
        ):
            errors.append(
                "EnableAutoUpdate is not true."
            )

    for kvs_service in kvs_services:
        service_id = normalize_service_id(
            kvs_service.get("name")
        )

        if not service_id:
            errors.append(
                "A KVS service has no name."
            )

            continue

        if (
            kvs_service.get(
                "startonload",
                ""
            ).strip().lower()
            != "true"
        ):
            warnings.append(
                f"KVS{service_id} is not active."
            )

        configuration = (
            get_direct_configuration(
                kvs_service
            )
        )

        if configuration is None:
            errors.append(
                f"KVS{service_id} does not "
                "contain Configuration."
            )

            continue

        touchscreen = get_section(
            configuration,
            "Touchscreen"
        )

        if touchscreen is None:
            errors.append(
                f"KVS{service_id} does not "
                "contain Touchscreen."
            )

        else:
            enable_parameter = find_parameter(
                touchscreen,
                "enable"
            )

            available_parameter = find_parameter(
                touchscreen,
                "available"
            )

            if (
                enable_parameter is None
                or enable_parameter.get(
                    "value",
                    ""
                ).strip().lower()
                != "true"
            ):
                errors.append(
                    f"KVS{service_id} Touchscreen "
                    "enable is not true."
                )

            if (
                available_parameter is None
                or available_parameter.get(
                    "value",
                    ""
                ).strip().lower()
                != "true"
            ):
                errors.append(
                    f"KVS{service_id} Touchscreen "
                    "available is not true."
                )

        bumpbar_adaptors = (
            kvs_service.xpath(
                "./Adaptors/Adaptor["
                "contains(translate("
                "@name, "
                f"'{LOWERCASE}', "
                f"'{UPPERCASE}'"
                "), 'BUMPBAR') "
                "or contains(translate("
                "@imports, "
                f"'{LOWERCASE}', "
                f"'{UPPERCASE}'"
                "), 'BUMPBAR')"
                "]"
            )
        )

        for adaptor in bumpbar_adaptors:
            if (
                adaptor.get(
                    "startonload",
                    ""
                ).strip().lower()
                != "false"
            ):
                errors.append(
                    f"KVS{service_id} has an active "
                    "Bumpbar adaptor."
                )

        browser_section = (
            browser_section_for_service(
                npw_service,
                service_id
            )
        )

        if browser_section is None:
            errors.append(
                "Browser section was not found "
                f"for KVS{service_id}."
            )

            continue

        expected_values = {
            "BrowserServer": "messagehub",
            "NodeName": f"KVS{service_id}",
            "LogicalName": f"KVS{service_id}",
            "InjectJavascriptCode": (
                "ClickPOSButtonHelper,"
                "MessageHubResponseHelper"
            ),
            "Urn": f"KVS/KVS{service_id}"
        }

        for parameter_name, expected_value in (
            expected_values.items()
        ):
            parameter = find_parameter(
                browser_section,
                parameter_name
            )

            if parameter is None:
                errors.append(
                    f"{parameter_name} was not "
                    f"found for KVS{service_id}."
                )

                continue

            actual_value = parameter.get(
                "value",
                ""
            )

            if actual_value != expected_value:
                errors.append(
                    f"{parameter_name} has an "
                    f"unexpected value for "
                    f"KVS{service_id}. "
                    f"Expected '{expected_value}', "
                    f"found '{actual_value}'."
                )

    physical_sections = []

    for section in (
        auto_update_configuration.xpath(
            "./Section[@name]"
        )
    ):
        section_name = (
            section.get("name", "")
            .strip()
            .upper()
        )

        if (
            section_name.startswith(
                "COMPONENT.DRIVERHOST.BUMPBAR"
            )
            or section_name.startswith(
                "COMPONENT.DRIVERHOST.PRINTER"
            )
        ):
            physical_sections.append(
                section.get("name")
            )

    if physical_sections:
        errors.append(
            "Physical DriverHost sections remain: "
            + ", ".join(
                physical_sections
            )
        )

    nested_services = tree.xpath(
        "/PosDB/Services/Service//Service"
    )

    if nested_services:
        errors.append(
            "Nested Service elements were found."
        )

    errors = list(dict.fromkeys(errors))
    warnings = list(dict.fromkeys(warnings))

    return {
        "errors": errors,
        "warnings": warnings
    }


def apply_performance_kvs_configuration(
    generated_tree,
    reference_itona_path=None
):
    """
    Aplica a configuração Performance em uma Itona.

    reference_itona_path permanece como parâmetro
    opcional apenas para manter compatibilidade com
    o kvs_transformer.py atual.

    A configuração do Touchscreen não depende mais
    da Itona de referência.
    """

    changes = []
    warnings = []
    errors = []

    kvs_services = find_direct_services(
        generated_tree,
        "KVS"
    )

    if not kvs_services:
        return {
            "updated": False,
            "changes": [],
            "warnings": [],
            "errors": [
                "No direct KVS service was found."
            ]
        }

    for kvs_service in kvs_services:
        service_id = normalize_service_id(
            kvs_service.get("name")
        )

        if not service_id:
            errors.append(
                "A KVS service has no valid name."
            )

            continue

        touchscreen_result = (
            ensure_touchscreen_enabled(
                kvs_service
            )
        )

        if touchscreen_result["updated"]:
            if touchscreen_result[
                "created_section"
            ]:
                changes.append(
                    "Touchscreen section created "
                    f"for KVS{service_id}."
                )
            else:
                changes.append(
                    "Touchscreen section updated "
                    f"for KVS{service_id}."
                )

            changes.append(
                "Touchscreen enable=true and "
                f"available=true for KVS{service_id}."
            )

        else:
            errors.append(
                f"KVS{service_id}: "
                + touchscreen_result["error"]
            )

        disabled_adaptors = (
            disable_bumpbar_adaptors(
                kvs_service
            )
        )

        for adaptor in disabled_adaptors:
            changes.append(
                f"{adaptor['adaptor']} disabled "
                f"for KVS{service_id}."
            )

        npw_service = get_npw_service(
            generated_tree
        )

        if npw_service is None:

            errors.append(
                "NPW service was not found."
            )

        else:

            #
            # LocalWebView
            #
            local_webview_result = (
                ensure_local_webview(
                    npw_service
                )
            )

            if not local_webview_result[
                "updated"
            ]:

                errors.append(
                    local_webview_result[
                        "error"
                    ]
                )

            else:

                if local_webview_result[
                    "created_section"
                ]:

                    changes.append(
                        "LocalWebView section created in NPW."
                    )

                elif local_webview_result[
                    "created_parameter"
                ]:

                    changes.append(
                        "LocalWebView Location parameter created in NPW."
                    )

                else:

                    changes.append(
                        "LocalWebView configuration validated in NPW."
                    )

            #
            # AutoUpdate
            #
            try:

                auto_update_result = (
                    configure_auto_update(
                        npw_service
                    )
                )

                if auto_update_result[
                    "created_section"
                ]:

                    changes.append(
                        "AutoUpdate section created."
                    )

                changes.append(
                    "EnableAutoUpdate set to true."
                )

            except ValueError as error:

                errors.append(
                    str(error)
                )
        removed_sections = (
            remove_physical_driver_sections(
                npw_service
            )
        )

        for section_name in removed_sections:
            changes.append(
                "Physical section removed: "
                f"{section_name}."
            )

        for kvs_service in kvs_services:
            service_id = normalize_service_id(
                kvs_service.get("name")
            )

            if not service_id:
                continue

            browser_section = (
                browser_section_for_service(
                    npw_service,
                    service_id
                )
            )

            if browser_section is None:
                errors.append(
                    "Browser section not found for "
                    f"KVS{service_id}."
                )

                continue

            configure_browser_section(
                browser_section,
                service_id
            )

            changes.append(
                "Coordinator configured in "
                f"Component.Browser.KVS{service_id}."
            )

    validation = validate_performance_itona(
        generated_tree
    )

    errors.extend(
        validation["errors"]
    )

    warnings.extend(
        validation["warnings"]
    )

    errors = list(dict.fromkeys(errors))
    warnings = list(dict.fromkeys(warnings))
    changes = list(dict.fromkeys(changes))

    return {
        "updated": not errors,
        "changes": changes,
        "warnings": warnings,
        "errors": errors
    }