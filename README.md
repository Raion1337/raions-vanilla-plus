# Raion's Vanilla Plus 2.0 — The Packwiz Rebuild

> **Pure Minecraft, refined.**

**Raion's Vanilla Plus** is a carefully curated **Fabric modpack** built to make Minecraft feel smoother, more immersive, and more convenient - without replacing the game you already love.

The focus is simple: **vanilla gameplay, better performance, improved visuals, and thoughtful quality-of-life features.** No unnecessary progression systems, overhauled crafting, or mandatory new content.

[**Download on Modrinth**](https://modrinth.com/project/TMAsWyhW) · [**Source code**](https://github.com/Raion1337/raions-vanilla-plus) · [**Report an issue**](https://github.com/Raion1337/raions-vanilla-plus/issues)

> [!IMPORTANT]
> **2.0.0 release candidate:** The Packwiz archive can be built and inspected locally. Clean launcher import, Minecraft startup, and first-launch defaults still require manual testing before public publication. Existing Modrinth downloads may differ from this repository.

## Why Vanilla Plus?

Raion's Vanilla Plus follows a few core principles:

- **Keep Minecraft Minecraft.** Preserve the familiar survival experience and progression.
- **Improve, don't overwhelm.** Add useful features such as a minimap, inventory management, better information displays, and quality-of-life controls.
- **Make it look and feel better.** Curate shaders, resource packs, ambience, and subtle visual improvements.
- **Prioritize performance.** Combine optimization mods with sensible defaults instead of relying on visual effects alone.
- **Respect player preferences.** Aim for a polished first launch without forcing personal settings on every subsequent update.
- **Stay multiplayer-friendly.** Support vanilla-friendly client features while clearly identifying anything that needs server-side installation.

## Features

| Area | What to expect |
| --- | --- |
| **Vanilla gameplay** | Familiar mechanics, progression, and overall game balance. |
| **Performance** | A curated set of Fabric optimization and rendering mods. |
| **Visuals** | Shader support, resource packs, improved ambience, and subtle visual effects. |
| **Quality of life** | Minimap, inventory utilities, clearer tooltips, and useful interface improvements. |
| **Customization** | Player-adjustable graphics and mod settings. |
| **Multiplayer** | A client-focused experience, with dedicated Fabric server packages planned. |

Individual mods and settings can change between releases. The Packwiz manifests define the contents of each build.

## Editions

Two world-generation editions are **planned** around the same shared modpack base:

| | **Vanilla Worldgen** | **Enhanced Worldgen** |
| --- | --- | --- |
| Terrain and biomes | Original Minecraft world generation | **Terralith + Tectonic** |
| Core gameplay | Vanilla | Vanilla |
| Performance, visuals, QoL | Shared base | Shared base |
| Best for | Maximum vanilla familiarity | Exploring more varied landscapes |
| Status | Planned release variant | Planned release variant |

> [!CAUTION]
> **Choose your world-generation edition before creating a world.** Removing Terralith from an existing Enhanced world is not considered safe. Changing world-generation mods can also cause visible terrain transitions in newly generated chunks. Always back up your worlds before changing editions or Minecraft versions.

The availability and update behavior of both editions will be verified before separate downloads are announced.

## Installation

### Modrinth App

1. Open the [Raion's Vanilla Plus project](https://modrinth.com/project/TMAsWyhW).
2. Choose a release compatible with your intended Minecraft version.
3. Install it with the Modrinth App and launch the new instance.

### Prism Launcher

1. Download a published `.mrpack` file from the project page or a release.
2. In Prism Launcher, choose **Add Instance → Import**.
3. Select the `.mrpack` file and let Prism install the required files.
4. Launch Minecraft.

**2.0.0 requirements:** Minecraft **26.3**, Fabric Loader **0.20.1**, and Java **25**. Use a launcher that can import Modrinth `.mrpack` files. Hardware needs vary with shaders and render distance; no minimum memory or graphics target has been validated for this pack.

## First launch and graphics

The archive includes intended controls, resource-pack selection, and mod settings under `config/modpack_defaults/`. [Config Manager](https://modrinth.com/mod/configmanager) copies each file only when the destination does not already exist. A launcher that creates `options.txt` first, or a mod that writes its own config before Config Manager runs, may prevent those defaults from applying. Clean-launch behavior is **not tested** for this release candidate.

- **Shaders:** Supported through the included shader tooling. If performance is poor, disable shaders in the video/shader settings.
- **Resource packs:** The intended selection and priority are managed through Minecraft settings; installed packs are not necessarily enabled automatically.
- **Controls and HUD:** Adjust them freely to your preferences.
- **Performance presets:** Dedicated in-game profiles are planned, but are not yet advertised as a released feature.

Your own settings should remain yours. Update behavior will be tested before a stable release.

## Multiplayer and servers

Many client-side improvements are designed to work when connecting to ordinary Minecraft servers. However, **some features require matching server-side mods** and will not be available on every vanilla server.

Dedicated **Fabric server packages** for the supported editions are planned. Until they are released and tested, do not assume the complete client pack can be copied directly into a server's `mods/` directory.

## Development

This repository uses **[Packwiz](https://packwiz.infra.link/)** to manage mod metadata, versions, configuration files, resource packs, shaders, and reproducible modpack exports.

### Local build

Install [Packwiz](https://packwiz.infra.link/) and clone the repository:

```bash
git clone https://github.com/Raion1337/raions-vanilla-plus.git
cd raions-vanilla-plus

packwiz refresh
mkdir -p dist
packwiz modrinth export -o dist/raions-vanilla-plus-2.0.0.mrpack
```

Import the generated `.mrpack` into a **fresh Prism Launcher instance** for testing. Complete the [release checklist](docs/releases/v2.0.0-checklist.md) before publishing. The build output in `dist/` is intentionally ignored by Git.

### Repository organization

The working layout is based on the following structure and may evolve as edition builds are introduced:

```text
pack.toml                  # Packwiz package metadata
index.toml                 # Packwiz file index
mods/                      # Mod metadata (*.pw.toml)
resourcepacks/             # Resource-pack metadata
shaderpacks/               # Shader-pack metadata
config/                    # Distributed configuration files
  modpack_defaults/        # Intended first-launch defaults
scripts/                   # Local migration and maintenance tools
README.md
CHANGELOG.md
docs/releases/             # Release notes, checklist, and guide
LICENSE
```

Packwiz metadata should reference the correct published files instead of committing third-party mod JARs or shader ZIPs without permission. Do not commit worlds, account data, private servers, credentials, logs, or personal minimap data.

### Contributions and bug reports

Feedback, compatibility reports, and suggestions are welcome through [GitHub Issues](https://github.com/Raion1337/raions-vanilla-plus/issues). For a useful bug report, include:

- Modpack version and Minecraft version.
- Launcher and operating system.
- Steps to reproduce and expected versus actual behavior.
- Relevant logs or crash reports **after removing personal information and tokens**.

Please discuss major mod additions or gameplay changes before proposing them - the vanilla-first scope is intentional.

## Roadmap

- [ ] Validate first-launch defaults (minimap, controls, resource-pack order, and mod settings).
- [ ] Complete clean-install and update tests in Prism Launcher and the Modrinth App.
- [ ] Produce separately tested Vanilla and Enhanced Worldgen editions.
- [ ] Add curated graphics/performance presets.
- [ ] Test and publish matching Fabric server packages.
- [ ] Automate validation and release artifacts with GitHub Actions.
- [ ] Expand installation, troubleshooting, and compatibility documentation.

This roadmap is directional, not a promise that every item is available in current releases.

## Credits and licensing

Raion's Vanilla Plus is built on the work of Minecraft's modding community. **All credit for individual mods, shaders, and resource packs belongs to their respective creators.** See each project's page for its authors, licensing terms, and attribution requirements.

The original repository code and documentation are covered by the [MIT License](LICENSE). **That license does not relicense third-party mods, shader packs, resource packs, or Minecraft assets.**

---

**Pure Minecraft, refined.**
