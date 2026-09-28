from __future__ import annotations

from typing import Any, Dict, List


READY_STATUSES = {
    "READY",
    "READY WITH OBSERVATION",
    "READY WITH OBSERVATIONS",
}

SKIPPED_STATUSES = {
    "SKIPPED",
}


def _upper(value: Any) -> str:
    return str(value or "").strip().upper()


def _validate_metadata(
    build_plan: Dict[str, Any],
    errors: List[str],
) -> None:

    build = build_plan.get("build") or {}

    if not build.get("laboratory"):
        errors.append(
            "Build plan is missing laboratory."
        )

    if not build.get("market"):
        errors.append(
            "Build plan is missing market."
        )


def _validate_pos_plan(
    pos_plan: List[Dict[str, Any]],
    errors: List[str],
    warnings: List[str],
) -> None:

    used_output_files = set()

    for pos in pos_plan:

        node = pos.get("target_node")
        status = _upper(
            pos.get("status")
        )

        output_file = pos.get(
            "output_file"
        )

        source_file = pos.get(
            "source_file"
        )

        if not node:
            errors.append(
                "POS entry has no target_node."
            )
            continue

        if status in SKIPPED_STATUSES:
            continue

        if not output_file:
            errors.append(
                f"{node} has no output_file."
            )

        if not source_file:
            warnings.append(
                f"{node} has no source_file yet."
            )

        if output_file:

            normalized = (
                str(output_file)
                .strip()
                .lower()
            )

            if normalized in used_output_files:
                errors.append(
                    f"Duplicated POS output file: "
                    f"{output_file}"
                )

            used_output_files.add(
                normalized
            )


def _validate_itona_plan(
    itona_plan: List[Dict[str, Any]],
    errors: List[str],
    warnings: List[str],
) -> None:

    used_kvs_files = set()

    for itona in itona_plan:

        slot = itona.get("slot")

        status = _upper(
            itona.get("status")
        )

        source_files = (
            itona.get("source_files")
            or []
        )

        kvs_services = (
            itona.get("kvs_services")
            or []
        )

        if not slot:
            errors.append(
                "Itona entry has no slot."
            )
            continue

        if status in SKIPPED_STATUSES:
            continue

        if len(source_files) > 2:
            errors.append(
                f"{slot} has more than "
                "2 assigned KVS files."
            )

        for file_name in source_files:

            normalized = (
                str(file_name)
                .strip()
                .lower()
            )

            if normalized in used_kvs_files:
                errors.append(
                    f"KVS file reused "
                    f"multiple times: {file_name}"
                )

            used_kvs_files.add(
                normalized
            )

        if (
            not source_files
            and not kvs_services
        ):
            warnings.append(
                f"{slot} has no KVS assignment."
            )


def _validate_manifest(
    manifest: Dict[str, Any],
    errors: List[str],
) -> None:

    expected_files = (
        manifest.get(
            "expected_files"
        )
        or []
    )

    if not expected_files:
        errors.append(
            "Manifest does not contain "
            "expected files."
        )
        return

    seen = set()

    for item in expected_files:

        filename = (
            item.get("file")
            or ""
        )

        if not filename:
            errors.append(
                "Manifest contains "
                "an entry without filename."
            )
            continue

        normalized = (
            filename
            .strip()
            .lower()
        )

        if normalized in seen:
            errors.append(
                f"Duplicated manifest file: "
                f"{filename}"
            )

        seen.add(
            normalized
        )


def validate_build_plan(
    build_plan: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Sprint 2.0.1

    Validates the Build Plan
    before any XML generation.

    The goal is to guarantee
    that Generation receives
    a coherent contract.
    """

    result = {
        "status": "PASS",
        "warnings": [],
        "errors": [],
    }

    errors = result["errors"]
    warnings = result["warnings"]

    if not build_plan:

        errors.append(
            "Build plan is empty."
       )

        result["status"] = "FAIL"

        return result

    generation_mode = _upper(
        build_plan.get(
            "generation_mode"
        )
    )

    if generation_mode != "FROM_SCRATCH":
        warnings.append(
            "Build plan is not running "
            "in FROM_SCRATCH mode."
        )

    _validate_metadata(
        build_plan,
        errors,
    )

    _validate_pos_plan(
        build_plan.get("pos")
        or [],
        errors,
        warnings,
    )

    _validate_itona_plan(
        build_plan.get("itonas")
        or [],
        errors,
        warnings,
    )

    _validate_manifest(
        build_plan.get("manifest")
        or {},
        errors,
    )

    if errors:

        result["status"] = "FAIL"

    elif warnings:

        result["status"] = (
            "PASS WITH OBSERVATIONS"
        )

    result["summary"] = {
        "errors": len(errors),
        "warnings": len(warnings),
        "generation_mode": (
            generation_mode
        ),
    }

    return result