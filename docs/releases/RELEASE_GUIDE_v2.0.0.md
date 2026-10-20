---
project: Raion's Vanilla Plus
version: 2.0.0
type: release-guide
platform: Linux/Fish
status: draft
---

# Raion's Vanilla Plus 2.0 — Release Guide (Fish)

> [!WARNING]
> These commands assume `pack.toml` is in your repository root. They do **not** repair missing first-launch settings. Complete the [Release checklist](v2.0.0-checklist.md) before publishing a Stable release. Do not run the Git/tag/release sections until tests pass.

## Step 0 — Open the repository and inspect it

```fish
git rev-parse --show-toplevel
git branch --show-current
git remote -v
git status --short
packwiz list -v
gh auth status
```

> [!NOTE]
> Use the **existing** repository `Raion1337/raions-vanilla-plus`. The remote `main` may not yet contain your local Packwiz changes, so verify your git status and remote first.

## Step 1 — Set pack version

Edit `pack.toml` (for example, with `nano pack.toml`), changing only the **top-level** version and leaving Minecraft, Fabric, index metadata and `pack-format` intact:

```toml
name = "Raion's Vanilla Plus"
version = "2.0.0"
```

Check the actual values:

```fish
python -c '
from pathlib import Path
import tomllib
p = tomllib.loads(Path("pack.toml").read_text(encoding="utf-8"))
print("Pack version:", p.get("version"))
print("Minecraft:", p["versions"].get("minecraft"))
print("Fabric Loader:", p["versions"].get("fabric"))
'
```

Do not infer the Minecraft version from the `2.0.0` modpack version.

## Step 2 — Ignore local developer and release files

Ensure the root `.gitignore` includes:

```gitignore
/dist/
/build/
*.mrpack
*.log
.env
.env.*
```

Ensure `.packwizignore` includes at least the **paths that exist in your repository** but should not be copied into Minecraft:

```gitignore
dist/
build/
scripts/
docs/
.github/
README.md
CHANGELOG.md
v2.0.0.md
v2.0.0-modrinth.md
v2.0.0-checklist.md
RELEASE_GUIDE_v2.0.0.md
LICENSE
```

Preserve any custom ignore patterns that already exist. `.packwizignore` is for the exported game pack; `.gitignore` is for Git itself.

## Step 3 — Build and validate

```fish
mkdir -p dist
packwiz refresh
packwiz list -v
packwiz modrinth export -o dist/raions-vanilla-plus-2.0.0.mrpack
unzip -t dist/raions-vanilla-plus-2.0.0.mrpack
```

Check the manifest:

```fish
unzip -p dist/raions-vanilla-plus-2.0.0.mrpack modrinth.index.json | python -c '
import json, sys
m=json.load(sys.stdin)
print("Pack:", m.get("name"))
print("Manifest versionId:", m.get("versionId"))
print("Dependencies:", m.get("dependencies"))
paths = [f["path"] for f in m.get("files", [])]
for folder in ("mods/", "resourcepacks/", "shaderpacks/"):
    print(folder, sum(p.startswith(folder) for p in paths))
'
```

List embedded overrides and configuration defaults:

```fish
unzip -Z1 dist/raions-vanilla-plus-2.0.0.mrpack | grep '^overrides/'
unzip -Z1 dist/raions-vanilla-plus-2.0.0.mrpack | grep '^overrides/config/'
```

Any unexpected JARs, third-party ZIP files, personal settings or missing configurations require investigation **before publishing**.

Create checksum:

```fish
cd dist
sha256sum raions-vanilla-plus-2.0.0.mrpack > raions-vanilla-plus-2.0.0.sha256
cd ..
```

## Step 4 — Fresh launcher testing

Import `dist/raions-vanilla-plus-2.0.0.mrpack` into a **brand-new** Prism Launcher instance, and do the same with the Modrinth App. Check every box in `v2.0.0-checklist.md`.

> [!CAUTION]
> Last observed local issue: some first-launch settings (Xaero's Minimap, resource packs, keybindings and Simple Blood) did not apply as intended. If not fixed, do not label this release stable. Publish an RC instead using `2.0.0-rc.1` consistently in `pack.toml`, filename, Git tag and Modrinth version number.

## Step 5 — Commit source, then tag exactly that commit

```fish
git status --short
git add -A
git diff --cached --stat
git diff --cached --check
git diff --cached --name-only
```

Inspect staged files for secrets, worlds, logs, and binary artifacts; then:

```fish
git commit -m "release: prepare Raion's Vanilla Plus 2.0.0"
git push origin main
git tag -a v2.0.0 -m "Raion's Vanilla Plus 2.0.0 - The Packwiz Rebuild"
git push origin v2.0.0
```

> [!NOTE]
> The commands above expect that your release commit is on `main`. If you are on a different branch, merge the reviewed changes into `main` before tagging. Don't force-push existing tags.

## Step 6 — Create a GitHub Release draft

```fish
gh release create v2.0.0 \
  dist/raions-vanilla-plus-2.0.0.mrpack \
  dist/raions-vanilla-plus-2.0.0.sha256 \
  --verify-tag \
  --draft \
  --title "Raion's Vanilla Plus 2.0 — The Packwiz Rebuild" \
  --notes-file docs/releases/v2.0.0.md
```

If the notes are kept under another directory, adjust `--notes-file` accordingly. Review the GitHub draft and assets before publication.

To publish the draft after verification:

```fish
gh release edit v2.0.0 --draft=false
```

## Step 7 — Publish to the existing Modrinth project

Open **https://modrinth.com/project/TMAsWyhW** and create a new project version (not a new project):

- Version name: `Raion's Vanilla Plus 2.0 — The Packwiz Rebuild`
- Version number: `2.0.0`
- Version type: `Release` **only after QA** (`Beta` for RC)
- Loader: `Fabric`
- Minecraft version: exactly the value in `pack.toml`
- File: `dist/raions-vanilla-plus-2.0.0.mrpack`
- Changelog: content of `v2.0.0-modrinth.md`

After publication, install the downloadable version from Modrinth once more and compare it with the locally tested artifact.

## Step 8 — Post-release sanity checks

```fish
git status --short
git tag --list 'v2.*'
gh release view v2.0.0 --web
cd dist
sha256sum -c raions-vanilla-plus-2.0.0.sha256
cd ..
```

> [!TIP]
> For future releases, create an upgrade branch, pin tested mod versions, export reproducibly from a tagged commit, and use the same QA gate for both planned world-generation editions. Avoid blind `packwiz update --all` on the stable release branch.
