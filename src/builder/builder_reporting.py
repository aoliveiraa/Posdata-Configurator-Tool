from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List


REPORT_WIDTH = 50


def _print_section(title: str) -> None:
    print(title)
    print("-" * REPORT_WIDTH)


def _display_value(value: Any, default: str = "UNKNOWN") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        value = value.strip()
        return value or default
    return str(value)


def _display_list(
    values: Iterable[Any] | None,
    default: str = "NONE",
) -> str:
    normalized = [
        str(value).strip()
        for value in (values or [])
        if str(value).strip()
    ]
    return ", ".join(normalized) if normalized else default


def _count_itona_types(
    candidates: List[Dict[str, Any]],
) -> Counter:
    counter: Counter = Counter()

    for candidate in candidates:
        types = candidate.get("kvs_types") or ["UNKNOWN"]
        for itona_type in types:
            counter[str(itona_type or "UNKNOWN").upper()] += 1

    return counter


def _print_discovery_summary(
    context: Any,
    discovery: Dict[str, Any],
    pos_files: List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
) -> None:
    market = context.market or {}
    store = context.store_info or {}
    way_files = discovery.get("way_files") or []
    production_files = discovery.get("production_files") or []

    _print_section("DISCOVERY SUMMARY")
    print(
        f"{'Country':<21}: "
        f"{_display_value(market.get('country'))}"
    )
    print(
        f"{'Store ID':<21}: "
        f"{_display_value(store.get('store_id'))}"
    )
    print(
        f"{'City':<21}: "
        f"{_display_value(store.get('city'))}"
    )
    print()
    print(f"{'POS Candidates':<21}: {len(pos_files)}")
    print(f"{'Itona Candidates':<21}: {len(candidates)}")
    print(f"{'WAY Files':<21}: {len(way_files)}")
    print(f"{'Production Files':<21}: {len(production_files)}")
    print()


def _print_pos_candidates(
    pos_files: List[Dict[str, Any]],
) -> None:
    _print_section("POS CANDIDATES")

    if not pos_files:
        print("No POS candidates discovered.")
        print()
        return

    print(f"Total: {len(pos_files)}")
    print()

    for pos in pos_files:
        print(_display_value(pos.get("file"), "<UNKNOWN FILE>"))
        print(
            "  Role: "
            + _display_value(pos.get("role"))
        )
        print(
            "  Role Source: "
            + _display_value(pos.get("role_source"))
        )
        print(
            "  Confidence: "
            + _display_value(pos.get("role_confidence"))
        )
        print(
            "  Status: "
            + _display_value(pos.get("role_status"))
        )

        node_candidates = pos.get("node_candidates") or []
        if node_candidates:
            print(
                "  Node Candidates: "
                + _display_list(node_candidates)
            )

        warnings = pos.get("warnings") or []
        if warnings:
            print("  Warnings:")
            for warning in warnings:
                print(f"    - {warning}")

        errors = pos.get("errors") or []
        if errors:
            print("  Errors:")
            for error in errors:
                print(f"    - {error}")

        print()


def _print_itona_type_summary(
    candidates: List[Dict[str, Any]],
) -> None:
    _print_section("ITONA TYPE SUMMARY")

    if not candidates:
        print("No Itona types available.")
        print()
        return

    type_counter = _count_itona_types(candidates)

    for name, total in sorted(type_counter.items()):
        print(f"{name:<15}: {total}")

    print()


def _print_type_evidence(
    candidate: Dict[str, Any],
) -> None:
    evidence = candidate.get("type_evidence") or {}

    if evidence:
        print("  Evidence:")

        for itona_type, entries in evidence.items():
            print(f"    {itona_type}:")

            for entry in entries or []:
                print(
                    "      - "
                    + _display_value(
                        entry.get("rule"),
                        "Unspecified classification rule",
                    )
                )
                print(
                    "        Strength: "
                    + _display_value(
                        entry.get("strength"),
                        "UNSPECIFIED",
                    )
                )
                print(
                    "        Source: "
                    + _display_value(entry.get("source"))
                )
                print(
                    "        Container: "
                    + _display_value(
                        entry.get("container"),
                        "NONE",
                    )
                )
                print(
                    "        Attribute: "
                    + _display_value(entry.get("attribute"))
                )
                print(
                    "        Value: "
                    + _display_value(entry.get("value"))
                )
                print(
                    "        Path: "
                    + _display_value(entry.get("path"))
                )

        return

    checked_sources = candidate.get("type_checked_sources") or []

    print("  Evidence: no supported type evidence found")

    if checked_sources:
        print("  Sources Checked:")
        for source in checked_sources:
            print(f"    - {source}")
    else:
        print("  Sources Checked: NONE")


def _print_itona_candidates(
    candidates: List[Dict[str, Any]],
) -> None:
    _print_section("ITONA CANDIDATES")

    if not candidates:
        print("No Itona candidates discovered.")
        print()
        return

    print(f"Total: {len(candidates)}")
    print()

    for candidate in candidates:
        print(
            _display_value(
                candidate.get("file"),
                "<UNKNOWN FILE>",
            )
        )
        print(
            "  Types: "
            + _display_list(
                candidate.get("kvs_types"),
                "UNKNOWN",
            )
        )
        print(
            "  Confidence: "
            + _display_value(
                candidate.get("type_confidence"),
                "NONE",
            )
        )
        print(
            "  Services: "
            + _display_list(
                candidate.get("kvs_services"),
                "NONE",
            )
        )
        print(
            "  NPW Services: "
            + _display_list(
                candidate.get("npw_services"),
                "NONE",
            )
        )
        print(
            "  Browser Nodes: "
            + _display_list(
                candidate.get("browser_nodes"),
                "NONE",
            )
        )
        print(
            "  Status: "
            + _display_value(
                candidate.get("type_status"),
                "REVIEW REQUIRED",
            )
        )

        _print_type_evidence(candidate)

        warnings = candidate.get("warnings") or []
        if warnings:
            print("  Warnings:")
            for warning in warnings:
                print(f"    - {warning}")

        errors = candidate.get("errors") or []
        if errors:
            print("  Errors:")
            for error in errors:
                print(f"    - {error}")

        print()


def _print_way_files(discovery: Dict[str, Any]) -> None:
    _print_section("WAY FILES")
    way_files = discovery.get("way_files") or []

    if not way_files:
        print("No WAY files discovered.")
    else:
        for way_file in way_files:
            print(way_file)

    print()


def _print_production_files(
    discovery: Dict[str, Any],
) -> None:
    _print_section("PRODUCTION FILES")
    production_files = discovery.get("production_files") or []

    if not production_files:
        print("No standard production file detected.")
        print(
            "The market may use a custom production "
            "naming convention."
        )
    else:
        for file_name in production_files:
            print(file_name)

    print()


def _print_phase_messages(
    discovery: Dict[str, Any],
) -> None:
    warnings = discovery.get("warnings") or []
    errors = discovery.get("errors") or []

    if warnings:
        _print_section("DISCOVERY WARNINGS")
        for warning in warnings:
            print(f"- {warning}")
        print()

    if errors:
        _print_section("DISCOVERY ERRORS")
        for error in errors:
            print(f"- {error}")
        print()


def print_builder_discovery_report(context: Any) -> None:
    """Print a detailed, human-readable Builder Discovery report."""
    discovery = context.source_validation or {}
    pos_discovery = context.discovered_pos or {}
    pos_files = pos_discovery.get("pos_files") or []
    candidates = context.discovered_itona_candidates or []

    print()
    print("=" * REPORT_WIDTH)
    print("POSDATA BUILDER DISCOVERY")
    print("=" * REPORT_WIDTH)
    print()

    _print_section("TEMPLATE")
    print(_display_value(context.template_market))
    print()

    _print_discovery_summary(
        context=context,
        discovery=discovery,
        pos_files=pos_files,
        candidates=candidates,
    )

    _print_pos_candidates(pos_files)
    _print_itona_type_summary(candidates)
    _print_itona_candidates(candidates)
    _print_way_files(discovery)
    _print_production_files(discovery)
    _print_phase_messages(discovery)

    _print_section("STATUS")
    print(_display_value(discovery.get("status")))
    print("=" * REPORT_WIDTH)
