# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com),
and this project adheres to no formal versioning yet (commits are the
release boundary).

## [Unreleased]

### Added
- Add CHANGELOG.md following Keep a Changelog format
- Add virtual gamepad relay and autonomous chase/evade scripts

### Changed
- add CHANGELOG.md and update with recent commits
- Enhance evade_chase with direct wall breaking and teleport escape
## [48337cd] — 2026-07-14

### Added
- Virtual gamepad (`gamepad_connect`, `gamepad_input`, `gamepad_disconnect`)
  so AI-controlled players move through real game physics (speed, gravity,
  collisions). Implementation in `js/gamepad.js` (virtual[] array,
  enableVirtual, setVirtualInput with rs support).
- `move_burst`: batch N relative steps in one relay request for smoother
  agent movement (`js/mcp-client.js`, `mcp-server.js`).
- `Cache-Control: no-store` header on static file serving — a plain reload
  always fetches fresh JS.
- `scripts/chase.py`: chase P1 using gamepad stick decomposition.
- `scripts/evade.py`: timed evade loop (100 s) with jump/steer/break.

### Changed
- Player state sync (`js/mcp-client.js` `syncState`) now includes rotation,
  isFlying, cameraMode, selectedSlot so the server mirror stays accurate.
- `js/mcp-server.js` removed duplicate `move_player`/`jump` handlers and
  the broken server-side `get_screenshot` (used `THREE`/`document` in Node).

### Fixed
- All world/perception/player commands now relay through the browser
  (source of truth) instead of failing with `Mundo no inicializado`.
- Relay response strips the internal `id` field before returning to the
  HTTP `/mcp` caller.

## [bf22afa] — 2026-07-14

### Changed
- Improved MCP server WebSocket error handling and resilience.

## [9b0d3ef] — 2026-07-14

### Added
- MCP integration: `mcp-server.js` unifies game serving, HTTP `/mcp` API,
  and WebSocket bridge.
- In-game console accessible via T/`~` (`js/console.js`).
- `MANUAL_MCP.md`: full MCP method reference.

## [56cc8f3] — 2026-07-14

### Added
- VoxelQuest v1.0: split-screen voxel game with procedural terrain,
  two-player local support, inventory, crafting, enemies (zombies,
  skeletons, creepers), day/night cycle, building assets (windows, doors,
  furniture, torches), physics with block collapse, flying (double jump),
  Xbox 360 gamepad support.

## [f01f05f] — 2026-07-14

### Added
- Initial Minecraft clone with split-screen rendering and basic voxel
  world generation.
