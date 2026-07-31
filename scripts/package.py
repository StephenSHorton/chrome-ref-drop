#!/usr/bin/env python3
"""Build an installable Blender extension zip for Chrome Reference Drop.

The archive root is the `chrome_ref_drop/` package (required by Blender's
Install from Disk / extensions flow).
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "chrome_ref_drop"
MANIFEST = PACKAGE / "blender_manifest.toml"

SKIP_DIR_NAMES = {"__pycache__", ".git", ".github"}
SKIP_SUFFIXES = {".pyc", ".pyo", ".zip"}


def read_version() -> str:
    text = MANIFEST.read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not m:
        raise SystemExit("Could not parse version from blender_manifest.toml")
    return m.group(1)


def should_include(path: Path) -> bool:
    rel_parts = path.relative_to(PACKAGE).parts
    if any(part in SKIP_DIR_NAMES for part in rel_parts):
        return False
    if path.suffix.lower() in SKIP_SUFFIXES:
        return False
    return True


def build_zip(out_path: Path) -> list[str]:
    if not PACKAGE.is_dir():
        raise SystemExit(f"Missing package directory: {PACKAGE}")
    if not MANIFEST.is_file():
        raise SystemExit(f"Missing manifest: {MANIFEST}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    written: list[str] = []
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(PACKAGE.rglob("*")):
            if not path.is_file() or not should_include(path):
                continue
            arcname = Path("chrome_ref_drop") / path.relative_to(PACKAGE)
            zf.write(path, arcname.as_posix())
            written.append(arcname.as_posix())

    if "chrome_ref_drop/blender_manifest.toml" not in written:
        raise SystemExit("Zip is missing chrome_ref_drop/blender_manifest.toml")
    if "chrome_ref_drop/__init__.py" not in written:
        raise SystemExit("Zip is missing chrome_ref_drop/__init__.py")
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output zip path (default: dist/chrome_ref_drop-<version>.zip)",
    )
    parser.add_argument(
        "--name-only",
        action="store_true",
        help="Print the default artifact filename and exit",
    )
    args = parser.parse_args(argv)

    version = read_version()
    default_name = f"chrome_ref_drop-{version}.zip"
    if args.name_only:
        print(default_name)
        return 0

    out = args.output or (ROOT / "dist" / default_name)
    files = build_zip(out.resolve())
    size = out.stat().st_size
    print(f"Built {out} ({size} bytes, {len(files)} files)")
    for f in files:
        print(f"  {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
