from __future__ import annotations

import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


POSDATA_TEXT_EXTENSIONS = {
    ".xml",
    ".json",
    ".ini",
    ".cfg",
    ".conf",
    ".properties",
    ".txt",
    ".csv",
    ".bat",
    ".cmd",
}

IGNORED_NAMES = {
    ".git",
    ".svn",
    "__pycache__",
    "thumbs.db",
    ".ds_store",
}


@dataclass
class XmlChange:
    kind: str
    location: str
    before: str | None = None
    after: str | None = None


@dataclass
class FileComparison:
    relative_path: str
    category: str
    status: str
    current_hash: str | None = None
    new_hash: str | None = None
    xml_changes: list[XmlChange] = field(default_factory=list)
    note: str | None = None


@dataclass
class PosDataComparison:
    current_folder: str
    new_folder: str
    generated_at: str
    added: list[FileComparison] = field(default_factory=list)
    removed: list[FileComparison] = field(default_factory=list)
    modified: list[FileComparison] = field(default_factory=list)
    unchanged_count: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed or self.modified)

    @property
    def totals(self) -> dict[str, int]:
        return {
            "added": len(self.added),
            "removed": len(self.removed),
            "modified": len(self.modified),
            "unchanged": self.unchanged_count,
            "errors": len(self.errors),
        }

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["has_changes"] = self.has_changes
        result["totals"] = self.totals
        return result


def normalize_name(value: str) -> str:
    return value.strip().lower()


def should_ignore(path: Path) -> bool:
    return any(normalize_name(part) in IGNORED_NAMES for part in path.parts)


def discover_files(folder: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for path in folder.rglob("*"):
        if not path.is_file() or should_ignore(path.relative_to(folder)):
            continue
        relative = path.relative_to(folder).as_posix()
        files[relative.lower()] = path
    return files


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify_file(relative_path: str) -> str:
    name = Path(relative_path).name.upper()

    if name == "STORE-DB.XML":
        return "STOREDB"
    if name == "SCREEN.XML":
        return "SCREEN"
    if "WAYSTATION" in name or re.search(r"(?:^|_)WAY(?:_|-)", name):
        return "WAY"
    if "ITONA" in name:
        return "ITONA"
    if re.search(r"(?:^|_)KVS\d+", name):
        return "KVS"
    if re.search(r"(?:^|_)POS\d+", name) or "POS-DB.XML" in name:
        return "POS"
    if "PROD" in name or "PRODUCTION" in name:
        return "PRODUCTION"
    if "COD" in name:
        return "COD"
    return "OTHER"


def local_tag(tag: str) -> str:
    return tag.split("}", 1)[-1]


def element_identity(element: ET.Element, position: int) -> str:
    for attribute in ("name", "type", "id", "key", "alias"):
        value = element.attrib.get(attribute)
        if value:
            return f"{local_tag(element.tag)}[@{attribute}='{value}']"
    return f"{local_tag(element.tag)}[{position}]"


def xml_leaf_map(root: ET.Element) -> dict[str, str]:
    values: dict[str, str] = {}

    def visit(element: ET.Element, path: str) -> None:
        children = list(element)

        for attribute, value in sorted(element.attrib.items()):
            values[f"{path}/@{attribute}"] = value.strip()

        text = (element.text or "").strip()
        if text:
            values[f"{path}/#text"] = text

        sibling_counts: Counter[str] = Counter()
        for child in children:
            tag = local_tag(child.tag)
            sibling_counts[tag] += 1
            child_path = f"{path}/{element_identity(child, sibling_counts[tag])}"
            visit(child, child_path)

    visit(root, f"/{local_tag(root.tag)}")
    return values


def compare_xml(current_file: Path, new_file: Path) -> tuple[list[XmlChange], str | None]:
    try:
        current_root = ET.parse(current_file).getroot()
        new_root = ET.parse(new_file).getroot()
    except ET.ParseError as error:
        return [], f"XML parsing failed: {error}"

    current_values = xml_leaf_map(current_root)
    new_values = xml_leaf_map(new_root)
    all_locations = sorted(set(current_values) | set(new_values))
    changes: list[XmlChange] = []

    for location in all_locations:
        before = current_values.get(location)
        after = new_values.get(location)
        if before == after:
            continue
        if before is None:
            kind = "ADDED"
        elif after is None:
            kind = "REMOVED"
        else:
            kind = "CHANGED"
        changes.append(
            XmlChange(
                kind=kind,
                location=location,
                before=before,
                after=after,
            )
        )

    return changes, None


def compare_posdata(current_folder: str | Path, new_folder: str | Path) -> PosDataComparison:
    current_root = Path(current_folder).expanduser().resolve()
    new_root = Path(new_folder).expanduser().resolve()

    if not current_root.is_dir():
        raise FileNotFoundError(f"Current PosData folder was not found: {current_root}")
    if not new_root.is_dir():
        raise FileNotFoundError(f"New PosData folder was not found: {new_root}")

    result = PosDataComparison(
        current_folder=str(current_root),
        new_folder=str(new_root),
        generated_at=datetime.now().isoformat(timespec="seconds"),
    )

    current_files = discover_files(current_root)
    new_files = discover_files(new_root)
    current_keys = set(current_files)
    new_keys = set(new_files)

    for key in sorted(new_keys - current_keys):
        path = new_files[key]
        result.added.append(
            FileComparison(
                relative_path=path.relative_to(new_root).as_posix(),
                category=classify_file(key),
                status="ADDED",
                new_hash=sha256_file(path),
            )
        )

    for key in sorted(current_keys - new_keys):
        path = current_files[key]
        result.removed.append(
            FileComparison(
                relative_path=path.relative_to(current_root).as_posix(),
                category=classify_file(key),
                status="REMOVED",
                current_hash=sha256_file(path),
            )
        )

    for key in sorted(current_keys & new_keys):
        current_file = current_files[key]
        new_file = new_files[key]
        current_hash = sha256_file(current_file)
        new_hash = sha256_file(new_file)

        if current_hash == new_hash:
            result.unchanged_count += 1
            continue

        comparison = FileComparison(
            relative_path=new_file.relative_to(new_root).as_posix(),
            category=classify_file(key),
            status="MODIFIED",
            current_hash=current_hash,
            new_hash=new_hash,
        )

        if new_file.suffix.lower() == ".xml":
            changes, note = compare_xml(current_file, new_file)
            comparison.xml_changes = changes
            comparison.note = note

        result.modified.append(comparison)

    return result


def group_by_category(items: Iterable[FileComparison]) -> dict[str, list[FileComparison]]:
    grouped: dict[str, list[FileComparison]] = {}
    for item in items:
        grouped.setdefault(item.category, []).append(item)
    return dict(sorted(grouped.items()))


def release_notes_text(result: PosDataComparison, max_xml_changes: int = 100) -> str:
    totals = result.totals
    lines = [
        "POSDATA RELEASE NOTES",
        "=" * 72,
        f"Current PosData: {result.current_folder}",
        f"New PosData    : {result.new_folder}",
        f"Generated at   : {result.generated_at}",
        "",
        "SUMMARY",
        "-" * 72,
        f"Added files    : {totals['added']}",
        f"Removed files  : {totals['removed']}",
        f"Modified files : {totals['modified']}",
        f"Unchanged files: {totals['unchanged']}",
        f"Errors         : {totals['errors']}",
        "",
    ]

    if not result.has_changes:
        lines.extend(["No differences were found.", ""])

    for title, items in (
        ("ADDED FILES", result.added),
        ("REMOVED FILES", result.removed),
        ("MODIFIED FILES", result.modified),
    ):
        if not items:
            continue
        lines.extend([title, "-" * 72])
        for category, category_items in group_by_category(items).items():
            lines.append(f"[{category}]")
            for item in category_items:
                prefix = "+" if item.status == "ADDED" else "-" if item.status == "REMOVED" else "*"
                lines.append(f"  {prefix} {item.relative_path}")

                if item.note:
                    lines.append(f"      Note: {item.note}")

                if item.xml_changes:
                    for change in item.xml_changes[:max_xml_changes]:
                        if change.kind == "ADDED":
                            detail = f"added = {change.after!r}"
                        elif change.kind == "REMOVED":
                            detail = f"removed (was {change.before!r})"
                        else:
                            detail = f"{change.before!r} -> {change.after!r}"
                        lines.append(f"      {change.kind}: {change.location}: {detail}")

                    hidden = len(item.xml_changes) - max_xml_changes
                    if hidden > 0:
                        lines.append(f"      ... {hidden} additional XML changes omitted")
            lines.append("")

    if result.errors:
        lines.extend(["ERRORS", "-" * 72])
        lines.extend(f"  - {error}" for error in result.errors)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def save_release_notes(
    result: PosDataComparison,
    output_folder: str | Path = "output/compare",
    base_name: str = "posdata_release_notes",
) -> dict[str, Path]:
    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)

    text_path = output_path / f"{base_name}.txt"
    json_path = output_path / f"{base_name}.json"

    text_path.write_text(release_notes_text(result), encoding="utf-8")
    json_path.write_text(
        json.dumps(result.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return {
        "text": text_path,
        "json": json_path,
    }


def compare_and_generate_release_notes(
    current_folder: str | Path,
    new_folder: str | Path,
    output_folder: str | Path = "output/compare",
) -> tuple[PosDataComparison, dict[str, Path]]:
    result = compare_posdata(current_folder, new_folder)
    outputs = save_release_notes(result, output_folder)
    return result, outputs


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare Current and New PosData folders and generate release notes."
    )
    parser.add_argument("current", help="Path to Current PosData folder")
    parser.add_argument("new", help="Path to New PosData folder")
    parser.add_argument(
        "--output",
        default="output/compare",
        help="Release notes output folder",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    result, outputs = compare_and_generate_release_notes(
        current_folder=arguments.current,
        new_folder=arguments.new,
        output_folder=arguments.output,
    )

    print(release_notes_text(result))
    print(f"Text report: {outputs['text']}")
    print(f"JSON report: {outputs['json']}")
    return 0 if not result.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
