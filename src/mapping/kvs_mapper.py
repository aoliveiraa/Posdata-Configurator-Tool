from pathlib import Path

from src.utils.xml_loader import load_xml


def normalize_service_name(service_name):
    """
    Normaliza o identificador do serviço.

    Exemplos:
        0101 -> 0101
        KVS0101 -> 0101
        kvs0101 -> 0101
    """

    if service_name is None:
        return None

    normalized = str(service_name).strip().upper()

    if normalized.startswith("KVS"):
        normalized = normalized[3:]

    return normalized


def discover_new_kvs_services(folder):
    """
    Procura todos os arquivos pos-db do novo PosData
    e extrai os serviços KVS encontrados dentro dos XMLs.

    A descoberta é feita pelo conteúdo do XML,
    não apenas pelo nome do arquivo.
    """

    folder = Path(folder)

    services = []

    for file_path in sorted(folder.glob("*_pos-db.xml")):

        try:
            tree = load_xml(file_path)

            kvs_nodes = tree.xpath(
                "//Service[translate("
                "@type, "
                "'abcdefghijklmnopqrstuvwxyz', "
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ'"
                ")='KVS']"
            )

            for kvs_node in kvs_nodes:

                service_name = normalize_service_name(
                    kvs_node.get("name")
                )

                if not service_name:
                    continue

                services.append({
                    "service": service_name,
                    "source_file": file_path.name,
                    "startonload": (
                        kvs_node.get(
                            "startonload",
                            "false"
                        ).lower()
                        == "true"
                    )
                })

        except Exception as error:

            services.append({
                "service": None,
                "source_file": file_path.name,
                "startonload": False,
                "error": str(error)
            })

    return services


def map_kvs_to_itonas(
    reference_itonas,
    new_posdata_folder
):
    """
    Compara os serviços usados nas Itonas de referência
    com os serviços existentes no novo PosData.

    Nesta primeira versão:

    - usa o service ID da referência;
    - encontra o mesmo service ID no PosData novo;
    - não adivinha substituições;
    - sinaliza serviços ausentes;
    - sinaliza serviços extras;
    - sinaliza serviços inativos.
    """

    discovered_services = discover_new_kvs_services(
        new_posdata_folder
    )

    valid_services = [
        item
        for item in discovered_services
        if item.get("service")
    ]

    services_by_id = {}

    for item in valid_services:

        service_id = item["service"]

        if service_id not in services_by_id:
            services_by_id[service_id] = []

        services_by_id[service_id].append(item)

    mappings = []

    mapped_service_ids = set()

    for reference_itona in reference_itonas:

        machine = reference_itona["machine"]

        reference_services = [
            normalize_service_name(service_id)
            for service_id
            in reference_itona["kvs_services"]
        ]

        mapped_services = []
        missing_services = []
        warnings = []

        for service_id in reference_services:

            candidates = services_by_id.get(
                service_id,
                []
            )

            if not candidates:

                missing_services.append(service_id)

                continue

            active_candidates = [
                candidate
                for candidate in candidates
                if candidate["startonload"]
            ]

            if active_candidates:
                selected = active_candidates[0]
            else:
                selected = candidates[0]

                warnings.append(
                    f"KVS{service_id} was found, "
                    "but startonload is false."
                )

            if len(candidates) > 1:
                warnings.append(
                    f"KVS{service_id} was found in "
                    f"{len(candidates)} files."
                )

            mapped_services.append({
                "service": service_id,
                "source_file": selected["source_file"],
                "startonload": selected["startonload"]
            })

            mapped_service_ids.add(service_id)

        status = "READY"

        if missing_services:
            status = "REVIEW REQUIRED"

            warnings.append(
                "Reference services not found in "
                "the new PosData: "
                + ", ".join(
                    f"KVS{service_id}"
                    for service_id
                    in missing_services
                )
            )

        if not mapped_services:
            status = "NOT MAPPED"

        mappings.append({
            "machine": machine,
            "target_file": (
                f"_{machine}_pos-db.xml"
            ),
            "reference_services": reference_services,
            "mapped_services": mapped_services,
            "missing_services": missing_services,
            "status": status,
            "warnings": warnings
        })

    extra_services = []

    for service_id, candidates in services_by_id.items():

        if service_id in mapped_service_ids:
            continue

        for candidate in candidates:

            extra_services.append({
                "service": service_id,
                "source_file": candidate["source_file"],
                "startonload": candidate["startonload"]
            })

    discovery_errors = [
        item
        for item in discovered_services
        if item.get("error")
    ]

    return {
        "mappings": mappings,
        "extra_services": extra_services,
        "discovered_services": valid_services,
        "discovery_errors": discovery_errors
    }