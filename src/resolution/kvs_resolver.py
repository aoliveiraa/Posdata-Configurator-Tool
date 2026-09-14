def _normalize_service_id(
    service_id,
):
    """
    Normaliza um identificador KVS.

    Exemplos:
        0501 -> 0501
        KVS0501 -> 0501
        kvs0501 -> 0501
    """

    if service_id is None:
        return None

    normalized = str(
        service_id
    ).strip().upper()

    if normalized.startswith(
        "KVS"
    ):
        normalized = normalized[3:]

    return normalized or None


def _build_services_by_id(
    kvs_mapping,
):
    """
    Cria um índice dos serviços descobertos.

    Exemplo:

    {
        "0501": [
            {
                "service": "0501",
                "source_file": "_KVS0501_pos-db.xml",
                "startonload": True
            }
        ]
    }
    """

    services_by_id = {}

    for item in kvs_mapping.get(
        "discovered_services",
        []
    ):
        service_id = (
            _normalize_service_id(
                item.get(
                    "service"
                )
            )
        )

        if not service_id:
            continue

        services_by_id.setdefault(
            service_id,
            []
        ).append({
            "service": service_id,
            "source_file": item.get(
                "source_file"
            ),
            "startonload": bool(
                item.get(
                    "startonload",
                    False
                )
            )
        })

    return services_by_id


def _normalize_candidate(
    candidate,
    services_by_id,
):
    """
    Aceita candidatos nos dois formatos:

    Formato simples:
        "0501"

    Formato enriquecido:
        {
            "service": "0501",
            "source_file": "_KVS0501_pos-db.xml",
            "startonload": True
        }

    Retorna sempre um dicionário padronizado.
    """

    if isinstance(
        candidate,
        dict
    ):
        service_id = (
            _normalize_service_id(
                candidate.get(
                    "service"
                )
            )
        )

        if not service_id:
            return None

        source_file = candidate.get(
            "source_file"
        )

        startonload = bool(
            candidate.get(
                "startonload",
                False
            )
        )

        if not source_file:
            discovered_matches = (
                services_by_id.get(
                    service_id,
                    []
                )
            )

            if discovered_matches:
                active_matches = [
                    item
                    for item in discovered_matches
                    if item.get(
                        "startonload",
                        False
                    )
                ]

                selected_match = (
                    active_matches[0]
                    if active_matches
                    else discovered_matches[0]
                )

                source_file = (
                    selected_match.get(
                        "source_file"
                    )
                )

                startonload = bool(
                    selected_match.get(
                        "startonload",
                        False
                    )
                )

        return {
            "service": service_id,
            "source_file": source_file,
            "startonload": startonload
        }

    service_id = (
        _normalize_service_id(
            candidate
        )
    )

    if not service_id:
        return None

    discovered_matches = (
        services_by_id.get(
            service_id,
            []
        )
    )

    if not discovered_matches:
        return {
            "service": service_id,
            "source_file": None,
            "startonload": False
        }

    active_matches = [
        item
        for item in discovered_matches
        if item.get(
            "startonload",
            False
        )
    ]

    selected_match = (
        active_matches[0]
        if active_matches
        else discovered_matches[0]
    )

    return {
        "service": service_id,
        "source_file": (
            selected_match.get(
                "source_file"
            )
        ),
        "startonload": bool(
            selected_match.get(
                "startonload",
                False
            )
        )
    }


def _prepare_candidates(
    raw_candidates,
    services_by_id,
):
    """
    Normaliza, remove duplicidades e ordena candidatos.

    Ordem:
        1. ativos;
        2. inativos;
        3. service ID;
        4. nome do arquivo.
    """

    normalized_candidates = []
    seen_candidates = set()

    for raw_candidate in (
        raw_candidates
        or []
    ):
        candidate = (
            _normalize_candidate(
                raw_candidate,
                services_by_id
            )
        )

        if not candidate:
            continue

        candidate_key = (
            candidate.get(
                "service"
            ),
            candidate.get(
                "source_file"
            )
        )

        if candidate_key in seen_candidates:
            continue

        seen_candidates.add(
            candidate_key
        )

        normalized_candidates.append(
            candidate
        )

    return sorted(
        normalized_candidates,
        key=lambda item: (
            not item.get(
                "startonload",
                False
            ),
            item.get(
                "service",
                ""
            ),
            item.get(
                "source_file"
            )
            or ""
        )
    )


def _select_candidate(
    machine,
    expected_service,
    candidates,
    input_function=input,
):
    """
    Mostra os candidatos e solicita uma opção válida.
    """

    print()
    print("KVS RESOLUTION REQUIRED")
    print("-" * 50)

    print(
        f"Machine: {machine}"
    )

    print(
        "Expected service: "
        f"KVS{expected_service}"
    )

    print()
    print("Available candidates:")

    for index, candidate in enumerate(
        candidates,
        start=1
    ):
        active_status = (
            "ACTIVE"
            if candidate.get(
                "startonload",
                False
            )
            else "INACTIVE"
        )

        source_file = (
            candidate.get(
                "source_file"
            )
            or "UNKNOWN FILE"
        )

        print(
            f"  {index} - "
            f"KVS{candidate['service']} "
            f"from {source_file} "
            f"[{active_status}]"
        )

    while True:
        selected_value = input_function(
            "Select replacement "
            f"[1-{len(candidates)}]: "
        )

        selected_value = str(
            selected_value
        ).strip()

        try:
            selected_index = int(
                selected_value
            )

        except ValueError:
            print(
                "Invalid option. "
                "Enter a number."
            )

            continue

        if not (
            1
            <= selected_index
            <= len(candidates)
        ):
            print(
                "Invalid option. "
                f"Select a number between "
                f"1 and {len(candidates)}."
            )

            continue

        return candidates[
            selected_index - 1
        ]


def _already_mapped(
    mapping,
    expected_service,
):
    """
    Evita registrar duas vezes o mesmo serviço lógico.
    """

    expected_service = (
        _normalize_service_id(
            expected_service
        )
    )

    for mapped_service in mapping.get(
        "mapped_services",
        []
    ):
        mapped_id = (
            _normalize_service_id(
                mapped_service.get(
                    "service"
                )
            )
        )

        if mapped_id == expected_service:
            return True

    return False


def resolve_missing_kvs(
    kvs_mapping,
    input_function=input,
):
    """
    Resolve serviços KVS ausentes por escolha manual.

    O arquivo escolhido é usado como fonte da configuração,
    mas o serviço esperado continua sendo o destino lógico.

    Exemplo:

        Expected:
            KVS1071

        Selected:
            KVS0502

        Mapping registrado:

            service = 1071
            source_service = 0502
            source_file = _KVS0502_pos-db.xml
    """

    if not kvs_mapping:
        return kvs_mapping

    services_by_id = (
        _build_services_by_id(
            kvs_mapping
        )
    )

    manual_resolutions = list(
        kvs_mapping.get(
            "manual_resolutions",
            []
        )
    )

    for mapping in kvs_mapping.get(
        "mappings",
        []
    ):
        machine = mapping.get(
            "machine",
            "UNKNOWN"
        )

        missing_services = [
            service_id
            for service_id in (
                _normalize_service_id(
                    item
                )
                for item in mapping.get(
                    "missing_services",
                    []
                )
            )
            if service_id
        ]

        candidate_services = (
            mapping.get(
                "candidate_services",
                {}
            )
            or {}
        )

        mapping.setdefault(
            "mapped_services",
            []
        )

        mapping.setdefault(
            "resolved_services",
            []
        )

        mapping.setdefault(
            "warnings",
            []
        )

        unresolved_services = []

        for expected_service in (
            missing_services
        ):
            raw_candidates = (
                candidate_services.get(
                    expected_service,
                    []
                )
            )

            if not raw_candidates:
                raw_candidates = (
                    candidate_services.get(
                        f"KVS{expected_service}",
                        []
                    )
                )

            candidates = (
                _prepare_candidates(
                    raw_candidates,
                    services_by_id
                )
            )

            if not candidates:
                unresolved_services.append(
                    expected_service
                )

                warning = (
                    "No replacement candidates "
                    "were found for "
                    f"KVS{expected_service}."
                )

                if warning not in mapping[
                    "warnings"
                ]:
                    mapping[
                        "warnings"
                    ].append(
                        warning
                    )

                continue

            if _already_mapped(
                mapping,
                expected_service
            ):
                continue

            selected_candidate = (
                _select_candidate(
                    machine=machine,
                    expected_service=
                        expected_service,
                    candidates=candidates,
                    input_function=
                        input_function
                )
            )

            selected_service = (
                selected_candidate[
                    "service"
                ]
            )

            source_file = (
                selected_candidate.get(
                    "source_file"
                )
            )

            startonload = bool(
                selected_candidate.get(
                    "startonload",
                    False
                )
            )

            resolution = {
                "machine": machine,
                "expected_service":
                    expected_service,
                "selected_service":
                    selected_service,
                "source_service":
                    selected_service,
                "source_file":
                    source_file,
                "startonload":
                    startonload,
                "selection":
                    "manual",
                "status":
                    "RESOLVED"
            }

            mapped_service = {
                "service":
                    expected_service,
                "source_service":
                    selected_service,
                "source_file":
                    source_file,
                "startonload":
                    startonload,
                "selection":
                    "manual"
            }

            mapping[
                "resolved_services"
            ].append(
                resolution
            )

            mapping[
                "mapped_services"
            ].append(
                mapped_service
            )

            manual_resolutions.append(
                resolution
            )

            print()
            print("KVS RESOLUTION SELECTED")
            print("-" * 50)

            print(
                f"Machine: {machine}"
            )

            print(
                "Expected service: "
                f"KVS{expected_service}"
            )

            print(
                "Selected source: "
                f"KVS{selected_service}"
            )

            print(
                "Source file: "
                f"{source_file or 'UNKNOWN FILE'}"
            )

            print(
                "Status: RESOLVED"
            )

        mapping[
            "missing_services"
        ] = unresolved_services

        if unresolved_services:
            mapping[
                "status"
            ] = "REVIEW REQUIRED"

        elif mapping.get(
            "mapped_services"
        ):
            mapping[
                "status"
            ] = "READY"

    kvs_mapping[
        "manual_resolutions"
    ] = manual_resolutions

    unresolved_count = sum(
        len(
            mapping.get(
                "missing_services",
                []
            )
        )
        for mapping in kvs_mapping.get(
            "mappings",
            []
        )
    )

    if unresolved_count:
        kvs_mapping[
            "resolution_status"
        ] = "REVIEW REQUIRED"

    else:
        kvs_mapping[
            "resolution_status"
        ] = "READY"

    return kvs_mapping