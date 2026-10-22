"""Import only enabled Prism resourcepacks into Packwiz using exact SHA-512 matches.

- No hard-coded instance paths. --instance/--repo or environment variables.
- Default is preview (never writes).
- --apply generates .pw.toml metadata only; never copies ZIPs.
- Uses Modrinth's version_files hash API, preserving local file names.
- Does not modify Prism instance or unrelated Packwiz data.
- --sync-order copies only resource-pack selection/order into shipped options defaults.
- --prune-inactive removes repository metadata for packs outside the enabled list.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tomllib
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

API = "https://api.modrinth.com/v2/version_files"
USER_AGENT = "RaionsVanillaPlus-PackwizImporter/1.0 (Modrinth API; Python urllib)"


def cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument(
        "--instance",
        "--source",
        default=os.environ.get("PRISM_INSTANCE") or os.environ.get("PACKWIZ_MAIN"),
        help="Prism instance path (or PRISM_INSTANCE/PACKWIZ_MAIN)",
    )
    p.add_argument(
        "--repo",
        default=os.environ.get("PACKWIZ_REPO") or os.getcwd(),
        help="Packwiz root containing pack.toml (or PACKWIZ_REPO; default current directory)",
    )
    p.add_argument("--apply", action="store_true", help="Write .pw.toml files; default is preview only")
    p.add_argument("--sync-order", action="store_true", help="Sync enabled pack order into options defaults")
    p.add_argument("--prune-inactive", action="store_true", help="Remove metadata for inactive resource packs")
    return p.parse_args()


def game_dir(instance: Path) -> Path:
    for directory in (instance / "minecraft", instance / ".minecraft"):
        if (directory / "resourcepacks").is_dir():
            return directory
    raise ValueError(f"No resourcepacks/ found in minecraft/ or .minecraft/ under {instance}")


def sha512(path: Path) -> str:
    h = hashlib.sha512()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def get_versions(hashes: list[str]) -> dict[str, dict]:
    results: dict[str, dict] = {}
    for start in range(0, len(hashes), 100):
        batch = hashes[start : start + 100]
        request = urllib.request.Request(
            API,
            json.dumps({"hashes": batch, "algorithm": "sha512"}).encode("utf-8"),
            {"User-Agent": USER_AGENT, "Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            payload = json.load(response)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected response from Modrinth version_files API")
        results.update(payload)
    return results


def quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def safe_meta_name(filename: str, hashvalue: str) -> str:
    stem = Path(filename).stem
    stem = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")[:75] or "pack"
    return f"{stem}-{hashvalue[:10]}.pw.toml"


def meta_content(asset: Path, version: dict, f: dict, digest: str) -> str:
    project = version["project_id"]
    ver_id = version["id"]
    url = f["url"]
    # Do not trust unexpected download hosts
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "cdn.modrinth.com":
        raise ValueError(f"Unexpected download URL: {url}")
    if f.get("hashes", {}).get("sha512") != digest:
        raise ValueError("Modrinth reported an unexpected file hash")
    return (
        f"name = {quote(asset.stem)}\n"
        f"filename = {quote(asset.name)}\n"
        'side = "client"\n\n'
        "[download]\n"
        'mode = "url"\n'
        f"url = {quote(url)}\n"
        'hash-format = "sha512"\n'
        f"hash = {quote(digest)}\n\n"
        "[update.modrinth]\n"
        f"mod-id = {quote(project)}\n"
        f"version = {quote(ver_id)}\n"
    )


def main() -> int:
    args = cli()
    path = args.instance
    if not path:
        path = input("Prism instance path: ").strip()
    if not path:
        print("Missing Prism instance path", file=sys.stderr)
        return 2
    repo = Path(args.repo).expanduser().resolve()
    instance = Path(path).expanduser().resolve()
    if not (repo / "pack.toml").is_file():
        print(f"No pack.toml found under {repo}; use --repo or cd into the Packwiz root.", file=sys.stderr)
        return 2
    try:
        source = game_dir(instance) / "resourcepacks"
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2
    try:
        option_lines = {}
        for line in (source.parent / "options.txt").read_text(encoding="utf-8").splitlines():
            key = line.partition(":")[0]
            if key in {"resourcePacks", "incompatibleResourcePacks"}:
                if key in option_lines:
                    raise ValueError(f"Duplicate {key} entry in options.txt")
                option_lines[key] = line
        active = json.loads(option_lines["resourcePacks"].partition(":")[2])
        if not isinstance(active, list) or not all(isinstance(item, str) for item in active):
            raise ValueError("resourcePacks must be a JSON list of strings")
        if len(active) != len(set(active)):
            raise ValueError("Duplicate enabled resource packs")
        assets = []
        for item in active:
            if not item.startswith("file/"):
                continue
            filename = item[5:]
            if not filename or Path(filename).name != filename or filename in {".", ".."}:
                raise ValueError(f"Unsafe resource-pack filename: {filename!r}")
            asset = source / filename
            if asset.is_symlink() or not asset.is_file() or asset.suffix.lower() != ".zip":
                raise ValueError(f"Enabled resource pack is not a regular ZIP: {filename}")
            assets.append(asset)
        incompatible = json.loads(option_lines.get("incompatibleResourcePacks", "incompatibleResourcePacks:[]").partition(":")[2])
        if not isinstance(incompatible, list) or not all(isinstance(item, str) for item in incompatible):
            raise ValueError("incompatibleResourcePacks must be a JSON list of strings")
        option_lines.setdefault("incompatibleResourcePacks", "incompatibleResourcePacks:[]")
    except (OSError, KeyError, ValueError) as exc:
        print(f"Cannot read enabled resource packs: {exc}", file=sys.stderr)
        return 1
    print(f"Prism resourcepacks : {source}")
    print(f"Packwiz destination : {repo / 'resourcepacks'}")
    print(f"Mode               : {'APPLY' if args.apply else 'PREVIEW'}")
    print(f"Enabled ZIP packs  : {len(assets)} ({len(active) - len(assets)} built-in entries)\n")

    hashes = {asset: sha512(asset) for asset in assets}
    destination = repo / "resourcepacks"
    existing_by_filename = {}
    inactive = []
    active_names = {asset.name for asset in assets}
    for previous in destination.glob("*.pw.toml"):
        try:
            if previous.is_symlink():
                raise ValueError(f"Symlink metadata: {previous}")
            data = tomllib.loads(previous.read_text(encoding="utf-8"))
            filename = data["filename"]
            if not isinstance(filename, str) or filename in existing_by_filename:
                raise ValueError(f"Invalid or duplicate filename: {filename!r}")
            existing_by_filename[filename] = (previous, data)
            if filename not in active_names:
                inactive.append(previous)
        except (OSError, KeyError, ValueError) as exc:
            print(f"Invalid existing metadata {previous.name}: {exc}", file=sys.stderr)
            return 1

    pending_assets = []
    existing = 0
    for asset in assets:
        old = existing_by_filename.get(asset.name)
        if old:
            download = old[1].get("download", {})
            if download.get("hash-format") != "sha512" or download.get("hash") != hashes[asset]:
                print(f"CONFLICT {asset.name}: existing metadata does not match local ZIP", file=sys.stderr)
                return 1
            existing += 1
            print(f"EXISTS    {asset.name}")
        else:
            pending_assets.append(asset)
    try:
        versions = get_versions(sorted({hashes[asset] for asset in pending_assets}))
    except (urllib.error.URLError, ValueError, json.JSONDecodeError) as exc:
        print(f"Modrinth lookup failed: {exc}", file=sys.stderr)
        return 1

    pending = {}
    unresolved = []
    for asset in pending_assets:
        digest = hashes[asset]
        version = versions.get(digest)
        if not version:
            print(f"UNMATCHED {asset.name}  (ZIP bytes not found by Modrinth SHA-512)")
            unresolved.append(asset.name)
            continue
        matching_files = [f for f in version.get("files", []) if f.get("hashes", {}).get("sha512") == digest]
        if not matching_files:
            print(f"UNMATCHED {asset.name}  (version found, file hash missing)")
            unresolved.append(asset.name)
            continue
        try:
            content = meta_content(asset, version, matching_files[0], digest)
        except (KeyError, ValueError) as exc:
            print(f"UNMATCHED {asset.name}  ({exc})")
            unresolved.append(asset.name)
            continue
        target = destination / safe_meta_name(asset.name, digest)
        if target.exists() and target.read_text(encoding="utf-8") != content:
            print(f"CONFLICT {target.name} already exists with different content", file=sys.stderr)
            return 1
        pending[target] = content
        print(f"{'ADD' if args.apply else 'WOULD ADD'} {asset.name}  =>  {target.name}")

    if unresolved:
        print("Unresolved active packs; no repository files changed.", file=sys.stderr)
        return 1

    options_target = repo / "config/modpack_defaults/options.txt"
    options_content = None
    if args.sync_order:
        if options_target.is_symlink():
            print("Refusing symlink options defaults", file=sys.stderr)
            return 1
        original = options_target.read_text(encoding="utf-8") if options_target.exists() else ""
        lines = []
        remaining = dict(option_lines)
        for line in original.splitlines(keepends=True):
            key = line.partition(":")[0]
            if key in option_lines:
                if key not in remaining:
                    print(f"Duplicate {key} in defaults", file=sys.stderr)
                    return 1
                lines.append(remaining.pop(key) + "\n")
            else:
                lines.append(line)
        options_content = "".join(lines)
        if remaining:
            if options_content and not options_content.endswith("\n"):
                options_content += "\n"
            options_content += "".join(line + "\n" for line in remaining.values())
        print(f"{'SYNC' if args.apply else 'WOULD SYNC'} resource-pack selection/order ({len(active)} entries)")
    if args.prune_inactive:
        for previous in sorted(inactive):
            print(f"{'REMOVE' if args.apply else 'WOULD REMOVE'} {previous.name}")
    if args.apply:
        destination.mkdir(parents=True, exist_ok=True)
        for target, content in pending.items():
            target.write_text(content, encoding="utf-8")
        if options_content is not None:
            options_target.parent.mkdir(parents=True, exist_ok=True)
            options_target.write_text(options_content, encoding="utf-8")
        if args.prune_inactive:
            for previous in inactive:
                previous.unlink()
    print(f"\nSummary: {len(pending)} additions, {existing} existing, {len(inactive) if args.prune_inactive else 0} removals")
    print("Next: packwiz refresh" if args.apply else "Preview only; use --apply to write.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
