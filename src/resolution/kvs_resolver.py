def _normalize_service_id(service_id):
    """Normalize KVS IDs such as 0501, KVS0501 or kvs0501."""
    if service_id is None:
        return None

    normalized = str(service_id).strip().upper()

    if normalized.startswith("KVS"):
        normalized = normalized[3:]

    return normalized or None


def _build_services_by_id(kvs_mapping):
    """Index discovered KVS services by normalized service ID."""
    services_by_id = {}

    for item in kvs_mapping.get("discovered_services", []):
        service_id = _normalize_service_id(item.get("service"))

        if not service_id:
            continue

        services_by_id.setdefault(service_id, []).append(
            {
                "service": service_id,
                "source_file": item.get("source_file"),
                "startonload": bool(item.get("startonload", False)),
            }
        )

    return services_by_id


def _normalize_candidate(candidate, services_by_id):
    """Return a candidate in the standard dictionary format."""
    if isinstance(candidate, dict):
        service_id = _normalize_service_id(candidate.get("service"))

        if not service_id:
            return None

        source_file = candidate.get("source_file")
        startonload = bool(candidate.get("startonload", False))

        if not source_file:
            discovered_matches = services_by_id.get(service_id, [])

            if discovered_matches:
                active_matches = [
                    item
                    for item in discovered_matches
                    if item.get("startonload", False)
                ]
                selected_match = (
                    active_matches[0]
                    if active_matches
                    else discovered_matches[0]
                )
                source_file = selected_match.get("source_file")
                startonload = bool(
                    selected_match.get("startonload", False)
                )

        return {
            "service": service_id,
            "source_file": source_file,
            "startonload": startonload,
        }

    service_id = _normalize_service_id(candidate)

    if not service_id:
        return None

    discovered_matches = services_by_id.get(service_id, [])

    if not discovered_matches:
        return {
            "service": service_id,
            "source_file": None,
            "startonload": False,
        }

    active_matches = [
        item
        for item in discovered_matches
        if item.get("startonload", False)
    ]
    selected_match = (
        active_matches[0]
        if active_matches
        else discovered_matches[0]
    )

    return {
        "service": service_id,
        "source_file": selected_match.get("source_file"),
        "startonload": bool(selected_match.get("startonload", False)),
    }


def _prepare_candidates(raw_candidates, services_by_id):
    """Normalize, deduplicate and sort KVS candidates."""
    normalized_candidates = []
    seen_candidates = set()

    for raw_candidate in raw_candidates or []:
        candidate = _normalize_candidate(raw_candidate, services_by_id)

        if not candidate:
            continue

        candidate_key = (
            candidate.get("service"),
            candidate.get("source_file"),
        )

        if candidate_key in seen_candidates:
            continue

        seen_candidates.add(candidate_key)
        normalized_candidates.append(candidate)

    return sorted(
        normalized_candidates,
        key=lambda item: (
            not item.get("startonload", False),
            item.get("service", ""),
            item.get("source_file") or "",
        ),
    )


def _select_candidate(
    machine,
    expected_service,
    candidates,
    selection_function,
):
    """
    Request a manual KVS selection through the provided UI callback.

    The resolver never calls input() and never accesses sys.stdin.
    The callback must return one candidate dictionary from candidates.
    Returning None means the user cancelled the resolution.
    """
    print()
    print("KVS RESOLUTION REQUIRED")
    print("-" * 50)
    print(f"Machine: {machine}")
    print(f"Expected service: KVS{expected_service}")
    print()
    print("Available candidates:")

    for index, candidate in enumerate(candidates, start=1):
        active_status = (
            "ACTIVE"
            if candidate.get("startonload", False)
            else "INACTIVE"
        )
        source_file = candidate.get("source_file") or "UNKNOWN FILE"

        print(
            f"  {index} - "
            f"KVS{candidate['service']} "
            f"from {source_file} "
            f"[{active_status}]"
        )

    if selection_function is None:
        raise RuntimeError(
            "Manual KVS resolution is required, but no GUI selection "
            "callback was provided."
        )

    selected_candidate = selection_function(
        machine,
        expected_service,
        candidates,
    )

    if selected_candidate is None:
        raise RuntimeError(
            "Manual KVS resolution was cancelled for "
            f"{machine} / KVS{expected_service}."
        )

    if not isinstance(selected_candidate, dict):
        raise TypeError(
            "The KVS selection callback must return a candidate dictionary."
        )

    selected_service = _normalize_service_id(
        selected_candidate.get("service")
    )

    valid_candidate = next(
        (
            candidate
            for candidate in candidates
            if (
                _normalize_service_id(candidate.get("service"))
                == selected_service
                and candidate.get("source_file")
                == selected_candidate.get("source_file")
            )
        ),
        None,
    )

    if valid_candidate is None:
        raise ValueError(
            "The selected KVS candidate is not part of the available list."
        )

    return valid_candidate


def _already_mapped(mapping, expected_service):
    """Prevent duplicate mapping of the same logical service."""
    expected_service = _normalize_service_id(expected_service)

    for mapped_service in mapping.get("mapped_services", []):
        mapped_id = _normalize_service_id(
            mapped_service.get("service")
        )

        if mapped_id == expected_service:
            return True

    return False


def resolve_missing_kvs(
    kvs_mapping,
    selection_function=None,
):
    """
    Resolve missing KVS services through a manual UI callback.

    The selected file supplies the source configuration, while the expected
    service remains the logical destination.

    Example:
        Expected: KVS1071
        Selected source: KVS1070
        Generated logical service: KVS1071
    """
    if not kvs_mapping:
        return kvs_mapping

    services_by_id = _build_services_by_id(kvs_mapping)
    manual_resolutions = list(
        kvs_mapping.get("manual_resolutions", [])
    )

    for mapping in kvs_mapping.get("mappings", []):
        machine = mapping.get("machine", "UNKNOWN")
        missing_services = [
            service_id
            for service_id in (
                _normalize_service_id(item)
                for item in mapping.get("missing_services", [])
            )
            if service_id
        ]
        candidate_services = mapping.get("candidate_services", {}) or {}

        mapping.setdefault("mapped_services", [])
        mapping.setdefault("resolved_services", [])
        mapping.setdefault("warnings", [])

        unresolved_services = []

        for expected_service in missing_services:
            raw_candidates = candidate_services.get(expected_service, [])

            if not raw_candidates:
                raw_candidates = candidate_services.get(
                    f"KVS{expected_service}",
                    [],
                )

            candidates = _prepare_candidates(
                raw_candidates,
                services_by_id,
            )

            if not candidates:
                unresolved_services.append(expected_service)
                warning = (
                    "No replacement candidates were found for "
                    f"KVS{expected_service}."
                )

                if warning not in mapping["warnings"]:
                    mapping["warnings"].append(warning)

                continue

            if _already_mapped(mapping, expected_service):
                continue

            try:
                selected_candidate = _select_candidate(
                    machine=machine,
                    expected_service=expected_service,
                    candidates=candidates,
                    selection_function=selection_function,
                )
            except RuntimeError as error:
                unresolved_services.append(expected_service)
                warning = str(error)

                if warning not in mapping["warnings"]:
                    mapping["warnings"].append(warning)

                print()
                print("KVS RESOLUTION NOT COMPLETED")
                print("-" * 50)
                print(warning)
                continue

            selected_service = selected_candidate["service"]
            source_file = selected_candidate.get("source_file")
            startonload = bool(
                selected_candidate.get("startonload", False)
            )

            resolution = {
                "machine": machine,
                "expected_service": expected_service,
                "selected_service": selected_service,
                "source_service": selected_service,
                "source_file": source_file,
                "startonload": startonload,
                "selection": "manual-ui",
                "status": "RESOLVED",
            }

            mapped_service = {
                "service": expected_service,
                "source_service": selected_service,
                "source_file": source_file,
                "startonload": startonload,
                "selection": "manual-ui",
            }

            mapping["resolved_services"].append(resolution)
            mapping["mapped_services"].append(mapped_service)
            manual_resolutions.append(resolution)

            print()
            print("KVS RESOLUTION SELECTED")
            print("-" * 50)
            print(f"Machine: {machine}")
            print(f"Expected service: KVS{expected_service}")
            print(f"Selected source: KVS{selected_service}")
            print(f"Source file: {source_file or 'UNKNOWN FILE'}")
            print("Selection mode: MANUAL UI")
            print("Status: RESOLVED")

        mapping["missing_services"] = unresolved_services

        if unresolved_services:
            mapping["status"] = "REVIEW REQUIRED"
        elif mapping.get("mapped_services"):
            mapping["status"] = "READY"

    kvs_mapping["manual_resolutions"] = manual_resolutions

    unresolved_count = sum(
        len(mapping.get("missing_services", []))
        for mapping in kvs_mapping.get("mappings", [])
    )

    kvs_mapping["resolution_status"] = (
        "REVIEW REQUIRED"
        if unresolved_count
        else "READY"
    )

    return kvs_mapping
