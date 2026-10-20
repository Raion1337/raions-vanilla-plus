"""Import installed Prism resourcepacks into Packwiz using exact Modrinth SHA-512 matches.

- No hard-coded instance paths. --instance/--repo or environment variables.
- Default is preview (never writes).
- --apply generates .pw.toml metadata only; never copies ZIPs.
- Uses Modrinth's version_files hash API, preserving local file names.
- Does not modify Prism instance or unrelated Packwiz data.
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
from collections import defaultdict
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
    assets = sorted(
        p for p in source.iterdir() if p.is_file() and p.suffix.lower() == ".zip" and not p.name.startswith(".")
    )
    print(f"Prism resourcepacks : {source}")
    print(f"Packwiz destination : {repo / 'resourcepacks'}")
    print(f"Mode               : {'APPLY' if args.apply else 'PREVIEW'}")
    print(f"ZIP files found    : {len(assets)}\n")
    if not assets:
        return 0

    hashes = {asset: sha512(asset) for asset in assets}
    digest_to_asset = defaultdict(list)
    for asset, digest in hashes.items():
        digest_to_asset[digest].append(asset)
    try:
        versions = get_versions(sorted(set(hashes.values())))
    except (urllib.error.URLError, ValueError, json.JSONDecodeError) as exc:
        print(f"Modrinth lookup failed: {exc}", file=sys.stderr)
        return 1

    destination = repo / "resourcepacks"
    existing_by_filename: dict[str, list[tuple[Path, str]]] = defaultdict(list)
    for previous in destination.glob("*.pw.toml"):
        try:
            data = tomllib.loads(previous.read_text(encoding="utf-8"))
            if isinstance(data.get("filename"), str):
                existing_by_filename[data["filename"]].append((previous, data.get("download", {}).get("hash", "")))
        except (OSError, ValueError, tomllib.TOMLDecodeError):
            print(f"WARNING: cannot parse existing metadata {previous.name}")

    new = existing = conflict = unmatched = 0
    for asset in assets:
        digest = hashes[asset]
        version = versions.get(digest)
        if not version:
            unmatched += 1
            print(f"UNMATCHED {asset.name}  (ZIP bytes not found by Modrinth SHA-512)")
            continue
        matching_files = [f for f in version.get("files", []) if f.get("hashes", {}).get("sha512") == digest]
        if not matching_files:
            unmatched += 1
            print(f"UNMATCHED {asset.name}  (version found, file hash missing)")
            continue
        try:
            content = meta_content(asset, version, matching_files[0], digest)
        except (KeyError, ValueError) as exc:
            unmatched += 1
            print(f"UNMATCHED {asset.name}  ({exc})")
            continue
        old_entries = existing_by_filename.get(asset.name, [])
        if old_entries:
            if any(old_hash == digest for _, old_hash in old_entries):
                existing += 1
                print(f"EXISTS    {asset.name}")
            else:
                conflict += 1
                print(
                    f"CONFLICT  {asset.name}  (Packwiz already references this filename with a different hash; review manually)"
                )
            continue
        target = destination / safe_meta_name(asset.name, digest)
        if target.exists() and target.read_text(encoding="utf-8") != content:
            conflict += 1
            print(f"CONFLICT  {target.name} already exists with different content")
            continue
        new += 1
        print(f"{'ADD' if args.apply else 'WOULD ADD'} {asset.name}  =>  {target.name}")
        if args.apply:
            destination.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    print(
        f"\nSummary: {new} {'added' if args.apply else 'to add'}, {existing} already present, {conflict} conflicts, {unmatched} unresolved"
    )
    if args.apply:
        print("Next: packwiz refresh && packwiz modrinth export -o /tmp/rvp-resourcepack-test.mrpack")
    else:
        print("Preview only. Run again with --apply after reviewing the list.")
    if unmatched:
        print("NOTE: A project being on Modrinth does not guarantee this exact ZIP was uploaded unchanged.")
    return 0 if conflict == 0 and unmatched == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
