#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
FILES = [
    ROOT / "apps/frontend/package.json",
    ROOT / "apps/frontend/package-lock.json",
    ROOT / "apps/cli/pyproject.toml",
    ROOT / "apps/backend/pyproject.toml",
]


def sync_json_version(path: Path) -> bool:
    data = json.loads(path.read_text(encoding="utf-8"))
    changed = data.get("version") != VERSION
    data["version"] = VERSION
    if "packages" in data and "" in data["packages"]:
        changed = changed or data["packages"][""].get("version") != VERSION
        data["packages"][""]["version"] = VERSION
    if changed:
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return changed


def sync_poetry_version(path: Path) -> bool:
    content = path.read_text(encoding="utf-8")
    updated = re.sub(
        r'(?m)^version = "[^"]+"$',
        f'version = "{VERSION}"',
        content,
        count=1,
    )
    if updated != content:
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def json_version_matches(path: Path) -> bool:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != VERSION:
        return False
    if "packages" in data and "" in data["packages"]:
        return data["packages"][""].get("version") == VERSION
    return True


def poetry_version_matches(path: Path) -> bool:
    content = path.read_text(encoding="utf-8")
    match = re.search(r'(?m)^version = "([^"]+)"$', content)
    return bool(match and match.group(1) == VERSION)


def check_versions() -> list[Path]:
    mismatched = []
    for path in FILES[:2]:
        if not json_version_matches(path):
            mismatched.append(path)
    for path in FILES[2:]:
        if not poetry_version_matches(path):
            mismatched.append(path)
    return mismatched


def sync_versions() -> list[Path]:
    changed = []
    for path in FILES[:2]:
        if sync_json_version(path):
            changed.append(path)
    for path in FILES[2:]:
        if sync_poetry_version(path):
            changed.append(path)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Synchronize component package metadata with root VERSION."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if component package metadata is not synchronized.",
    )
    args = parser.parse_args()

    if args.check:
        mismatched = check_versions()
        if mismatched:
            print("Component metadata is not synchronized with VERSION.")
            for path in mismatched:
                print(f"Out of sync: {path.relative_to(ROOT)}")
            print("Run: python scripts/sync-version.py")
            return 1
        print(f"Component metadata is synchronized to {VERSION}")
        return 0

    changed = sync_versions()
    if changed:
        print(f"Synchronized component metadata to {VERSION}")
    else:
        print(f"Component metadata already synchronized to {VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
