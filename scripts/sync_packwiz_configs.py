"""Sync selected first-launch defaults from a configured Prism test instance.

Copies Xaero's Minimap config, optional Iris config and selected options.txt
entries to Config Manager's config/modpack_defaults/ directory.

No instance paths are stored in the script. CLI > environment > prompt.
Dry-run by default; --apply is required to write. Existing affected files
are backed up outside the repository before modification. Other config files
are left untouched.

Requires Python 3.10+; no third-party dependencies.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import shutil
import sys
import tempfile
from pathlib import Path


def resolve(value: str | Path) -> Path:
    return Path(os.path.expandvars(str(value))).expanduser().resolve()


def get_source(value: str | None) -> Path:
    candidate = value or os.environ.get("PACKWIZ_SOURCE") or os.environ.get("PACKWIZ_TEST")
    if not candidate:
        if not sys.stdin.isatty():
            raise ValueError("Quelle fehlt: --source oder PACKWIZ_SOURCE angeben.")
        candidate = input("Pfad zur angepassten Prism-Testinstanz: ").strip()
    if not candidate:
        raise ValueError("Kein Instanzpfad angegeben.")
    return resolve(candidate)


def minecraft_root(instance: Path) -> Path:
    candidates = [p for p in (instance / "minecraft", instance / ".minecraft") if p.is_dir()]
    if len(candidates) != 1:
        raise ValueError(f"Prism-Minecraft-Verzeichnis nicht eindeutig unter {instance} gefunden.")
    return candidates[0]


def secure_regular_file(path: Path, root: Path) -> bool:
    """True only for regular files without symlink components below root."""
    if not path.is_file() or path.is_symlink():
        return False
    current = path.parent
    while current != root:
        if current.is_symlink():
            return False
        if current == current.parent:
            return False
        current = current.parent
    return True


def check_repo_path(repo: Path, target: Path) -> None:
    if not target.is_relative_to(repo):
        raise ValueError(f"Ziel außerhalb Repository: {target}")
    current = target
    while current != repo:
        if current.is_symlink():
            raise ValueError(f"Symlink im Repo-Pfad: {current}")
        current = current.parent
    if target.exists() and not target.is_file():
        raise ValueError(f"Ziel ist keine reguläre Datei: {target}")


def xaero_config(relative: Path) -> bool:
    parts = [part.casefold() for part in relative.parts]
    # Avoid personal world/map/waypoint caches and server-enforcement profiles.
    excluded = {"server_profiles", "waypoints", "waypoint", "cache", "caches", "maps", "worlds"}
    if any(part in excluded for part in parts):
        return False
    return any("xaero" in part or "minimap" in part for part in parts)


def safe_config_files(config: Path, all_configs: bool, include_iris: bool) -> dict[Path, Path]:
    files: dict[Path, Path] = {}
    for path in config.rglob("*"):
        if not secure_regular_file(path, config):
            continue
        rel = path.relative_to(config)
        lowered = [part.casefold() for part in rel.parts]
        if any(part in {"modpack_defaults", "yosbr", "defaultoptions"} for part in lowered):
            continue
        # Avoid personal/minimap map caches, even in --all-configs mode.
        if any(part in {"waypoints", "xaerowaypoints", "cache", "caches"} for part in lowered):
            continue
        if all_configs or xaero_config(rel) or (include_iris and rel.as_posix().lower() == "iris.properties"):
            files[rel] = path
    return files


def options_defaults(options_path: Path, full: bool) -> tuple[bytes, list[str]]:
    if not options_path.is_file() or options_path.is_symlink():
        raise ValueError(f"options.txt fehlt: {options_path}. Minecraft zuerst regulär beenden.")
    # Minecraft's options.txt is UTF-8, but be tolerant of unknown modded lines.
    content = options_path.read_text(encoding="utf-8", errors="replace")
    if full:
        print("ACHTUNG: --full-options kopiert auch hardware- und spielerbezogene Optionen!")
        return content.encode("utf-8"), ["complete options.txt"]
    selected: list[str] = []
    labels: list[str] = []
    for line in content.splitlines():
        key = line.partition(":")[0]
        if key == "version" or key.startswith("key_") or key in {"resourcePacks", "incompatibleResourcePacks"}:
            selected.append(line)
            labels.append(key)
    if not any(x.startswith("key_") for x in labels):
        raise ValueError("Keine Keybinds in options.txt gefunden; prüfe den Instanzpfad.")
    if "resourcePacks" not in labels:
        print("WARNUNG: Keine resourcePacks-Zeile in options.txt gefunden.")
    return ("\n".join(selected) + "\n").encode("utf-8"), labels


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aktuelle Einstellungen aus Prism in Packwiz/Config-Manager-Defaults übernehmen"
    )
    parser.add_argument(
        "--source", "--test", dest="source", help="Angepasste Prism-Instanz (oder PACKWIZ_SOURCE/PACKWIZ_TEST)"
    )
    parser.add_argument("--repo", help="Packwiz-Repo (oder PACKWIZ_REPO; standardmäßig aktuelles Arbeitsverzeichnis)")
    parser.add_argument("--apply", action="store_true", help="Schreiben; sonst nur Vorschau")
    parser.add_argument(
        "--all-configs", action="store_true", help="Auch andere Configs aus der Testinstanz übernehmen (nach Prüfung)"
    )
    parser.add_argument("--no-iris", action="store_true", help="Iris-Shader-Konfiguration nicht übernehmen")
    parser.add_argument(
        "--full-options", action="store_true", help="Gesamte options.txt statt nur Keybinds/Resourcepacks übernehmen"
    )
    args = parser.parse_args()

    source = get_source(args.source)
    repo = resolve(args.repo or os.environ.get("PACKWIZ_REPO") or Path.cwd())
    if not (repo / "pack.toml").is_file() or not (repo / "index.toml").is_file():
        raise ValueError(f"Kein Packwiz-Paket unter {repo} (pack.toml/index.toml fehlen).")
    if repo.is_symlink():
        raise ValueError("Repository darf kein Symlink sein.")
    mc = minecraft_root(source)
    if repo == source or repo == mc or repo.is_relative_to(mc):
        raise ValueError("Repository darf nicht innerhalb der Prism-Instanz liegen.")
    config = mc / "config"
    if not config.is_dir() or config.is_symlink():
        raise ValueError(f"Kein regulärer config/ Ordner: {config}")

    configurations = safe_config_files(config, args.all_configs, not args.no_iris)
    options_data, keys = options_defaults(mc / "options.txt", args.full_options)

    # Mapping: relative repository path -> byte content.
    defaults = Path("config/modpack_defaults")
    pending: dict[Path, bytes] = {defaults / "options.txt": options_data}
    remove_direct: set[Path] = set()
    if (repo / "options.txt").exists():
        remove_direct.add(Path("options.txt"))
    for relative, path in configurations.items():
        pending[defaults / "config" / relative] = path.read_bytes()
        # An existing override under config/ would defeat Config Manager's
        # copy-if-missing behaviour; relocate only corresponding files.
        direct = Path("config") / relative
        if (repo / direct).exists():
            remove_direct.add(direct)

    for relative in set(pending) | remove_direct:
        check_repo_path(repo, repo / relative)

    print(f"Quelle: {mc}")
    print(f"Repo:   {repo}")
    print(
        f"Options: {sum(key.startswith('key_') for key in keys)} Keybinds, "
        f"Resourcepacks: {'ja' if 'resourcePacks' in keys or args.full_options else 'nein'}"
    )
    print(f"Übernommene Config-Dateien: {len(configurations)}")
    for relative in sorted(configurations):
        print(f"  + {relative}")
    if not configurations:
        print("HINWEIS: Keine Xaero-/Iris-Configs gefunden. Starte die Instanz und beende sie normal.")
    if args.all_configs:
        print("ACHTUNG: --all-configs kann persönliche Mod-Einstellungen enthalten; vor Push prüfen!")
    print(f"In Config Manager Defaults: {len(pending)} Datei(en)")
    if remove_direct:
        print("Alte direkte Overrides, die nach Sicherung entfernt werden:")
        for item in sorted(remove_direct):
            print(f"  - {item}")
    print("Hinweis: Andere Dateien in repo/config bleiben unverändert.")
    if not args.apply:
        print("\nVORSCHAU – nichts verändert. Zum Ausführen --apply hinzufügen.")
        return 0

    # Back up all affected existing targets outside the repository first.
    existing = [relative for relative in set(pending) | remove_direct if (repo / relative).exists()]
    backup = None
    if existing:
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup = repo.parent / f".{repo.name}-sync-backups" / stamp
        backup.mkdir(parents=True, exist_ok=False)
        for relative in sorted(existing):
            destination = backup / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(repo / relative, destination)

    # Stage complete output before touching the repo.
    with tempfile.TemporaryDirectory(prefix=".packwiz-defaults-", dir=repo.parent) as tmp:
        stage = Path(tmp)
        for relative, content in pending.items():
            output = stage / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(content)
        for relative in sorted(pending):
            dest = repo / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            os.replace(stage / relative, dest)
        for relative in sorted(remove_direct):
            (repo / relative).unlink()

    print(f"\nFERTIG: {len(pending)} Dateien unter {repo / defaults}")
    if backup:
        print(f"Backup vorheriger Dateien: {backup}")
    print("Als Nächstes: packwiz refresh; frischen .mrpack-Import testen.")
    print("ACHTUNG: Config Manager setzt Defaults nur, wenn die jeweilige Zieldatei noch nicht existiert.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        raise SystemExit(1)
