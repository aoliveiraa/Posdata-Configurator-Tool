from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List


def _unique(values):
    return list(
        dict.fromkeys(
            value for value in values if value
        )
    )


def _build_pos_plan(
    confirmed_pos_mapping: Dict[str, Any],
) -> List[Dict[str, Any]]:

    result = []

    for assignment in (
        confirmed_pos_mapping.get("assignments")
        or []
    ):
        result.append(
            {
                "target_node": assignment.get(
                    "target_node"
                ),
                "output_file": assignment.get(
                    "output_file"
                ),
                "source_file": assignment.get(
                    "source_file"
                ),
                "effective_role": assignment.get(
                    "effective_role"
                ),
                "status": assignment.get(
                    "status"
                ),
                "origin": "USER_DECISION",
            }
        )

    return result


def _build_itona_plan(
    confirmed_itona_mapping: Dict[str, Any],
) -> List[Dict[str, Any]]:

    result = []

    for assignment in (
        confirmed_itona_mapping.get(
            "assignments"
        )
        or []
    ):
        slot = assignment.get(
            "slot"
        )

        result.append(
            {
                "slot": slot,
                "output_file": (
                    assignment.get(
                        "output_file"
                    )
                    or (
                        f"_{slot}_pos-db.xml"
                        if slot
                        else None
                    )
                ),
                "source_files": list(
                    assignment.get(
                        "source_files"
                    )
                    or (
                        [
                            assignment[
                                "source_file"
                            ]
                        ]
                        if assignment.get(
                            "source_file"
                        )
                        else []
                    )
                ),
                "source_types": list(
                    assignment.get(
                        "source_types"
                    )
                    or []
                ),
                "kvs_services": list(
                    assignment.get(
                        "kvs_services"
                    )
                    or []
                ),
                "status": assignment.get(
                    "status"
                ),
                "origin": (
                    assignment.get(
                        "origin"
                    )
                    or "USER_DECISION"
                ),
            }
        )

    return result

def _build_artifact_manifest(
    pos_plan: List[Dict[str, Any]],
    itona_plan: List[Dict[str, Any]],
) -> Dict[str, Any]:

    files = []

    for pos in pos_plan:

        if (
            pos.get("status")
            and str(
                pos["status"]
            ).upper()
            != "SKIPPED"
        ):
            files.append(
                {
                    "type": "POS",
                    "file": pos.get(
                        "output_file"
                    ),
                }
            )

    for itona in itona_plan:

        if (
            str(
                itona.get(
                    "status",
                    "",
                )
            ).upper()
            != "SKIPPED"
        ):
            files.append(
                {
                    "type": "ITONA",
                    "file": (
                        itona.get(
                            "output_file"
                        )
                        or (
                            f"_{itona['slot']}"
                            "_pos-db.xml"
                        )
                    ),
                }
            )

    return {
        "expected_files": files,
        "expected_file_count": len(
            files
        ),
    }


def build_build_plan(
    context: Any,
) -> Dict[str, Any]:
    """
    Sprint 2.0.1

    Central Builder contract.

    This does not generate XML.

    It creates the final build plan that
    future native generators will consume.
    """

    result = {
        "status": "READY",
        "generation_mode": "FROM_SCRATCH",
        "created_at": (
            datetime.now()
            .astimezone()
            .isoformat()
        ),
        "warnings": [],
        "errors": [],
    }

    market = (
        context.market
        if isinstance(
            context.market,
            dict,
        )
        else {}
    )

    store = (
        context.store_info
        if isinstance(
            context.store_info,
            dict,
        )
        else {}
    )

    pos_plan = _build_pos_plan(
        context.confirmed_pos_mapping
        or {}
    )

    itona_plan = _build_itona_plan(
        context.confirmed_itona_mapping
        or {}
    )

    manifest = (
        _build_artifact_manifest(
            pos_plan,
            itona_plan,
        )
    )

    result["build"] = {
        "laboratory": getattr(
            context,
            "selected_lab",
            None,
        ),
        "market": market.get(
            "country"
        )
        or market.get(
            "market"
        ),
        "store_id": store.get(
            "store_id"
        ),
        "city": store.get(
            "city"
        ),
    }

    result["input"] = {
        "source_folder": str(
            getattr(
                context,
                "source_posdata_folder",
                "",
            )
            or ""
        ),
        "config_path": getattr(
            context,
            "config_path",
            None,
        ),
        "rules_path": getattr(
            context,
            "rules_path",
            None,
        ),
    }

    result["pos"] = pos_plan

    result["itonas"] = itona_plan

    result["manifest"] = manifest

    result["metrics"] = {
        "pos_count": len(
            pos_plan
        ),
        "itona_count": len(
            itona_plan
        ),
        "artifact_count": manifest[
            "expected_file_count"
        ],
    }

    if not pos_plan:
        result["warnings"].append(
            "Build plan contains no POS targets."
        )

    if not itona_plan:
        result["warnings"].append(
        "Build plan contains no Itona targets."
        )

    if result["errors"]:
        result["status"] = "FAIL"

    elif result["warnings"]:
        result["status"] = (
            "READY WITH OBSERVATIONS"
        )

    context.build_plan = result

    return result