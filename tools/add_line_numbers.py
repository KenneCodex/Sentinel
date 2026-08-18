#!/usr/bin/env python3
"""Generate line-numbered review copies for repository documents.

Default behavior is non-destructive: numbered copies are written under
.line-numbered/ while preserving relative paths. Use --in-place only for
sealed audit exports or intentionally numbered artifacts.
"""

from __future__ import annotations

import argparse
import os
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


def iter_documents(
    root: Path,
    extensions: set[str],
    excludes: set[str],
    output_root: Path | None = None,
) -> Iterable[Path]:
    """Yield matching documents while pruning excluded directories during traversal."""
    resolved_output = output_root.resolve() if output_root else None

    for dirpath, dirnames, filenames in os.walk(root):
        current_dir = Path(dirpath)
        dirnames[:] = sorted(
            dirname
            for dirname in dirnames
            if dirname not in excludes
            and (resolved_output is None or (current_dir / dirname).resolve() != resolved_output)
        )

        for filename in sorted(filenames):
            if filename in excludes:
                continue
            path = current_dir / filename
            if path.suffix.lower() in extensions:
                yield path


def split_lines(text: str) -> list[str]:
    """Split text into lines using only the \\n and \\r\\n newline conventions.

    Unlike str.splitlines(), this does not treat other Unicode line-boundary
    characters (\\v, \\f, \\x1c-\\x1e, \\x85, \\u2028, \\u2029) or a lone \\r as
    line breaks. Those characters are content, not newlines, and must survive
    numbering unchanged instead of being silently replaced by the file's
    detected newline convention.
    """
    if text == "":
        return []
    parts = text.split("\n")
    if parts and parts[-1] == "":
        parts.pop()
    return [part[:-1] if part.endswith("\r") else part for part in parts]


def already_numbered(lines: list[str]) -> bool:
    sample = [line for line in lines[:10] if line.strip()]
    if not sample:
        return False
    for line in sample[:3]:
        if not line.startswith("L"):
            return False
        parts = line.split(" | ", 1)
        if len(parts) < 2 or not parts[0][1:].isdigit():
            return False
    return True


def numbered_text(text: str, width: int) -> str:
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = split_lines(text)
    numbered = [f"L{idx:0{width}d} | {line}" for idx, line in enumerate(lines, start=1)]
    suffix = newline if text.endswith(newline) else ("\n" if text.endswith("\n") else "")
    return newline.join(numbered) + suffix


def write_numbered_copy(path: Path, root: Path, output_root: Path, width: int, force: bool) -> Path | None:
    text = path.read_text(encoding="utf-8")
    lines = split_lines(text)
    if already_numbered(lines) and not force:
        return None

    relative = path.relative_to(root)
    target = output_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(numbered_text(text, width), encoding="utf-8")
    return target


def number_in_place(path: Path, width: int, force: bool) -> bool:
    text = path.read_text(encoding="utf-8")
    lines = split_lines(text)
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
    for path in iter_documents(root, extensions, excludes, None if args.in_place else output_root):
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
