def _already_resolved(
    mapping,
    target_pos
):
    """
    Evita resolver o mesmo POS duas vezes.
    """

    for resolution in mapping.get(
        "resolved_positions",
        []
    ):
        if (
            resolution.get(
                "target_pos"
            )
            == target_pos
        ):
            return True

    return False


def resolve_missing_positions(
    pos_mapping,
    input_function=input,
):
    """
    Resolve POS ausentes.

    Opções:

        1..N
            Seleciona um POS substituto

        0
            Continua sem gerar o POS

    Estruturas geradas:

        RESOLVED

            POS0004 -> POS0001

        SKIPPED

            POS0004 -> NONE
    """

    if not pos_mapping:
        return pos_mapping

    manual_resolutions = []

    for mapping in pos_mapping.get(
        "mappings",
        []
    ):

        missing_positions = list(
            mapping.get(
                "missing_positions",
                []
            )
        )

        candidate_positions = (
            mapping.get(
                "candidate_positions",
                {}
            )
        )

        mapping.setdefault(
            "resolved_positions",
            []
        )

        mapping.setdefault(
            "warnings",
            []
        )

        unresolved_positions = []

        for missing_position in (
            missing_positions
        ):

            if _already_resolved(
                mapping,
                missing_position
            ):
                continue

            candidates = (
                candidate_positions.get(
                    missing_position,
                    []
                )
            )

            if not candidates:

                unresolved_positions.append(
                    missing_position
                )

                warning = (
                    f"No replacement "
                    f"candidates found for "
                    f"{missing_position}."
                )

                if warning not in (
                    mapping["warnings"]
                ):
                    mapping[
                        "warnings"
                    ].append(
                        warning
                    )

                continue

            print()
            print(
                "POS RESOLUTION REQUIRED"
            )

            print(
                "-" * 50
            )

            print(
                f"Expected POS: "
                f"{missing_position}"
            )

            print()
            print(
                "Available candidates:"
            )

            for index, candidate in enumerate(
                candidates,
                start=1
            ):

                node = (
                    candidate.get(
                        "node",
                        "UNKNOWN"
                    )
                )

                source_file = (
                    candidate.get(
                        "source_file",
                        "UNKNOWN"
                    )
                )

                role = (
                    candidate.get(
                        "role",
                        "UNKNOWN"
                    )
                )

                print(
                    f"  {index} - "
                    f"{node} "
                    f"[{role}] "
                    f"({source_file})"
                )

            print()

            print(
                "  0 - NONE "
                "(continue without "
                "this POS)"
            )

            resolution = None

            while resolution is None:

                selected_value = (
                    input_function(
                        f"Select replacement "
                        f"[0-{len(candidates)}]: "
                    )
                    .strip()
                )

                try:

                    selected_index = int(
                        selected_value
                    )

                except ValueError:

                    print(
                        "Invalid option."
                    )

                    continue

                #
                # NONE
                #
                if selected_index == 0:

                    resolution = {
                        "target_pos":
                            missing_position,

                        "source_pos":
                            None,

                        "source_file":
                            None,

                        "selection":
                            "none",

                        "status":
                            "SKIPPED"
                    }

                    break

                if not (
                    1
                    <= selected_index
                    <= len(candidates)
                ):

                    print(
                        "Invalid option."
                    )

                    continue

                selected_candidate = (
                    candidates[
                        selected_index - 1
                    ]
                )

                resolution = {
                    "target_pos":
                        missing_position,

                    "source_pos":
                        selected_candidate.get(
                            "node"
                        ),

                    "source_file":
                        selected_candidate.get(
                            "source_file"
                        ),

                    "selection":
                        "manual",

                    "status":
                        "RESOLVED"
                }

            #
            # SKIPPED
            #
            if (
                resolution["status"]
                == "SKIPPED"
            ):

                print()
                print(
                    "POS RESOLUTION SELECTED"
                )

                print(
                    "-" * 50
                )

                print(
                    f"Expected POS: "
                    f"{missing_position}"
                )

                print(
                    "Selection: NONE"
                )

                print(
                    "Status: SKIPPED"
                )

                mapping[
                    "resolved_positions"
                ].append(
                    resolution
                )

                manual_resolutions.append(
                    resolution
                )

                continue

            #
            # RESOLVED
            #
            print()

            print(
                "POS RESOLUTION SELECTED"
            )

            print(
                "-" * 50
            )

            print(
                f"Expected POS: "
                f"{missing_position}"
            )

            print(
                f"Selected POS: "
                f"{resolution['source_pos']}"
            )

            print(
                f"Source file: "
                f"{resolution['source_file']}"
            )

            print(
                "Status: RESOLVED"
            )

            mapping[
                "resolved_positions"
            ].append(
                resolution
            )

            manual_resolutions.append(
                resolution
            )

        #
        # Atualiza pendências
        #
        mapping[
            "missing_positions"
        ] = unresolved_positions

        if unresolved_positions:

            mapping[
                "status"
            ] = (
                "REVIEW REQUIRED"
            )

        else:

            mapping[
                "status"
            ] = (
                "READY"
            )

    #
    # Consolidação global
    #
    pos_mapping[
        "manual_resolutions"
    ] = manual_resolutions

    unresolved_count = sum(
        len(
            mapping.get(
                "missing_positions",
                []
            )
        )
        for mapping in (
            pos_mapping.get(
                "mappings",
                []
            )
        )
    )

    resolved_count = sum(
        1
        for item in (
            manual_resolutions
        )
        if item.get(
            "status"
        ) == "RESOLVED"
    )

    skipped_count = sum(
        1
        for item in (
            manual_resolutions
        )
        if item.get(
            "status"
        ) == "SKIPPED"
    )

    pos_mapping[
        "resolution_summary"
    ] = {
        "resolved":
            resolved_count,

        "skipped":
            skipped_count,

        "unresolved":
            unresolved_count
    }

    if unresolved_count:

        pos_mapping[
            "resolution_status"
        ] = (
            "REVIEW REQUIRED"
        )

    else:

        pos_mapping[
            "resolution_status"
        ] = (
            "READY"
        )

    return pos_mapping