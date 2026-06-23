#!/usr/bin/env python3
"""Generate line-numbered review copies for repository documents.

Default behavior is non-destructive: numbered copies are written under
.line-numbered/ while preserving relative paths. Use --in-place only for
sealed audit exports or intentionally numbered artifacts.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

DEFAULT_EXTENSIONS = {".md", ".markdown", ".txt", ".rst", ".adoc"}
DEFAULT_EXCLUDES = {
    ".git",
    ".line-numbered",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    "__pycache__",
}


def is_excluded(path: Path, root: Path, excludes: set[str]) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True
    return any(part in excludes for part in relative.parts)


def iter_documents(root: Path, extensions: set[str], excludes: set[str]) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if is_excluded(path, root, excludes):
            continue
        if path.suffix.lower() in extensions:
            yield path


def already_numbered(lines: list[str]) -> bool:
    sample = [line for line in lines[:10] if line.strip()]
    if not sample:
        return False
    return all(line.startswith("L") and " | " in line[:12] for line in sample[:3])


def numbered_text(text: str, width: int) -> str:
    lines = text.splitlines()
    numbered = [f"L{idx:0{width}d} | {line}" for idx, line in enumerate(lines, start=1)]
    suffix = "\n" if text.endswith("\n") else ""
    return "\n".join(numbered) + suffix


def write_numbered_copy(path: Path, root: Path, output_root: Path, width: int, force: bool) -> Path | None:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if already_numbered(lines) and not force:
        return None

    relative = path.relative_to(root)
    target = output_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(numbered_text(text, width), encoding="utf-8")
    return target


def number_in_place(path: Path, width: int, force: bool) -> bool:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if already_numbered(lines) and not force:
        return False
    path.write_text(numbered_text(text, width), encoding="utf-8")
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate line-numbered document review copies.")
    parser.add_argument("--root", default=".", help="Repository or document root to scan.")
    parser.add_argument("--output", default=".line-numbered", help="Output directory for sidecar copies.")
    parser.add_argument("--extensions", nargs="*", default=sorted(DEFAULT_EXTENSIONS), help="File extensions to number.")
    parser.add_argument("--exclude", nargs="*", default=sorted(DEFAULT_EXCLUDES), help="Directory names to skip.")
    parser.add_argument("--width", type=int, default=4, help="Zero-padding width for line numbers.")
    parser.add_argument("--in-place", action="store_true", help="Rewrite matching files in place. Use only for sealed artifacts.")
    parser.add_argument("--force", action="store_true", help="Renumber files that already look numbered.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    output_root = Path(args.output).resolve()
    extensions = {ext if ext.startswith(".") else f".{ext}" for ext in args.extensions}
    excludes = set(args.exclude)

    if not root.exists():
        raise SystemExit(f"Root does not exist: {root}")

    changed = []
    skipped = []
    for path in iter_documents(root, extensions, excludes):
        if args.in_place:
            did_change = number_in_place(path, args.width, args.force)
            (changed if did_change else skipped).append(path)
        else:
            target = write_numbered_copy(path, root, output_root, args.width, args.force)
            (changed if target else skipped).append(target or path)

    print(f"Documents processed: {len(changed) + len(skipped)}")
    print(f"Documents numbered: {len(changed)}")
    print(f"Documents skipped: {len(skipped)}")
    if not args.in_place:
        print(f"Output root: {output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
