"""Import active Prism mod, resource pack, or shader pack metadata into Packwiz.

Does not copy archives, delete any files, or modify the Prism instance.
Run in your Packwiz pack directory (containing pack.toml).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tomllib
from pathlib import Path

CATEGORIES = ("resourcepacks", "shaderpacks")
EXCLUDED_MOD_METADATA = frozenset({"lambdynamiclights.pw.toml"})


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--instance",
        "--main",
        dest="instance",
        default=os.environ.get("PACKWIZ_MAIN") or os.environ.get("PRISM_INSTANCE"),
        help="Path to Prism instance (also PACKWIZ_MAIN or PRISM_INSTANCE env)",
    )
    parser.add_argument(
        "--repo",
        default=os.environ.get("PACKWIZ_REPO") or os.getcwd(),
        help="Packwiz pack directory containing pack.toml (default: cwd or PACKWIZ_REPO)",
    )
    parser.add_argument("--apply", action="store_true", help="Write .pw.toml files; otherwise preview only")
    parser.add_argument(
        "--mods-only", action="store_true", help="Import active mod metadata instead of resource/shader packs"
    )
    parser.add_argument(
        "--only", action="append", metavar="NAME.pw.toml",
        help="Import only this metadata filename (repeatable)"
    )
    return parser.parse_args()


def locate_game_dir(instance: Path) -> Path:
    # Prism commonly uses minecraft/, but support .minecraft/ layouts as well.
    for directory in (instance / "minecraft", instance / ".minecraft"):
        if directory.is_dir():
            return directory
    raise ValueError(f"No minecraft/ or .minecraft/ directory found in: {instance}")


def main() -> int:
    args = arguments()
    instance_value = args.instance
    if not instance_value:
        instance_value = input("Prism instance path: ").strip()
    if not instance_value:
        print("Error: no Prism instance provided", file=sys.stderr)
        return 2
    instance = Path(instance_value).expanduser().resolve()
    repo = Path(args.repo).expanduser().resolve()
    if not (repo / "pack.toml").is_file():
        print(f"Error: no pack.toml in {repo}. Run in the Packwiz pack directory or use --repo.", file=sys.stderr)
        return 2
    try:
        game = locate_game_dir(instance)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(f"Prism:    {game}")
    print(f"Packwiz:  {repo}")
    print(f"Mode:     {'APPLY' if args.apply else 'DRY RUN'}\n")
    selected = set(args.only or ())
    categories = ("mods",) if args.mods_only else CATEGORIES
    active_resourcepacks = set()
    if "resourcepacks" in categories:
        try:
            lines = (game / "options.txt").read_text(encoding="utf-8").splitlines()
            selections = [line.partition(":")[2] for line in lines if line.startswith("resourcePacks:")]
            if len(selections) != 1:
                raise ValueError("Expected one resourcePacks entry in options.txt")
            active = json.loads(selections[0])
            if not isinstance(active, list) or not all(isinstance(item, str) for item in active):
                raise ValueError("resourcePacks must be a JSON list of strings")
            active_resourcepacks = {item[5:] for item in active if item.startswith("file/")}
        except (OSError, ValueError) as exc:
            print(f"Error reading enabled resource packs: {exc}", file=sys.stderr)
            return 1
    available = {
        meta.name
        for category in categories
        for meta in (game / category / ".index").glob("*.pw.toml")
        if category != "mods" or meta.name not in EXCLUDED_MOD_METADATA
    }
    if selected - available:
        for name in sorted(selected - available):
            print(f"ERROR: metadata not found: {name}", file=sys.stderr)
        return 1
    total = 0
    warnings = 0
    for category in categories:
        source = game / category
        dest = repo / category
        index = source / ".index"
        print(f"[{category}]")
        if not source.is_dir():
            print("  Source directory missing; skipped\n")
            continue
        known = set()
        excluded_files = set()
        for meta in sorted(index.glob("*.pw.toml")):
            if selected and meta.name not in selected:
                continue
            if category == "mods" and meta.name in EXCLUDED_MOD_METADATA:
                print(f"  SKIP excluded mod {meta.name}")
                try:
                    excluded_files.add(tomllib.loads(meta.read_text(encoding="utf-8"))["filename"])
                except (OSError, UnicodeError, KeyError, tomllib.TOMLDecodeError):
                    pass
                continue
            try:
                data = tomllib.loads(meta.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
                print(f"  WARNING invalid TOML {meta.name}: {exc}")
                warnings += 1
                continue
            filename = data.get("filename")
            if not isinstance(filename, str) or not filename or Path(filename).name != filename:
                print(f"  SKIP invalid/missing filename in {meta.name}")
                warnings += 1
                continue
            if category == "resourcepacks" and filename not in active_resourcepacks:
                print(f"  SKIP inactive resource pack {meta.name}")
                continue
            active_file = source / filename
            if not active_file.is_file():
                print(f"  SKIP unused metadata {meta.name} (missing: {filename})")
                continue
            known.add(filename)
            target = dest / meta.name
            if target.exists() and target.read_bytes() == meta.read_bytes():
                print(f"  OK   {meta.name} (unchanged)")
                continue
            if args.apply:
                dest.mkdir(parents=True, exist_ok=True)
                shutil.copy2(meta, target)
            print(f"  {'COPY' if args.apply else 'WOULD COPY'} {meta.name} -> {category}/")
            total += 1
        for asset in (sorted(source.iterdir()) if not selected else ()):
            if asset.name.startswith(".") or asset.name in known:
                continue
            if category == "resourcepacks" and asset.name not in active_resourcepacks:
                continue
            if asset.name in excluded_files:
                continue
            if asset.is_file() and asset.suffix.lower() == (".jar" if category == "mods" else ".zip"):
                print(f"  MANUAL: no active metadata for {asset.name}")
                warnings += 1
            elif asset.is_dir():
                print(f"  MANUAL: unpacked directory {asset.name}")
                warnings += 1
        if not index.is_dir():
            print("  NOTE: Prism .index/ does not exist here")
        print()
    print(f"{'Imported' if args.apply else 'Would import'}: {total} metadata file(s)")
    print(f"Manual checks: {warnings}")
    if args.apply:
        print("Next: packwiz refresh && packwiz list && packwiz modrinth export -o test.mrpack")
    else:
        print("Use --apply to copy metadata files. No files were changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
