from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Dict

from src.builder.generators.xml_factory import (
    XmlFactory,
)


def _safe_text(
    value: Any,
    default: str = "",
) -> str:

    if value is None:
        return default

    text = str(value).strip()

    return text or default


def _extract_market(
    context,
) -> str:

    market = getattr(
        context,
        "market",
        {},
    )

    if isinstance(
        market,
        dict,
    ):
        return (
            market.get("country")
            or market.get("market")
            or market.get("code")
            or "UNKNOWN"
        )

    return "UNKNOWN"


def _extract_store_info(
    context,
):

    store = getattr(
        context,
        "store_info",
        {},
    )

    if not isinstance(
        store,
        dict,
    ):
        return {}

    return store


def _extract_lunch_screen_number(
    context,
) -> str | None:

    lunch_screen = getattr(
        context,
        "lunch_screen",
        None,
    )

    if not isinstance(
        lunch_screen,
        dict,
    ):
        return None

    for key in (
        "number",
        "screen_number",
        "screenNumber",
    ):
        value = lunch_screen.get(
            key
        )

        if value is not None:
            return str(value)

    return None


def build_storedb_document(
    context,
    build_plan: Dict[str, Any],
    rules: Dict[str, Any],
):
    """
    Build a StoreDB XML document
    completely FROM_SCRATCH.
    """

    document, storedb = (
        XmlFactory.create_storedb_document()
    )

    configuration = (
        XmlFactory.add_configuration(
            storedb
        )
    )

    market = _extract_market(
        context
    )

    store_info = (
        _extract_store_info(
            context
        )
    )

    store_id = (
        store_info.get(
            "store_id"
        )
        or store_info.get(
            "store"
        )
    )

    city = store_info.get(
        "city"
    )

    XmlFactory.add_parameter(
        configuration,
        "Market",
        market,
    )

    if store_id:

        XmlFactory.add_parameter(
            configuration,
            "StoreId",
            store_id,
        )

    if city:

        XmlFactory.add_parameter(
            configuration,
            "City",
            city,
        )

    #
    # Main Screen
    #

    screen_number = (
        _extract_lunch_screen_number(
            context
        )
    )

    if screen_number:

        XmlFactory.add_parameter(
            configuration,
            "MainScreenNumber",
            screen_number,
        )

    return document


def generate_storedb(
    context,
    build_plan: Dict[str, Any],
    rules: Dict[str, Any],
    output_file: str | Path,
):
    """
    High level generation entry point.
    """

    result = {
        "generated": False,
        "output_file": None,
        "warnings": [],
        "errors": [],
    }

    try:

        document = (
            build_storedb_document(
                context,
                build_plan,
                rules,
            )
        )

        XmlFactory.save(
            document,
            output_file,
        )

        result["generated"] = True

        result["output_file"] = str(
            output_file
        )

    except Exception as error:

        result["errors"].append(
            str(error)
        )

    return result