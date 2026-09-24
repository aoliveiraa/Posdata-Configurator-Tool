"""Reports for PosData Builder generation results.

Creates:
    output/reports/builder_generation_report.txt
    output/reports/builder_generation_report.json
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping


DEFAULT_OUTPUT_ROOT = Path("output")
REPORTS_FOLDER_NAME = "reports"
TEXT_REPORT_NAME = "builder_generation_report.txt"
JSON_REPORT_NAME = "builder_generation_report.json"


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    result = str(value).strip()
    return result or default


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, (tuple, set)):
        return list(value)
    return [value]


def _unique_strings(values: Iterable[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = _text(value)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "__dict__"):
        return _json_safe(vars(value))
    return str(value)


def _read(source: Any, key: str, default: Any = None) -> Any:
    if source is None:
        return default
    if isinstance(source, Mapping):
        return source.get(key, default)
    return getattr(source, key, default)


def _result_name(item: Mapping[str, Any], fallback: str) -> str:
    for key in (
        "node_name",
        "target_node",
        "machine",
        "file",
        "source_file",
        "output_file",
    ):
        value = _text(item.get(key))
        if value:
            return value
    return fallback


def _summarize_items(items: Iterable[Any], prefix: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, raw_item in enumerate(items, start=1):
        item = dict(raw_item) if isinstance(raw_item, Mapping) else {}
        result.append(
            {
                "name": _result_name(item, f"{prefix}{index}"),
                "generated": item.get("generated") is True,
                "output_file": _text(item.get("output_file")) or None,
                "warnings": _unique_strings(_as_list(item.get("warnings"))),
                "errors": _unique_strings(_as_list(item.get("errors"))),
                "changes": _unique_strings(_as_list(item.get("changes"))),
            }
        )
    return result


def _collect_messages(groups: Iterable[Iterable[Any]], field: str) -> list[str]:
    messages: list[str] = []
    for group in groups:
        for raw_item in group:
            item = raw_item if isinstance(raw_item, Mapping) else {}
            messages.extend(_as_list(item.get(field)))
    return _unique_strings(messages)


def _resolve_market(builder_context: Any, runtime: Any) -> str:
    for source in (
        _read(builder_context, "market", {}),
        _read(runtime, "market", {}),
    ):
        if not isinstance(source, Mapping):
            continue
        value = source.get("country") or source.get("market") or source.get("code")
        if value:
            return _text(value, "UNKNOWN")
    return "UNKNOWN"


def _resolve_store_info(builder_context: Any, runtime: Any) -> dict[str, str]:
    store_id = ""
    city = ""
    for source in (
        _read(builder_context, "store_info", {}),
        _read(runtime, "store_info", {}),
        _read(builder_context, "market", {}),
    ):
        if not isinstance(source, Mapping):
            continue
        if not store_id:
            store_id = _text(
                source.get("store_id")
                or source.get("store")
                or source.get("store_number")
            )
        if not city:
            city = _text(source.get("city") or source.get("store_city"))
    return {"store_id": store_id or "UNKNOWN", "city": city or "UNKNOWN"}


def _normalize_way_result(runtime: Any) -> list[Any]:
    value = _read(runtime, "generated_way", {})
    if isinstance(value, Mapping):
        return [dict(value)] if value else []
    return _as_list(value)


def _artifact_section(items: list[dict[str, Any]]) -> dict[str, Any]:
    generated_count = sum(1 for item in items if item["generated"])
    return {
        "total_results": len(items),
        "generated_count": generated_count,
        "not_generated_count": len(items) - generated_count,
        "items": items,
    }


def build_builder_generation_report_data(
    runtime: Any,
    builder_context: Any = None,
    output_root: str | Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, Any]:
    """Builds report data without writing files."""

    resolved_output_root = Path(output_root)

    pos_raw = _as_list(_read(runtime, "generated_pos", []))
    itona_raw = _as_list(_read(runtime, "generated_itonas", []))
    production_raw = _as_list(_read(runtime, "generated_production", []))
    way_raw = _normalize_way_result(runtime)
    foe_raw = _as_list(_read(runtime, "generated_foe", []))
    cod_raw = _as_list(_read(runtime, "generated_cod", []))

    pos = _artifact_section(_summarize_items(pos_raw, "POS"))
    itonas = _artifact_section(_summarize_items(itona_raw, "Itona"))
    production = _artifact_section(_summarize_items(production_raw, "Production"))
    way = _artifact_section(_summarize_items(way_raw, "WAY"))

    store_db = _read(runtime, "store_db_generation", {}) or {}
    validation = _read(runtime, "validation_summary", {}) or {}
    validation_status = _text(validation.get("status"), "UNKNOWN").upper()

    adapter_warnings = _unique_strings(
        _as_list(_read(runtime, "builder_adapter_warnings", []))
    )
    adapter_errors = _unique_strings(
        _as_list(_read(runtime, "builder_adapter_errors", []))
    )

    all_groups = [pos_raw, itona_raw, production_raw, way_raw, foe_raw, cod_raw]
    warnings = _unique_strings(
        _collect_messages(all_groups, "warnings") + adapter_warnings
    )
    errors = _unique_strings(
        _collect_messages(all_groups, "errors")
        + _as_list(store_db.get("errors"))
        + adapter_errors
    )

    overall_status = "SUCCESS"
    if validation_status != "PASS" or errors:
        overall_status = "FAIL"
    elif warnings or any(
        section["not_generated_count"] > 0
        for section in (pos, itonas, production, way)
    ):
        overall_status = "SUCCESS WITH OBSERVATIONS"

    store_info = _resolve_store_info(builder_context, runtime)

    data = {
        "report": {
            "name": "PosData Builder Generation Report",
            "generated_at": datetime.now().astimezone().isoformat(),
            "overall_status": overall_status,
        },
        "build": {
            "market": _resolve_market(builder_context, runtime),
            "template_market": _text(
                _read(builder_context, "template_market", None), "UNKNOWN"
            ),
            "laboratory": _text(
                _read(builder_context, "selected_lab", None)
                or _read(runtime, "selected_lab", None),
                "UNKNOWN",
            ),
            "store_id": store_info["store_id"],
            "city": store_info["city"],
            "source_posdata_folder": _text(
                _read(builder_context, "source_posdata_folder", None)
                or _read(runtime, "new_posdata_folder", None),
                "UNKNOWN",
            ),
            "template_folder": _text(
                _read(builder_context, "template_folder", None)
                or _read(runtime, "current_posdata_folder", None),
                "UNKNOWN",
            ),
            "output_folder": str(resolved_output_root),
        },
        "adapter": {
            "status": _text(
                _read(runtime, "builder_adapter_status", None), "UNKNOWN"
            ),
            "warnings": adapter_warnings,
            "errors": adapter_errors,
        },
        "store_db": {
            "prepared": bool(store_db.get("prepared")),
            "source_file": _text(store_db.get("source_file")) or None,
            "output_file": _text(store_db.get("output_file")) or None,
            "warnings": _unique_strings(_as_list(store_db.get("warnings"))),
            "errors": _unique_strings(_as_list(store_db.get("errors"))),
        },
        "pos": pos,
        "itonas": itonas,
        "production": production,
        "way": way,
        "validation": {
            "status": validation_status,
            "total": int(validation.get("total", 0) or 0),
            "passed": int(validation.get("passed", 0) or 0),
            "failed": int(validation.get("failed", 0) or 0),
            "skipped": int(validation.get("skipped", 0) or 0),
            "report_file": str(
                resolved_output_root / "validation" / "validation_report.txt"
            ),
        },
        "warnings": warnings,
        "errors": errors,
    }
    return _json_safe(data)


def _append_artifact_details(
    lines: list[str], title: str, section: Mapping[str, Any]
) -> None:
    lines.extend(["", title, "-" * 80])
    items = section.get("items") or []
    if not items:
        lines.append("No results.")
        return
    for item in items:
        status = "GENERATED" if item.get("generated") else "NOT GENERATED"
        lines.append(f"- {item.get('name', 'UNKNOWN')} [{status}]")
        if item.get("output_file"):
            lines.append(f"  Output: {item['output_file']}")
        for warning in item.get("warnings") or []:
            lines.append(f"  Warning: {warning}")
        for error in item.get("errors") or []:
            lines.append(f"  Error: {error}")


def _append_messages(lines: list[str], title: str, messages: Iterable[str]) -> None:
    values = list(messages)
    lines.extend(["", title, "-" * 80])
    if not values:
        lines.append("None")
        return
    lines.extend(f"- {message}" for message in values)


def render_builder_generation_text(report_data: Mapping[str, Any]) -> str:
    """Renders the report as plain text."""

    report = report_data.get("report", {})
    build = report_data.get("build", {})
    adapter = report_data.get("adapter", {})
    store_db = report_data.get("store_db", {})
    pos = report_data.get("pos", {})
    itonas = report_data.get("itonas", {})
    production = report_data.get("production", {})
    way = report_data.get("way", {})
    validation = report_data.get("validation", {})

    lines = [
        "POSDATA BUILDER GENERATION REPORT",
        "=" * 80,
        "",
        "EXECUTIVE SUMMARY",
        "-" * 80,
        f"Generated At      : {report.get('generated_at', 'UNKNOWN')}",
        f"Overall Status    : {report.get('overall_status', 'UNKNOWN')}",
        f"Validation Status : {validation.get('status', 'UNKNOWN')}",
        "",
        "BUILD INFORMATION",
        "-" * 80,
        f"Market            : {build.get('market', 'UNKNOWN')}",
        f"Template Market   : {build.get('template_market', 'UNKNOWN')}",
        f"Laboratory        : {build.get('laboratory', 'UNKNOWN')}",
        f"Store ID          : {build.get('store_id', 'UNKNOWN')}",
        f"City              : {build.get('city', 'UNKNOWN')}",
        f"Source PosData    : {build.get('source_posdata_folder', 'UNKNOWN')}",
        f"Template Folder   : {build.get('template_folder', 'UNKNOWN')}",
        f"Output Folder     : {build.get('output_folder', 'UNKNOWN')}",
        "",
        "GENERATION ADAPTER",
        "-" * 80,
        f"Status            : {adapter.get('status', 'UNKNOWN')}",
        "",
        "STOREDB",
        "-" * 80,
        f"Prepared          : {'YES' if store_db.get('prepared') else 'NO'}",
        f"Source            : {store_db.get('source_file') or 'NONE'}",
        f"Output            : {store_db.get('output_file') or 'NONE'}",
        "",
        "ARTIFACT SUMMARY",
        "-" * 80,
        f"POS Generated     : {pos.get('generated_count', 0)}",
        f"POS Not Generated : {pos.get('not_generated_count', 0)}",
        f"Itonas Generated  : {itonas.get('generated_count', 0)}",
        f"Itonas Not Gen.   : {itonas.get('not_generated_count', 0)}",
        f"Production Gen.   : {production.get('generated_count', 0)}",
        f"Production Not G. : {production.get('not_generated_count', 0)}",
        f"WAY Generated     : {way.get('generated_count', 0)}",
        f"WAY Not Generated : {way.get('not_generated_count', 0)}",
        "",
        "VALIDATION",
        "-" * 80,
        f"Status            : {validation.get('status', 'UNKNOWN')}",
        f"Checks Executed   : {validation.get('total', 0)}",
        f"Passed            : {validation.get('passed', 0)}",
        f"Failed            : {validation.get('failed', 0)}",
        f"Skipped           : {validation.get('skipped', 0)}",
        f"Report            : {validation.get('report_file', 'UNKNOWN')}",
    ]

    _append_artifact_details(lines, "POS DETAILS", pos)
    _append_artifact_details(lines, "ITONA DETAILS", itonas)
    _append_artifact_details(lines, "PRODUCTION DETAILS", production)
    _append_artifact_details(lines, "WAY DETAILS", way)
    _append_messages(lines, "WARNINGS", report_data.get("warnings", []))
    _append_messages(lines, "ERRORS", report_data.get("errors", []))
    lines.extend(["", "END OF REPORT", "=" * 80, ""])
    return "\n".join(lines)


def generate_builder_generation_report(
    runtime: Any,
    builder_context: Any = None,
    output_root: str | Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, Any]:
    """Writes TXT and JSON reports and returns their paths and data."""

    result: dict[str, Any] = {
        "generated": False,
        "status": "FAIL",
        "reports_folder": None,
        "text_report": None,
        "json_report": None,
        "data": {},
        "warnings": [],
        "errors": [],
    }

    try:
        output_root_path = Path(output_root)
        report_data = build_builder_generation_report_data(
            runtime=runtime,
            builder_context=builder_context,
            output_root=output_root_path,
        )

        reports_folder = output_root_path / REPORTS_FOLDER_NAME
        reports_folder.mkdir(parents=True, exist_ok=True)

        text_report_path = reports_folder / TEXT_REPORT_NAME
        json_report_path = reports_folder / JSON_REPORT_NAME

        text_report_path.write_text(
            render_builder_generation_text(report_data), encoding="utf-8"
        )
        json_report_path.write_text(
            json.dumps(report_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        if not text_report_path.is_file() or not json_report_path.is_file():
            raise FileNotFoundError("Builder generation reports were not created.")

        result.update(
            {
                "generated": True,
                "status": "READY",
                "reports_folder": str(reports_folder),
                "text_report": str(text_report_path),
                "json_report": str(json_report_path),
                "data": report_data,
                "warnings": list(report_data.get("warnings", [])),
                "errors": [],
            }
        )
    except Exception as error:
        result["errors"].append(str(error))

    return result


# Compatibility alias.
write_builder_generation_report = generate_builder_generation_report
