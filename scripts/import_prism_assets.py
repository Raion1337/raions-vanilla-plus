"""Import active resource/shader pack metadata from a Prism instance into Packwiz.

Does not copy ZIPs, delete any files, or modify the Prism instance.
Run in your Packwiz pack directory (containing pack.toml).
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tomllib
from pathlib import Path

CATEGORIES = ("resourcepacks", "shaderpacks")


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
    total = 0
    warnings = 0
    for category in CATEGORIES:
        source = game / category
        dest = repo / category
        index = source / ".index"
        print(f"[{category}]")
        if not source.is_dir():
            print("  Source directory missing; skipped\n")
            continue
        known = set()
        for meta in sorted(index.glob("*.pw.toml")):
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
        for asset in sorted(source.iterdir()):
            if asset.name.startswith(".") or asset.name in known:
                continue
            if asset.is_file() and asset.suffix.lower() == ".zip":
                print(f"  MANUAL: no active metadata for ZIP {asset.name}")
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
