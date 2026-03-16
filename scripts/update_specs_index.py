#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parent.parent
SPECS_DIR = REPO_ROOT / "specs"
INDEX_PATH = SPECS_DIR / "INDEX.md"
SUPPORTED_EXTENSIONS = {".md", ".xlsx", ".xls", ".docx", ".pdf"}


@dataclass
class SpecEntry:
    relative_path: Path
    base_key: str
    date_text: str
    title: str
    fmt: str


def extract_date_from_path(path: Path) -> str:
    match = re.match(r"^(\d{4}-\d{2}-\d{2})", path.name)
    if match:
        return match.group(1)
    return "-"


def normalize_title(path: Path) -> str:
    if path.suffix.lower() == ".md":
        first_heading = read_first_heading(path)
        if first_heading:
            return first_heading
    else:
        sibling_md = path.with_suffix(".md")
        if sibling_md.exists():
            first_heading = read_first_heading(sibling_md)
            if first_heading:
                return first_heading
    return path.stem.replace("-", " ").replace("_", " ").strip().title()


def read_first_heading(path: Path) -> str | None:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip()
    except UnicodeDecodeError:
        return None
    return None


def collect_entries() -> list[SpecEntry]:
    if not SPECS_DIR.exists():
        return []

    entries: list[SpecEntry] = []
    for path in SPECS_DIR.rglob("*"):
        if not path.is_file():
            continue
        if path == INDEX_PATH:
            continue
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        relative_path = path.relative_to(REPO_ROOT)
        base_key = relative_path.with_suffix("").as_posix()
        date_text = extract_date_from_path(path)
        title = normalize_title(path)
        fmt = path.suffix.lower().lstrip(".")
        entries.append(SpecEntry(relative_path, base_key, date_text, title, fmt))

    entries.sort(key=lambda e: (e.date_text, str(e.relative_path)), reverse=True)
    return entries


def build_markdown(entries: list[SpecEntry]) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Реестр технических заданий",
        "",
        f"_Автообновлено: {generated_at}_",
        "",
        "## Общий список",
        "",
        "| № | Дата | Название | Файлы |",
        "|---:|---|---|---|",
    ]

    if not entries:
        lines.append("| 1 | - | (пока пусто) | - |")
    else:
        grouped: dict[str, dict[str, object]] = {}
        for entry in entries:
            if entry.base_key not in grouped:
                grouped[entry.base_key] = {
                    "date_text": entry.date_text,
                    "title": entry.title,
                    "files": [],
                }
            files = grouped[entry.base_key]["files"]
            assert isinstance(files, list)
            files.append(entry.relative_path)

        sorted_groups = sorted(
            grouped.values(),
            key=lambda g: (str(g["date_text"]), str(g["title"])),
            reverse=True,
        )
        for idx, group in enumerate(sorted_groups, start=1):
            files = group["files"]
            assert isinstance(files, list)
            files = sorted(files, key=lambda p: p.suffix)
            files_text = ", ".join(
                f"[{path.as_posix()}]({path.as_posix()})" for path in files
            )
            lines.append(
                f"| {idx} | {group['date_text']} | {group['title']} | {files_text} |"
            )

    lines.extend(
        [
            "",
            "## Как добавить новое ТЗ",
            "",
            "1. Сохранить файл в `specs/<год>/` с датой в начале имени, например:",
            "   - `specs/2026/2026-03-16-my-spec.md`",
            "   - `specs/2026/2026-03-16-my-spec.xlsx`",
            "2. Обновить общий реестр:",
            "   - `python3 scripts/update_specs_index.py`",
            "3. Закоммитить изменения.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    entries = collect_entries()
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(build_markdown(entries), encoding="utf-8")
    print(f"Updated {INDEX_PATH}")


if __name__ == "__main__":
    main()
