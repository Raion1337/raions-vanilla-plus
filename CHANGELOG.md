# Changelog

Notable changes to **Raion's Vanilla Plus** are recorded here. Pack versions are independent of Minecraft and Fabric Loader versions.

## [2.0.0] - 2026-10-20

### Added

- Packwiz-based metadata and manifest management as the basis for reproducible modpack exports.
- Pinned Modrinth download references for 105 mods, 39 resource packs, and 6 shader packs.
- Release notes and a validation checklist.

### Changed

- Rebuilt the previous Prism-based release workflow around Packwiz.
- Placed intended first-launch settings under `config/modpack_defaults/` for Config Manager.
- Set the pack version to `2.0.0` while retaining Minecraft `26.3` and Fabric Loader `0.20.1`.

### Technical

- Added a reproducible Packwiz `.mrpack` export and SHA-256 checksum workflow.
- Separated development files from the exported game pack with `.packwizignore`.

### Known Issues

- First-launch application of Xaero, Simple Blood, keybindings, shaders, and resource-pack order still requires a clean-instance runtime test.
- 20 pinned resource packs do not declare Minecraft `26.3` compatibility in their metadata; 16 are selected in the default `options.txt`. Their appearance and behavior need in-game review.

### Upgrade Notes

- Install into a fresh launcher instance and back up saves and personal settings before migrating.

### Planned — Not Part of This Release

- Separate Vanilla and Enhanced Worldgen editions.
- Graphics/performance presets.
- Dedicated Fabric server distributions.
- Automated CI/CD validation and publishing.

Earlier version details are omitted because no verified release history is present in this repository.
