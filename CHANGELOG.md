# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com),
and this project adheres to no formal versioning yet (commits are the
release boundary).

## [Unreleased]

### Added
- **Estructuras declarativas CSG (propuesta 004 implementada)**: nuevo evaluador `core/python/server/engine/csg.py` que convierte árboles CSG JSON (primitivas `box`/`sphere`/`cylinder`/`pyramid`, booleanas `union`/`subtract`/`intersect`, transformaciones `at`/`rotate` 90°, repeticiones `array`/`radial`) en bloques voxel o esculturas subvoxel. 4 tools MCP nuevas en la categoría `building` (`build_csg`, `preview_csg` dry-run, `list_csg_structures`, `build_csg_named`), disponibles solo en el stack Python. Biblioteca inicial en `core/shared/structures/` (house, tower, castle_walls, cathedral_nave). Sustituye el patrón "generar script por estructura" por "emitir árbol CSG JSON". Concepto en `docs/LEARN-csg.md`. Tests en `server/tests/test_csg.py` (21) y `test_csg_e2e.py` (11).
- Propuesta (no implementado): agente constructor in-game con bucle LLM dentro del servidor (OpenAI-compatible, default Ollama local, configurable a cloud vía `VQ_AGENT_*`). Documentada en `docs/proposals/005-agente-constructor-ingame/`.
- **Objetos móviles (propuesta 002 implementada)**: nuevo subsistema `MobileObject` en `core/python/server/engine/objects.py` con física de colisiones obj↔grid y obj↔obj (AABB/sphere, resolución impulsiva), movimientos programables (`waypoints`/`dynamic`/`orbit`/`parametric`/`rotate`), destrucción reactiva (colisión por umbral `fragile`, daño, expiración, manual), esculturas subvoxel con 6 generadores built-in (`sphere`/`cube`/`pyramid`/`helix`/`cross`/`humanoid_bust`) y renderizado en el cliente con `THREE.InstancedMesh`. 15 tools MCP nuevas en la categoría `objects` (`create_object`, `update_object`, `list_objects`, `get_object`, `destroy_object`, `move_object`, `move_linear`, `move_orbit`, `move_bounce`, `move_projectile`, `move_rotate`, `stop_motion`, `apply_impulse`, `damage_object`, `create_sculpture`), disponibles solo en el stack Python. Eventos nuevos en `state_update`: `object_collided`, `object_destroyed` (con FX `explosion_small`/`break`/`poof`), `object_damaged`, `entity_damaged`. Sección "Objetos y física" añadida a `docs/MANUAL_MCP.md`. Tests en `server/tests/test_objects.py`, `test_physics_objects.py`, `test_motions.py`, `test_motion_presets.py`, `test_destruction.py`, `test_sculptures.py`, `test_objects_e2e.py` (≈90 tests nuevos, suite total 161 pasan).
- Cliente web: nuevo módulo `core/web/js/objects.js` (`ObjectRenderer`) que renderiza box/sphere/vehicle/projectile con `THREE.Mesh` y esculturas con `InstancedMesh` agrupado por color, más FX visuales (explosión/poof) al recibir `object_destroyed`. `server-bridge.js` aplica `state.objects[]` y eventos al cliente.
- MCP: nuevas tools `apply_blocks` (aplicar lista de bloques en un request) y `clear_area` (borrado masivo) en el stack Python
- Cliente: notificación visual cuando el servidor está modificando el mundo
- Propuesta (no implementado): cliente CLI standalone `vq` con dos modos — subcomandos Typer generados dinámicamente desde `definitions.json` (reemplaza los 11 scripts dispersos) y modo `vq chat` de lenguaje natural con LLM configurable en runtime (Ollama Local, Ollama Cloud, o cualquier endpoint OpenAI-compatible). Documentada en `docs/proposals/003-cliente-cli-mcp/` (propuesta, contrato de subcomandos + tools virtuales, plan de ejecución, análisis de impacto)

### Changed
- Sincronía servidor→cliente: los cambios de bloques se difunden vía `block_updates` en cada `state_update` (antes la lista nunca se llenaba)
- Deltas de chunks incrementales: un chunk se envía completo solo la primera vez; después solo los bloques modificados (incluye aire, así las destrucciones llegan al navegador)
- Scripts de construcción (castle, fortress, gothic cathedral, house, maze, pyramid, village): usan `apply_blocks` por lotes en vez de una llamada HTTP por bloque
- Scripts de cliente (chase, evade, evade_chase, follow_p1_distance): corregido el parseo de respuestas MCP (`content` a nivel raíz)
- Cliente: rebuild de chunks limitado a 1 por frame para no bloquear el render en construcciones masivas
- Cliente: throttle de envío de input al servidor (~10 msg/s)

### Fixed
- Construcciones "fantasma": los scripts parseaban `resp["result"]` pero el servidor devuelve `content` a nivel raíz, así que `detect_ground` usaba la altura de fallback y las estructuras quedaban flotando o bajo tierra
- Destrucciones masivas sin efecto visual: `get_modified_blocks` filtraba el aire, por lo que los bloques borrados nunca llegaban al cliente

### Changed
- refactor: reorganización de estructura y contrato MCP compartido
  - Renombrado `minecraft-clone/` → `core/`
  - Stack Node.js: todo en `core/node/` (servidor + web client)
  - Stack Python: todo en `core/python/` (servidor + client + scripts + training)
  - Contrato compartido: `core/shared/tools/definitions.json` (51 tools)
  - Servidor Python carga tools dinámicamente del contrato
  - `AGENTS.md` actualizado con nueva estructura

### Added
- add follow-p1-distance script and gothic cathedral builder
- sistema de aprendizaje de habilidades + avatares + construcciones
- add seguir_a_p1 action and bt_load_follow preset
- Phase 4 integration - heartbeat sync, bt_load_example, docs
- add Behavior Tree engine in Node.js (Phase 3)
- add A* pathfinding and path follower (Phase 2)
- add melee combat system with cone detection (Phase 1)
- Add update_changelog.py script and update CHANGELOG
- Add CHANGELOG.md following Keep a Changelog format
- Add virtual gamepad relay and autonomous chase/evade scripts

### Changed
- separar game-server de mcp-server, gamepad-only movement
- create documentation structure with ADRs and phase tracking
- Initial commit: VoxelQuest base game with MCP server
- add CHANGELOG.md and update with recent commits
- Enhance evade_chase with direct wall breaking and teleport escape

### Fixed
- move EnemyManager.nextEnemyId after class definition
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
